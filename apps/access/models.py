"""Perfiles y permisos (spec 005). Los perfiles y concesiones son datos editables por Talento."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from . import registry


class Profile(models.Model):
    """Conjunto de permisos con alcance. Cada usuario tiene exactamente uno (Clarification P1)."""

    slug = models.SlugField("clave", max_length=60, unique=True)
    name = models.CharField("nombre", max_length=80, unique=True)
    description = models.CharField("descripción", max_length=240, blank=True)
    is_system = models.BooleanField("de sistema", default=False,
                                    help_text="Superusuario: no se edita ni se asigna desde la UI.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "perfil"
        verbose_name_plural = "perfiles"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProfileGrant(models.Model):
    """Alcance concedido a un perfil para un permiso del registro. Sin fila = Sin acceso."""

    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="grants")
    permission_key = models.CharField("permiso", max_length=80)
    scope = models.PositiveSmallIntegerField("alcance", default=registry.Scope.NINGUNO)

    class Meta:
        verbose_name = "concesión"
        verbose_name_plural = "concesiones"
        constraints = [
            models.UniqueConstraint(fields=["profile", "permission_key"], name="uniq_profile_permission"),
        ]

    def __str__(self):
        return f"{self.profile} · {self.permission_key} = {registry.Scope(self.scope).label}"

    def clean(self):
        try:
            perm = registry.get(self.permission_key)
        except KeyError as exc:
            raise ValidationError(str(exc)) from exc
        if registry.Scope(self.scope) not in perm.scopes:
            raise ValidationError(f"Alcance no admitido para {perm.key}.")


class AccessAuditLog(models.Model):
    """Bitácora inmutable de cambios a perfiles, concesiones y asignaciones (FR-006)."""

    class Kind(models.TextChoices):
        PROFILE_CREATED = "PROFILE_CREATED", "Perfil creado"
        PROFILE_RENAMED = "PROFILE_RENAMED", "Perfil editado"
        PROFILE_DELETED = "PROFILE_DELETED", "Perfil eliminado"
        GRANT_CHANGED = "GRANT_CHANGED", "Permiso cambiado"
        PROFILE_ASSIGNED = "PROFILE_ASSIGNED", "Perfil asignado"

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name="+")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    profile_name = models.CharField(max_length=80, blank=True)
    permission_key = models.CharField(max_length=80, blank=True)
    old_value = models.CharField(max_length=80, blank=True)
    new_value = models.CharField(max_length=80, blank=True)
    target_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "cambio de permisos"
        verbose_name_plural = "bitácora de permisos"
        ordering = ["-created_at", "-pk"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("La bitácora de permisos es inmutable.")
        super().save(*args, **kwargs)
