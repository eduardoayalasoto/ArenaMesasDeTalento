"""Comportamiento ANTERIOR a la spec 005, congelado por permiso (research R7).

Fuente: `specs/005-matriz-permisos-perfiles/research-permisos-actuales.md` (as-is verificado contra
el código el 2026-10-07). Solo se usa para la batería de paridad y el comando `access_report`;
puede borrarse una vez activada la matriz en producción.

Orden de cada tupla: (Colaborador, Lead, Director, Talento).
"""

from .registry import AR, A, N, P, T

LEGACY = {
    "dashboard.home.view":            (P,   P,   P,   P),
    "people.results.view":            (P,   AR,  T,   T),   # Colab abría Mi área por URL (solo su fila)
    "people.results.export":          (P,   AR,  T,   T),   # export sin verificación de rol
    "ownership.self.manage":          (P,   P,   P,   P),   # ruta abierta aunque el menú la oculte
    "ownership.view":                 (A,   AR,  T,   T),
    "ownership.validate":             (A,   A,   A,   T),
    "ownership.admin":                (N,   N,   N,   T),
    "period.closed.correct":          (N,   N,   N,   T),
    "value_delivery.capture":         (A,   A,   T,   T),   # _is_admin incluía al Director
    "value_delivery.validate":        (A,   A,   A,   T),
    "arena_impact.edit":              (N,   N,   N,   T),
    "feedback.view":                  (A,   A,   A,   T),
    "feedback.edit":                  (A,   A,   A,   T),
    "talent_table.view":              (N,   N,   T,   T),
    "talent_table.edit":              (N,   N,   N,   T),
    "talent_table.assign_feedback":   (N,   N,   N,   T),
    "current_scenario.view":          (N,   N,   T,   T),
    "current_scenario.move":          (N,   N,   T,   T),
    "period_progress.view":           (N,   N,   N,   T),
    "users.manage":                   (N,   N,   N,   T),
    "users.reset_password":           (N,   N,   N,   T),
    "users.delete":                   (N,   N,   N,   T),
    "projects.edit":                  (N,   T,   T,   T),
    "projects.close":                 (N,   N,   N,   T),
    "periods.manage":                 (N,   N,   N,   T),
    "areas.manage":                   (N,   N,   N,   T),
    "scenarios.manage":               (N,   N,   N,   T),
    "questionnaires.manage":          (N,   N,   N,   T),
    "weights.manage":                 (N,   N,   N,   T),
    "access.manage":                  (N,   N,   N,   T),   # pantalla nueva; equivale a "solo Talento"
    "learn.self":                     (P,   P,   P,   P),
    "learn.public.view":              (T,   T,   T,   T),
    "learn.private.view":             (A,   A,   T,   T),
    "learn.approve.lead":             (A,   AR,  A,   A),
    "learn.approve.direction":        (N,   N,   T,   N),
    "learn.approve.talento":          (N,   N,   N,   T),
    "learn.all_requests.view":        (N,   N,   N,   T),
    "learn.reassign":                 (N,   N,   N,   T),
    "learn.evidence.validate":        (N,   N,   N,   T),
    "learn.catalog.manage":           (N,   N,   N,   T),
    "learn.tracking.view":            (N,   N,   T,   T),
    "learn.historic.create":          (N,   N,   N,   T),
    "learn.settings.edit":            (N,   N,   N,   T),
    "assign.ownership_evaluator":     (T,   T,   T,   T),
    "assign.project_role":            (T,   T,   T,   T),
    "assign.feedback_responsable":    (T,   T,   T,   T),
    "assign.direct_lead":             (T,   T,   T,   T),   # aceptaba a cualquiera
    "assign.area_director":           (N,   N,   T,   N),
    "assign.learn_approver":          (T,   T,   T,   T),   # aceptaba a cualquiera
}

# Correcciones intencionales de FR-011a ("deber ser"): (permiso, perfil) que cambian a propósito.
EXPECTED_CHANGES = {
    ("people.results.view", "colaborador"): "Colaborador ya no abre Mi área ni resultados de otros por URL.",
    ("people.results.export", "colaborador"): "Colaborador ya no exporta calificaciones por URL.",
    ("ownership.self.manage", "director"): "Director ya no abre Mis evaluaciones por URL (no se autoevalúa).",
    ("ownership.self.manage", "talento"): "Talento ya no abre Mis evaluaciones por URL (no se autoevalúa).",
    ("value_delivery.capture", "director"): "Director solo captura Entrega de Valor de proyectos donde es Responsable.",
    ("assign.direct_lead", "colaborador"): "Un Colaborador ya no puede ser elegido como Lead directo.",
    ("assign.direct_lead", "talento"): "Talento ya no puede ser elegido como Lead directo.",
    ("assign.learn_approver", "colaborador"): "Un Colaborador ya no puede ser aprobador reasignado de cursos.",
}

PROFILE_ORDER = ("colaborador", "lead", "director", "talento")


def legacy_for(slug: str) -> dict[str, int]:
    idx = PROFILE_ORDER.index(slug)
    return {key: int(values[idx]) for key, values in LEGACY.items()}
