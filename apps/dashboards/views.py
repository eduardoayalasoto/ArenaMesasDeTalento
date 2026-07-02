"""Tableros, vista de área, avance del periodo y exportes."""

import csv
import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from apps.catalog.models import Area, EvaluationPeriod, ProjectMembership, SeniorityLevel
from apps.core.services import final_flow, permissions
from apps.evaluations.models import (
    FinalScore,
    OwnershipEvaluation,
    ValueDeliveryEvaluation,
)


def _open_period():
    return EvaluationPeriod.objects.filter(status=EvaluationPeriod.Status.ABIERTO).first()


def build_results(subject, period):
    """Arma el contexto del informe de resultados (estilo slide) de una persona.

    Para Leads: projects viene de membresías (ownership es transversal) y
    lead_eval es la OwnershipEvaluation con project=None.
    Para el resto: comportamiento original.
    """
    final = final_flow.recompute_final_score(subject, period)
    weight = getattr(subject.level, "weight", None)

    from apps.evaluations.models import ArenaImpactScore
    impact = ArenaImpactScore.objects.filter(user=subject, period=period).first()
    arena_notes = impact.notes if impact and impact.notes else ""

    if subject.is_lead:
        lead_eval = (
            OwnershipEvaluation.objects.filter(
                user=subject, project__isnull=True, period=period
            ).first()
        )
        member_projects = list(
            subject.memberships.select_related("project")
            .filter(project__is_active=True).order_by("project__name")
        )
        vd_evals = {
            vd.project_id: vd
            for vd in ValueDeliveryEvaluation.objects.filter(
                period=period,
                project__in=[m.project_id for m in member_projects],
                status=ValueDeliveryEvaluation.Status.VALIDADA,
            ).select_related("evaluator")
        }
        projects = [
            {
                "evaluation": None,
                "project": m.project,
                "ownership_score": None,
                "vd_score": vd_evals[m.project_id].score if m.project_id in vd_evals else None,
                "vd_evaluator": vd_evals[m.project_id].evaluator if m.project_id in vd_evals else None,
                "vd_comments": vd_evals[m.project_id].comments if m.project_id in vd_evals else "",
                "closed": None,
                "is_lead_project": True,
            }
            for m in member_projects
        ]
        feedback = [lead_eval] if lead_eval and lead_eval.is_submitted else []
        vd_comment_rows = [row for row in projects if row["vd_comments"]]
        return {
            "final": final, "weight": weight, "projects": projects,
            "feedback": feedback, "arena_notes": arena_notes,
            "lead_eval": lead_eval, "vd_comment_rows": vd_comment_rows,
        }

    # Colaborador normal
    evals = list(
        OwnershipEvaluation.objects.filter(user=subject, period=period)
        .select_related("project").order_by("project__name")
    )
    vd_evals = {
        vd.project_id: vd
        for vd in ValueDeliveryEvaluation.objects.filter(
            period=period, project__in=[e.project_id for e in evals],
            status=ValueDeliveryEvaluation.Status.VALIDADA,
        ).select_related("evaluator")
    }
    projects = [
        {
            "evaluation": e,
            "project": e.project,
            "ownership_score": e.score,
            "vd_score": vd_evals[e.project_id].score if e.project_id in vd_evals else None,
            "vd_evaluator": vd_evals[e.project_id].evaluator if e.project_id in vd_evals else None,
            "vd_comments": vd_evals[e.project_id].comments if e.project_id in vd_evals else "",
            "closed": e.is_submitted,
            "is_lead_project": False,
        }
        for e in evals
    ]
    feedback = [e for e in evals if e.is_submitted]
    vd_comment_rows = [row for row in projects if row["vd_comments"]]
    return {
        "final": final, "weight": weight, "projects": projects,
        "feedback": feedback, "arena_notes": arena_notes,
        "lead_eval": None, "vd_comment_rows": vd_comment_rows,
    }


class HomeView(LoginRequiredMixin, TemplateView):
    """Mi tablero = mi informe de resultados (unificado)."""

    template_name = "dashboards/my_results.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Mi tablero"
        period = _open_period()
        ctx["period"] = period
        if period:
            ctx.update(build_results(self.request.user, period))
        return ctx


