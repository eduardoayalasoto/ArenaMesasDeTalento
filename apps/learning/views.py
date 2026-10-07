"""Vistas de Arena Learn: validar entrada → servicio (learning_flow) → renderizar.

Toda escritura pasa por `apps/core/services/learning_flow.py`; los permisos de lectura
por `apps/core/services/permissions.py`.
"""

import io
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.catalog.models import Area, SeniorityLevel
from apps.core.services import learning_flow as flow
from apps.core.services import permissions

from .forms import (
    CatalogCourseForm,
    CommentForm,
    DecisionForm,
    DirectCourseForm,
    EvidenceUploadForm,
    EvidenceValidationForm,
    HistoricCourseForm,
    PaymentForm,
    ReasonForm,
    ReassignForm,
    RequestForm,
    ReviewForm,
    SettingsForm,
    SingleEvidenceForm,
)
from .models import (
    ApprovalStep,
    CatalogCourse,
    CourseEvidence,
    CourseKind,
    CourseRequest,
    LearningSettings,
    Pillar,
)

User = get_user_model()


def _forbidden(request, mensaje="No tienes acceso a esta sección de Arena Learn."):
    return render(request, "errors/403.html", {"titulo": "Acceso restringido", "mensaje": mensaje}, status=403)


def _error_text(exc: ValidationError) -> str:
    if hasattr(exc, "message_dict"):
        return " ".join(m for msgs in exc.message_dict.values() for m in msgs)
    return " ".join(exc.messages)


def _apply_errors(form, exc: ValidationError):
    if hasattr(exc, "error_dict"):
        for field, errs in exc.message_dict.items():
            form.add_error(field if field in form.fields else None, errs)
    else:
        form.add_error(None, exc.messages)


def _get_request(pk):
    return get_object_or_404(
        CourseRequest.objects.select_related("user", "user__area", "user__level", "catalog_course"), pk=pk,
    )


def _base_ctx(request, active, **extra):
    ctx = {
        "learn_tab": active,
        "can_manage": permissions.can_manage_learning(request.user),
        "can_track": permissions.can_view_learning_tracking(request.user),
        "approvals_count": len(flow.approvals_for(request.user)),
        "is_approver": flow.is_course_approver(request.user),
    }
    ctx.update(extra)
    return ctx


# --- Mis cursos / solicitud ---------------------------------------------------------


@login_required
def my_courses(request):
    reqs = (
        CourseRequest.objects.filter(user=request.user)
        .select_related("catalog_course")
        .order_by("-created_at")
    )
    St = CourseRequest.Status
    groups = [
        ("Acción requerida", [r for r in reqs if r.status in (St.REQUIERE_AJUSTES, St.BORRADOR)]),
        ("En autorización", [r for r in reqs if r.status == St.EN_REVISION]),
        ("En curso", [r for r in reqs if r.status == St.AUTORIZADA]),
        ("Completados", [r for r in reqs if r.status in (St.COMPLETADA, St.VALIDADA)]),
        ("Cerrados sin completar", [r for r in reqs if r.status in (St.RECHAZADA, St.CANCELADA, St.NO_CONCLUIDA)]),
    ]
    return render(request, "learning/my_courses.html", _base_ctx(
        request, "mine", page_title="Arena Learn", groups=[g for g in groups if g[1]],
        pending=flow.pending_closure(request.user), has_any=reqs.exists(),
    ))


def _catalog_from_query(request):
    cid = request.GET.get("catalogo") or request.POST.get("catalogo")
    if not cid:
        return None
    return get_object_or_404(CatalogCourse, pk=cid, is_active=True)


@login_required
def request_start(request):
    """Paso 1 de "Solicitar curso": elegir un curso ya conocido en Arena o uno nuevo."""
    q = request.GET.get("q", "").strip()
    data = flow.requestable_courses(request.user, q)
    return render(request, "learning/request_start.html", _base_ctx(
        request, "mine", page_title="Solicitar curso", q=q, catalog=data["catalog"], known=data["known"],
        pending=flow.pending_closure(request.user),
    ))


