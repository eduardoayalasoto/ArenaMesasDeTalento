"""Altas, cambios y bajas de los catálogos Área, Posición y Categoría (spec 009).

Regla común: nunca se borra algo que otra cosa referencia; en ese caso se desactiva.
"""

from django.core.exceptions import ValidationError
from django.db import transaction


def usage(obj) -> list[str]:
    """Descripciones («3 personas») de lo que referencia a `obj`; vacío = se puede borrar."""
    found = []
    for rel in obj._meta.related_objects:
        if rel.related_model._meta.model_name.startswith("historical"):
            continue
        n = rel.related_model._default_manager.filter(**{rel.field.name: obj}).count()
        if n:
            found.append(f"{n} {rel.related_model._meta.verbose_name_plural}")
    return found


def delete_if_unused(obj, label: str):
    used = usage(obj)
    if used:
        raise ValidationError(
            f"No se puede borrar {label}: lo usan {', '.join(used)}. Desactívalo en su lugar."
        )
    obj.delete()


# --- Áreas -------------------------------------------------------------------

@transaction.atomic
def save_area(*, pk, code, name, director_id, is_active):
    from apps.catalog.models import Area

    code = code.strip().upper()
    if Area.objects.filter(code=code).exclude(pk=pk).exists():
        raise ValidationError(f"Ya existe un área con la clave «{code}».")
    area = Area.objects.get(pk=pk) if pk else Area()
    area.code, area.name, area.is_active = code, name.strip(), is_active
    area.director_id = director_id or None
    area.save()
    return area


def delete_area(area):
    delete_if_unused(area, f"el área «{area.name}»")


# --- Niveles -------------------------------------------------------------------

@transaction.atomic
def ensure_level_pillar_weights(level):
    """Un nivel nuevo nace con la ponderación de pilares del nivel anterior más cercano (se ajusta después).

    Sin ponderación, la calificación final de quien tenga ese nivel no se podría calcular.
    """
    from apps.catalog.models import PillarWeight

    if PillarWeight.objects.filter(level=level).exists():
        return None
    base = (
        PillarWeight.objects.filter(level__order__lte=level.order).order_by("-level__order").first()
        or PillarWeight.objects.order_by("level__order").first()
    )
    if base is None:
        return None
    return PillarWeight.objects.create(
        level=level, w_ownership=base.w_ownership, w_value_delivery=base.w_value_delivery,
        w_arena_impact=base.w_arena_impact,
    )


# --- Posiciones ----------------------------------------------------------------

@transaction.atomic
def save_position(*, pk, area, level, name, is_active):
    from apps.catalog.models import Position
    from apps.core.services import positions

    if Position.objects.filter(area=area, level=level).exclude(pk=pk).exists():
        raise ValidationError(
            f"Ya existe la posición de {area.name}{f' · {level.name}' if level else ''}: edítala en lugar de crear otra."
        )
    position = Position.objects.get(pk=pk) if pk else Position()
    position.area, position.level, position.name, position.is_active = area, level, name.strip(), is_active
    position.save()
    positions.invalidate()
    return position


def delete_position(position):
    from apps.accounts.models import User
    from apps.core.services import positions
    from apps.questionnaires.models import QuestionnaireTemplate

    used = []
    people = User.objects.filter(area_id=position.area_id, level_id=position.level_id).count()
    if people:
        used.append(f"{people} persona(s) de esa área y nivel")
    templates = QuestionnaireTemplate.objects.filter(area_id=position.area_id, level_id=position.level_id).count()
    if templates:
        used.append(f"{templates} cuestionario(s)")
    if used:
        raise ValidationError(
            f"No se puede borrar la posición «{position.name}»: la usan {', '.join(used)}. Desactívala en su lugar."
        )
    position.delete()
    positions.invalidate()


# --- Categorías ----------------------------------------------------------------

def delete_category(category):
    if category.code == category.GENERAL_CODE:
        raise ValidationError("La categoría «General» es la base de los cuestionarios y no se borra.")
    delete_if_unused(category, f"la categoría «{category.name}»")


# --- Bloques del catálogo de competencias ---------------------------------------

