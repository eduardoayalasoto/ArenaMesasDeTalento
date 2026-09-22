"""Admin de catálogos (soporte del superusuario)."""

from django.contrib import admin

from .models import (
    Area,
    EvaluationPeriod,
    PillarWeight,
    Project,
    ProjectMembership,
    SeniorityLevel,
)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active"]
    list_filter = ["is_active"]


@admin.register(SeniorityLevel)
class SeniorityLevelAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "order"]
    ordering = ["order"]


@admin.register(PillarWeight)
class PillarWeightAdmin(admin.ModelAdmin):
    list_display = ["level", "w_ownership", "w_value_delivery", "w_arena_impact"]


@admin.register(EvaluationPeriod)
class EvaluationPeriodAdmin(admin.ModelAdmin):
    """Solo lectura para status/fechas/tipo: las transiciones de ciclo de vida
    (abrir/cerrar) y la edición de fechas viven en las vistas de `catalog`,
    que pasan por `period_lifecycle` — nunca directo desde este admin
    (evitaría el constraint de unicidad y la continuidad, ver spec 002-ciclo-vida-periodos FR-002/FR-005/FR-013)."""

    list_display = ["name", "kind", "status", "start_date", "end_date"]
    list_filter = ["status", "kind"]

    def get_readonly_fields(self, request, obj=None):
        # Al crear (obj is None) sí se capturan status/fechas/tipo iniciales;
        # al editar un periodo ya existente quedan bloqueados.
        if obj is None:
            return []
        return ["status", "start_date", "end_date", "kind"]


class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 1
    autocomplete_fields = ["user"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "client", "owner", "duration_type", "is_active"]
    list_filter = ["is_active", "duration_type"]
    search_fields = ["name", "client"]
    autocomplete_fields = ["owner"]
    inlines = [ProjectMembershipInline]