def _template_from_query(request):
    """`?desde=<pk>`: curso que alguien en Arena ya tomó con autorización (plantilla)."""
    pk = request.GET.get("desde") or request.POST.get("desde")
    if not pk or not str(pk).isdigit():
        return None
    return CourseRequest.objects.filter(
        pk=pk, status__in=flow.KNOWN_STATUSES, catalog_course__isnull=True,
    ).first()


@login_required
def request_create(request):
    catalog_course = _catalog_from_query(request)
    template_req = None if catalog_course else _template_from_query(request)
    initial = {"currency": "MXN", "kind": "CURSO"}
    if template_req is not None:
        initial.update(flow.template_data_from(template_req))
    form = RequestForm(request.POST or None, catalog_course=catalog_course, initial=initial)
    if request.method == "POST" and form.is_valid():
        submit = request.POST.get("action") == "submit"
        try:
            req = flow.create_request(request.user, form.service_data(), catalog_course=catalog_course, submit=False)
            req.payment_mode = form.cleaned_data.get("payment_mode") or ""
            req.save(update_fields=["payment_mode"])
            if submit:
                flow.submit_request(req, request.user)
                messages.success(request, f"Enviaste tu solicitud: {req.status_display.lower()}.")
            else:
                messages.success(request, "Guardaste tu solicitud como borrador.")
            return redirect("learning:request_detail", pk=req.pk)
        except ValidationError as exc:
            # El borrador ya existe si falló solo el envío: lo llevamos a editar.
            if "req" in locals() and req.pk:
                messages.error(request, _error_text(exc))
                return redirect("learning:request_edit", pk=req.pk)
            _apply_errors(form, exc)
    duplicate = flow.open_request_for(
        request.user, catalog_course,
        template_req.name if template_req else "", template_req.provider if template_req else "",
    ) if (catalog_course or template_req) else None
    return render(request, "learning/request_form.html", _base_ctx(
        request, "mine", page_title="Solicitar curso", form=form, catalog_course=catalog_course,
        template_req=template_req, duplicate=duplicate,
        pending=flow.pending_closure(request.user), editing=None,
    ))


@login_required
def request_edit(request, pk):
    req = _get_request(pk)
    if req.user_id != request.user.pk:
        return _forbidden(request, "Solo quien hizo la solicitud puede editarla.")
    if not req.is_editable:
        messages.info(request, "Esta solicitud ya no se puede editar.")
        return redirect("learning:request_detail", pk=pk)
    form = RequestForm(request.POST or None, catalog_course=req.catalog_course,
                       initial=RequestForm.initial_from(req))
    if request.method == "POST" and form.is_valid():
        submit = request.POST.get("action") == "submit"
        try:
            flow.update_request(req, request.user, form.service_data(), submit=False)
            CourseRequest.objects.filter(pk=req.pk).update(payment_mode=form.cleaned_data.get("payment_mode") or "")
            if submit:
                req = flow.submit_request(req, request.user)
                messages.success(request, f"Enviaste tu solicitud: {req.status_display.lower()}.")
            else:
                messages.success(request, "Guardaste los cambios.")
            return redirect("learning:request_detail", pk=pk)
        except ValidationError as exc:
            _apply_errors(form, exc)
    last_return = req.steps.filter(action=ApprovalStep.Action.REGRESAR).order_by("-created_at").first()
    return render(request, "learning/request_form.html", _base_ctx(
        request, "mine", page_title="Editar solicitud", form=form, catalog_course=req.catalog_course,
        pending=flow.pending_closure(request.user), editing=req, last_return=last_return,
    ))


