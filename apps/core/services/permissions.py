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
    if evaluation.validator_id == viewer.pk:
        return True
    if viewer.is_lead and viewer.area_id and evaluation.user.area_id == viewer.area_id:
        return True
    return False


def projects_led_by(viewer) -> QuerySet:
    """Proyectos activos liderados por el usuario."""
    return viewer.led_projects.all()


def can_validate_ownership(viewer, evaluation) -> bool:
    """Solo el validador designado (líder del proyecto) o un administrador."""
    return _is_admin(viewer) or evaluation.validator_id == viewer.pk


def can_capture_value_delivery(viewer, project) -> bool:
    """Solo el líder del proyecto o un administrador captura la Entrega de Valor."""
    return _is_admin(viewer) or project.lead_id == viewer.pk


def can_validate_value_delivery(viewer) -> bool:
    """Solo el Director (o superusuario) valida la Entrega de Valor."""
    return bool(viewer.is_superuser or getattr(viewer, "is_director", False))
