"""Catálogo único de permisos (spec 005, research R1).

El catálogo es código: describe qué pantallas y acciones existen. Los perfiles y sus
alcances son datos (`Profile`, `ProfileGrant`) que Talento edita desde la matriz.

Toda ruta del URLconf debe estar protegida por un permiso de este registro o estar en
`EXEMPT_ROUTES`; `apps/core/tests/test_access_coverage.py` lo verifica.
"""

from dataclasses import dataclass, field
from enum import IntEnum


class Scope(IntEnum):
    """Alcance jerárquico: cada nivel incluye a los anteriores (research R2)."""

    NINGUNO = 0
    PROPIO = 10
    ASIGNADO = 20
    AREA = 30
    TODOS = 40

    @property
    def label(self) -> str:
        return SCOPE_LABELS[self]

    @property
    def short(self) -> str:
        return SCOPE_SHORT[self]


SCOPE_LABELS = {
    Scope.NINGUNO: "Sin acceso",
    Scope.PROPIO: "Propio",
    Scope.ASIGNADO: "Asignado",
    Scope.AREA: "Su área",
    Scope.TODOS: "Todos",
}
SCOPE_SHORT = {Scope.NINGUNO: "—", Scope.PROPIO: "P", Scope.ASIGNADO: "A", Scope.AREA: "Ár", Scope.TODOS: "T"}

N, P, A, AR, T = Scope.NINGUNO, Scope.PROPIO, Scope.ASIGNADO, Scope.AREA, Scope.TODOS
ALL_SCOPES = (N, P, A, AR, T)
ON_OFF = (N, T)


@dataclass(frozen=True)
class PermissionDef:
    key: str
    module: str
    screen: str
    action: str  # ver | crear | editar | borrar | aprobar | exportar | asignable | administrar
    scopes: tuple = ON_OFF
    routes: tuple = ()
    kind: str = "screen"  # screen | inline | assignable
    status: str = "active"  # active | pending
    help: str = ""
    extra: dict = field(default_factory=dict, hash=False, compare=False)

    @property
    def is_active(self) -> bool:
        return self.status == "active"


# Rutas siempre accesibles para cualquier usuario autenticado (o públicas).
EXEMPT_ROUTES = frozenset({
    "dashboards:help",
    "accounts:profile",
    "accounts:password_change",
    "accounts:user_photo",
    "accounts:login",
    "accounts:logout",
    "accounts:password_reset",
    "accounts:password_reset_done",
    "accounts:password_reset_confirm",
    "accounts:password_reset_complete",
})

MODULES = ("General", "Evaluaciones", "Mesa de Talento", "Catálogos", "Arena Learn", "Asignables")