@login_required
def request_detail(request, pk):
    req = _get_request(pk)
    if not permissions.can_view_course_private(request.user, req):
        if req.is_public:
            return redirect("learning:course_public", pk=pk)
        return _forbidden(request)
    is_owner = req.user_id == request.user.pk
    can_decide = flow.can_decide(request.user, req)
    St = CourseRequest.Status
    ctx = _base_ctx(
        request, "mine" if is_owner else "approvals",
        page_title=req.name, req=req, is_owner=is_owner,
        steps=req.steps.select_related("actor", "assigned_to"),
        evidences=req.evidences.defer("data"),
        review=getattr(req, "review", None),
        can_decide=can_decide,
        approver_ctx=flow.approver_context(req) if (can_decide or request.user.is_admin) else None,
        current_approvers=list(flow.eligible_approvers(req, req.current_stage)) if req.current_stage else [],
        can_cancel=(is_owner and req.status in (St.BORRADOR, St.EN_REVISION, St.REQUIERE_AJUSTES))
        or (request.user.is_admin and req.status in (St.BORRADOR, St.EN_REVISION, St.REQUIERE_AJUSTES, St.AUTORIZADA)),
        can_reassign=request.user.is_admin and req.status == St.EN_REVISION,
        can_pay=(is_owner or request.user.is_admin) and req.status in (St.AUTORIZADA, St.COMPLETADA, St.VALIDADA),
        can_promote=request.user.is_admin and not req.catalog_course_id and req.status in (St.COMPLETADA, St.VALIDADA),
        payment_form=PaymentForm(instance=req),
        reassign_form=ReassignForm(),
        fiscal=LearningSettings.load().fiscal_instructions,
    )
    return render(request, "learning/request_detail.html", ctx)


# --- Decisiones -----------------------------------------------------------------------


@login_required
@require_POST
def request_decide(request, pk):
    req = _get_request(pk)
    form = DecisionForm(request.POST)
    next_url = request.POST.get("next") or reverse("learning:request_detail", args=[pk])
    if not form.is_valid():
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
        return redirect(next_url)
    try:
        req = flow.decide(req, request.user, form.cleaned_data["action"], form.cleaned_data["comment"])
    except PermissionDenied as exc:
        return _forbidden(request, str(exc))
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
        return redirect(next_url)
    label = {"approve": "Aprobaste", "return": "Regresaste", "reject": "Rechazaste"}[form.cleaned_data["action"]]
    messages.success(request, f"{label} la solicitud «{req.name}» de {req.user.full_name}.")
    return redirect(next_url)


@login_required
@require_POST
def request_cancel(request, pk):
    req = _get_request(pk)
    form = CommentForm(request.POST)
    form.is_valid()
    try:
        flow.cancel(req, request.user, form.cleaned_data.get("comment", ""))
    except PermissionDenied as exc:
        return _forbidden(request, str(exc))
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
        return redirect("learning:request_detail", pk=pk)
    messages.success(request, "Cancelaste la solicitud.")
    return redirect("learning:request_detail", pk=pk)


@login_required
@require_POST
def request_reassign(request, pk):
    req = _get_request(pk)
    if not permissions.can_manage_learning(request.user):
        return _forbidden(request, "Solo Talento puede reasignar aprobadores.")
    form = ReassignForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Elige al nuevo aprobador y escribe el motivo.")
        return redirect("learning:request_detail", pk=pk)
    try:
        flow.reassign(req, request.user, form.cleaned_data["approver"], form.cleaned_data["comment"])
    except PermissionDenied as exc:
        return _forbidden(request, str(exc))
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
        return redirect("learning:request_detail", pk=pk)
    messages.success(request, f"Reasignaste la etapa a {form.cleaned_data['approver'].full_name}.")
    return redirect("learning:request_detail", pk=pk)


@login_required
def approvals_inbox(request):
    reqs = flow.approvals_for(request.user)
    # Talento ve todo: además de lo que le toca decidir, todas las solicitudes en revisión.
    others = (
        flow.all_in_review_for_talento(exclude_pks=[r.pk for r in reqs])
        if permissions.can_manage_learning(request.user) else None
    )
    return render(request, "learning/approvals_inbox.html", _base_ctx(
        request, "approvals", page_title="Por aprobar · Arena Learn",
        items=[{"req": r, "ctx": flow.approver_context(r)} for r in reqs],
        others=others,
    ))


# --- Pago ---------------------------------------------------------------------------------