@login_required
def my_area(request):
    """Lista de colaboradores visibles con su avance y calificación (RN-14/15)."""
    period = _open_period()
    users = permissions.visible_users(request.user).select_related("area", "level")

    # Filtros
    level_code = request.GET.get("level")
    if level_code:
        users = users.filter(level__code=level_code)

    finals = {}
    submitted_counts = {}
    if period:
        finals = {f.user_id: f for f in FinalScore.objects.filter(period=period, user__in=users)}
        for ev in OwnershipEvaluation.objects.filter(
            period=period, user__in=users, status=OwnershipEvaluation.Status.ENVIADA
        ):
            submitted_counts[ev.user_id] = submitted_counts.get(ev.user_id, 0) + 1

    rows = [
        {"user": u, "final": finals.get(u.id), "submitted": submitted_counts.get(u.id, 0)}
        for u in users
    ]
    return render(request, "dashboards/my_area.html", {
        "page_title": "Mi área",
        "rows": rows,
        "period": period,
        "levels": SeniorityLevel.objects.all(),
        "level_filter": level_code or "",
    })


@login_required
def user_results(request, pk):
    """Consulta de los resultados y evaluaciones de una persona (drill-down desde Mi área)."""
    target = get_object_or_404(
        permissions.visible_users(request.user).select_related("area", "level"), pk=pk
    )
    period = _open_period()
    ctx = {"page_title": f"Resultados · {target.full_name}", "target": target, "period": period}
    if period:
        ctx.update(build_results(target, period))
    return render(request, "dashboards/user_results.html", ctx)


class HelpView(LoginRequiredMixin, TemplateView):
    """Centro de ayuda: guías por rol en pestañas."""

    template_name = "dashboards/help.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_title"] = "Ayuda"
        return ctx


@login_required
def talent_table(request):
    """Mesa de Talento: lista de todos los colaboradores con su calificación general."""
    if not request.user.is_admin and not request.user.is_director:
        return render(request, "errors/403.html", {
            "titulo": "Panel reservado al comité de Talento",
            "mensaje": "La Mesa de Talento es para Talento y Cultura y la Dirección.",
        }, status=403)

    from django.contrib.auth import get_user_model
    User = get_user_model()
    period = _open_period()

    from django.core.paginator import Paginator

    users = (
        User.objects.filter(is_active=True, is_superuser=False)
        .select_related("area", "level")
        .annotate(num_projects=Count("memberships", distinct=True))
        .order_by("full_name")
    )
    level_code = request.GET.get("level")
    area_code = request.GET.get("area")
    q = request.GET.get("q", "").strip()
    if level_code:
        users = users.filter(level__code=level_code)
    if area_code:
        users = users.filter(area__code=area_code)
    if q:
        users = users.filter(full_name__icontains=q)

    # Estadísticas sobre TODO el conjunto filtrado.
    finals_all = {}
    if period:
        finals_all = {f.user_id: f for f in FinalScore.objects.filter(period=period, user__in=users)}
    complete = [f for f in finals_all.values() if f.is_complete]
    excede = sum(1 for f in complete if f.band == "Excede")
    avg = None
    if complete:
        from decimal import ROUND_HALF_UP, Decimal
        total = sum(f.final_score for f in complete)
        avg = (total / len(complete)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Paginación.
    paginator = Paginator(users, 25)
    page = paginator.get_page(request.GET.get("page"))

    evaluators_by_user = {}
    if period:
        from apps.evaluations.models import OwnershipEvaluator
        for rec in (
            OwnershipEvaluator.objects.filter(
                evaluation__period=period, evaluation__user__in=page.object_list,
            ).select_related("user", "evaluation")
        ):
            evaluators_by_user.setdefault(rec.evaluation.user_id, [])
            name = rec.user.full_name
            if name not in evaluators_by_user[rec.evaluation.user_id]:
                evaluators_by_user[rec.evaluation.user_id].append(name)

    lead_projects_by_user = {}
    for u in page.object_list:
        if u.is_lead:
            lead_projects_by_user[u.id] = list(
                ProjectMembership.objects.filter(user=u, project__is_active=True)
                .order_by("project__name")
                .values_list("project__name", flat=True)
            )

    rows = [
        {
            "user": u,
            "final": finals_all.get(u.id),
            "evaluators": evaluators_by_user.get(u.id, []),
            "lead_projects": lead_projects_by_user.get(u.id),
        }
        for u in page.object_list
    ]

    # Querystring para conservar filtros al paginar.
    params = request.GET.copy()
    params.pop("page", None)
    base_qs = params.urlencode()

    return render(request, "dashboards/talent_table.html", {
        "page_title": "Mesa de Talento",
        "rows": rows,
        "page_obj": page,
        "base_qs": base_qs,
        "period": period,
        "areas": Area.objects.all(),
        "levels": SeniorityLevel.objects.all(),
        "area_filter": area_code or "",
        "level_filter": level_code or "",
        "q": q,
        "stat_total": paginator.count,
        "stat_complete": len(complete),
        "stat_excede": excede,
        "stat_avg": avg,
    })


@login_required
def period_progress(request):
    """Avance de llenado del periodo (solo Talento/admin)."""
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Panel reservado a Talento",
            "mensaje": "El avance del periodo lo consulta Talento y Cultura.",
        }, status=403)

    period = _open_period()
    ctx = {"page_title": "Avance del periodo", "period": period}
    if period:
        own = OwnershipEvaluation.objects.filter(period=period)
        vd = ValueDeliveryEvaluation.objects.filter(period=period)
        finals = FinalScore.objects.filter(period=period)
        ctx.update({
            "own_total": own.count(),
            "own_submitted": own.filter(status=OwnershipEvaluation.Status.ENVIADA).count(),
            "vd_total": vd.count(),
            "vd_validated": vd.filter(status=ValueDeliveryEvaluation.Status.VALIDADA).count(),
            "finals_complete": finals.filter(is_complete=True).count(),
            "finals_total": finals.count(),
        })
    return render(request, "dashboards/period_progress.html", ctx)


