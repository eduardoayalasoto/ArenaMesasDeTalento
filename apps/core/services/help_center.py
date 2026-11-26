"""Centro de ayuda contextual (spec 011): qué pestañas ve cada persona y con qué datos reales.

Las pestañas se deciden por permisos y relaciones (no por el rol «a mano») y lo que no aplica no se renderiza.
Talento no ve la guía personal (autoevaluación, evaluador, liderazgo): ve cómo organizar y mantener los catálogos.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist, ValidationError

from apps.access import services as access
from apps.access.registry import Scope
from apps.core.services import ownership_flow, permissions, pillar_weights, positions, three_sixty


def _pct(fraction) -> str:
    value = Decimal(str(fraction)) * 100
    return f"{value:.0f}" if value == value.to_integral_value() else f"{value:.1f}"


def my_pillars(user):
    """Ponderación de pilares de la persona según SU Área › Posición › Nivel, o None si no tiene."""
    if not user.area_id:
        return None
    try:
        own, vd, arena = pillar_weights.effective_weights(user)
    except (ValidationError, ObjectDoesNotExist, AttributeError):
        return None
    return {"ownership": _pct(own), "value_delivery": _pct(vd), "arena_impact": _pct(arena)}


def my_questionnaire(user):
    """Cuestionario de Ownership que le corresponde: puesto, nº de preguntas y categorías con su ponderación."""
    template = ownership_flow.resolve_ownership_template(user) if user.area_id else None
    if template is None:
        return None
    from apps.questionnaires.models import Question

    questions = list(Question.objects.filter(section__template=template, qtype=Question.Type.SCALE))
    links = list(template.template_categories.select_related("category").order_by("category__order"))
    return {
        "template": template, "n_questions": len(questions),
        "categories": [{"name": l.category.name, "weight": _pct(l.weight_pct / 100)} for l in links if l.weight_pct > 0],
        "unweighted": [q.title for q in questions if not q.is_weighted],
    }


def my_evaluators(user, period):
    """Evaluadores de la persona en el periodo abierto: [{project, evaluators: [(nombre, principal)]}]."""
    from apps.evaluations.models import OwnershipEvaluation

    if period is None:
        return []
    rows = []
    for ev in OwnershipEvaluation.objects.filter(user=user, period=period).select_related("project"):
        rows.append({
            "project": ev.project.name if ev.project_id else "Todos tus proyectos",
            "evaluators": [(r.user.full_name, r.is_primary) for r in ev.evaluators.select_related("user").order_by("-is_primary")],
            "submitted": ev.is_submitted,
        })
    return rows


def evaluator_pending(user, period):
    """Evaluaciones donde la persona es evaluadora y siguen abiertas: [{person, project}]."""
    from apps.evaluations.models import OwnershipEvaluator

    if period is None:
        return []
    qs = (OwnershipEvaluator.objects.filter(user=user, evaluation__period=period, evaluation__submitted_at__isnull=True)
          .select_related("evaluation__user", "evaluation__project"))
    return [{"person": r.evaluation.user.full_name,
             "project": r.evaluation.project.name if r.evaluation.project_id else "Todos sus proyectos",
             "primary": r.is_primary} for r in qs]


def is_evaluator_anywhere(user) -> bool:
    from apps.evaluations.models import OwnershipEvaluator

    return OwnershipEvaluator.objects.filter(user=user).exists()


def org_tree():
    """Organigrama vivo para Talento: Áreas › Posiciones › niveles (con su nombre visible y personas)."""
    from django.contrib.auth import get_user_model

    from apps.catalog.models import Area, Department, Position

    User = get_user_model()
    people = {}
    for a, l in User.objects.filter(is_active=True, deleted_at__isnull=True, is_superuser=False).values_list("area_id", "level_id"):
        people[(a, l)] = people.get((a, l), 0) + 1
    by_area = {}
    for p in Position.objects.select_related("level").order_by("level__order"):
        by_area.setdefault(p.area_id, []).append({
            "level": p.level.name if p.level_id else "Sin nivel", "name": p.name, "active": p.is_active,
            "people": people.get((p.area_id, p.level_id), 0),
        })
    tree = []
    for dept in Department.objects.filter(is_active=True).select_related("director").order_by("order", "name"):
        areas = [{"name": a.name, "positions": by_area.get(a.pk, [])}
                 for a in Area.objects.filter(department=dept, is_active=True).order_by("code")]
        tree.append({"name": dept.name, "director": dept.director.full_name if dept.director_id else "", "areas": areas})
    return tree


def build(user) -> dict:
    """Todo lo que necesita la pantalla: perfil, pestañas visibles (en orden) y los datos de cada una."""
    admin = access.is_admin(user)
    period = three_sixty.open_period()
    position_name = positions.user_position_name(user) if user.area_id else ""
    department = user.area.department if user.area_id and user.area.department_id else None
    lead, director = bool(user.is_lead_flag), bool(user.is_director_flag)

    owned = list(user.owned_projects.filter(is_active=True).order_by("name"))
    responsible = list(user.responsible_projects.filter(is_active=True).order_by("name"))
    validated = list(user.validated_projects.filter(is_active=True).order_by("name"))
    owner_360 = list(three_sixty.owned_projects(user))
    to_answer_360 = three_sixty.to_answer(user, period) if period else []

    feedback_given = False
    feedback_received = False
    if not admin:
        from apps.evaluations.models import FeedbackResponsible, TalentSessionNote

        feedback_given = FeedbackResponsible.objects.filter(user=user).exists()
        feedback_received = TalentSessionNote.objects.filter(user=user).exists()
    sees_mesa = access.has(user, "talent_table.view") or admin
    has_feedback = permissions.has_feedback_sessions(user) or feedback_given or feedback_received

    evaluator = (not admin) and (is_evaluator_anywhere(user) or ((lead or director) and access.has(user, "ownership.validate")))
    my_eval = (not admin) and access.has(user, "ownership.self.manage")
    leadership = (not admin) and (lead or owned or responsible or validated)
    show_360 = bool(owner_360 or to_answer_360 or admin or director)

    tabs = []

    def add(key, label, icon):
        tabs.append({"key": key, "label": label, "icon": icon})

    if admin:
        add("org", "Organización y catálogos", "building-2")
        add("cuestionarios", "Cuestionarios y ponderaciones", "clipboard-check")
        add("periodo", "Ciclo del periodo", "calendar-check")
    if my_eval:
        add("mi_evaluacion", "Mi evaluación", "user")
    if evaluator:
        add("evaluador", "Soy evaluador", "circle-check-big")
    if leadership:
        add("lider", "Liderazgo y proyectos", "package")
    if director and not admin:
        add("direccion", "Dirección", "shield-check")
    if show_360:
        add("tres_sesenta", "Evaluación 360", "message-square-heart")
    if sees_mesa or has_feedback:
        add("mesa", "Mesa y retroalimentación", "table-2")
    if access.has(user, "learn.self"):
        add("learn", "Arena Learn", "graduation-cap")
    add("modelo", "El modelo", "rocket")

    data = {
        "profile": {
            "name": user.full_name, "position": position_name, "department": department.name if department else "",
            "area_name": user.area.name if user.area_id else "", "level": user.level.name if user.level_id else "",
            "lead": lead, "director": director, "admin": admin,
        },
        "tabs": tabs,
        "default_tab": tabs[0]["key"],
        "period": period,
        "pillars": my_pillars(user) if not admin else None,
        "questionnaire": my_questionnaire(user) if my_eval else None,
        "evaluators": my_evaluators(user, period) if my_eval else [],
        "pending_as_evaluator": evaluator_pending(user, period) if evaluator else [],
        "owned": owned, "responsible": responsible, "validated": validated,
        "owner_360": owner_360, "to_answer_360": to_answer_360,
        "feedback_given": feedback_given, "feedback_received": feedback_received,
        "can": {
            "area_view": access.has(user, "people.results.view", Scope.AREA),
            "edit_projects": access.has(user, "projects.edit"),
            "approve_lead": access.has(user, "learn.approve.lead"),
            "approve_direction": access.has(user, "learn.approve.direction"),
            "talent_edit": access.has(user, "talent_table.edit"),
            "scenario": access.has(user, "current_scenario.view"),
            "vd_capture": bool(responsible) or access.has(user, "value_delivery.capture", Scope.TODOS),
            "vd_validate": bool(validated) or access.has(user, "value_delivery.validate", Scope.TODOS),
        },
    }
    if admin:
        data["org_tree"] = org_tree()
        data["all_weights"] = pillar_weights.matrix()
    return data
