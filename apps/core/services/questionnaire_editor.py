"""Versionado y edición de cuestionarios (los cuestionarios son datos administrables)."""

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.services import ownership_weights


@transaction.atomic
def duplicate_as_new_version(template):
    """Crea una copia BORRADOR con la siguiente versión, copiando secciones, preguntas y escala."""
    from apps.questionnaires.models import (
        Question,
        QuestionnaireTemplate,
        ScaleOption,
        Section,
        TemplateCategory,
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
    TemplateCategory.objects.bulk_create([
        TemplateCategory(template=copy, category_id=link.category_id, weight_pct=link.weight_pct)
        for link in template.template_categories.all()
    ])
    for section in template.sections.all():
        new_section = Section.objects.create(
            template=copy, title=section.title, order=section.order
        )
        for q in section.questions.all():
            Question.objects.create(
                section=new_section, order=q.order, title=q.title, text=q.text,
                qtype=q.qtype, weight=q.weight, allow_na=q.allow_na, is_required=q.is_required,
                category_id=q.category_id, weight_pct=q.weight_pct,
                block_id=q.block_id, target_level=q.target_level, is_weighted=q.is_weighted,
                **{name: getattr(q, name) for name in Question.CHECKLIST_FIELDS},
            )
    for opt in template.scale_options.filter(question__isnull=True):
        ScaleOption.objects.create(
            template=copy, value=opt.value, label=opt.label,
            description=opt.description, order=opt.order,
        )
    return copy


@transaction.atomic
def create_template(kind, area=None, level=None):
    """Crea un cuestionario nuevo (versión 1, BORRADOR) para un puesto que aún no tiene ninguno.

    Ownership exige área y nivel; Entrega de Valor no lleva ninguno. La escala y su nota se copian
    del cuestionario más reciente del mismo tipo (publicado si lo hay), para que nazca completo.
    Si ya existe cualquier versión para ese puesto, se rechaza: se debe versionar el existente.
    """
    from apps.questionnaires.models import (
        Category,
        QuestionnaireTemplate,
        ScaleOption,
        Section,
        TemplateCategory,
    )

    Kind = QuestionnaireTemplate.Kind
    if kind == Kind.OWNERSHIP:
        if area is None:
            raise ValidationError("Elige el Área y la posición del cuestionario de Ownership (el nivel es opcional).")
    elif kind == Kind.VALUE_DELIVERY:
        area = level = None
    else:
        raise ValidationError("Elige el tipo de cuestionario.")

    if QuestionnaireTemplate.objects.filter(kind=kind, area=area, level=level).exists():
        raise ValidationError(
            "Ya existe un cuestionario para ese puesto: ábrelo y crea una nueva versión para editarlo."
        )

    with_scale = QuestionnaireTemplate.objects.filter(kind=kind, scale_options__isnull=False).distinct()
    source = (
        with_scale.filter(status=QuestionnaireTemplate.Status.PUBLICADO).order_by("-version", "-pk").first()
        or with_scale.order_by("-version", "-pk").first()
    )
    template = QuestionnaireTemplate.objects.create(
        kind=kind, area=area, level=level, version=1,
        status=QuestionnaireTemplate.Status.BORRADOR,
        scale_note=source.scale_note if source else "",
    )
    if source:
        ScaleOption.objects.bulk_create([
            ScaleOption(template=template, value=o.value, label=o.label,
                        description=o.description, order=o.order)
            for o in source.scale_options.filter(question__isnull=True).order_by("order")
        ])
    if kind == Kind.OWNERSHIP:
        general, _ = Category.objects.get_or_create(
            code=Category.GENERAL_CODE, defaults={"name": "General", "order": 0},
        )
        TemplateCategory.objects.create(template=template, category=general, weight_pct=100)
    Section.objects.create(
        template=template, order=1,
        title="Criterios" if kind == Kind.VALUE_DELIVERY else "Preguntas",
    )
    return template


def delete_draft(template):
    """Descarta un BORRADOR completo (secciones, preguntas, escala y ponderaciones). Nunca uno publicado."""
    from django.db.models import ProtectedError

    from apps.questionnaires.models import QuestionnaireTemplate

    if template.status != QuestionnaireTemplate.Status.BORRADOR:
        raise ValidationError("Solo se puede descartar un borrador; los publicados y archivados se conservan.")
    try:
        template.delete()
    except ProtectedError:
        raise ValidationError("Este borrador ya tiene información ligada y no se puede eliminar.") from None


# --- Secciones --------------------------------------------------------------

def add_section(template, title):
    from apps.questionnaires.models import Section

    last = template.sections.order_by("-order").values_list("order", flat=True).first() or 0
    return Section.objects.create(template=template, title=title, order=last + 1)


def rename_section(section, title):
    section.title = title
    section.save(update_fields=["title"])
    return section


def delete_section(section):
    """Elimina una sección solo si está vacía: nunca borra preguntas por arrastre."""
    if section.questions.exists():
        raise ValidationError(
            "La sección tiene preguntas; muévelas a otra sección o elimínalas antes de quitarla."
        )
    section.delete()


def move_section(template, section_id, direction):
    """Intercambia el orden de una sección con su vecina (arriba/abajo)."""
    from apps.questionnaires.models import Section

    siblings = list(template.sections.order_by("order", "pk"))
    ids = [s.pk for s in siblings]
    if int(section_id) not in ids:
        raise ValidationError("La sección no pertenece a este cuestionario.")
    idx = ids.index(int(section_id))
    swap = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap < len(siblings):
        # Renumera de forma contigua para que dos secciones con el mismo orden nunca queden empatadas.
        siblings[idx], siblings[swap] = siblings[swap], siblings[idx]
        for order, section in enumerate(siblings, start=1):
            section.order = order
        Section.objects.bulk_update(siblings, ["order"])


# --- Escala de respuestas ---------------------------------------------------

def save_scale_option(template, *, value, label, description="", option=None):
    """Crea o actualiza una opción de la escala del cuestionario (value None = N/A)."""
    from apps.questionnaires.models import ScaleOption

    if option is not None:
        option.value, option.label, option.description = value, label, description
        option.save(update_fields=["value", "label", "description"])
        return option
    last = (
        template.scale_options.filter(question__isnull=True)
        .order_by("-order").values_list("order", flat=True).first() or 0
    )
    return ScaleOption.objects.create(
        template=template, value=value, label=label, description=description, order=last + 1,
    )


def delete_scale_option(option):
    option.delete()


def move_scale_option(template, option_id, direction):
    from apps.questionnaires.models import ScaleOption

    options = list(template.scale_options.filter(question__isnull=True).order_by("order", "pk"))
    ids = [o.pk for o in options]
    if int(option_id) not in ids:
        raise ValidationError("La opción no pertenece a este cuestionario.")
    idx = ids.index(int(option_id))
    swap = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap < len(options):
        options[idx], options[swap] = options[swap], options[idx]
        for order, option in enumerate(options, start=1):
            option.order = order
        ScaleOption.objects.bulk_update(options, ["order"])


def has_responses(template) -> bool:
    """True si el cuestionario ya tiene alguna contestación (Ownership o Entrega de Valor)."""
    from apps.evaluations.models import OwnershipAnswer, OwnershipEvaluation

    return (
        OwnershipAnswer.objects.filter(evaluation__template=template).exists()
        or OwnershipEvaluation.objects.filter(template=template, status=OwnershipEvaluation.Status.ENVIADA).exists()
    )


def is_editable(template) -> bool:
    """Borrador y publicado se editan en sitio (también con respuestas: p. ej. para ajustar una ponderación).
    Solo el archivado (versión anterior) es de solo lectura. Lo que dejaría respuestas huérfanas
    (borrar una pregunta contestada, quitar u renumerar una opción de la escala) lo frenan las
    vistas con `has_responses`."""
    return template.status in (template.Status.BORRADOR, template.Status.PUBLICADO)


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
    if template.kind == template.Kind.OWNERSHIP:
        errors.extend(ownership_weights.validate_template_weights(template))
        errors.extend(_position_errors(template))
    return errors


def _position_errors(template):
    """Un cuestionario solo se publica para una combinación área × nivel definida (spec 008, FR-020)."""
    from apps.core.services import positions

    if template.area_id and not positions.position_defined(template.area, template.level):
        level_name = f" · {template.level.name}" if template.level_id else ""
        return [f"No existe una posición activa para {template.area.name}{level_name} en Catálogos → Posiciones."]
    return []


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
