"""Vistas del flujo de Ownership (colaborador) y validación (líder)."""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from decimal import Decimal, InvalidOperation

from apps.catalog.models import EvaluationPeriod, Project
from apps.core.services import (
    final_flow,
    ownership_flow,
    permissions,
    scoring,
    value_delivery_flow,
)
from apps.questionnaires.models import Question

from .models import (
    ArenaImpactScore,
    OwnershipAnswer,
    OwnershipEvaluation,
    ValueDeliveryEvaluation,
)


def _open_period():
    return EvaluationPeriod.objects.filter(status=EvaluationPeriod.Status.ABIERTO).first()


def _progress(evaluation):
    """(respondidas, total, promedio_en_vivo)."""
    total = Question.objects.filter(
        section__template=evaluation.template, qtype=Question.Type.SCALE
    ).count()
    answered = evaluation.answers.filter(
        Q(value__isnull=False) | Q(is_na=True)
    ).count()
    return answered, total, scoring.ownership_evaluation_score(evaluation)


@login_required
def ownership_list(request):
    """Mis evaluaciones de Ownership: una tarjeta por proyecto del periodo abierto."""
    period = _open_period()
    cards = []
    if period:
        memberships = request.user.memberships.select_related("project").filter(
            project__is_active=True
        )
        evals = {
            e.project_id: e
            for e in OwnershipEvaluation.objects.filter(user=request.user, period=period)
        }
        for m in memberships:
            ev = evals.get(m.project_id)
            answered = total = 0
            if ev:
                answered, total, _ = _progress(ev)
            cards.append({"project": m.project, "evaluation": ev,
                          "answered": answered, "total": total})
    return render(request, "evaluations/ownership_list.html", {
        "page_title": "Mis evaluaciones",
        "period": period,
        "cards": cards,
    })