def _payment_block(request, req, error="", saved=False):
    return render(request, "learning/_payment_block.html", {
        "req": req, "payment_form": PaymentForm(instance=req), "saved": saved, "error": error,
        "fiscal": LearningSettings.load().fiscal_instructions,
    })


@login_required
@require_POST
def request_payment(request, pk):
    req = _get_request(pk)
    is_htmx = bool(request.headers.get("HX-Request"))
    form = PaymentForm(request.POST, instance=CourseRequest(pk=req.pk))
    error = ""
    if not form.is_valid():
        error = "Revisa los datos del pago."
    else:
        d = form.cleaned_data
        try:
            req = flow.update_payment(req, request.user, d["payment_mode"], d["payment_status"],
                                      d.get("final_cost"), d.get("receipt_type", ""))
        except PermissionDenied as exc:
            return _forbidden(request, str(exc))
        except ValidationError as exc:
            error = _error_text(exc)
    if is_htmx:
        return _payment_block(request, req, error=error, saved=not error)
    if error:
        messages.error(request, error)
    else:
        messages.success(request, "Registraste el pago.")
    return redirect("learning:request_detail", pk=pk)


@login_required
@require_POST
def request_receipt(request, pk):
    """Sube el comprobante fiscal (privado) de un curso autorizado."""
    req = _get_request(pk)
    form = SingleEvidenceForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Elige el archivo del comprobante.")
        return redirect("learning:request_detail", pk=pk)
    try:
        flow.add_evidence(req, request.user, form.cleaned_data["file"], CourseEvidence.Kind.COMPROBANTE_FISCAL)
    except PermissionDenied as exc:
        return _forbidden(request, str(exc))
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
        return redirect("learning:request_detail", pk=pk)
    messages.success(request, "Subiste tu comprobante fiscal (solo lo ven tú y Talento).")
    return redirect("learning:request_detail", pk=pk)


# --- Cierre ---------------------------------------------------------------------------------


@login_required
def request_complete(request, pk):
    req = _get_request(pk)
    if req.user_id != request.user.pk:
        return _forbidden(request, "Solo el dueño puede cerrar su curso.")
    if req.status != CourseRequest.Status.AUTORIZADA:
        messages.info(request, "Este curso no está en curso; no se puede cerrar.")
        return redirect("learning:request_detail", pk=pk)
    review_form = ReviewForm(request.POST or None, prefix="r")
    files_form = EvidenceUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and review_form.is_valid() and files_form.is_valid():
        try:
            flow.complete(req, request.user, review_form.service_data(), files_form.cleaned_data["files"])
            messages.success(request, "¡Cerraste tu curso! Ya aparece en tu Arena Learn.")
            return redirect("learning:request_detail", pk=pk)
        except ValidationError as exc:
            files_form.add_error(None, exc.messages)
    return render(request, "learning/complete_form.html", _base_ctx(
        request, "mine", page_title=f"Cerrar curso · {req.name}", req=req,
        review_form=review_form, files_form=files_form, reason_form=ReasonForm(),
    ))


@login_required
def review_edit(request, pk):
    req = _get_request(pk)
    review = getattr(req, "review", None)
    if req.user_id != request.user.pk or review is None:
        return _forbidden(request, "Solo el dueño puede editar su reseña.")
    form = ReviewForm(request.POST or None, instance=review, prefix="r")
    if request.method == "POST" and form.is_valid():
        try:
            flow.update_review(req, request.user, form.service_data())
            messages.success(request, "Actualizaste tu reseña.")
            return redirect("learning:request_detail", pk=pk)
        except ValidationError as exc:
            _apply_errors(form, exc)
    return render(request, "learning/review_form.html", _base_ctx(
        request, "mine", page_title="Editar reseña", req=req, review_form=form,
    ))


@login_required
@require_POST
def request_not_completed(request, pk):
    req = _get_request(pk)
    form = ReasonForm(request.POST)
    try:
        flow.mark_not_completed(req, request.user, form.data.get("reason", ""))
    except PermissionDenied as exc:
        return _forbidden(request, str(exc))
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
        return redirect("learning:request_complete", pk=pk)
    messages.success(request, "Marcaste el curso como no concluido. Ya puedes solicitar otro.")
    return redirect("learning:request_detail", pk=pk)


