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


# --- Posiciones ----------------------------------------------------------------

@transaction.atomic
def save_position(*, pk, area, level, name, is_active):
    from apps.catalog.models import Position
    from apps.core.services import positions

    if Position.objects.filter(area=area, level=level).exclude(pk=pk).exists():
        raise ValidationError(f"Ya existe la posición de {area.name} · {level.name}: edítala en lugar de crear otra.")
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