@login_required
def ownership_start(request, project_id):
    """Antes de iniciar, el evaluado elige a su evaluador (cualquiera de Arena)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    period = _open_period()
    if not period:
        messages.error(request, "No hay un periodo abierto en este momento.")
        return redirect("evaluations:ownership_list")
    membership = get_object_or_404(
        request.user.memberships.select_related("project"), project_id=project_id
    )

    # Si ya existe, no se vuelve a elegir evaluador.
    existing = OwnershipEvaluation.objects.filter(
        user=request.user, project=membership.project, period=period
    ).first()
    if existing:
        return redirect("evaluations:ownership_edit", pk=existing.pk)

    if request.method == "POST":
        evaluator = User.objects.filter(
            pk=request.POST.get("evaluator"), is_active=True
        ).exclude(pk=request.user.pk).first()
        if not evaluator:
            messages.error(request, "Elige un evaluador válido para continuar.")
        else:
            evaluation, error = ownership_flow.get_or_create_ownership_evaluation(
                request.user, membership.project, period, evaluator=evaluator
            )
            if error:
                messages.error(request, error)
                return redirect("evaluations:ownership_list")
            messages.success(request, f"Asignaste a {evaluator.full_name} como tu evaluador.")
            return redirect("evaluations:ownership_edit", pk=evaluation.pk)

    evaluators = (
        User.objects.filter(is_active=True).exclude(pk=request.user.pk).order_by("full_name")
    )
    return render(request, "evaluations/ownership_start.html", {
        "page_title": "Elegir evaluador",
        "project": membership.project,
        "evaluators": evaluators,
    })


def _can_edit_answers(user, evaluation):
    """Respuestas: editables por el evaluado o por el líder/admin, mientras no esté cerrada."""
    if evaluation.is_submitted:
        return False
    return evaluation.user_id == user.pk or permissions.can_validate_ownership(user, evaluation)


def _can_complement(user, evaluation):
    """Fortalezas/Oportunidades/Comentarios y cierre: solo líder/admin, mientras no esté cerrada."""
    return not evaluation.is_submitted and permissions.can_validate_ownership(user, evaluation)


def _render_ownership(request, pk, *, editing):
    evaluation = get_object_or_404(
        OwnershipEvaluation.objects.select_related("template", "project", "user"), pk=pk
    )
    if not permissions.can_view_evaluation(request.user, evaluation):
        return render(request, "errors/403.html", {
            "titulo": "No puedes ver esta evaluación",
            "mensaje": "Esta evaluación pertenece a otra persona o área.",
        }, status=403)

    can_edit_answers = _can_edit_answers(request.user, evaluation)
    can_complement = _can_complement(request.user, evaluation)
    is_owner = evaluation.user_id == request.user.pk
    can_change_evaluator = editing and is_owner and not evaluation.is_submitted
    evaluators = None
    if can_change_evaluator:
        from django.contrib.auth import get_user_model
        evaluators = (
            get_user_model().objects.filter(is_active=True)
            .exclude(pk=request.user.pk).order_by("full_name")
        )
    # En modo edición, los controles se habilitan según el permiso; en Ver, todo es lectura.
    answers = {a.question_id: a for a in evaluation.answers.all()}
    sections = evaluation.template.sections.prefetch_related(
        Prefetch("questions", queryset=Question.objects.order_by("order"))
    ).order_by("order")
    scale = list(evaluation.template.scale_options.order_by("order"))
    answered, total, average = _progress(evaluation)

    return render(request, "evaluations/ownership_fill.html", {
        "page_title": evaluation.project.name,
        "evaluation": evaluation,
        "sections": sections,
        "answers": answers,
        "scale": scale,
        "answered": answered,
        "total": total,
        "average": average,
        "is_owner": is_owner,
        "editing": editing,
        "answers_editable": editing and can_edit_answers,
        "can_complement": editing and can_complement,
        "can_change_evaluator": can_change_evaluator,
        "evaluators": evaluators,
        # El usuario puede alternar a edición si tiene algún permiso de edición.
        "can_edit_link": (can_edit_answers or can_complement),
    })


@login_required
def ownership_view(request, pk):
    """Vista de solo lectura de una evaluación."""
    return _render_ownership(request, pk, editing=False)


@login_required
def ownership_edit(request, pk):
    """Vista de edición: respuestas (evaluado o líder) y complemento + cierre (líder)."""
    return _render_ownership(request, pk, editing=True)


@login_required
@require_POST
def ownership_set_evaluator(request, pk):
    """El evaluado cambia a su evaluador, solo mientras la evaluación esté abierta."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    evaluation = get_object_or_404(OwnershipEvaluation, pk=pk)
    if evaluation.user_id != request.user.pk or evaluation.is_submitted:
        messages.error(request, "Solo puedes cambiar al evaluador antes de que se cierre la evaluación.")
        return redirect("evaluations:ownership_edit", pk=pk)

    evaluator = User.objects.filter(
        pk=request.POST.get("evaluator"), is_active=True
    ).exclude(pk=request.user.pk).first()
    if not evaluator:
        messages.error(request, "Elige un evaluador válido.")
    else:
        evaluation.validator = evaluator
        evaluation.save(update_fields=["validator", "updated_at"])
        messages.success(request, f"Tu evaluador ahora es {evaluator.full_name}.")
    return redirect("evaluations:ownership_edit", pk=pk)


@login_required
@require_POST
def ownership_autosave(request, pk):
    """Guarda una respuesta (JSON). Permitido al evaluado o al líder mientras esté abierta."""
    evaluation = get_object_or_404(OwnershipEvaluation, pk=pk)
    if not _can_edit_answers(request.user, evaluation):
        return JsonResponse({"ok": False, "error": "No editable."}, status=403)

    payload = json.loads(request.body or "{}")
    question = get_object_or_404(
        Question, pk=payload.get("question"), section__template=evaluation.template
    )
    is_na = bool(payload.get("is_na"))
    value = None if is_na else payload.get("value")

    OwnershipAnswer.objects.update_or_create(
        evaluation=evaluation, question=question,
        defaults={"value": value, "is_na": is_na},
    )
    answered, total, average = _progress(evaluation)
    return JsonResponse({
        "ok": True, "answered": answered, "total": total,
        "average": str(average) if average is not None else None,
    })


