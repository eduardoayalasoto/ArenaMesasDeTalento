"""Admin de Django como herramienta de soporte del superusuario (Talento usa pantallas propias)."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["full_name"]
    list_display = ["email", "full_name", "area", "level", "role", "is_active"]
    list_filter = ["role", "area", "level", "is_active", "is_superuser"]
    search_fields = ["email", "full_name"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Datos del colaborador"), {"fields": ("full_name", "area", "level", "role", "photo")}),
        (_("Seguridad"), {"fields": ("must_change_password",)}),
        (_("Permisos"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Fechas"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "area", "level", "role", "password1", "password2"),
        }),
    )
