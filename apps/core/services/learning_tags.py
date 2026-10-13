"""Etiquetas gestionables de Arena Learn (spec 006, US1).

Una etiqueta es solo un nombre, único sin distinguir mayúsculas, acentos ni espacios
(`Tag.key`). Se asignan a cursos del catálogo y a solicitudes/registros; Talento las
renombra, fusiona y desactiva.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, QuerySet

from apps.access import services as access

MAX_TAGS = 15
MAX_LENGTH = 60


def _tag_model():
    from apps.learning.models import Tag

    return Tag


def normalize_tag_key(name: str) -> str:
    from apps.learning.models import normalize_tag_key as _key

    return _key(name)


def clean_names(names) -> list[str]:
    """Limpia una lista de nombres: espacios colapsados, sin vacíos ni duplicados por clave."""
    out, seen = [], set()
    for raw in names or ():
        name = " ".join(str(raw or "").split())
        key = normalize_tag_key(name)
        if not key or key in seen:
            continue
        if len(name) > MAX_LENGTH:
            raise ValidationError(f"La etiqueta «{name[:20]}…» es muy larga (máximo {MAX_LENGTH} caracteres).")
        seen.add(key)
        out.append(name)
    if len(out) > MAX_TAGS:
        raise ValidationError(f"Usa como máximo {MAX_TAGS} etiquetas.")
    return out


def resolve(names, actor=None, keep=()) -> list:
    """Nombres -> etiquetas. Crea las que no existen; una etiqueta inactiva no se puede
    asignar de nuevo (FR-006), salvo que el elemento ya la tuviera (`keep`)."""
    Tag = _tag_model()
    names = clean_names(names)
    keep_ids = {t.pk for t in keep}
    existing = {t.key: t for t in Tag.objects.filter(key__in=[normalize_tag_key(n) for n in names])}
    tags = []
    for name in names:
        tag = existing.get(normalize_tag_key(name))
        if tag is None:
            tag = Tag.objects.create(name=name, created_by=actor)
        elif not tag.is_active and tag.pk not in keep_ids:
            raise ValidationError(f"La etiqueta «{tag.name}» está desactivada; elige otra.")
        tags.append(tag)
    return tags


def set_tags(obj, names, actor=None):
    """Asigna exactamente esas etiquetas a un curso o solicitud (M2M `tags`)."""
    obj.tags.set(resolve(names, actor, keep=list(obj.tags.all())))


def suggest(q: str, limit: int = 8, exclude=()) -> QuerySet:
    Tag = _tag_model()
    key = normalize_tag_key(q)
    qs = Tag.objects.filter(is_active=True).exclude(key__in=[normalize_tag_key(e) for e in exclude])
    if key:
        qs = qs.filter(key__contains=key)
    return qs.order_by("name")[:limit]


def with_usage() -> QuerySet:
    """Etiquetas con número de cursos y de solicitudes (FR-005)."""
    return _tag_model().objects.annotate(
        course_count=Count("courses", distinct=True), request_count=Count("requests", distinct=True),
    ).order_by("name")


def _require_manage(actor):
    access.require(actor, "learn.tags.manage")


def rename(tag, name: str, actor):
    _require_manage(actor)
    Tag = _tag_model()
    name = " ".join((name or "").split())
    key = normalize_tag_key(name)
    if not key:
        raise ValidationError("Escribe el nombre de la etiqueta.")
    if len(name) > MAX_LENGTH:
        raise ValidationError(f"Máximo {MAX_LENGTH} caracteres.")
    other = Tag.objects.filter(key=key).exclude(pk=tag.pk).first()
    if other is not None:
        raise ValidationError(f"Ya existe la etiqueta «{other.name}». Si son la misma, fusiónalas.")
    tag.name = name
    tag.save()
    return tag


@transaction.atomic
def merge(src, dst, actor):
    """Mueve los elementos de `src` a `dst` (sin duplicar) y elimina `src`."""
    _require_manage(actor)
    if src.pk == dst.pk:
        raise ValidationError("No puedes fusionar una etiqueta consigo misma.")
    if not dst.is_active:
        raise ValidationError("No puedes fusionar en una etiqueta desactivada.")
    dst.courses.add(*src.courses.all())
    dst.requests.add(*src.requests.all())
    src.delete()
    return dst


def set_active(tag, active: bool, actor):
    _require_manage(actor)
    tag.is_active = active
    tag.save(update_fields=["is_active"])
    return tag


def filter_by_tags(qs: QuerySet, tag_ids, path: str = "tags") -> QuerySet:
    """AND de etiquetas (FR-007): solo elementos que tienen todas."""
    for tid in tag_ids or ():
        qs = qs.filter(**{f"{path}__pk": tid})
    return qs