@login_required
@require_POST
def ownership_save(request, pk):
    """Guardar (sigue abierta) o Guardar y cerrar (bloquea para todos). Solo líder/admin."""
    evaluation = get_object_or_404(OwnershipEvaluation, pk=pk)
    if not _can_complement(request.user, evaluation):
        messages.error(request, "Solo el líder o Talento pueden completar y cerrar esta evaluación.")
        return redirect("evaluations:ownership_view", pk=pk)

    evaluation.strengths = request.POST.get("strengths", "").strip()
    evaluation.opportunities = request.POST.get("opportunities", "").strip()
    evaluation.comments = request.POST.get("comments", "").strip()
    evaluation.save(update_fields=["strengths", "opportunities", "comments", "updated_at"])

    if request.POST.get("action") == "save_close":
        errors = ownership_flow.close_ownership_evaluation(evaluation)
        if errors:
            for e in errors:
                messages.error(request, e)
            return redirect("evaluations:ownership_edit", pk=pk)
        _send_close_email(evaluation)
        messages.success(
            request,
            f"Cerraste la evaluación de {evaluation.user.full_name} "
            f"({evaluation.project.name}). Calificación: {evaluation.score}.",
        )
        return redirect("evaluations:ownership_validation")

    messages.success(request, "Guardaste los cambios. La evaluación sigue abierta.")
    return redirect("evaluations:ownership_edit", pk=pk)


def _send_close_email(evaluation):
    try:
        send_mail(
            subject=f"Evaluación de Ownership cerrada — {evaluation.project.name}",
            message=(
                f"Hola {evaluation.user.get_short_name()},\n\n"
                f"Tu evaluación de Ownership del proyecto «{evaluation.project.name}» "
                f"quedó cerrada con calificación {evaluation.score}.\n\n"
                f"Ya no puede modificarse. Si necesitas un cambio, contacta a Talento y Cultura.\n\n"
                f"— Evaluaciones Arena"
            ),
            from_email=None,
            recipient_list=[evaluation.user.email],
            fail_silently=True,
        )
    except Exception:  # noqa: BLE001
        pass


# --- Validación del líder --------------------------------------------------

@login_required
def ownership_validation(request):
    """Cola de evaluaciones donde el usuario fue elegido como evaluador."""
    period = _open_period()
    evals = (
        OwnershipEvaluation.objects.filter(validator=request.user, period=period)
        .select_related("user", "project")
        .order_by("project__name", "user__full_name")
        if period else OwnershipEvaluation.objects.none()
    )
    return render(request, "evaluations/ownership_validation.html", {
        "page_title": "Validación de Ownership",
        "evaluations": evals,
    })


# --- Entrega de Valor (líder) ---------------------------------------------

def _validate_scale(raw):
    """Devuelve un entero 1–4 o None (N/A / vacío)."""
    if raw in (None, "", "na", "NA"):
        return None
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return None
    return v if 1 <= v <= 4 else None


@login_required
def value_delivery_list(request):
    """Proyectos que lidera el usuario, con el estado de su Entrega de Valor."""
    period = _open_period()
    led = permissions.projects_led_by(request.user)
    rows = []
    if period:
        existing = {vd.project_id: vd for vd in ValueDeliveryEvaluation.objects.filter(
            project__in=led, period=period)}
        for project in led:
            rows.append({"project": project, "vd": existing.get(project.id)})
    return render(request, "evaluations/value_delivery_list.html", {
        "page_title": "Entrega de Valor",
        "rows": rows,
        "period": period,
    })