def _skill_names(text: str) -> list[str]:
    """Skills de un texto «uno por línea» (o separados por «·»), sin vacíos ni repetidos, en orden."""
    names = []
    for line in (text or "").replace("·", "\n").splitlines():
        name = " ".join(line.split())[:160]
        if name and name not in names:
            names.append(name)
    return names


@transaction.atomic
def save_block(*, pk, name, order, is_active, skills_text):
    """Crea o edita un bloque y deja sus skills EXACTAMENTE como el texto (el orden de las líneas es el orden)."""
    from django.utils.text import slugify

    from apps.questionnaires.models import BlockSkill, CompetencyBlock

    name = name.strip()
    if not name:
        raise ValidationError("El nombre del bloque es obligatorio.")
    if CompetencyBlock.objects.filter(name__iexact=name).exclude(pk=pk).exists():
        raise ValidationError(f"Ya existe un bloque llamado «{name}».")
    if pk:
        block = CompetencyBlock.objects.get(pk=pk)
        block.name, block.order, block.is_active = name, order, is_active
        block.save(update_fields=["name", "order", "is_active"])
    else:
        base, code, n = (slugify(name) or "bloque")[:56], None, 2
        code = base
        while CompetencyBlock.objects.filter(code=code).exists():
            code, n = f"{base}-{n}", n + 1
        block = CompetencyBlock.objects.create(code=code, name=name, order=order, is_active=is_active)
    names = _skill_names(skills_text)
    block.skills.exclude(name__in=names).delete()
    for position, skill in enumerate(names, 1):
        BlockSkill.objects.update_or_create(block=block, name=skill, defaults={"order": position})
    return block


def delete_block(block):
    """Un bloque solo se borra si ninguna pregunta lo usa (si no, se desactiva). Sus skills se van con él."""
    n = block.questions.count()
    if n:
        raise ValidationError(
            f"No se puede borrar el bloque «{block.name}»: lo usan {n} pregunta{'s' if n != 1 else ''}. Desactívalo en su lugar."
        )
    block.delete()


# --- Bloques del catálogo de competencias ---------------------------------------

def _skill_names(text: str) -> list[str]:
    """Skills de un texto «uno por línea» (o separados por «·»), sin vacíos ni repetidos, en orden."""
    names = []
    for line in (text or "").replace("·", "\n").splitlines():
        name = " ".join(line.split())[:160]
        if name and name not in names:
            names.append(name)
    return names


@transaction.atomic
def save_block(*, pk, name, order, is_active, skills_text):
    """Crea o edita un bloque y deja sus skills EXACTAMENTE como el texto (el orden de las líneas es el orden)."""
    from django.utils.text import slugify

    from apps.questionnaires.models import BlockSkill, CompetencyBlock

    name = name.strip()
    if not name:
        raise ValidationError("El nombre del bloque es obligatorio.")
    if CompetencyBlock.objects.filter(name__iexact=name).exclude(pk=pk).exists():
        raise ValidationError(f"Ya existe un bloque llamado «{name}».")
    if pk:
        block = CompetencyBlock.objects.get(pk=pk)
        block.name, block.order, block.is_active = name, order, is_active
        block.save(update_fields=["name", "order", "is_active"])
    else:
        base = (slugify(name) or "bloque")[:56]
        code, n = base, 2
        while CompetencyBlock.objects.filter(code=code).exists():
            code, n = f"{base}-{n}", n + 1
        block = CompetencyBlock.objects.create(code=code, name=name, order=order, is_active=is_active)
    names = _skill_names(skills_text)
    block.skills.exclude(name__in=names).delete()
    for position, skill in enumerate(names, 1):
        BlockSkill.objects.update_or_create(block=block, name=skill, defaults={"order": position})
    return block


def delete_block(block):
    """Un bloque solo se borra si ninguna pregunta lo usa (si no, se desactiva). Sus skills se van con él."""
    n = block.questions.count()
    if n:
        raise ValidationError(
            f"No se puede borrar el bloque «{block.name}»: lo usan {n} pregunta{'s' if n != 1 else ''}. Desactívalo en su lugar."
        )
    block.delete()
