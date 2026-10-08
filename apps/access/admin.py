"""Admin de perfiles (soporte del superusuario). La edición normal es en Catálogos → Perfiles y permisos."""

from django.contrib import admin

from .models import AccessAuditLog, Profile, ProfileGrant


class ProfileGrantInline(admin.TabularInline):
    model = ProfileGrant
    extra = 0


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_system"]
    inlines = [ProfileGrantInline]


@admin.register(AccessAuditLog)
class AccessAuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "actor", "kind", "profile_name", "permission_key", "old_value", "new_value"]
    readonly_fields = [f.name for f in AccessAuditLog._meta.fields]