@login_required
def talent_person(request, pk):
    """Vista de sesión de Mesa de Talento para una persona (Talento y Directores)."""
    if not request.user.is_admin and not request.user.is_director:
        return render(request, "errors/403.html", {
            "titulo": "Panel reservado al comité de Talento",
            "mensaje": "La Mesa de Talento es para Talento y Cultura y la Dirección.",
        }, status=403)

    from django.contrib.auth import get_user_model
    from apps.evaluations.models import TalentSessionNote
    from apps.catalog.models import ScenarioOption

    User = get_user_model()
    target = get_object_or_404(User, pk=pk, is_active=True, is_superuser=False)
    period = _open_period()

    ctx = {
        "page_title": f"Mesa de Talento · {target.full_name}",
        "target": target,
        "period": period,
    }
    if period:
        ctx.update(build_results(target, period))

        # En Mesa de Talento se muestran TODAS las evaluaciones del periodo,
        # no solo las cerradas (Talento necesita ver los comentarios en vivo).
        from apps.evaluations.models import OwnershipEvaluation
        ctx["feedback"] = list(
            OwnershipEvaluation.objects.filter(user=target, period=period)
            .select_related("project")
            .order_by("project__name")
        )

        note, _ = TalentSessionNote.objects.get_or_create(
            user=target, period=period,
            defaults={"created_by": request.user},
        )
        scenario_options = ScenarioOption.objects.filter(is_active=True)
        responsables = list(note.responsables.select_related("user__area").order_by("-is_primary", "user__full_name"))
        primary = next((r for r in responsables if r.is_primary), None)
        secondaries = [r for r in responsables if not r.is_primary]
        all_users = User.objects.filter(is_active=True, is_superuser=False).exclude(
            pk__in=[r.user_id for r in responsables]
        ).order_by("full_name")
        ctx.update({
            "note": note,
            "scenario_options": scenario_options,
            "escenarios_ctx": [
                ("actual", "Escenario Actual", set(note.scenario_actual.values_list("pk", flat=True))),
                ("s1", "Escenario S+1", set(note.scenario_s1.values_list("pk", flat=True))),
                ("s2", "Escenario S+2", set(note.scenario_s2.values_list("pk", flat=True))),
            ],
            "primary": primary,
            "secondaries": secondaries,
            "all_users": all_users,
        })
    return render(request, "dashboards/talent_person.html", ctx)


@login_required
@require_POST
def talent_note_autosave(request, pk):
    """Guarda fortalezas/oportunidades de la nota de Mesa de Talento (JSON). Solo Talento."""
    if not request.user.is_admin:
        return JsonResponse({"ok": False, "error": "No autorizado."}, status=403)

    from django.contrib.auth import get_user_model
    from apps.evaluations.models import TalentSessionNote

    User = get_user_model()
    target = get_object_or_404(User, pk=pk, is_active=True)
    period = _open_period()
    if not period:
        return JsonResponse({"ok": False, "error": "No hay periodo abierto."}, status=400)

    payload = json.loads(request.body or "{}")
    note, _ = TalentSessionNote.objects.get_or_create(
        user=target, period=period,
        defaults={"created_by": request.user},
    )
    field = payload.get("field")
    value = (payload.get("value") or "").strip()
    if field == "fortalezas":
        note.fortalezas = value
        note.save(update_fields=["fortalezas", "updated_at"])
    elif field == "oportunidades":
        note.oportunidades = value
        note.save(update_fields=["oportunidades", "updated_at"])
    else:
        return JsonResponse({"ok": False, "error": "Campo inválido."}, status=400)
    return JsonResponse({"ok": True})


