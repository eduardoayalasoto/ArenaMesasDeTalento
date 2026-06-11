"""Versionado y edición de cuestionarios (los cuestionarios son datos administrables)."""

from django.db import transaction


@transaction.atomic
def duplicate_as_new_version(template):
    """Crea una copia BORRADOR con la siguiente versión, copiando secciones, preguntas y escala."""
    from apps.questionnaires.models import (
        Question,
        QuestionnaireTemplate,
        ScaleOption,
        Section,
    )

    next_version = (
        QuestionnaireTemplate.objects.filter(
            kind=template.kind, area=template.area, level=template.level
        ).order_by("-version").first().version
    ) + 1

    copy = QuestionnaireTemplate.objects.create(
        kind=template.kind, area=template.area, level=template.level,
        version=next_version, status=QuestionnaireTemplate.Status.BORRADOR,
        scale_note=template.scale_note,
    )
    for section in template.sections.all():
        new_section = Section.objects.create(
            template=copy, title=section.title, order=section.order
        )
        for q in section.questions.all():
            Question.objects.create(
                section=new_section, order=q.order, title=q.title, text=q.text,
                qtype=q.qtype, weight=q.weight, allow_na=q.allow_na, is_required=q.is_required,
            )
    for opt in template.scale_options.filter(question__isnull=True):
        ScaleOption.objects.create(
            template=copy, value=opt.value, label=opt.label,
            description=opt.description, order=opt.order,
        )
    return copy


@transaction.atomic
def publish_template(template):
    """Publica el cuestionario y archiva el que estuviera publicado para el mismo puesto."""
    from apps.questionnaires.models import QuestionnaireTemplate

    QuestionnaireTemplate.objects.filter(
        kind=template.kind, area=template.area, level=template.level,
        status=QuestionnaireTemplate.Status.PUBLICADO,
    ).exclude(pk=template.pk).update(status=QuestionnaireTemplate.Status.ARCHIVADO)

    template.status = QuestionnaireTemplate.Status.PUBLICADO
    template.save(update_fields=["status"])
    return template
