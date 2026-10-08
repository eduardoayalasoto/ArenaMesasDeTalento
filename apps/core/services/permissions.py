"""Visibilidad y capacidades (RN-14/15, KB §9) — fachada sobre la matriz de perfiles (spec 005).

Las funciones conservan su firma para no tocar a sus ~40 llamadores, pero ya no deciden por
rol: consultan el perfil del usuario (`apps.access.services`) y, cuando aplica, la relación
(evaluador, responsable, validador…). El filtrado sigue siendo a nivel queryset.
"""

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.access import services as access
from apps.access.registry import Scope

User = get_user_model()


def visible_users(viewer) -> QuerySet:
    """Personas cuyos resultados puede ver: según `people.results.view` (su área / todos), o solo él."""
    if access.has(viewer, "people.results.view", Scope.AREA):
        return access.users_in_scope(viewer, "people.results.view")
    return User.objects.filter(pk=viewer.pk)


def can_view_evaluation(viewer, evaluation) -> bool:
    """Quién puede ver una evaluación de Ownership (RN-15): por alcance de `ownership.view`."""
    is_evaluator = evaluation.evaluators.filter(user_id=viewer.pk).exists()
    return access.allows_person(viewer, "ownership.view", evaluation.user, assigned=is_evaluator)


def projects_led_by(viewer) -> QuerySet:
    """Proyectos activos donde el usuario es responsable (captura Entrega de Valor)."""
    return viewer.responsible_projects.all()


def projects_validated_by(viewer) -> QuerySet:
    """Proyectos donde el usuario es el Validador de Entrega de Valor asignado."""
    return viewer.validated_projects.all()


def can_validate_ownership(viewer, evaluation) -> bool:
    """Evaluador asignado (alcance Asignado) o alcance Todos en `ownership.validate`."""
    if access.has(viewer, "ownership.validate", Scope.TODOS):
        return True
    return access.has(viewer, "ownership.validate", Scope.ASIGNADO) and evaluation.evaluators.filter(
        user_id=viewer.pk
    ).exists()


def can_capture_value_delivery(viewer, project) -> bool:
    """Responsable del proyecto (Asignado) o alcance Todos en `value_delivery.capture`."""
    if access.has(viewer, "value_delivery.capture", Scope.TODOS):
        return True
    return access.has(viewer, "value_delivery.capture", Scope.ASIGNADO) and project.responsable_id == viewer.pk


def can_validate_value_delivery(viewer, vd) -> bool:
    """Validador asignado al proyecto (Asignado) o alcance Todos en `value_delivery.validate`."""
    if access.has(viewer, "value_delivery.validate", Scope.TODOS):
        return True
    return access.has(viewer, "value_delivery.validate", Scope.ASIGNADO) and vd.project.validador_id == viewer.pk


def has_value_delivery_validations(viewer) -> bool:
    """Puede entrar a la cola de validación: alcance Todos, o es Validador de algún proyecto activo."""
    if access.has(viewer, "value_delivery.validate", Scope.TODOS):
        return True
    return access.has(viewer, "value_delivery.validate", Scope.ASIGNADO) and getattr(
        viewer, "validates_projects", False
    )


def can_edit_feedback_session(viewer, note) -> bool:
    """Responsable asignado a esa nota (Asignado) o alcance Todos en `feedback.edit`."""
    if access.has(viewer, "feedback.edit", Scope.TODOS):
        return True
    return access.has(viewer, "feedback.edit", Scope.ASIGNADO) and note.responsables.filter(
        user_id=viewer.pk
    ).exists()


def can_view_feedback_session(viewer, note) -> bool:
    """Ver: quien puede editar, más el colaborador de la nota (la recibe), según `feedback.view`."""
    if access.has(viewer, "feedback.view", Scope.TODOS):
        return True
    if not access.has(viewer, "feedback.view", Scope.ASIGNADO):
        return False
    return note.user_id == viewer.pk or note.responsables.filter(user_id=viewer.pk).exists()


def sees_all_feedback(viewer) -> bool:
    return access.has(viewer, "feedback.view", Scope.TODOS)


def has_feedback_sessions(viewer) -> bool:
    """Tiene al menos una asignación como responsable de retroalimentación."""
    return viewer.feedback_responsable_records.exists()


def can_edit_project(user) -> bool:
    """Ver, crear y editar proyectos y su equipo (`projects.edit`)."""
    return access.has(user, "projects.edit")


def can_close_project(user) -> bool:
    """Cerrar, reabrir y eliminar proyectos (`projects.close`)."""
    return access.has(user, "projects.close")


def is_period_correction_allowed(user) -> bool:
    """Corregir un registro de un periodo ya Cerrado, con motivo (`period.closed.correct`)."""
    return access.has(user, "period.closed.correct")


def can_admin_ownership(user) -> bool:
    """Reabrir y reiniciar evaluaciones de Ownership (`ownership.admin`)."""
    return access.has(user, "ownership.admin")


def sees_all_ownership(user) -> bool:
    """Navegación histórica de Talento: todas las evaluaciones (`ownership.validate` = Todos)."""
    return access.has(user, "ownership.validate", Scope.TODOS)


def sees_all_value_delivery(user) -> bool:
    """Navegación histórica: todas las Entregas de Valor (`value_delivery.capture` = Todos)."""
    return access.has(user, "value_delivery.capture", Scope.TODOS)


def can_view_talent_person(viewer, person) -> bool:
    return access.allows_person(viewer, "talent_table.view", person)


def can_edit_talent_person(viewer, person) -> bool:
    return access.allows_person(viewer, "talent_table.edit", person)


# --- Arena Learn (spec 004) ------------------------------------------------------
# Excepción explícita y acotada a RN-14: la ficha pública y la sección Arena Learn de
# cualquier persona son visibles según `learn.public.view` (por defecto, todos). Los datos
# privados de cada curso se rigen por `learn.private.view`.


def can_view_learning_profile(viewer, person) -> bool:
    return bool(viewer and viewer.is_authenticated) and access.has(viewer, "learn.public.view")


def can_view_course_public(viewer, req) -> bool:
    """Vista pública de un curso: solo estados públicos (o siempre para quien ve lo privado)."""
    if not (viewer and viewer.is_authenticated):
        return False
    return (req.is_public and access.has(viewer, "learn.public.view")) or can_view_course_private(viewer, req)


def can_view_course_private(viewer, req) -> bool:
    """Costo, pago, justificación, comprobante y bitácora, según el alcance de `learn.private.view`:
    Propio = los míos; Asignado = también donde actué o soy aprobador elegible; Su área; Todos."""
    if not (viewer and viewer.is_authenticated):
        return False
    s = access.scope(viewer, "learn.private.view")
    if s >= Scope.TODOS:
        return True
    if s >= Scope.AREA and access.same_area(viewer, req.user):
        return True
    if s >= Scope.PROPIO and req.user_id == viewer.pk:
        return True
    if s >= Scope.ASIGNADO:
        from apps.core.services import learning_flow

        if req.steps.filter(actor=viewer).exists():
            return True
        if req.current_stage and learning_flow.eligible_approvers(req, req.current_stage).filter(
            pk=viewer.pk
        ).exists():
            return True
    return False


def can_decide_course(viewer, req) -> bool:
    from apps.core.services import learning_flow

    return learning_flow.can_decide(viewer, req)


def can_manage_learning(viewer) -> bool:
    """Catálogo de cursos (alta, edición, archivar, promover)."""
    return access.has(viewer, "learn.catalog.manage")


def can_view_learning_tracking(viewer) -> bool:
    return access.has(viewer, "learn.tracking.view")
