"""Registro del menú de arena-talento (docs/PLAN_MIGRACION_DISENO.md §3.3).

El menú es DATOS: 4 categorías (Inicio · Arena Learn · Mesa de Talento · Administración) con
ítems declarativos. La visibilidad de cada ítem sale de la matriz de perfiles (spec 005) — nunca
de condiciones por rol en la plantilla. `templates/_navbar.html` solo itera lo que arma
`build_nav(request)`; `apps/core/tests/test_navigation.py` verifica que todo ítem apunte a una
ruta protegida por un permiso registrado.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from django.urls import NoReverseMatch, reverse

from apps.access import services as access
from apps.access.registry import Scope


@dataclass(frozen=True)
class NavItem:
    label: str
    url_name: str
    icon: str
    perm: tuple = ()                       # (clave, alcance mínimo): visible si el perfil lo concede
    visible: Callable | None = None        # regla extra (relación vigente); recibe al usuario
    badge: Callable | None = None          # contador de pendientes (el navbar copia del CRM no lo pinta; se calcula solo si se usa)
    also_active: tuple = ()
    group: str = ""                        # subtítulo dentro de la categoría (Mesa de Talento)


@dataclass(frozen=True)
class NavCategory:
    key: str
    label: str
    icon: str
    items: tuple = field(default_factory=tuple)


# --- Reglas de visibilidad / contadores (relación vigente además del permiso) ---------------

def _is_evaluator(u):
    from apps.evaluations.models import OwnershipEvaluator

    return access.has(u, "ownership.validate", Scope.TODOS) or (
        access.has(u, "ownership.validate", Scope.ASIGNADO) and OwnershipEvaluator.objects.filter(user=u).exists()
    )


def _ownership_to_validate(u):
    from apps.catalog.models import EvaluationPeriod
    from apps.evaluations.models import OwnershipEvaluator

    return OwnershipEvaluator.objects.filter(
        user=u, evaluation__period__status=EvaluationPeriod.Status.ABIERTO, evaluation__submitted_at__isnull=True,
    ).values("evaluation").distinct().count()


def _has_feedback(u):
    from apps.evaluations.models import FeedbackResponsible, TalentSessionNote

    return access.has(u, "feedback.view", Scope.TODOS) or (
        access.has(u, "feedback.view", Scope.ASIGNADO)
        and (FeedbackResponsible.objects.filter(user=u).exists() or TalentSessionNote.objects.filter(user=u).exists())
    )


def _captures_vd(u):
    return access.has(u, "value_delivery.capture", Scope.TODOS) or (
        access.has(u, "value_delivery.capture", Scope.ASIGNADO) and u.leads_projects
    )


def _vd_to_capture(u):
    from apps.catalog.models import EvaluationPeriod
    from apps.evaluations.models import ValueDeliveryEvaluation

    period = EvaluationPeriod.objects.filter(status=EvaluationPeriod.Status.ABIERTO).first()
    if not period:
        return 0
    projects = u.responsible_projects.filter(is_active=True)
    done = ValueDeliveryEvaluation.objects.filter(period=period, project__in=projects).exclude(
        status=ValueDeliveryEvaluation.Status.BORRADOR).values("project")
    return projects.exclude(pk__in=done).count()


def _validates_vd(u):
    from apps.core.services.permissions import has_value_delivery_validations

    return has_value_delivery_validations(u)


def _vd_to_validate(u):
    from apps.evaluations.models import ValueDeliveryEvaluation

    qs = ValueDeliveryEvaluation.objects.filter(status=ValueDeliveryEvaluation.Status.EN_VALIDACION)
    if not access.has(u, "value_delivery.validate", Scope.TODOS):
        qs = qs.filter(project__validador=u)
    return qs.count()


def _is_course_approver(u):
    from apps.core.services.learning_flow import is_course_approver

    return is_course_approver(u)


def _courses_to_approve(u):
    from apps.core.services.learning_flow import approvals_for

    return len(approvals_for(u))


P, A, AR, T = Scope.PROPIO, Scope.ASIGNADO, Scope.AREA, Scope.TODOS

LEARN_ALSO = ("learning:request_start", "learning:request_create", "learning:request_edit",
              "learning:request_detail", "learning:request_complete", "learning:review_edit",
              "learning:direct_create")
OWNERSHIP_ALSO = ("evaluations:ownership_start", "evaluations:ownership_lead_start", "evaluations:ownership_edit",
                  "evaluations:ownership_view", "evaluations:ownership_set_evaluator",
                  "evaluations:ownership_add_evaluator", "evaluations:ownership_remove_evaluator")

NAV: tuple[NavCategory, ...] = (
    NavCategory("inicio", "Inicio", "house", (
        NavItem("Mi tablero", "dashboards:home", "layout-dashboard", ("dashboard.home.view", P),
                also_active=("dashboards:user_results",)),
    )),
    NavCategory("learn", "Arena Learn", "graduation-cap", (
        NavItem("Mis cursos", "learning:my_courses", "book-open", ("learn.self", P), also_active=LEARN_ALSO),
        NavItem("Aprobar cursos", "learning:approvals_inbox", "badge-check", visible=_is_course_approver,
                badge=_courses_to_approve),
        NavItem("Catálogo", "learning:catalog_list", "library", ("learn.public.view", P),
                also_active=("learning:catalog_detail", "learning:catalog_create", "learning:catalog_edit")),
        NavItem("Personas", "learning:people_list", "users", ("learn.public.view", P),
                also_active=("learning:person_profile", "learning:course_public")),
        NavItem("Seguimiento", "learning:tracking", "chart-no-axes-column", ("learn.tracking.view", AR),
                also_active=("learning:historic_create", "learning:settings_edit")),
    )),
    NavCategory("mesa", "Mesa de Talento", "table-2", (
        NavItem("Mis evaluaciones", "evaluations:ownership_list", "clipboard-list", ("ownership.self.manage", P),
                also_active=OWNERSHIP_ALSO, group="Mi evaluación"),
        NavItem("Mi retroalimentación", "dashboards:feedback_session_list", "message-circle", visible=_has_feedback,
                also_active=("dashboards:feedback_session_detail",), group="Mi evaluación"),
        NavItem("Validar Ownership", "evaluations:ownership_validation", "circle-check-big", visible=_is_evaluator,
                badge=_ownership_to_validate, group="Por validar"),
        NavItem("Entrega de Valor", "evaluations:value_delivery_list", "package", visible=_captures_vd,
                badge=_vd_to_capture, also_active=("evaluations:value_delivery_capture",), group="Por validar"),
        NavItem("Validar Entrega de Valor", "evaluations:value_delivery_review", "shield-check", visible=_validates_vd,
                badge=_vd_to_validate, group="Por validar"),
        NavItem("Mi área", "dashboards:my_area", "users", ("people.results.view", AR), group="Comité"),
        NavItem("Mesa de Talento", "dashboards:talent_table", "layout-list", ("talent_table.view", AR),
                also_active=("dashboards:talent_person",), group="Comité"),
        NavItem("Escenario Actual", "dashboards:current_scenario_board", "move", ("current_scenario.view", AR),
                group="Comité"),
        NavItem("Avance del periodo", "dashboards:period_progress", "chart-column", ("period_progress.view", P),
                group="Comité"),
        NavItem("Impacto Arena", "evaluations:arena_impact", "star", ("arena_impact.edit", P), group="Comité"),
    )),
    NavCategory("admin", "Administración", "settings", (
        NavItem("Usuarios", "accounts:user_admin", "id-card", ("users.manage", P), also_active=("accounts:user_create",)),
        NavItem("Perfiles y permisos", "access:profile_list", "shield", ("access.manage", P),
                also_active=("access:profile_matrix", "access:effective_access")),
        NavItem("Proyectos", "catalog:project_admin", "folder", ("projects.edit", P),
                also_active=("catalog:project_create", "catalog:project_edit")),
        NavItem("Periodos", "catalog:period_admin", "calendar", ("periods.manage", P),
                also_active=("catalog:period_create", "catalog:period_edit")),
        NavItem("Áreas", "catalog:area_admin", "map", ("areas.manage", P)),
        NavItem("Escenarios", "catalog:scenario_admin", "layers", ("scenarios.manage", P),
                also_active=("catalog:scenario_create", "catalog:scenario_edit")),
        NavItem("Cuestionarios", "questionnaires:admin_list", "list-checks", ("questionnaires.manage", P),
                also_active=("questionnaires:template_edit",)),
    )),
)


def _visible(item: NavItem, user) -> bool:
    if item.perm and not access.has(user, item.perm[0], item.perm[1]):
        return False
    if item.visible is not None and not item.visible(user):
        return False
    return True


def build_nav(request) -> dict:
    """Categorías visibles para el usuario, con estado activo y contadores."""
    user = request.user
    try:
        rm = request.resolver_match
        current = f"{rm.namespace}:{rm.url_name}" if rm and rm.namespace else (rm.url_name if rm else "")
    except AttributeError:
        current = ""
    categories, flat = [], []
    for cat in NAV:
        items = []
        for it in cat.items:
            if not _visible(it, user):
                continue
            try:
                url = reverse(it.url_name)
            except NoReverseMatch:
                continue
            entry = {"label": it.label, "url": url, "icon": it.icon, "name": it.url_name, "group": it.group,
                     "active": current == it.url_name or current in it.also_active,
                     "category": cat.label}
            items.append(entry)
            flat.append(entry)
        if items:
            categories.append({"key": cat.key, "label": cat.label, "icon": cat.icon, "items": items,
                               "active": any(i["active"] for i in items)})
    return {"nav_categories": categories, "nav_items": flat}
