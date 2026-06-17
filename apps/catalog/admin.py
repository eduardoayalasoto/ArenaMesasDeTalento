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
    list_display = ["name", "kind", "status", "start_date", "end_date"]
    list_filter = ["status", "kind"]


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
