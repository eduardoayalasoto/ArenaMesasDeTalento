"""Vistas del flujo de Ownership (colaborador) y validación (evaluadores)."""

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
    OwnershipEvaluator,
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
    """Para Leads: una tarjeta transversal. Para el resto: una tarjeta por proyecto."""
    period = _open_period()

    if request.user.is_lead:
        lead_eval = None
        answered = total = 0
        lead_projects = []
        if period:
            lead_eval = OwnershipEvaluation.objects.filter(
                user=request.user, project__isnull=True, period=period
            ).first()
            if lead_eval:
                answered, total, _ = _progress(lead_eval)
            lead_projects = list(
                request.user.memberships.select_related("project")
                .filter(project__is_active=True).order_by("project__name")
            )
        return render(request, "evaluations/ownership_list.html", {
            "page_title": "Mis evaluaciones",
            "period": period,
            "is_lead": True,
            "lead_eval": lead_eval,
            "lead_projects": lead_projects,
            "answered": answered,
            "total": total,
        })

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
        "is_lead": False,
        "cards": cards,
    })


@login_required
def ownership_start(request, project_id):
    """Antes de iniciar, el evaluado elige su evaluador principal y opcionalmente secundarios."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    period = _open_period()
    if not period:
        messages.error(request, "No hay un periodo abierto en este momento.")
        return redirect("evaluations:ownership_list")
    membership = get_object_or_404(
        request.user.memberships.select_related("project"), project_id=project_id
    )

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
            messages.error(request, "Elige un evaluador principal válido para continuar.")
        else:
            evaluation, error = ownership_flow.get_or_create_ownership_evaluation(
                request.user, period, project=membership.project, evaluator=evaluator
            )
            if error:
                messages.error(request, error)
                return redirect("evaluations:ownership_list")

            secondary_ids = request.POST.getlist("secondary_evaluators")
            for sid in secondary_ids:
                secondary = User.objects.filter(
                    pk=sid, is_active=True
                ).exclude(pk=request.user.pk).exclude(pk=evaluator.pk).first()
                if secondary:
                    ownership_flow.add_evaluator(evaluation, secondary, is_primary=False)

            messages.success(request, f"Asignaste a {evaluator.full_name} como evaluador principal.")
            return redirect("evaluations:ownership_edit", pk=evaluation.pk)

    evaluators = (
        User.objects.filter(is_active=True).exclude(pk=request.user.pk).order_by("full_name")
    )
    return render(request, "evaluations/ownership_start.html", {
        "page_title": "Elegir evaluador",
        "project": membership.project,
        "evaluators": evaluators,
    })


@login_required
def ownership_lead_start(request):
    """Lead elige su evaluador para la evaluación unificada (sin proyecto específico)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if not request.user.is_lead:
        messages.error(request, "Esta pantalla es solo para colaboradores con nivel Lead.")
        return redirect("evaluations:ownership_list")

    period = _open_period()
    if not period:
        messages.error(request, "No hay un periodo abierto en este momento.")
        return redirect("evaluations:ownership_list")

    existing = OwnershipEvaluation.objects.filter(
        user=request.user, project__isnull=True, period=period
    ).first()
    if existing:
        return redirect("evaluations:ownership_edit", pk=existing.pk)

    if request.method == "POST":
        evaluator = User.objects.filter(
            pk=request.POST.get("evaluator"), is_active=True
        ).exclude(pk=request.user.pk).first()
        if not evaluator:
            messages.error(request, "Elige un evaluador principal válido para continuar.")
        else:
            evaluation, error = ownership_flow.get_or_create_ownership_evaluation(
                request.user, period, project=None, evaluator=evaluator
            )
            if error:
                messages.error(request, error)
                return redirect("evaluations:ownership_list")

            secondary_ids = request.POST.getlist("secondary_evaluators")
            for sid in secondary_ids:
                secondary = User.objects.filter(
                    pk=sid, is_active=True
                ).exclude(pk=request.user.pk).exclude(pk=evaluator.pk).first()
                if secondary:
                    ownership_flow.add_evaluator(evaluation, secondary, is_primary=False)

            messages.success(request, f"Asignaste a {evaluator.full_name} como evaluador principal.")
            return redirect("evaluations:ownership_edit", pk=evaluation.pk)

    evaluators = (
        User.objects.filter(is_active=True).exclude(pk=request.user.pk).order_by("full_name")
    )
    return render(request, "evaluations/ownership_start.html", {
        "page_title": "Elegir evaluador",
        "project": None,
        "evaluators": evaluators,
    })


