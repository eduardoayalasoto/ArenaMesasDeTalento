"""Versionado y edición de cuestionarios (los cuestionarios son datos administrables)."""

from django.core.exceptions import ValidationError
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
                **{name: getattr(q, name) for name in Question.CHECKLIST_FIELDS},
            )
    for opt in template.scale_options.filter(question__isnull=True):
        ScaleOption.objects.create(
            template=copy, value=opt.value, label=opt.label,
            description=opt.description, order=opt.order,
        )
    return copy


def validate_for_publish(template):
    """Errores (en español) que impiden publicar: sin reactivos de escala, títulos repetidos o sin escala."""
    from collections import Counter

    from apps.questionnaires.models import Question

    questions = Question.objects.filter(section__template=template)
    errors = []
    if not questions.filter(qtype=Question.Type.SCALE).exists():
        errors.append("El cuestionario no tiene reactivos de escala.")
    repeated = [t for t, n in Counter(questions.values_list("title", flat=True)).items() if n > 1]
    if repeated:
        errors.append("Hay títulos repetidos: " + ", ".join(f"«{t}»" for t in repeated) + ".")
    if not template.scale_options.filter(question__isnull=True).exists():
        errors.append("El cuestionario no tiene escala de respuestas.")
    return errors


@transaction.atomic
def publish_template(template):
    """Publica el cuestionario y archiva el que estuviera publicado para el mismo puesto.

    Valida antes de publicar (spec 007, FR-014) y archiva instancia por instancia para que
    el cambio quede en el historial.
    """
    from apps.questionnaires.models import QuestionnaireTemplate

    errors = validate_for_publish(template)
    if errors:
        raise ValidationError(errors)

    previous = QuestionnaireTemplate.objects.filter(
        kind=template.kind, area=template.area, level=template.level,
        status=QuestionnaireTemplate.Status.PUBLICADO,
    ).exclude(pk=template.pk)
    for old in previous:
        old.status = QuestionnaireTemplate.Status.ARCHIVADO
        old.save(update_fields=["status"])

    template.status = QuestionnaireTemplate.Status.PUBLICADO
    template.save(update_fields=["status"])
    return template
