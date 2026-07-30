"""Tableros, vista de área, avance del periodo y exportes."""

import csv
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from apps.catalog.models import Area, EvaluationPeriod, Project, ProjectMembership, SeniorityLevel
from apps.core.services import final_flow, permissions
from apps.evaluations.models import (
    FeedbackResponsible,
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

    from apps.evaluations.models import ArenaImpactScore, TalentSessionNote
    impact = ArenaImpactScore.objects.filter(user=subject, period=period).first()
    arena_notes = impact.notes if impact and impact.notes else ""

    talent_note = TalentSessionNote.objects.filter(user=subject, period=period).first()
    feedback_session = talent_note if talent_note and talent_note.has_feedback_session else None

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
            "feedback_session": feedback_session,
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
        "feedback_session": feedback_session,
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


def _project_team_ids(project):
    """IDs de los integrantes del equipo de un proyecto: miembros ∪ owner (lead)."""
    ids = set(
        ProjectMembership.objects.filter(project=project).values_list("user_id", flat=True)
    )
    if project.owner_id:
        ids.add(project.owner_id)
    return ids


def _project_progress(period):
    """Avance de Mesa por proyecto: total del equipo, listos y pendientes.

    Equipo = miembros activos ∪ owner del proyecto (sin duplicar). "Listo" = el
    comité tiene una revisión (`MesaProjectReview`) de esa persona EN ese
    proyecto. Solo proyectos activos con al menos un integrante, ordenados por
    % ascendente (los más atrasados primero).
    """
    if not period:
        return []
    from django.contrib.auth import get_user_model
    from apps.evaluations.models import MesaProjectReview

    User = get_user_model()
    valid_ids = set(
        User.objects.filter(is_active=True, is_superuser=False).values_list("id", flat=True)
    )
    projects = {}
    teams = {}
    for p in Project.objects.filter(is_active=True).select_related("owner"):
        projects[p.id] = p
        ids = set()
        if p.owner_id in valid_ids:
            ids.add(p.owner_id)
        teams[p.id] = ids
    for pid, uid in (
        ProjectMembership.objects.filter(project__is_active=True)
        .values_list("project_id", "user_id")
    ):
        if pid in teams and uid in valid_ids:
            teams[pid].add(uid)
    reviewed = set(
        MesaProjectReview.objects.filter(period=period).values_list("user_id", "project_id")
    )
    rows = []
    for pid, ids in teams.items():
        total = len(ids)
        if total == 0:
            continue
        listos = sum(1 for uid in ids if (uid, pid) in reviewed)
        rows.append({
            "project": projects[pid],
            "total": total,
            "listos": listos,
            "pendientes": total - listos,
            "pct": round(listos / total * 100),
        })
    rows.sort(key=lambda r: (r["pct"], r["project"].name))
    return rows


def _person_team_projects(target, period):
    """Equipos de una persona (proyectos activos donde es miembro u owner) con
    el estado de revisión de Mesa por cada uno, y el estado general derivado
    (`mesa_all_ready`: tiene equipos y todos están revisados)."""
    projects = list(
        Project.objects.filter(is_active=True)
        .filter(Q(memberships__user=target) | Q(owner=target))
        .distinct().order_by("name")
    )
    reviewed_ids = set()
    if period and projects:
        from apps.evaluations.models import MesaProjectReview
        reviewed_ids = set(
            MesaProjectReview.objects.filter(period=period, user=target, project__in=projects)
            .values_list("project_id", flat=True)
        )
    rows = [{"project": p, "reviewed": p.id in reviewed_ids} for p in projects]
    return {
        "project_reviews": rows,
        "mesa_all_ready": bool(rows) and all(r["reviewed"] for r in rows),
    }


def _general_ready_ids(period, users):
    """IDs de las personas (de `users`) con estado 'Listo' general derivado:
    tienen al menos un equipo y todos sus equipos están revisados en Mesa."""
    if not period:
        return set()
    from apps.evaluations.models import MesaProjectReview

    team_proj = {}
    for pid, uid in (
        ProjectMembership.objects.filter(project__is_active=True, user__in=users)
        .values_list("project_id", "user_id")
    ):
        team_proj.setdefault(uid, set()).add(pid)
    for pid, oid in (
        Project.objects.filter(is_active=True, owner__in=users).values_list("id", "owner_id")
    ):
        team_proj.setdefault(oid, set()).add(pid)
    reviewed = {}
    for uid, pid in (
        MesaProjectReview.objects.filter(period=period, user__in=users)
        .values_list("user_id", "project_id")
    ):
        reviewed.setdefault(uid, set()).add(pid)
    return {
        uid for uid, pids in team_proj.items()
        if pids and pids <= reviewed.get(uid, set())
    }


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

    # Filtro exclusivo por proyecto: si viene ?proyecto=, la lista muestra solo
    # el equipo de ese proyecto e ignora área/nivel/búsqueda.
    selected_project = None
    proyecto_id = request.GET.get("proyecto")
    if proyecto_id:
        selected_project = (
            Project.objects.filter(pk=proyecto_id, is_active=True)
            .select_related("owner").first()
        )

    if selected_project:
        users = users.filter(id__in=_project_team_ids(selected_project))
        level_code = area_code = ""
        q = ""
    else:
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

    ready_ids = _general_ready_ids(period, page.object_list)

    rows = [
        {
            "user": u,
            "final": finals_all.get(u.id),
            "evaluators": evaluators_by_user.get(u.id, []),
            "lead_projects": lead_projects_by_user.get(u.id),
            "mesa_ready": u.id in ready_ids,
        }
        for u in page.object_list
    ]

    # Querystring para conservar filtros al paginar.
    params = request.GET.copy()
    params.pop("page", None)
    base_qs = params.urlencode()

    template = (
        "dashboards/_talent_table_main.html"
        if request.headers.get("HX-Request")
        else "dashboards/talent_table.html"
    )
    return render(request, template, {
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
        "project_progress": _project_progress(period),
        "selected_project": selected_project,
    })


@login_required
def current_scenario_board(request):
    """Tablero drag-and-drop de Escenario Actual (no es un catálogo, es un
    accionador): permite a Talento y Dirección mover colaboradores entre los
    valores de escenario actual, filtrando por área/nivel en el cliente."""
    if not request.user.is_admin and not request.user.is_director:
        return render(request, "errors/403.html", {
            "titulo": "Panel reservado al comité de Talento",
            "mensaje": "Escenario Actual es para Talento y Cultura y la Dirección.",
        }, status=403)

    from django.contrib.auth import get_user_model

    from apps.catalog.models import ScenarioOption
    from apps.evaluations.models import TalentSessionNote

    User = get_user_model()
    period = _open_period()
    ctx = {"page_title": "Escenario Actual", "period": period}
    if not period:
        return render(request, "dashboards/current_scenario_board.html", ctx)

    users = (
        User.objects.filter(is_active=True, is_superuser=False)
        .select_related("area", "level").order_by("full_name")
    )
    scenario_by_user = dict(
        TalentSessionNote.objects.filter(period=period, user__in=users)
        .values_list("user_id", "scenario_actual_id")
    )
    options = list(ScenarioOption.objects.filter(is_active=True).order_by("order"))
    critical_option = next((o for o in options if o.order == 1), None)
    board_options = [o for o in options if o.order != 1]

    columns = [{"key": "none", "option": None, "label": "Sin asignar", "cards": []}] + [
        {"key": str(o.pk), "option": o, "label": o.name, "cards": []} for o in board_options
    ]
    columns_by_key = {c["key"]: c for c in columns}
    critical_cards = []
    for u in users:
        scenario_id = scenario_by_user.get(u.id)
        card = {"user": u}
        if critical_option and scenario_id == critical_option.pk:
            critical_cards.append(card)
        else:
            columns_by_key.get(str(scenario_id) if scenario_id else "none", columns_by_key["none"])["cards"].append(card)

    ctx.update({
        "areas": Area.objects.filter(is_active=True).order_by("code"),
        "levels": SeniorityLevel.objects.order_by("order"),
        "columns": columns,
        "critical_option": critical_option,
        "critical_cards": critical_cards,
    })
    return render(request, "dashboards/current_scenario_board.html", ctx)


@login_required
@require_POST
def current_scenario_move(request, pk):
    """HTMX: mueve a una persona a otro valor de Escenario Actual (o a 'sin
    asignar' si scenario_pk viene vacío). Talento y Dirección."""
    if not request.user.is_admin and not request.user.is_director:
        return HttpResponse(status=403)

    from django.contrib.auth import get_user_model

    from apps.catalog.models import ScenarioOption
    from apps.evaluations.models import TalentSessionNote

    User = get_user_model()
    target = get_object_or_404(User, pk=pk, is_active=True, is_superuser=False)
    period = _open_period()
    if not period:
        return HttpResponse(status=400)

    scenario_pk = request.POST.get("scenario_pk")
    option = None
    if scenario_pk:
        option = get_object_or_404(ScenarioOption, pk=scenario_pk, is_active=True)

    note, _ = TalentSessionNote.objects.get_or_create(
        user=target, period=period,
        defaults={"created_by": request.user},
    )
    note.scenario_actual = option
    note.save(update_fields=["scenario_actual"])
    return HttpResponse(status=204)


def _pending_people(period):
    """Personas con algo pendiente en el periodo: ownership propia, Entrega de Valor
    (captura como responsable, validación como Validador) y retroalimentación.

    No incluye Impacto Arena: lo captura Talento internamente, no es una tarea
    delegada a un colaborador o lead.

    Directores y Talento nunca llenan su propia autoevaluación de Ownership (la
    app ni siquiera les muestra "Mis evaluaciones" en el menú — ver
    `context_processors.navigation`), así que quedan fuera de esa categoría
    aunque tengan membresías de proyecto.
    """
    from django.contrib.auth import get_user_model
    from django.db.models import Count, Q

    User = get_user_model()
    users = User.objects.filter(is_active=True, is_superuser=False).select_related("area", "level")

    memberships_by_user = {}
    for m in ProjectMembership.objects.filter(project__is_active=True).select_related("project"):
        memberships_by_user.setdefault(m.user_id, []).append(m.project)

    own_by_project = {}
    lead_eval_info = {}
    own_evals = OwnershipEvaluation.objects.filter(period=period).annotate(
        answered_count=Count(
            "answers", filter=Q(answers__value__isnull=False) | Q(answers__is_na=True)
        )
    )
    for ev in own_evals:
        info = {"submitted": ev.is_submitted, "answered": ev.answered_count}
        if ev.project_id is None:
            lead_eval_info[ev.user_id] = info
        else:
            own_by_project[(ev.user_id, ev.project_id)] = info

    vd_by_project = {
        vd.project_id: vd for vd in ValueDeliveryEvaluation.objects.filter(period=period)
    }

    responsable_projects = {}
    validador_projects = {}
    for p in Project.objects.filter(is_active=True):
        if p.responsable_id:
            responsable_projects.setdefault(p.responsable_id, []).append(p)
        if p.validador_id:
            validador_projects.setdefault(p.validador_id, []).append(p)

    feedback_missing_by_user = {}
    for fr in (
        FeedbackResponsible.objects.filter(note__period=period, note__feedback_agreed=False)
        .select_related("note__user")
    ):
        feedback_missing_by_user.setdefault(fr.user_id, []).append(fr.note.user)

    def _detail(info):
        return "Con avance, falta enviar" if info and info["answered"] else "Sin iniciar"

    rows = []
    for u in users:
        ownership_missing = []
        if not (u.is_talento or u.is_director):
            if u.is_lead:
                info = lead_eval_info.get(u.id)
                if not info or not info["submitted"]:
                    ownership_missing.append({
                        "label": "Autoevaluación transversal", "detail": _detail(info),
                    })
            else:
                for project in memberships_by_user.get(u.id, []):
                    info = own_by_project.get((u.id, project.id))
                    if not info or not info["submitted"]:
                        ownership_missing.append({"label": project.name, "detail": _detail(info)})

        vd_capture_missing = []
        for project in responsable_projects.get(u.id, []):
            vd = vd_by_project.get(project.id)
            if vd is None or vd.status == ValueDeliveryEvaluation.Status.BORRADOR:
                started = vd is not None and any(
                    v is not None for v in (
                        vd.client_satisfaction, vd.deliverables, vd.time_finite, vd.time_indefinite,
                    )
                )
                detail = "Con avance, falta enviar a validación" if started else "Sin iniciar"
                vd_capture_missing.append({"label": project.name, "detail": detail})

        vd_validation_missing = []
        for project in validador_projects.get(u.id, []):
            vd = vd_by_project.get(project.id)
            if vd is not None and vd.status == ValueDeliveryEvaluation.Status.EN_VALIDACION:
                vd_validation_missing.append({"label": project.name, "detail": "Esperando su validación"})

        feedback_missing = [
            {"label": t.full_name, "detail": "Sesión sin cerrar"}
            for t in feedback_missing_by_user.get(u.id, [])
        ]

        total = (
            len(ownership_missing) + len(vd_capture_missing)
            + len(vd_validation_missing) + len(feedback_missing)
        )
        if total:
            rows.append({
                "user": u,
                "ownership_missing": ownership_missing,
                "vd_capture_missing": vd_capture_missing,
                "vd_validation_missing": vd_validation_missing,
                "feedback_missing": feedback_missing,
                "total": total,
            })

    rows.sort(key=lambda r: (-r["total"], r["user"].full_name))
    return rows


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
            "pending_rows": _pending_people(period),
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

        # Igual para Entrega de Valor: aquí se ven los comentarios aunque el
        # proyecto siga en Borrador/En validación, no solo cuando ya está Validada.
        from apps.evaluations.models import ValueDeliveryEvaluation
        project_ids = [row["project"].id for row in ctx["projects"] if row["project"]]
        vd_by_project = {
            vd.project_id: vd
            for vd in ValueDeliveryEvaluation.objects.filter(period=period, project_id__in=project_ids)
            .select_related("evaluator")
        }
        ctx["vd_comment_rows"] = [
            {"project": row["project"], "vd_comments": vd_by_project[row["project"].id].comments,
             "vd_evaluator": vd_by_project[row["project"].id].evaluator}
            for row in ctx["projects"]
            if row["project"] and row["project"].id in vd_by_project and vd_by_project[row["project"].id].comments
        ]

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
                ("actual", "Escenario Actual", {note.scenario_actual_id} if note.scenario_actual_id else set()),
                ("s1", "Escenario S+1", set(note.scenario_s1.values_list("pk", flat=True))),
                ("s2", "Escenario S+2", set(note.scenario_s2.values_list("pk", flat=True))),
            ],
            "primary": primary,
            "secondaries": secondaries,
            "all_users": all_users,
        })
        ctx.update(_person_team_projects(target, period))
    return render(request, "dashboards/talent_person.html", ctx)


