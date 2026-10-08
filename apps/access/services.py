"""Evaluación y administración de permisos por perfil (spec 005).

- `scope(user, key)` / `has(user, key, at_least)` / `require(...)`: decisiones de acceso.
  Las concesiones del perfil se cargan con 1 consulta y se cachean en el objeto usuario del
  request (los cambios aplican en el siguiente request; research R4).
- Falla cerrado: sin perfil → perfil `colaborador`; permiso sin concesión → Sin acceso.
- El superusuario siempre tiene TODOS.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils.text import slugify

from . import registry
from .registry import Scope

DEFAULT_PROFILE_SLUG = "colaborador"
_CACHE_ATTR = "_access_grants"


def _models():
    from . import models

    return models


# --- Lectura -----------------------------------------------------------------------------


def fallback_slug(user) -> str:
    """Sin perfil asignado: el sugerido por rol/nivel (mismo criterio que la migración, research R8).

    Cubre altas que no pasan por la pantalla de Usuarios (importación CSV, comandos). Nunca da
    más de lo que correspondía al rol; un usuario sin rol reconocible cae en `colaborador`.
    """
    from .seed import suggested_profile_slug

    slug = suggested_profile_slug(user)
    return DEFAULT_PROFILE_SLUG if slug == "superusuario" else slug


def _fallback_q(slug: str):
    """Q de usuarios SIN perfil cuyo perfil sugerido es `slug`."""
    from django.db.models import Q

    if slug == "talento":
        return Q(role="TALENTO")
    if slug == "director":
        return Q(role="DIRECTOR")
    if slug == "lead":
        return Q(level__code="LEAD") & ~Q(role__in=("TALENTO", "DIRECTOR"))
    if slug == DEFAULT_PROFILE_SLUG:
        return ~Q(role__in=("TALENTO", "DIRECTOR")) & (Q(level__isnull=True) | ~Q(level__code="LEAD"))
    return Q(pk__in=[])


def effective_profile(user):
    """Perfil vigente del usuario; sin perfil → el sugerido por rol/nivel (falla cerrado)."""
    m = _models()
    if getattr(user, "profile_id", None):
        return user.profile
    return (m.Profile.objects.filter(slug=fallback_slug(user)).first()
            or m.Profile.objects.filter(slug=DEFAULT_PROFILE_SLUG).first())


def grants_for(user) -> dict[str, Scope]:
    """{clave: alcance} del usuario, cacheado en el objeto (1 consulta por request)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return {}
    cached = getattr(user, _CACHE_ATTR, None)
    if cached is not None:
        return cached
    if user.is_superuser:
        grants = {p.key: Scope.TODOS for p in registry.PERMISSIONS}
    else:
        m = _models()
        profile_id = getattr(user, "profile_id", None)
        qs = m.ProfileGrant.objects.filter(
            **({"profile_id": profile_id} if profile_id else {"profile__slug": fallback_slug(user)})
        ).values_list("permission_key", "scope")
        grants = {k: Scope(s) for k, s in qs if k in registry.BY_KEY}
    try:
        setattr(user, _CACHE_ATTR, grants)
    except AttributeError:  # pragma: no cover - usuarios sin __dict__
        pass
    return grants


def invalidate(user) -> None:
    if hasattr(user, _CACHE_ATTR):
        delattr(user, _CACHE_ATTR)


def scope(user, key: str) -> Scope:
    registry.get(key)  # falla si la clave no existe (evita typos silenciosos)
    return grants_for(user).get(key, Scope.NINGUNO)


def has(user, key: str, at_least: Scope = Scope.PROPIO) -> bool:
    s = scope(user, key)
    return s > Scope.NINGUNO and s >= at_least


def has_any(user, keys, at_least: Scope = Scope.PROPIO) -> bool:
    return any(has(user, k, at_least) for k in keys)


def require(user, key: str, at_least: Scope = Scope.PROPIO) -> Scope:
    if not has(user, key, at_least):
        raise PermissionDenied(f"Sin permiso: {registry.get(key).screen}.")
    return scope(user, key)


def is_admin(user) -> bool:
    """Única definición de "administrador": Talento + superusuario (spec 005, FR-011a).

    Se conserva solo para reglas de negocio que no son permisos configurables.
    """
    return bool(user and user.is_authenticated and (user.is_superuser or getattr(user, "is_talento", False)))


def same_area(viewer, person) -> bool:
    return bool(getattr(viewer, "area_id", None)) and viewer.area_id == getattr(person, "area_id", None)


def allows_person(user, key: str, person, *, assigned: bool = False) -> bool:
    """¿El alcance de `key` cubre a `person`? (propio / relación / área / todos)."""
    s = scope(user, key)
    if s >= Scope.TODOS:
        return True
    if s >= Scope.AREA and same_area(user, person):
        return True
    if s >= Scope.ASIGNADO and assigned:
        return True
    if s >= Scope.PROPIO and person is not None and getattr(person, "pk", None) == user.pk:
        return True
    return False