def _can_edit_answers(user, evaluation):
    """Respuestas: editables por el evaluado o por cualquier evaluador/admin, mientras no esté cerrada."""
    if evaluation.is_submitted:
        return False
    return evaluation.user_id == user.pk or permissions.can_validate_ownership(user, evaluation)


def _can_complement(user, evaluation):
    """Fortalezas/Oportunidades/Comentarios y cierre: cualquier evaluador/admin, mientras no esté cerrada."""
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

    if ownership_flow.sync_evaluation_template(evaluation):
        messages.info(
            request,
            "Tu área o nivel cambiaron; tu cuestionario se actualizó al correspondiente. "
            "Las respuestas anteriores fueron eliminadas.",
        )
        return redirect(request.path)

    can_edit_answers = _can_edit_answers(request.user, evaluation)
    can_complement = _can_complement(request.user, evaluation)
    is_owner = evaluation.user_id == request.user.pk
    can_manage_evaluators = editing and is_owner and not evaluation.is_submitted

    all_users = None
    if can_manage_evaluators:
        from django.contrib.auth import get_user_model
        all_users = (
            get_user_model().objects.filter(is_active=True)
            .exclude(pk=request.user.pk).order_by("full_name")
        )

    ev_records = (
        evaluation.evaluators.select_related("user")
        .order_by("-is_primary", "added_at")
    )

    answers = {a.question_id: a for a in evaluation.answers.all()}
    sections = evaluation.template.sections.prefetch_related(
        Prefetch("questions", queryset=Question.objects.order_by("order"))
    ).order_by("order")
    scale = list(evaluation.template.scale_options.order_by("order"))
    answered, total, average = _progress(evaluation)

    lead_projects = None
    if evaluation.project is None:
        lead_projects = list(
            evaluation.user.memberships.select_related("project")
            .filter(project__is_active=True).order_by("project__name")
        )

    page_title = evaluation.project.name if evaluation.project else "Todos mis proyectos"

    return render(request, "evaluations/ownership_fill.html", {
        "page_title": page_title,
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
        "can_manage_evaluators": can_manage_evaluators,
        "all_users": all_users,
        "ev_records": ev_records,
        "can_edit_link": (can_edit_answers or can_complement),
        "can_reopen": evaluation.is_submitted and request.user.is_admin,
        "can_reset": request.user.is_admin,
        "lead_projects": lead_projects,
    })


@login_required
def ownership_view(request, pk):
    return _render_ownership(request, pk, editing=False)


@login_required
def ownership_edit(request, pk):
    return _render_ownership(request, pk, editing=True)


@login_required
@require_POST
def ownership_set_evaluator(request, pk):
    """El evaluado cambia al evaluador principal, solo mientras la evaluación esté abierta."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    evaluation = get_object_or_404(OwnershipEvaluation, pk=pk)
    if evaluation.user_id != request.user.pk or evaluation.is_submitted:
        messages.error(request, "Solo puedes cambiar al evaluador principal antes de que se cierre la evaluación.")
        return redirect("evaluations:ownership_edit", pk=pk)

    new_primary = User.objects.filter(
        pk=request.POST.get("evaluator"), is_active=True
    ).exclude(pk=request.user.pk).first()
    if not new_primary:
        messages.error(request, "Elige un evaluador principal válido.")
    else:
        ownership_flow.set_primary_evaluator(evaluation, new_primary)
        messages.success(request, f"El evaluador principal ahora es {new_primary.full_name}.")
    return redirect("evaluations:ownership_edit", pk=pk)


@login_required
@require_POST
def ownership_add_evaluator(request, pk):
    """El evaluado agrega un evaluador secundario mientras la evaluación esté abierta."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    evaluation = get_object_or_404(OwnershipEvaluation, pk=pk)
    if evaluation.user_id != request.user.pk or evaluation.is_submitted:
        messages.error(request, "Solo puedes gestionar los evaluadores antes de que se cierre la evaluación.")
        return redirect("evaluations:ownership_edit", pk=pk)

    new_user = User.objects.filter(
        pk=request.POST.get("evaluator"), is_active=True
    ).exclude(pk=request.user.pk).first()
    if not new_user:
        messages.error(request, "Elige una persona válida.")
    elif evaluation.evaluators.filter(user=new_user).exists():
        messages.info(request, f"{new_user.full_name} ya es evaluador de esta evaluación.")
    else:
        ownership_flow.add_evaluator(evaluation, new_user, is_primary=False)
        messages.success(request, f"Agregaste a {new_user.full_name} como evaluador secundario.")
    return redirect("evaluations:ownership_edit", pk=pk)