# --- Evidencia --------------------------------------------------------------------------------


@login_required
def evidence_file(request, pk):
    ev = get_object_or_404(CourseEvidence.objects.select_related("request"), pk=pk)
    req = ev.request
    if ev.is_private:
        allowed = req.user_id == request.user.pk or request.user.is_admin
    else:
        allowed = permissions.can_view_course_public(request.user, req)
    if not allowed:
        return _forbidden(request, "No tienes acceso a este archivo.")
    resp = HttpResponse(bytes(ev.data), content_type=ev.mime)
    safe_name = ev.filename.replace('"', "")
    resp["Content-Disposition"] = f'inline; filename="{safe_name}"'
    resp["X-Content-Type-Options"] = "nosniff"
    resp["Cache-Control"] = "private, max-age=3600"
    return resp


@login_required
@require_POST
def evidence_validate(request, pk):
    ev = get_object_or_404(CourseEvidence.objects.select_related("request"), pk=pk)
    form = EvidenceValidationForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Acción inválida.")
        return redirect("learning:request_detail", pk=ev.request_id)
    try:
        flow.validate_evidence(ev, request.user, form.cleaned_data["action"] == "validate",
                               form.cleaned_data.get("comment", ""))
    except PermissionDenied as exc:
        return _forbidden(request, str(exc))
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
        return redirect("learning:request_detail", pk=ev.request_id)
    messages.success(request, "Validaste la evidencia." if form.cleaned_data["action"] == "validate"
                     else "Regresaste la evidencia al colaborador.")
    return redirect(request.POST.get("next") or reverse("learning:request_detail", args=[ev.request_id]))


@login_required
@require_POST
def evidence_replace(request, pk):
    ev = get_object_or_404(CourseEvidence.objects.select_related("request"), pk=pk)
    form = SingleEvidenceForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Elige el archivo nuevo.")
        return redirect("learning:request_detail", pk=ev.request_id)
    try:
        flow.replace_evidence(ev, request.user, form.cleaned_data["file"])
    except PermissionDenied as exc:
        return _forbidden(request, str(exc))
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
        return redirect("learning:request_detail", pk=ev.request_id)
    messages.success(request, "Reemplazaste tu evidencia; Talento la revisará de nuevo.")
    return redirect("learning:request_detail", pk=ev.request_id)


# --- Registro directo / histórico ------------------------------------------------------------


def _direct_view(request, historic: bool):
    catalog_course = _catalog_from_query(request)
    FormCls = HistoricCourseForm if historic else DirectCourseForm
    form = FormCls(request.POST or None, catalog_course=catalog_course,
                   initial={"currency": "MXN", "kind": "CURSO"})
    review_form = ReviewForm(request.POST or None, prefix="r")
    files_form = EvidenceUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid() and review_form.is_valid() and files_form.is_valid():
        person = form.cleaned_data.pop("person") if historic else request.user
        data = dict(form.cleaned_data)
        try:
            req = flow.create_direct(
                person, request.user, data, review_form.service_data(), files_form.cleaned_data["files"],
                origin=CourseRequest.Origin.HISTORICO if historic else CourseRequest.Origin.REGISTRO_DIRECTO,
                catalog_course=catalog_course,
            )
            messages.success(request, "Registraste el curso en Arena Learn.")
            return redirect("learning:request_detail", pk=req.pk)
        except PermissionDenied as exc:
            return _forbidden(request, str(exc))
        except ValidationError as exc:
            _apply_errors(form, exc)
    return render(request, "learning/direct_form.html", _base_ctx(
        request, "mine", page_title="Carga histórica" if historic else "Registrar curso",
        form=form, review_form=review_form, files_form=files_form, catalog_course=catalog_course,
        historic=historic,
    ))


@login_required
def direct_create(request):
    return _direct_view(request, historic=False)


