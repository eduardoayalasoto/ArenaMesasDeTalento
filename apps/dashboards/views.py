"""Tableros, vista de área, avance del periodo y exportes."""

import csv

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.generic import TemplateView

from apps.catalog.models import EvaluationPeriod, SeniorityLevel
from apps.core.services import final_flow, permissions
from apps.evaluations.models import (
    FinalScore,
    OwnershipEvaluation,
    ValueDeliveryEvaluation,
)


def _open_period():
    return EvaluationPeriod.objects.filter(status=EvaluationPeriod.Status.ABIERTO).first()


def build_results(subject, period):
    """Arma el contexto del informe de resultados (estilo slide) de una persona."""
    final = final_flow.recompute_final_score(subject, period)
    weight = getattr(subject.level, "weight", None)

    evals = list(
        OwnershipEvaluation.objects.filter(user=subject, period=period)
        .select_related("project").order_by("project__name")
    )
    # Calificación de Entrega de Valor por proyecto (validada) para mostrar junto al de Ownership.
    vd_by_project = {
        vd.project_id: vd.score
        for vd in ValueDeliveryEvaluation.objects.filter(
            period=period, project__in=[e.project_id for e in evals],
            status=ValueDeliveryEvaluation.Status.VALIDADA,
        )
    }
    projects = [
        {
            "evaluation": e,
            "project": e.project,
            "ownership_score": e.score,
            "vd_score": vd_by_project.get(e.project_id),
            "closed": e.is_submitted,
        }
        for e in evals
    ]
    feedback = [e for e in evals if e.is_submitted]

    from apps.evaluations.models import ArenaImpactScore
    impact = ArenaImpactScore.objects.filter(user=subject, period=period).first()
    arena_notes = impact.notes if impact and impact.notes else ""

    return {
        "final": final, "weight": weight, "projects": projects,
        "feedback": feedback, "arena_notes": arena_notes,
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

    rows = [
        {"user": u, "final": finals_all.get(u.id), "evaluators": evaluators_by_user.get(u.id, [])}
        for u in page.object_list
    ]

    # Querystring para conservar filtros al paginar.
    params = request.GET.copy()
    params.pop("page", None)
    base_qs = params.urlencode()

    from apps.catalog.models import Area, SeniorityLevel
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