@login_required
@require_POST
def ownership_remove_evaluator(request, pk, user_pk):
    """El evaluado elimina un evaluador secundario mientras la evaluación esté abierta."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    evaluation = get_object_or_404(OwnershipEvaluation, pk=pk)
    if evaluation.user_id != request.user.pk or evaluation.is_submitted:
        messages.error(request, "Solo puedes gestionar los evaluadores antes de que se cierre la evaluación.")
        return redirect("evaluations:ownership_edit", pk=pk)

    target = get_object_or_404(User, pk=user_pk)
    ownership_flow.remove_evaluator(evaluation, target)
    messages.success(request, f"Quitaste a {target.full_name} como evaluador secundario.")
    return redirect("evaluations:ownership_edit", pk=pk)


@login_required
@require_POST
def ownership_autosave(request, pk):
    """Guarda una respuesta (JSON). Permitido al evaluado o a cualquier evaluador mientras esté abierta."""
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
    """Guardar (sigue abierta) o Guardar y cerrar. Cualquier evaluador/admin."""
    evaluation = get_object_or_404(OwnershipEvaluation, pk=pk)
    if not _can_complement(request.user, evaluation):
        messages.error(request, "Solo los evaluadores o Talento pueden completar y cerrar esta evaluación.")
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
        project_label = evaluation.project.name if evaluation.project else "todos sus proyectos"
        messages.success(
            request,
            f"Cerraste la evaluación de {evaluation.user.full_name} "
            f"({project_label}). Calificación: {evaluation.score}.",
        )
        return redirect("evaluations:ownership_validation")

    messages.success(request, "Guardaste los cambios. La evaluación sigue abierta.")
    return redirect("evaluations:ownership_edit", pk=pk)


@login_required
@require_POST
def ownership_reopen(request, pk):
    """Reapertura de una evaluación cerrada (ENVIADA → BORRADOR). Solo Talento/admin (RN-06)."""
    evaluation = get_object_or_404(OwnershipEvaluation, pk=pk)
    if not request.user.is_admin:
        messages.error(request, "Solo Talento y Cultura puede reabrir una evaluación cerrada.")
        return redirect("evaluations:ownership_view", pk=pk)
    if not evaluation.is_submitted:
        messages.info(request, "Esta evaluación ya está abierta.")
        return redirect("evaluations:ownership_edit", pk=pk)

    ownership_flow.reopen_ownership_evaluation(evaluation)
    project_label = evaluation.project.name if evaluation.project else "todos sus proyectos"
    messages.success(
        request,
        f"Reabriste la evaluación de {evaluation.user.full_name} "
        f"({project_label}). Ahora puede editarse de nuevo.",
    )
    return redirect("evaluations:ownership_edit", pk=pk)


@login_required
@require_POST
def ownership_reset_user(request, user_pk):
    """Reinicia TODAS las evaluaciones de Ownership de un usuario en el periodo abierto. Solo Talento/admin."""
    from django.contrib.auth import get_user_model
    from django.http import HttpResponse
    User = get_user_model()

    if not request.user.is_admin:
        return HttpResponse("No autorizado.", status=403)

    target = get_object_or_404(User, pk=user_pk)
    period = _open_period()
    if not period:
        return HttpResponse("No hay periodo abierto.", status=400)

    evals = list(OwnershipEvaluation.objects.filter(user=target, period=period))
    for ev in evals:
        ownership_flow.reset_ownership_evaluation(ev)

    if request.headers.get("HX-Request"):
        label = f"{len(evals)} reiniciada{'s' if len(evals) != 1 else ''}" if evals else "sin evaluaciones"
        return HttpResponse(
            f'<span class="text-emerald-600 text-xs font-medium flex items-center gap-1">'
            f'<i data-lucide="check" class="w-3.5 h-3.5"></i>{label}</span>'
        )

    messages.success(request, f"Reiniciaste las evaluaciones de {target.full_name}. Puede empezar desde cero.")
    return redirect("accounts:user_admin")


@login_required
@require_POST
def ownership_reset(request, pk):
    """Reinicio completo de una evaluación (cualquier estado → eliminada). Solo Talento/admin."""
    evaluation = get_object_or_404(OwnershipEvaluation, pk=pk)
    if not request.user.is_admin:
        messages.error(request, "Solo Talento y Cultura puede reiniciar una evaluación.")
        return redirect("evaluations:ownership_view", pk=pk)

    user_name = evaluation.user.full_name
    project_label = evaluation.project.name if evaluation.project else "todos sus proyectos"
    ownership_flow.reset_ownership_evaluation(evaluation)
    messages.success(
        request,
        f"Reiniciaste la evaluación de {user_name} ({project_label}). "
        "Ahora puede volver a elegir evaluador y comenzar desde cero.",
    )
    return redirect("evaluations:ownership_list")


# --- Validación (evaluadores) --------------------------------------------------

@login_required
def ownership_validation(request):
    """Evaluaciones donde el usuario es evaluador (primario o secundario)."""
    period = _open_period()
    ev_records = (
        OwnershipEvaluator.objects.filter(user=request.user, evaluation__period=period)
        .select_related("evaluation__user", "evaluation__project")
        .order_by("evaluation__user__full_name")
        if period else OwnershipEvaluator.objects.none()
    )
    return render(request, "evaluations/ownership_validation.html", {
        "page_title": "Validación de Ownership",
        "ev_records": ev_records,
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
            comments=request.POST.get("comments", "").strip(),
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


# --- Entrega de Valor (Validador) ------------------------------------------

@login_required
def value_delivery_review(request):
    """Cola del Validador: validar o rechazar las Entregas de Valor de sus proyectos asignados."""
    if not permissions.has_value_delivery_validations(request.user):
        return render(request, "errors/403.html", {
            "titulo": "No tienes proyectos por validar",
            "mensaje": "Esta cola solo aparece para quien esté asignado como Validador de "
            "Entrega de Valor de algún proyecto (o para Talento).",
        }, status=403)

    period = _open_period()
    if request.method == "POST":
        vd = get_object_or_404(
            ValueDeliveryEvaluation.objects.select_related("project"), pk=request.POST.get("vd")
        )
        if not permissions.can_validate_value_delivery(request.user, vd):
            messages.error(request, "No eres el Validador asignado a este proyecto.")
            return redirect("evaluations:value_delivery_review")

        action = request.POST.get("action")
        if action == "validate":
            value_delivery_flow.validate_vd(vd, request.user)
            messages.success(request, f"Validaste la Entrega de Valor de {vd.project.name}.")
        elif action == "reject":
            value_delivery_flow.reject_vd(vd, request.POST.get("comment", "").strip())
            messages.info(request, f"Regresaste a borrador la Entrega de Valor de {vd.project.name}.")
        elif action == "comment":
            value_delivery_flow.save_vd_comment(vd, request.POST.get("comments", "").strip())
            messages.success(request, "Guardaste el comentario.")
        return redirect("evaluations:value_delivery_review")

    queue = ValueDeliveryEvaluation.objects.filter(
        period=period, status=ValueDeliveryEvaluation.Status.EN_VALIDACION
    ).select_related("project", "evaluator", "project__validador")
    if not request.user.is_admin:
        queue = queue.filter(project__validador=request.user)
    for vd in queue:
        vd.criteria = value_delivery_flow.criteria_summary(vd)

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
    saved_ids = []
    if period:
        scores = {a.user_id: a for a in ArenaImpactScore.objects.filter(period=period)}
        for user in User.objects.filter(is_active=True, role="COLABORADOR").order_by("full_name"):
            impact = scores.get(user.id)
            rows.append({"user": user, "impact": impact})
            if impact and impact.score is not None:
                saved_ids.append(user.id)
    return render(request, "evaluations/arena_impact.html", {
        "page_title": "Impacto Arena",
        "rows": rows,
        "period": period,
        "saved_ids": saved_ids,
    })


@login_required
@require_POST
def arena_impact_autosave(request):
    """Guarda la calificación/nota de una persona al instante (JSON). Solo Talento/admin."""
    if not request.user.is_admin:
        return JsonResponse({"ok": False, "error": "No autorizado."}, status=403)

    period = _open_period()
    if not period:
        return JsonResponse({"ok": False, "error": "No hay un periodo abierto."}, status=400)

    from django.contrib.auth import get_user_model
    User = get_user_model()

    payload = json.loads(request.body or "{}")
    user = get_object_or_404(
        User, pk=payload.get("user_id"), is_active=True, role="COLABORADOR"
    )

    raw_score = payload.get("score")
    has_score = raw_score not in (None, "")
    score = _parse_decimal(raw_score) if has_score else None
    if has_score and score is None:
        return JsonResponse(
            {"ok": False, "error": "La calificación debe ser un número del 1 al 4."},
            status=400,
        )
    notes = (payload.get("notes") or "").strip()

    ArenaImpactScore.objects.update_or_create(
        user=user, period=period,
        defaults={"score": score, "notes": notes, "captured_by": request.user},
    )
    final_flow.recompute_final_score(user, period)
    return JsonResponse({"ok": True, "has_score": score is not None})


def _parse_decimal(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        v = Decimal(raw)
    except (InvalidOperation, TypeError):
        return None
    return v if Decimal("1") <= v <= Decimal("4") else None