@login_required
def historic_create(request):
    if not permissions.can_manage_learning(request.user):
        return _forbidden(request, "Solo Talento carga cursos históricos.")
    return _direct_view(request, historic=True)


# --- Catálogo -----------------------------------------------------------------------------------


def _filters(request, keys):
    return {k: request.GET.get(k, "").strip() for k in keys if request.GET.get(k, "").strip()}


@login_required
def catalog_list(request):
    f = _filters(request, ("q", "area", "level", "kind", "pillar"))
    show_archived = request.GET.get("archivados") == "1" and request.user.is_admin
    courses = flow.catalog_queryset(f, include_archived=show_archived)
    if show_archived:
        courses = courses.filter(is_active=False)
    return render(request, "learning/catalog_list.html", _base_ctx(
        request, "catalog", page_title="Catálogo · Arena Learn", courses=courses, f=f,
        areas=Area.objects.filter(is_active=True), levels=SeniorityLevel.objects.all(),
        kinds=CourseKind.choices, pillars=[p for p in Pillar.choices if p[0]], show_archived=show_archived,
    ))


@login_required
def catalog_detail(request, pk):
    course = get_object_or_404(flow.catalog_queryset(include_archived=True), pk=pk)
    if not course.is_active and not request.user.is_admin:
        raise Http404
    return render(request, "learning/catalog_detail.html", _base_ctx(
        request, "catalog", page_title=course.name, course=course, reviews=flow.catalog_reviews(course),
    ))


@login_required
def catalog_edit(request, pk=None):
    if not permissions.can_manage_learning(request.user):
        return _forbidden(request, "Solo Talento administra el catálogo.")
    course = get_object_or_404(CatalogCourse, pk=pk) if pk else None
    form = CatalogCourseForm(request.POST or None, instance=course)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        if course is None:
            obj.created_by = request.user
        obj.save()
        form.save_m2m()
        messages.success(request, "Guardaste el curso del catálogo.")
        return redirect("learning:catalog_detail", pk=obj.pk)
    return render(request, "learning/catalog_form.html", _base_ctx(
        request, "catalog", page_title="Editar curso" if course else "Nuevo curso", form=form, course=course,
    ))


@login_required
@require_POST
def catalog_archive(request, pk):
    if not permissions.can_manage_learning(request.user):
        return _forbidden(request, "Solo Talento administra el catálogo.")
    course = get_object_or_404(CatalogCourse, pk=pk)
    course.is_active = not course.is_active
    course.save(update_fields=["is_active"])
    messages.success(request, "Archivaste el curso." if not course.is_active else "Reactivaste el curso.")
    return redirect("learning:catalog_detail", pk=pk)


@login_required
@require_POST
def catalog_promote(request, pk):
    req = _get_request(pk)
    try:
        course = flow.promote_to_catalog(req, request.user)
    except PermissionDenied as exc:
        return _forbidden(request, str(exc))
    except ValidationError as exc:
        messages.error(request, _error_text(exc))
        return redirect("learning:request_detail", pk=pk)
    messages.success(request, "El curso ya forma parte del catálogo sugerido.")
    return redirect("learning:catalog_edit", pk=course.pk)


# --- Personas y perfil público (excepción acotada a RN-14) ------------------------------------------


@login_required
def people_list(request):
    St = CourseRequest.Status
    q = request.GET.get("q", "").strip()
    area = request.GET.get("area", "").strip()
    people = (
        User.objects.filter(is_active=True, deleted_at__isnull=True)
        .select_related("area", "level")
        .annotate(courses_done=Count(
            "course_requests", filter=Q(course_requests__status__in=(St.COMPLETADA, St.VALIDADA)),
        ))
        .defer("photo_data", "photo_thumb_data", "photo")
        .order_by("full_name")
    )
    if q:
        people = people.filter(Q(full_name__icontains=q) | Q(email__icontains=q))
    if area:
        people = people.filter(area_id=area)
    page = Paginator(people, 30).get_page(request.GET.get("page"))
    return render(request, "learning/people_list.html", _base_ctx(
        request, "people", page_title="Personas · Arena Learn", page=page, q=q, area=area,
        areas=Area.objects.filter(is_active=True),
    ))