@login_required
@require_POST
def talent_note_autosave(request, pk):
    """Guarda fortalezas/oportunidades/comentarios de la nota de Mesa de Talento (JSON). Solo Talento."""
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
    elif field == "comentarios":
        note.comentarios = value
        note.save(update_fields=["comentarios", "updated_at"])
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

    if tipo == "actual":
        # Escenario Actual es de selección única (FK): seleccionar reemplaza,
        # no hay toggle posible desde un <input type="radio">.
        note.scenario_actual = option
        note.save(update_fields=["scenario_actual"])
        return HttpResponse(status=200)

    scenario_map = {"s1": note.scenario_s1, "s2": note.scenario_s2}
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
def talent_mesa_project_toggle(request, pk, project_id):
    """Marca/desmarca 'revisado en Mesa' para (persona, proyecto) (HTMX). Solo Talento.

    El estado 'Listo' general de la persona se deriva de tener todos sus
    equipos revisados; aquí solo se alterna la revisión de un proyecto.
    """
    if not request.user.is_admin:
        return HttpResponse(status=403)

    from django.contrib.auth import get_user_model
    from apps.evaluations.models import MesaProjectReview

    User = get_user_model()
    target = get_object_or_404(User, pk=pk, is_active=True)
    project = get_object_or_404(Project, pk=project_id, is_active=True)
    period = _open_period()
    if not period:
        return HttpResponse(status=400)

    # La persona debe pertenecer al equipo del proyecto (miembro u owner).
    if target.id not in _project_team_ids(project):
        return HttpResponse(status=400)

    review = MesaProjectReview.objects.filter(
        period=period, user=target, project=project,
    ).first()
    if review:
        review.delete()
    else:
        MesaProjectReview.objects.create(
            period=period, user=target, project=project, reviewed_by=request.user,
        )

    ctx = {"target": target}
    ctx.update(_person_team_projects(target, period))
    return render(request, "dashboards/_mesa_review_block.html", ctx)


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


