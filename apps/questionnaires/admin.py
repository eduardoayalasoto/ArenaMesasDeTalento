"""Admin de cuestionarios (soporte del superusuario)."""

from django.contrib import admin

from .models import Question, QuestionnaireTemplate, ScaleOption, Section


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0


class SectionInline(admin.TabularInline):
    model = Section
    extra = 0


@admin.register(QuestionnaireTemplate)
class QuestionnaireTemplateAdmin(admin.ModelAdmin):
    list_display = ["__str__", "kind", "area", "level", "version", "status", "question_count"]
    list_filter = ["kind", "status", "area", "level"]
    inlines = [SectionInline]


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["title", "template", "order"]
    list_filter = ["template"]
    inlines = [QuestionInline]


@admin.register(ScaleOption)
class ScaleOptionAdmin(admin.ModelAdmin):
    list_display = ["__str__", "template", "question", "value", "order"]