@login_required
def person_profile(request, pk):
    person = get_object_or_404(User.objects.select_related("area", "level"), pk=pk)
    if not permissions.can_view_learning_profile(request.user, person):
        return _forbidden(request)
    courses = [flow.public_course_context(r) for r in flow.learning_public_requests(person)]
    St = CourseRequest.Status
    return render(request, "learning/person_profile.html", _base_ctx(
        request, "people", page_title=f"{person.full_name} · Arena Learn", person=person,
        completed=[c for c in courses if c["status"] in (St.COMPLETADA, St.VALIDADA)],
        in_progress=[c for c in courses if c["status"] == St.AUTORIZADA],
        is_me=person.pk == request.user.pk,
    ))


@login_required
def course_public(request, pk):
    req = _get_request(pk)
    if not permissions.can_view_course_public(request.user, req):
        raise Http404
    return render(request, "learning/course_public.html", _base_ctx(
        request, "people", page_title=req.name, course=flow.public_course_context(req),
        can_see_private=permissions.can_view_course_private(request.user, req),
    ))


# --- Seguimiento (US7) ------------------------------------------------------------------------------


def _tracking_filters(request):
    f = _filters(request, ("area", "persona", "anio", "estado"))
    out = {}
    if f.get("area"):
        out["area"] = f["area"]
    if f.get("persona"):
        out["person"] = f["persona"]
    if f.get("anio", "").isdigit():
        out["year"] = int(f["anio"])
    if f.get("estado"):
        out["status"] = f["estado"]
    return f, out


@login_required
def tracking(request):
    if not permissions.can_view_learning_tracking(request.user):
        return _forbidden(request, "El seguimiento es para Talento y Dirección.")
    raw, filters = _tracking_filters(request)
    data = flow.dashboard_rows(filters)
    return render(request, "learning/tracking.html", _base_ctx(
        request, "tracking", page_title="Seguimiento · Arena Learn", data=data, f=raw,
        areas=Area.objects.filter(is_active=True),
        people=User.objects.filter(course_requests__isnull=False).distinct().order_by("full_name"),
        statuses=[s for s in CourseRequest.Status.choices if s[0] != CourseRequest.Status.BORRADOR],
        years=range(datetime.now().year, datetime.now().year - 4, -1),
        export_query=request.GET.urlencode(),
    ))


@login_required
def tracking_export(request):
    if not permissions.can_view_learning_tracking(request.user):
        return _forbidden(request, "El seguimiento es para Talento y Dirección.")
    from openpyxl import Workbook
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    _, filters = _tracking_filters(request)
    wb = Workbook()
    ws = wb.active
    ws.title = "Arena Learn"
    ws.append(flow.EXPORT_HEADERS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in flow.export_rows(filters):
        ws.append(row)
    for idx, header in enumerate(flow.EXPORT_HEADERS, start=1):
        ws.column_dimensions[get_column_letter(idx)].width = max(12, len(header) + 4)
    for col in ("I", "K"):
        for cell in ws[col][1:]:
            cell.number_format = "#,##0"
    for col in ("N", "O", "P"):
        for cell in ws[col][1:]:
            cell.number_format = "dd/mm/yyyy"
    buf = io.BytesIO()
    wb.save(buf)
    resp = HttpResponse(
        buf.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    resp["Content-Disposition"] = 'attachment; filename="arena_learn_seguimiento.xlsx"'
    return resp


@login_required
def settings_edit(request):
    if not permissions.can_manage_learning(request.user):
        return _forbidden(request, "Solo Talento edita la configuración de Arena Learn.")
    obj = LearningSettings.load()
    form = SettingsForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        s = form.save(commit=False)
        s.updated_by = request.user
        s.save()
        messages.success(request, "Guardaste las instrucciones fiscales.")
        return redirect("learning:settings_edit")
    return render(request, "learning/settings_form.html", _base_ctx(
        request, "tracking", page_title="Configuración · Arena Learn", form=form,
    ))
