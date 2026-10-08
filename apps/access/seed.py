"""Matriz semilla "deber ser" (spec 005, seed-matrix.md aprobada por el usuario el 2026-10-07).

Se aplica una sola vez con la migración de datos `0002_seed_profiles`. Después los perfiles
se editan desde la matriz (son datos, no código).
"""

from .registry import AR, A, N, P, T

PROFILES = (
    ("colaborador", "Colaborador", "Perfil base: lo propio y lo que se le asigna."),
    ("lead", "Lead", "Lead de área: ve su área; aprueba la etapa Lead de cursos."),
    ("director", "Director", "Dirección: Mesa de Talento, Escenario Actual y aprobación de cursos."),
    ("talento", "Talento", "Talento y Cultura: administración completa."),
)
SUPERUSER = ("superusuario", "Superusuario", "Acceso total; de sistema.")

#                                        Colab Lead Dir  Tal
SEED_MATRIX = {
    "dashboard.home.view":            (P,   P,   P,   P),
    "people.results.view":            (N,   AR,  T,   T),
    "people.results.export":          (N,   AR,  T,   T),
    "ownership.self.manage":          (P,   P,   N,   N),
    "ownership.view":                 (A,   AR,  T,   T),
    "ownership.validate":             (A,   A,   A,   T),
    "ownership.admin":                (N,   N,   N,   T),
    "period.closed.correct":          (N,   N,   N,   T),
    "value_delivery.capture":         (A,   A,   A,   T),
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
    "access.manage":                  (N,   N,   N,   T),
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
    "assign.direct_lead":             (N,   T,   T,   N),
    "assign.area_director":           (N,   N,   T,   N),
    "assign.learn_approver":          (N,   T,   T,   T),
}

PROFILE_ORDER = ("colaborador", "lead", "director", "talento")


def matrix_for(slug: str) -> dict[str, int]:
    idx = PROFILE_ORDER.index(slug)
    return {key: int(values[idx]) for key, values in SEED_MATRIX.items()}


def suggested_profile_slug(user) -> str:
    """Perfil sugerido al migrar y al dar de alta (research R8). El nivel solo sugiere."""
    if getattr(user, "is_superuser", False):
        return "superusuario"
    role = getattr(user, "role", "")
    if role == "TALENTO":
        return "talento"
    if role == "DIRECTOR":
        return "director"
    level = getattr(user, "level", None)
    if level is not None and getattr(level, "code", "") == "LEAD":
        return "lead"
    return "colaborador"
