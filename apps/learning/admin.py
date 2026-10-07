"""Admin de Arena Learn (soporte del superusuario)."""

from django.contrib import admin

from .models import ApprovalStep, CatalogCourse, CourseEvidence, CourseRequest, CourseReview, LearningSettings


@admin.register(CatalogCourse)
class CatalogCourseAdmin(admin.ModelAdmin):
    list_display = ["name", "provider", "kind", "is_active"]
    list_filter = ["kind", "is_active"]
    search_fields = ["name", "provider", "tags"]


class ApprovalStepInline(admin.TabularInline):
    model = ApprovalStep
    extra = 0
    can_delete = False
    readonly_fields = ["stage", "actor", "action", "from_status", "to_status", "comment", "assigned_to", "created_at"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CourseRequest)
class CourseRequestAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "status", "current_stage", "origin", "created_at"]
    list_filter = ["status", "current_stage", "origin"]
    search_fields = ["name", "user__full_name", "user__email"]
    inlines = [ApprovalStepInline]


@admin.register(CourseEvidence)
class CourseEvidenceAdmin(admin.ModelAdmin):
    list_display = ["filename", "request", "kind", "validation", "size"]


admin.site.register(CourseReview)
admin.site.register(LearningSettings)