@login_required
@require_POST
def talent_scenario_toggle(request, pk, tipo):
    """Activa/desactiva una opción de escenario en la nota (HTMX). Solo Talento."""
    if not request.user.is_admin:
        return HttpResponse(status=403)

    from django.contrib.auth import get_user_model
    from apps.evaluations.models import TalentSessionNote
    from apps.catalog.models import ScenarioOption

    User = get_user_model()
    target = get_object_or_404(User, pk=pk, is_active=True)
    period = _open_period()
    if not period:
        return HttpResponse(status=400)

    option = get_object_or_404(ScenarioOption, pk=request.POST.get("option_pk"))
    note, _ = TalentSessionNote.objects.get_or_create(
        user=target, period=period,
        defaults={"created_by": request.user},
    )

    scenario_map = {"actual": note.scenario_actual, "s1": note.scenario_s1, "s2": note.scenario_s2}
    m2m = scenario_map.get(tipo)
    if m2m is None:
        return HttpResponse(status=400)

    if m2m.filter(pk=option.pk).exists():
        m2m.remove(option)
    else:
        m2m.add(option)
    return HttpResponse(status=200)


@login_required
@require_POST
def talent_responsable_add(request, pk):
    """Agrega un responsable de retroalimentación (HTMX). Solo Talento."""
    if not request.user.is_admin:
        return HttpResponse(status=403)

    from django.contrib.auth import get_user_model
    from apps.evaluations.models import TalentSessionNote, FeedbackResponsible

    User = get_user_model()
    target = get_object_or_404(User, pk=pk, is_active=True)
    period = _open_period()
    if not period:
        return HttpResponse(status=400)

    note, _ = TalentSessionNote.objects.get_or_create(
        user=target, period=period,
        defaults={"created_by": request.user},
    )
    is_primary = request.POST.get("is_primary") == "1"
    new_user = get_object_or_404(User, pk=request.POST.get("user_id"), is_active=True)

    if not note.responsables.filter(user=new_user).exists():
        if is_primary:
            note.responsables.filter(is_primary=True).update(is_primary=False)
        FeedbackResponsible.objects.create(note=note, user=new_user, is_primary=is_primary)

    return _responsables_fragment(request, note, target)


@login_required
@require_POST
def talent_responsable_remove(request, pk, rid):
    """Quita un responsable de retroalimentación (HTMX). Solo Talento."""
    if not request.user.is_admin:
        return HttpResponse(status=403)

    from django.contrib.auth import get_user_model
    from apps.evaluations.models import TalentSessionNote, FeedbackResponsible

    User = get_user_model()
    target = get_object_or_404(User, pk=pk, is_active=True)
    period = _open_period()
    note = get_object_or_404(TalentSessionNote, user=target, period=period)
    FeedbackResponsible.objects.filter(pk=rid, note=note).delete()
    return _responsables_fragment(request, note, target)


def _responsables_fragment(request, note, target):
    """Renderiza el fragmento HTMX de la lista de responsables."""
    from django.contrib.auth import get_user_model
    from django.template.loader import render_to_string

    User = get_user_model()
    responsables = list(note.responsables.select_related("user__area").order_by("-is_primary", "user__full_name"))
    primary = next((r for r in responsables if r.is_primary), None)
    secondaries = [r for r in responsables if not r.is_primary]
    all_users = User.objects.filter(is_active=True, is_superuser=False).exclude(
        pk__in=[r.user_id for r in responsables]
    ).order_by("full_name")
    html = render_to_string("dashboards/_responsables_widget.html", {
        "note": note,
        "target": target,
        "primary": primary,
        "secondaries": secondaries,
        "all_users": all_users,
        "request": request,
    })
    return HttpResponse(html)


@login_required
def export_scores_csv(request):
    """Exporta a CSV las calificaciones de los colaboradores visibles para el viewer."""
    period = _open_period()
    users = permissions.visible_users(request.user).select_related("area", "level")
    finals = {}
    if period:
        finals = {f.user_id: f for f in FinalScore.objects.filter(period=period, user__in=users)}

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    period_name = period.name if period else "sin-periodo"
    response["Content-Disposition"] = f'attachment; filename="calificaciones_{period_name}.csv"'
    response.write("﻿")  # BOM para que Excel reconozca UTF-8
    writer = csv.writer(response)
    writer.writerow([
        "Colaborador", "Correo", "Área", "Nivel",
        "Ownership", "Entrega de Valor", "Impacto Arena", "Final", "Banda", "Completa",
    ])
    for u in users:
        f = finals.get(u.id)
        writer.writerow([
            u.full_name, u.email,
            u.area.name if u.area else "",
            u.level.name if u.level else "",
            f.ownership_score if f else "",
            f.value_delivery_score if f else "",
            f.arena_impact_score if f else "",
            f.final_score if f else "",
            f.band if f else "",
            "Sí" if (f and f.is_complete) else "No",
        ])
    return response