@login_required
def value_delivery_capture(request, project_id):
    """Captura de los 3 criterios de Entrega de Valor por el líder del proyecto."""
    period = _open_period()
    project = get_object_or_404(Project, pk=project_id)
    if not permissions.can_capture_value_delivery(request.user, project):
        return render(request, "errors/403.html", {
            "titulo": "No puedes capturar esta Entrega de Valor",
            "mensaje": "Solo el líder del proyecto o Talento pueden capturarla.",
        }, status=403)

    vd = value_delivery_flow.get_or_create_vd(project, period, evaluator=request.user)

    if request.method == "POST" and vd.status != ValueDeliveryEvaluation.Status.VALIDADA:
        value_delivery_flow.save_vd_criteria(
            vd,
            client_satisfaction=_validate_scale(request.POST.get("client_satisfaction")),
            deliverables=_validate_scale(request.POST.get("deliverables")),
            time_value=_validate_scale(request.POST.get("time_value")),
        )
        errors = value_delivery_flow.submit_vd_for_validation(vd)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            messages.success(request, "Enviaste la Entrega de Valor a validación del director.")
            return redirect("evaluations:value_delivery_list")

    members = project.memberships.select_related("user").count()
    return render(request, "evaluations/value_delivery_capture.html", {
        "page_title": "Entrega de Valor",
        "project": project,
        "vd": vd,
        "members_count": members,
        "scale_values": [1, 2, 3, 4],
    })


# --- Entrega de Valor (director) ------------------------------------------

@login_required
def value_delivery_review(request):
    """Cola del director: validar o rechazar las Entregas de Valor en validación."""
    if not permissions.can_validate_value_delivery(request.user):
        return render(request, "errors/403.html", {
            "titulo": "Solo el Director valida la Entrega de Valor",
            "mensaje": "Esta cola es exclusiva del Director del área.",
        }, status=403)

    period = _open_period()
    if request.method == "POST":
        vd = get_object_or_404(ValueDeliveryEvaluation, pk=request.POST.get("vd"))
        action = request.POST.get("action")
        if action == "validate":
            value_delivery_flow.validate_vd(vd, request.user)
            messages.success(request, f"Validaste la Entrega de Valor de {vd.project.name}.")
        elif action == "reject":
            value_delivery_flow.reject_vd(vd, request.POST.get("comment", "").strip())
            messages.info(request, f"Regresaste a borrador la Entrega de Valor de {vd.project.name}.")
        return redirect("evaluations:value_delivery_review")

    queue = ValueDeliveryEvaluation.objects.filter(
        period=period, status=ValueDeliveryEvaluation.Status.EN_VALIDACION
    ).select_related("project", "evaluator")
    return render(request, "evaluations/value_delivery_review.html", {
        "page_title": "Validar Entrega de Valor",
        "queue": queue,
    })


# --- Impacto Arena (Talento) ----------------------------------------------

@login_required
def arena_impact(request):
    """Captura masiva del Impacto Arena por periodo (solo Talento/admin)."""
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Captura reservada a Talento",
            "mensaje": "Solo Talento y Cultura captura el Impacto Arena.",
        }, status=403)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    period = _open_period()

    if request.method == "POST" and period:
        existing = {a.user_id: a for a in ArenaImpactScore.objects.filter(period=period)}
        affected = set()
        for key, raw in request.POST.items():
            if not key.startswith("score-"):
                continue
            user_id = int(key.removeprefix("score-"))
            score = _parse_decimal(raw)
            notes = request.POST.get(f"notes-{user_id}", "").strip()
            if score is None and not notes:
                continue
            ArenaImpactScore.objects.update_or_create(
                user_id=user_id, period=period,
                defaults={"score": score, "notes": notes, "captured_by": request.user},
            )
            affected.add(user_id)
        for user_id in affected:
            final_flow.recompute_final_score(User.objects.get(pk=user_id), period)
        messages.success(request, f"Guardaste el Impacto Arena de {len(affected)} persona(s).")
        return redirect("evaluations:arena_impact")

    rows = []
    if period:
        scores = {a.user_id: a for a in ArenaImpactScore.objects.filter(period=period)}
        for user in User.objects.filter(is_active=True, role="COLABORADOR").order_by("full_name"):
            rows.append({"user": user, "impact": scores.get(user.id)})
    return render(request, "evaluations/arena_impact.html", {
        "page_title": "Impacto Arena",
        "rows": rows,
        "period": period,
    })


def _parse_decimal(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        v = Decimal(raw)
    except (InvalidOperation, TypeError):
        return None
    return v if Decimal("1") <= v <= Decimal("4") else None