PERMISSIONS: tuple[PermissionDef, ...] = (
    # --- General ---------------------------------------------------------------------
    PermissionDef("dashboard.home.view", "General", "Mi tablero (mis resultados)", "ver",
                  (N, P), ("dashboards:home", "dashboards:user_results"),
                  help="Incluye abrir mis propios resultados de periodos anteriores."),
    PermissionDef("people.results.view", "General", "Mi área y resultados de otras personas", "ver",
                  (N, AR, T), ("dashboards:my_area", "dashboards:user_results")),
    PermissionDef("people.results.export", "General", "Exportar calificaciones (.xlsx)", "exportar",
                  (N, AR, T), ("dashboards:export_scores_xlsx",)),
    # --- Evaluaciones ----------------------------------------------------------------
    PermissionDef("ownership.self.manage", "Evaluaciones",
                  "Mis evaluaciones de Ownership: iniciar, responder y elegir evaluadores", "editar",
                  (N, P), ("evaluations:ownership_list", "evaluations:ownership_start",
                           "evaluations:ownership_lead_start", "evaluations:ownership_set_evaluator",
                           "evaluations:ownership_add_evaluator", "evaluations:ownership_remove_evaluator")),
    PermissionDef("ownership.view", "Evaluaciones", "Ver evaluaciones de Ownership", "ver",
                  (N, P, A, AR, T), ("evaluations:ownership_view", "evaluations:ownership_edit",
                                     "evaluations:ownership_autosave"),
                  help="Propio: las mías. Asignado: también donde soy evaluador. Su área / Todos: las de más personas."),
    PermissionDef("ownership.validate", "Evaluaciones", "Validación de Ownership: complementar y cerrar", "aprobar",
                  (N, A, T), ("evaluations:ownership_validation", "evaluations:ownership_save"),
                  help="Asignado: solo como evaluador. Todos: cualquier evaluación (incluye periodos cerrados)."),
    PermissionDef("ownership.admin", "Evaluaciones", "Reabrir y reiniciar evaluaciones de Ownership", "administrar",
                  ON_OFF, ("evaluations:ownership_reopen", "evaluations:ownership_reset",
                           "evaluations:ownership_reset_user")),
    PermissionDef("period.closed.correct", "Evaluaciones",
                  "Corregir registros de un periodo Cerrado (con motivo)", "administrar", ON_OFF, kind="inline"),
    PermissionDef("value_delivery.capture", "Evaluaciones", "Entrega de Valor: lista y captura", "editar",
                  (N, A, T), ("evaluations:value_delivery_list", "evaluations:value_delivery_capture"),
                  help="Asignado: solo proyectos donde es Responsable."),
    PermissionDef("value_delivery.validate", "Evaluaciones", "Validar, regresar y comentar Entrega de Valor",
                  "aprobar", (N, A, T), ("evaluations:value_delivery_review",),
                  help="Asignado: solo proyectos donde es Validador."),
    PermissionDef("arena_impact.edit", "Evaluaciones", "Impacto Arena", "editar",
                  ON_OFF, ("evaluations:arena_impact", "evaluations:arena_impact_autosave")),
    # --- Mesa de Talento y retroalimentación -------------------------------------------
    PermissionDef("feedback.view", "Mesa de Talento", "Retroalimentación: lista y detalle", "ver",
                  (N, A, T), ("dashboards:feedback_session_list", "dashboards:feedback_session_detail"),
                  help="Asignado: las que doy, asisto o recibo."),
    PermissionDef("feedback.edit", "Mesa de Talento", "Editar y reabrir sesiones de retroalimentación", "editar",
                  (N, A, T), kind="inline"),
    PermissionDef("talent_table.view", "Mesa de Talento", "Mesa de Talento (tabla y ficha)", "ver",
                  (N, AR, T), ("dashboards:talent_table", "dashboards:talent_person")),
    PermissionDef("talent_table.edit", "Mesa de Talento",
                  "Ficha: notas, escenarios S+1/S+2 y proyectos revisados", "editar",
                  (N, AR, T), ("dashboards:talent_note_autosave", "dashboards:talent_scenario_toggle",
                               "dashboards:talent_mesa_project_toggle")),
    PermissionDef("talent_table.assign_feedback", "Mesa de Talento",
                  "Asignar o quitar responsables de retroalimentación", "administrar",
                  (N, AR, T), ("dashboards:talent_responsable_add", "dashboards:talent_responsable_remove")),
    PermissionDef("current_scenario.view", "Mesa de Talento", "Escenario Actual: ver tablero", "ver",
                  (N, AR, T), ("dashboards:current_scenario_board",)),
    PermissionDef("current_scenario.move", "Mesa de Talento", "Escenario Actual: mover personas", "editar",
                  (N, AR, T), ("dashboards:current_scenario_move",)),
    PermissionDef("period_progress.view", "Mesa de Talento", "Avance del periodo", "ver",
                  ON_OFF, ("dashboards:period_progress",)),
    # --- Catálogos ---------------------------------------------------------------------
    PermissionDef("users.manage", "Catálogos", "Usuarios: ver, alta y edición (área, nivel, rol, Lead directo)",
                  "editar", ON_OFF, ("accounts:user_admin", "accounts:user_create")),
    PermissionDef("users.reset_password", "Catálogos", "Resetear contraseña", "administrar",
                  ON_OFF, ("accounts:user_reset_password",)),
    PermissionDef("users.delete", "Catálogos", "Eliminar o desactivar usuarios", "borrar",
                  ON_OFF, ("accounts:user_delete",)),
    PermissionDef("projects.edit", "Catálogos", "Proyectos: ver, crear, editar y equipo", "editar",
                  ON_OFF, ("catalog:project_admin", "catalog:project_create", "catalog:project_edit")),
    PermissionDef("projects.close", "Catálogos", "Cerrar, reabrir y eliminar proyectos", "borrar",
                  ON_OFF, ("catalog:project_delete", "catalog:project_reactivate")),
    PermissionDef("periods.manage", "Catálogos", "Periodos: alta, edición, abrir/cerrar y borrar", "administrar",
                  ON_OFF, ("catalog:period_admin", "catalog:period_create", "catalog:period_edit",
                           "catalog:period_delete")),
    PermissionDef("areas.manage", "Catálogos", "Áreas: Director por área", "editar",
                  ON_OFF, ("catalog:area_admin",)),
    PermissionDef("scenarios.manage", "Catálogos", "Escenarios", "editar",
                  ON_OFF, ("catalog:scenario_admin", "catalog:scenario_create", "catalog:scenario_edit")),
    PermissionDef("questionnaires.manage", "Catálogos", "Cuestionarios: editar, versionar y publicar", "editar",
                  ON_OFF, ("questionnaires:admin_list", "questionnaires:template_edit")),
    PermissionDef("weights.manage", "Catálogos", "Ponderaciones", "editar", ON_OFF, status="pending",
                  help="Pantalla pendiente: aún no existe."),
    PermissionDef("access.manage", "Catálogos", "Perfiles y permisos (matriz y asignación de perfiles)",
                  "administrar", ON_OFF,
                  ("access:profile_list", "access:profile_matrix", "access:profile_delete",
                   "access:profile_duplicate", "access:profile_assign", "access:effective_access")),
    # --- Arena Learn -------------------------------------------------------------------
    PermissionDef("learn.self", "Arena Learn",
                  "Mis cursos: solicitar, registrar, editar, cancelar, pago propio, cerrar y reseña", "editar",
                  (N, P), ("learning:my_courses", "learning:request_start", "learning:request_create",
                           "learning:direct_create", "learning:request_edit", "learning:request_cancel",
                           "learning:request_payment", "learning:request_receipt", "learning:request_complete",
                           "learning:review_edit", "learning:request_not_completed",
                           "learning:evidence_replace")),
    PermissionDef("learn.public.view", "Arena Learn", "Catálogo, Personas y perfil/curso públicos", "ver",
                  ON_OFF, ("learning:catalog_list", "learning:catalog_detail", "learning:people_list",
                           "learning:person_profile", "learning:course_public", "learning:evidence_file")),
    PermissionDef("learn.private.view", "Arena Learn",
                  "Datos privados de cursos (costo, pago, justificación, comprobante, bitácora)", "ver",
                  (N, P, A, AR, T), ("learning:request_detail",),
                  help="Asignado: los míos y donde soy aprobador."),
    PermissionDef("learn.approve.lead", "Arena Learn", "Aprobar cursos — etapa Lead", "aprobar",
                  (N, A, AR, T), ("learning:approvals_inbox", "learning:request_decide"),
                  help="Asignado: como Lead directo o aprobador reasignado. Su área: cualquier Lead del área "
                       "cuando la persona no tiene Lead directo."),
    PermissionDef("learn.approve.direction", "Arena Learn", "Aprobar cursos — etapa Dirección", "aprobar",
                  (N, A, AR, T), ("learning:approvals_inbox", "learning:request_decide"),
                  help="Se prefiere al Director asignado al área; si no hay, cualquiera con este permiso."),
    PermissionDef("learn.approve.talento", "Arena Learn", "Aprobar cursos — etapa Talento", "aprobar",
                  (N, A, T), ("learning:approvals_inbox", "learning:request_decide")),
    PermissionDef("learn.all_requests.view", "Arena Learn", "Ver todas las solicitudes en revisión", "ver",
                  (N, AR, T), kind="inline"),
    PermissionDef("learn.reassign", "Arena Learn",
                  "Gestionar solicitudes de otros: reasignar aprobador, cancelar autorizadas, registrar pago",
                  "administrar", ON_OFF, ("learning:request_reassign",)),
    PermissionDef("learn.evidence.validate", "Arena Learn", "Validar o regresar evidencias", "aprobar",
                  ON_OFF, ("learning:evidence_validate",)),
    PermissionDef("learn.catalog.manage", "Arena Learn", "Catálogo: alta, edición, archivar y promover",
                  "editar", ON_OFF, ("learning:catalog_create", "learning:catalog_edit",
                                     "learning:catalog_archive", "learning:catalog_promote")),
    PermissionDef("learn.tracking.view", "Arena Learn", "Seguimiento: tablero y exporte", "ver",
                  (N, AR, T), ("learning:tracking", "learning:tracking_export")),
    PermissionDef("learn.historic.create", "Arena Learn", "Carga histórica", "crear",
                  ON_OFF, ("learning:historic_create",)),
    PermissionDef("learn.settings.edit", "Arena Learn", "Instrucciones fiscales", "editar",
                  ON_OFF, ("learning:settings_edit",)),
    # --- Asignables: quién puede aparecer en cada selector ----------------------------------
    PermissionDef("assign.ownership_evaluator", "Asignables", "Evaluador de Ownership", "asignable",
                  kind="assignable"),
    PermissionDef("assign.project_role", "Asignables", "Owner, Responsable, Validador y miembro de proyecto",
                  "asignable", kind="assignable"),
    PermissionDef("assign.feedback_responsable", "Asignables", "Responsable de retroalimentación", "asignable",
                  kind="assignable"),
    PermissionDef("assign.direct_lead", "Asignables", "Lead directo", "asignable", kind="assignable"),
    PermissionDef("assign.area_director", "Asignables", "Director de área", "asignable", kind="assignable"),
    PermissionDef("assign.learn_approver", "Asignables", "Aprobador reasignado (Arena Learn)", "asignable",
                  kind="assignable"),
)

BY_KEY: dict[str, PermissionDef] = {p.key: p for p in PERMISSIONS}

ROUTE_TO_KEYS: dict[str, set[str]] = {}
for _p in PERMISSIONS:
    for _r in _p.routes:
        ROUTE_TO_KEYS.setdefault(_r, set()).add(_p.key)

ACTION_ORDER = ("ver", "crear", "editar", "aprobar", "exportar", "borrar", "administrar", "asignable")


def get(key: str) -> PermissionDef:
    try:
        return BY_KEY[key]
    except KeyError as exc:
        raise KeyError(f"Permiso no registrado: {key!r}") from exc


def grouped() -> list[tuple[str, list[PermissionDef]]]:
    """Permisos agrupados por módulo en el orden de `MODULES` (para la matriz)."""
    return [(m, [p for p in PERMISSIONS if p.module == m]) for m in MODULES]