# --- Retroalimentación (responsables de retroalimentación) -----------------

@login_required
def feedback_session_list(request):
    """Índice de personas a las que el usuario debe dar retroalimentación en el periodo abierto."""
    from apps.evaluations.models import TalentSessionNote

    period = _open_period()
    rows = []
    if period:
        notes = (
            TalentSessionNote.objects.filter(period=period, responsables__user=request.user)
            .select_related("user__area", "user__level")
            .prefetch_related("responsables__user")
            .distinct()
            .order_by("user__full_name")
        )
        for note in notes:
            all_responsables = note.responsables.all()
            secondaries = [
                r.user for r in all_responsables
                if not r.is_primary and r.user_id != request.user.pk
            ]
            viewer_record = next((r for r in all_responsables if r.user_id == request.user.pk), None)
            rows.append({
                "note": note,
                "target": note.user,
                "secondaries": secondaries,
                "is_primary": bool(viewer_record and viewer_record.is_primary),
            })

    return render(request, "dashboards/feedback_session_list.html", {
        "page_title": "Retroalimentación",
        "rows": rows,
        "period": period,
    })


@login_required
def feedback_session_detail(request, pk):
    """Pantalla de Retroalimentación de Mesa de Talento: la llena el responsable asignado."""
    from django.contrib.auth import get_user_model
    from apps.evaluations.models import OwnershipEvaluator, TalentSessionNote

    User = get_user_model()
    period = _open_period()
    if not period:
        messages.error(request, "No hay un periodo abierto en este momento.")
        return redirect("dashboards:feedback_session_list")

    target = get_object_or_404(User, pk=pk, is_active=True)
    note = get_object_or_404(
        TalentSessionNote.objects.select_related("user"), user=target, period=period
    )
    if not permissions.can_edit_feedback_session(request.user, note):
        return render(request, "errors/403.html", {
            "titulo": "No puedes dar retroalimentación a esta persona",
            "mensaje": "Esta pantalla es solo para quien esté asignado como responsable "
            "de retroalimentación de esta persona en Mesa de Talento.",
        }, status=403)

    if request.method == "POST":
        action = request.POST.get("action", "save")

        if action == "reopen":
            if not request.user.is_admin:
                messages.error(request, "Solo Talento y Cultura puede reabrir una retroalimentación acordada.")
            else:
                note.feedback_agreed = False
                note.feedback_agreed_at = None
                note.feedback_agreed_by = None
                note.save(update_fields=["feedback_agreed", "feedback_agreed_at", "feedback_agreed_by", "updated_at"])
                messages.success(request, f"Reabriste la retroalimentación de {target.full_name}.")
            return redirect("dashboards:feedback_session_detail", pk=target.pk)

        if note.feedback_agreed:
            messages.error(request, "Esta retroalimentación ya está acordada y cerrada; no puede editarse.")
            return redirect("dashboards:feedback_session_detail", pk=target.pk)

        if action == "agree":
            from django.utils import timezone
            note.feedback_agreed = True
            note.feedback_agreed_at = timezone.now()
            note.feedback_agreed_by = request.user
            note.save(update_fields=["feedback_agreed", "feedback_agreed_at", "feedback_agreed_by", "updated_at"])
            messages.success(request, f"Marcaste como acordada la retroalimentación de {target.full_name}. Queda cerrada.")
            return redirect("dashboards:feedback_session_detail", pk=target.pk)

        fields = [
            "objetivo_desarrollo_1", "objetivo_desarrollo_2", "objetivo_desarrollo_3",
            "expectativas_profesionales", "expectativas_personales", "comentarios_adicionales",
        ]
        for field in fields:
            setattr(note, field, request.POST.get(field, "").strip())
        note.save(update_fields=fields + ["updated_at"])
        messages.success(request, f"Guardaste la retroalimentación de {target.full_name}.")
        return redirect("dashboards:feedback_session_detail", pk=target.pk)

    results = build_results(target, period)
    evaluators = list(
        OwnershipEvaluator.objects.filter(evaluation__user=target, evaluation__period=period)
        .select_related("user").order_by("-is_primary", "user__full_name")
    )

    return render(request, "dashboards/feedback_session_detail.html", {
        "page_title": f"Retroalimentación · {target.full_name}",
        "target": target,
        "note": note,
        "period": period,
        "final": results["final"],
        "weight": results["weight"],
        "evaluators": evaluators,
        "scenario_actual": [note.scenario_actual] if note.scenario_actual_id else [],
        "can_reopen": note.feedback_agreed and request.user.is_admin,
    })


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