def users_in_scope(user, key: str):
    """Usuarios que `user` puede ver según el alcance de `key` (filtrado a nivel queryset)."""
    User = get_user_model()
    s = scope(user, key)
    if s >= Scope.TODOS:
        return User.objects.all()
    if s >= Scope.AREA and user.area_id:
        return User.objects.filter(area_id=user.area_id)
    if s >= Scope.PROPIO:
        return User.objects.filter(pk=user.pk)
    return User.objects.none()


def profiles_with(key: str, at_least: Scope = Scope.PROPIO):
    m = _models()
    return m.Profile.objects.filter(grants__permission_key=key, grants__scope__gte=max(int(at_least), 1))


def users_with(key: str, at_least: Scope = Scope.PROPIO, *, include_superusers: bool = False):
    """Usuarios activos cuyo perfil concede `key` con al menos `at_least` (1 consulta, sin N+1)."""
    from django.db.models import Q

    User = get_user_model()
    registry.get(key)
    profiles = profiles_with(key, at_least)
    cond = Q(profile_id__in=list(profiles.values_list("pk", flat=True)))
    for slug in profiles.values_list("slug", flat=True):
        cond |= Q(profile__isnull=True) & _fallback_q(slug)
    if include_superusers:
        cond |= Q(is_superuser=True)
    qs = User.objects.filter(cond, is_active=True, deleted_at__isnull=True)
    return qs if include_superusers else qs.filter(is_superuser=False)


def assignable_users(key: str):
    """Usuarios activos que pueden aparecer en un selector "Asignable como …" (research R9)."""
    perm = registry.get(key)
    if perm.kind != "assignable":
        raise ValueError(f"{key} no es un permiso asignable.")
    return users_with(key)


def effective_access(user) -> dict:
    """Resumen para Talento: perfil, permisos con alcance por módulo y relaciones (FR-022)."""
    grants = grants_for(user)
    modules = []
    for module, perms in registry.grouped():
        rows = [{"perm": p, "scope": grants.get(p.key, Scope.NINGUNO)} for p in perms]
        modules.append({"module": module, "rows": rows,
                        "granted": sum(1 for r in rows if r["scope"] > Scope.NINGUNO)})
    relations = []
    try:
        from apps.evaluations.models import FeedbackResponsible, OwnershipEvaluator

        relations.append(("Evaluador de Ownership",
                          OwnershipEvaluator.objects.filter(user=user).count()))
        relations.append(("Responsable de retroalimentación",
                          FeedbackResponsible.objects.filter(user=user).count()))
    except Exception:  # pragma: no cover - apps opcionales
        pass
    relations.append(("Responsable de proyecto activo", user.responsible_projects.filter(is_active=True).count()))
    relations.append(("Validador de proyecto activo", user.validated_projects.filter(is_active=True).count()))
    relations.append(("Lead directo de", user.direct_reports.filter(deleted_at__isnull=True).count()))
    relations.append(("Director de área", user.directed_areas.count()))
    return {"user": user, "profile": None if user.is_superuser else effective_profile(user),
            "modules": modules, "relations": relations}


# --- Administración (US1/US2) --------------------------------------------------------------


def _log(actor, kind, profile=None, key="", old="", new="", target=None):
    _models().AccessAuditLog.objects.create(
        actor=actor, kind=kind, profile_name=getattr(profile, "name", "") or "",
        permission_key=key, old_value=str(old), new_value=str(new), target_user=target,
    )


def _admin_count() -> int:
    User = get_user_model()
    m = _models()
    ok_profiles = list(m.Profile.objects.filter(
        grants__permission_key="access.manage", grants__scope__gte=Scope.TODOS,
    ).values_list("pk", flat=True))
    return User.objects.filter(
        is_active=True, deleted_at__isnull=True, is_superuser=False, profile_id__in=ok_profiles,
    ).count()


def _assert_admin_survives(before: int):
    """FR-007: un cambio no puede dejar en cero a quienes administran Perfiles y permisos."""
    if before > 0 and _admin_count() == 0:
        raise ValidationError(
            "Ese cambio dejaría al sistema sin nadie que administre Perfiles y permisos. "
            "Conserva al menos una persona con ese acceso."
        )


def _editable(profile):
    if profile.is_system:
        raise ValidationError("El perfil Superusuario es de sistema y no se puede modificar.")


@transaction.atomic
def save_matrix(profile, data: dict[str, int], actor) -> int:
    """Guarda la matriz completa de un perfil. Devuelve cuántas celdas cambiaron (auditoría por diff)."""
    m = _models()
    _editable(profile)
    current = dict(profile.grants.values_list("permission_key", "scope"))
    before = _admin_count()
    changed = 0
    for key, raw in data.items():
        perm = registry.get(key)
        new = Scope(int(raw))
        if new not in perm.scopes:
            raise ValidationError(f"Alcance «{new.label}» no admitido en «{perm.screen}».")
        old = Scope(current.get(key, Scope.NINGUNO))
        if new == old:
            continue
        m.ProfileGrant.objects.update_or_create(profile=profile, permission_key=key, defaults={"scope": int(new)})
        _log(actor, m.AccessAuditLog.Kind.GRANT_CHANGED, profile, key, old.label, new.label)
        changed += 1
    if changed:
        _assert_admin_survives(before)
        profile.save(update_fields=["updated_at"])
    return changed


