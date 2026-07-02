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


def can_edit_project(user) -> bool:
    """Talento, Director o cualquier colaborador con nivel Lead pueden administrar proyectos."""
    return _is_admin(user) or user.is_lead
