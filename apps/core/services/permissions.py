"""Segregación de visibilidad y capacidades por rol (RN-14/15, KB §9).

El filtrado se aplica siempre a nivel queryset; las vistas nunca dependen solo de ocultar botones.
"""

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

User = get_user_model()


def _is_admin(user) -> bool:
    """Talento, Director o superusuario tienen visibilidad total."""
    return bool(
        user.is_superuser or getattr(user, "is_talento", False) or getattr(user, "is_director", False)
    )


def visible_users(viewer) -> QuerySet:
    """Usuarios que el viewer puede ver: todos / su área / solo él (RN-14)."""
    if _is_admin(viewer):
        return User.objects.all()
    if viewer.is_lead and viewer.area_id:
        return User.objects.filter(area_id=viewer.area_id)
    return User.objects.filter(pk=viewer.pk)


def can_view_evaluation(viewer, evaluation) -> bool:
    """Quién puede ver una evaluación de Ownership (RN-15)."""
    if _is_admin(viewer):
        return True
    if evaluation.user_id == viewer.pk:
        return True
    if evaluation.evaluators.filter(user_id=viewer.pk).exists():
        return True
    if viewer.is_lead and viewer.area_id and evaluation.user.area_id == viewer.area_id:
        return True
    return False


def projects_led_by(viewer) -> QuerySet:
    """Proyectos activos donde el usuario es responsable (captura Entrega de Valor)."""
    return viewer.responsible_projects.all()


def projects_validated_by(viewer) -> QuerySet:
    """Proyectos donde el usuario es el Validador de Entrega de Valor asignado."""
    return viewer.validated_projects.all()


def can_validate_ownership(viewer, evaluation) -> bool:
    """Cualquier evaluador asignado (primario o secundario) o un administrador."""
    return _is_admin(viewer) or evaluation.evaluators.filter(user_id=viewer.pk).exists()


def can_capture_value_delivery(viewer, project) -> bool:
    """Solo el responsable del proyecto o un administrador captura la Entrega de Valor."""
    return _is_admin(viewer) or project.responsable_id == viewer.pk


def can_validate_value_delivery(viewer, vd) -> bool:
    """Solo el Validador asignado al proyecto de esa Entrega de Valor, o Talento/superusuario.

    A diferencia de `_is_admin`, aquí NO se incluye a los directores en general:
    un Director solo valida los proyectos donde esté asignado como Validador.
    """
    return bool(viewer.is_admin) or vd.project.validador_id == viewer.pk


def has_value_delivery_validations(viewer) -> bool:
    """Puede entrar a la cola de validación: es Validador de al menos un proyecto, o Talento/superusuario."""
    return bool(viewer.is_admin) or getattr(viewer, "validates_projects", False)


def can_edit_feedback_session(viewer, note) -> bool:
    """Solo un responsable de retroalimentación asignado (primario o secundario) a esa nota, o Talento/superusuario."""
    return bool(viewer.is_admin) or note.responsables.filter(user_id=viewer.pk).exists()


def can_view_feedback_session(viewer, note) -> bool:
    """Ver (no necesariamente editar): quien puede editar, más el propio colaborador de la nota
    (quien recibe la retroalimentación puede consultarla en solo lectura)."""
    return can_edit_feedback_session(viewer, note) or note.user_id == viewer.pk


def has_feedback_sessions(viewer) -> bool:
    """Tiene al menos una asignación como responsable de retroalimentación."""
    return viewer.feedback_responsable_records.exists()


def can_edit_project(user) -> bool:
    """Talento, Director o cualquier colaborador con nivel Lead pueden administrar proyectos."""
    return _is_admin(user) or user.is_lead


def is_period_correction_allowed(user) -> bool:
    """Solo Talento/superusuario puede corregir un registro de un periodo ya Cerrado (FR-006)."""
    return bool(user.is_admin)


# --- Arena Learn (spec 004) ------------------------------------------------------
# Excepción explícita y acotada a RN-14: la ficha pública y la sección Arena Learn de
# cualquier persona son visibles para todo usuario autenticado. Calificaciones,
# evaluaciones, escenarios y retroalimentación siguen con `visible_users`.


def can_view_learning_profile(viewer, person) -> bool:
    """Cualquier usuario autenticado ve la ficha pública + Arena Learn de otra persona."""
    return bool(viewer and viewer.is_authenticated)


def can_view_course_public(viewer, req) -> bool:
    """Vista pública de un curso: solo estados públicos (o siempre para quien ve lo privado)."""
    if not (viewer and viewer.is_authenticated):
        return False
    return req.is_public or can_view_course_private(viewer, req)


def can_view_course_private(viewer, req) -> bool:
    """Costo, pago, justificación, comprobante y bitácora: dueño, sus aprobadores,
    Talento/superusuario y Dirección (FR-024/025)."""
    if not (viewer and viewer.is_authenticated):
        return False
    if req.user_id == viewer.pk or _is_admin(viewer):
        return True
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
    """Catálogo, validación de evidencia, reasignación, histórico, configuración."""
    return bool(viewer.is_admin)


def can_view_learning_tracking(viewer) -> bool:
    return bool(viewer.is_admin or viewer.is_director)