@transaction.atomic
def create_profile(name: str, actor, *, copy_from=None, description: str = ""):
    m = _models()
    name = " ".join((name or "").split())
    if not name:
        raise ValidationError("Escribe el nombre del perfil.")
    if m.Profile.objects.filter(name__iexact=name).exists():
        raise ValidationError("Ya existe un perfil con ese nombre.")
    base = slugify(name) or "perfil"
    slug, i = base, 2
    while m.Profile.objects.filter(slug=slug).exists():
        slug, i = f"{base}-{i}", i + 1
    profile = m.Profile.objects.create(slug=slug, name=name, description=description)
    if copy_from is not None:
        m.ProfileGrant.objects.bulk_create([
            m.ProfileGrant(profile=profile, permission_key=g.permission_key, scope=g.scope)
            for g in copy_from.grants.all()
        ])
        if not description:
            profile.description = f"Copia de {copy_from.name}"
            profile.save(update_fields=["description"])
    _log(actor, m.AccessAuditLog.Kind.PROFILE_CREATED, profile,
         new=f"copia de {copy_from.name}" if copy_from else "")
    return profile


@transaction.atomic
def rename_profile(profile, name: str, description: str, actor):
    m = _models()
    _editable(profile)
    name = " ".join((name or "").split())
    if not name:
        raise ValidationError("Escribe el nombre del perfil.")
    if m.Profile.objects.filter(name__iexact=name).exclude(pk=profile.pk).exists():
        raise ValidationError("Ya existe un perfil con ese nombre.")
    old = profile.name
    profile.name, profile.description = name, description or ""
    profile.save(update_fields=["name", "description", "updated_at"])
    _log(actor, m.AccessAuditLog.Kind.PROFILE_RENAMED, profile, old=old, new=name)
    return profile


@transaction.atomic
def delete_profile(profile, actor) -> None:
    m = _models()
    _editable(profile)
    if profile.slug == DEFAULT_PROFILE_SLUG:
        raise ValidationError("El perfil Colaborador es el perfil base y no se puede eliminar.")
    n = profile.users.count()
    if n:
        raise ValidationError(f"No se puede eliminar: {n} persona{'s' if n != 1 else ''} tiene{'n' if n != 1 else ''} "
                              "este perfil. Reasígnalas primero.")
    _log(actor, m.AccessAuditLog.Kind.PROFILE_DELETED, profile, old=profile.name)
    profile.delete()


@transaction.atomic
def assign_profile(user, profile, actor) -> bool:
    """Asigna (mueve) el perfil de una persona. Devuelve True si cambió."""
    m = _models()
    if user.is_superuser:
        raise ValidationError("El superusuario no tiene perfil asignable.")
    if profile is not None and profile.is_system:
        raise ValidationError("Ese perfil es de sistema.")
    old = effective_profile(user)
    if getattr(user, "profile_id", None) == getattr(profile, "pk", None):
        return False
    before = _admin_count()
    user.profile = profile
    user.save(update_fields=["profile"])
    invalidate(user)
    _log(actor, m.AccessAuditLog.Kind.PROFILE_ASSIGNED, profile, old=getattr(old, "name", ""),
         new=getattr(profile, "name", ""), target=user)
    _assert_admin_survives(before)
    return True


def out_of_profile_assignments() -> list[dict]:
    """Asignaciones vigentes que ya no cumplen su permiso "Asignable" (FR-021)."""
    from apps.catalog.models import Area, Project

    User = get_user_model()
    rows = []

    def ok_ids(key):
        return set(assignable_users(key).values_list("pk", flat=True))

    lead_ok = ok_ids("assign.direct_lead")
    bad = User.objects.filter(direct_lead__isnull=False, deleted_at__isnull=True).exclude(direct_lead_id__in=lead_ok)
    if bad.exists():
        rows.append({"label": "Lead directo", "count": bad.count(),
                     "examples": [f"{u.full_name} → {u.direct_lead.full_name}" for u in bad.select_related("direct_lead")[:5]]})
    dir_ok = ok_ids("assign.area_director")
    bad_areas = Area.objects.filter(director__isnull=False).exclude(director_id__in=dir_ok)
    if bad_areas.exists():
        rows.append({"label": "Director de área", "count": bad_areas.count(),
                     "examples": [f"{a.name} → {a.director.full_name}" for a in bad_areas.select_related("director")[:5]]})
    proj_ok = ok_ids("assign.project_role")
    from django.db.models import Q

    bad_p = Project.objects.filter(is_active=True).filter(
        Q(responsable__isnull=False) & ~Q(responsable_id__in=proj_ok)
        | Q(validador__isnull=False) & ~Q(validador_id__in=proj_ok)
    )
    if bad_p.exists():
        rows.append({"label": "Responsable o Validador de proyecto", "count": bad_p.count(),
                     "examples": [p.name for p in bad_p[:5]]})
    return rows
