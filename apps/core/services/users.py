"""Administración de usuarios: búsqueda, alta, edición, contraseña, baja y bitácora.

Toda acción de Talento sobre una persona pasa por aquí y deja un renglón en `UserAuditLog`
(quién, a quién, qué y cuándo). Las vistas solo validan entrada, llaman al servicio y renderizan.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.utils import timezone

from apps.accounts.models import UserAuditLog

User = get_user_model()

DEFAULT_PASSWORD = "Arena2026!"

STATUS_CHOICES = (
    ("", "Todos los estados"),
    ("activos", "Activos"),
    ("inactivos", "Inactivos"),
    ("incompletos", "Sin área o nivel"),
    ("cambiar", "Debe cambiar contraseña"),
    ("nunca", "Nunca han ingresado"),
)

_TRACKED = (
    ("full_name", "Nombre"),
    ("email", "Correo"),
    ("area", "Área"),
    ("level", "Nivel"),
    ("role", "Rol"),
    ("direct_lead", "Lead directo"),
    ("is_active", "Activo"),
)


def base_queryset():
    """Personas administrables (sin superusuarios ni dadas de baja)."""
    return User.objects.filter(is_superuser=False, deleted_at__isnull=True).select_related(
        "area", "level", "profile", "direct_lead")


def search_users(*, q: str = "", area: str = "", level: str = "", role: str = "", status: str = ""):
    """Filtra por CUALQUIER palabra: cada palabra debe aparecer en algún campo visible (AND entre palabras)."""
    qs = base_queryset()
    role_labels = {value: label.lower() for value, label in User.Role.choices}
    for token in (q or "").split():
        cond = (
            Q(full_name__icontains=token) | Q(email__icontains=token)
            | Q(area__name__icontains=token) | Q(area__code__icontains=token)
            | Q(level__name__icontains=token) | Q(profile__name__icontains=token)
            | Q(direct_lead__full_name__icontains=token)
        )
        matching_roles = [v for v, label in role_labels.items() if token.lower() in label]
        if matching_roles:
            cond |= Q(role__in=matching_roles)
        qs = qs.filter(cond)
    if area:
        qs = qs.filter(area__code=area)
    if level:
        qs = qs.filter(level__code=level)
    if role:
        qs = qs.filter(role=role)
    if status == "activos":
        qs = qs.filter(is_active=True)
    elif status == "inactivos":
        qs = qs.filter(is_active=False)
    elif status == "incompletos":
        qs = qs.filter(Q(area__isnull=True) | Q(level__isnull=True))
    elif status == "cambiar":
        qs = qs.filter(must_change_password=True)
    elif status == "nunca":
        qs = qs.filter(last_login__isnull=True)
    return qs.order_by("full_name")


# --- Bitácora ----------------------------------------------------------------------------------


def _label(user) -> str:
    return f"{user.full_name} <{user.email}>"


def log(actor, kind, target, detail: str = "") -> UserAuditLog:
    return UserAuditLog.objects.create(
        actor=actor, kind=kind, target_user=target if getattr(target, "pk", None) else None,
        target_label=_label(target), detail=detail,
    )


def history_for(user, limit: int = 8):
    return UserAuditLog.objects.filter(target_user=user).select_related("actor")[:limit]


def _snapshot(user) -> dict[str, str]:
    def name(obj):
        return getattr(obj, "full_name", None) or getattr(obj, "name", "") if obj else "—"

    return {
        "Nombre": user.full_name, "Correo": user.email,
        "Área": name(user.area), "Nivel": name(user.level),
        "Rol": user.get_role_display(), "Lead directo": name(user.direct_lead),
        "Activo": "Sí" if user.is_active else "No",
    }


def _diff(before: dict[str, str], after: dict[str, str]) -> str:
    return "; ".join(f"{k}: {before[k]} → {after[k]}" for k in after if before[k] != after[k])


# --- Operaciones ---------------------------------------------------------------------------------


@transaction.atomic
def create_user(form, actor):
    """Alta: guarda la persona (form ya validado), le asigna perfil y deja bitácora."""
    from apps.access import services as access
    from apps.access.models import Profile
    from apps.access.seed import suggested_profile_slug

    user = form.save()
    chosen = form.cleaned_data.get("profile")
    if chosen is None:
        chosen = Profile.objects.filter(slug=suggested_profile_slug(user), is_system=False).first()
    if chosen is not None:
        access.assign_profile(user, chosen, actor)
    log(actor, UserAuditLog.Kind.CREATED, user, "; ".join(f"{k}: {v}" for k, v in _snapshot(user).items()))
    return user


@transaction.atomic
def update_user(form, actor):
    """Edición: guarda, asigna perfil si cambió y deja bitácora con el antes/después.

    Lanza `ValidationError` (y revierte todo) si el cambio de perfil dejaría al sistema sin administradores.
    """
    from apps.access import services as access

    before = _snapshot(User.objects.select_related("area", "level", "direct_lead").get(pk=form.instance.pk))
    user = form.save()
    profile = form.cleaned_data.get("profile")
    if "profile" in form.fields and profile is not None:
        access.assign_profile(user, profile, actor)  # su propia bitácora de permisos
    changes = _diff(before, _snapshot(user))
    if changes:
        log(actor, UserAuditLog.Kind.UPDATED, user, changes)
    return user, bool(changes)


@transaction.atomic
def reset_password(user, actor) -> None:
    user.set_password(DEFAULT_PASSWORD)
    user.must_change_password = True
    user.save(update_fields=["password", "must_change_password"])
    log(actor, UserAuditLog.Kind.PASSWORD_RESET, user, "Restablecida a la contraseña inicial; debe cambiarla al ingresar.")


@transaction.atomic
def delete_user(user, actor) -> str:
    """Elimina a la persona. Con evaluaciones históricas solo se da de baja (conserva el historial).

    Devuelve el mensaje de resultado. Lanza `ValidationError` si es la propia persona o hay vínculos protegidos.
    """
    from apps.evaluations.models import ArenaImpactScore, FinalScore, OwnershipEvaluation

    if user.pk == actor.pk:
        raise ValidationError("No puedes eliminarte a ti mismo.")
    name = user.full_name
    has_history = (
        OwnershipEvaluation.objects.filter(user=user).exists()
        or ArenaImpactScore.objects.filter(user=user).exists()
        or FinalScore.objects.filter(user=user).exists()
    )
    if has_history:
        user.is_active = False
        user.deleted_at = timezone.now()
        user.save(update_fields=["is_active", "deleted_at"])
        log(actor, UserAuditLog.Kind.DEACTIVATED, user, "Tiene evaluaciones: se dio de baja y se conserva su historial.")
        return f"{name} eliminado/a. Sus evaluaciones históricas se conservan."
    label = _label(user)
    try:
        with transaction.atomic():
            user.delete()
    except ProtectedError as exc:
        detail = ", ".join(str(o) for o in list(exc.protected_objects)[:3])
        raise ValidationError(f"No se puede eliminar: hay registros vinculados ({detail}…). Reasigna primero.") from exc
    UserAuditLog.objects.create(actor=actor, kind=UserAuditLog.Kind.DELETED, target_user=None,
                                target_label=label, detail="Eliminada permanentemente (sin evaluaciones).")
    return f"{name} eliminado/a permanentemente."
