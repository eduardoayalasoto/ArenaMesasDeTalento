"""Nombre de puesto por área × nivel (spec 008). Caché corta para no consultar por cada usuario listado."""

from django.core.cache import cache

_CACHE_KEY = "catalog:positions:v1"
_TTL_SECONDS = 60


def _mapping() -> dict:
    """{(area_id, level_id): (nombre, activo)}; se recarga cada minuto o al guardar un puesto."""
    mapping = cache.get(_CACHE_KEY)
    if mapping is None:
        from apps.catalog.models import Position

        mapping = {
            (p.area_id, p.level_id): (p.name, p.is_active)
            for p in Position.objects.all()
        }
        cache.set(_CACHE_KEY, mapping, _TTL_SECONDS)
    return mapping


def invalidate():
    cache.delete(_CACHE_KEY)


def position_name(area_id, level_id, fallback="") -> str:
    """Nombre del puesto del catálogo; si no existe, `fallback` (normalmente el nombre del nivel)."""
    entry = _mapping().get((area_id, level_id))
    return entry[0] if entry else fallback


def position_defined(area, level) -> bool:
    """True si existe un puesto activo para la combinación área × nivel."""
    entry = _mapping().get((area.pk, level.pk))
    return bool(entry and entry[1])


def user_position_name(user) -> str:
    """Puesto visible de una persona: nombre del catálogo o, sin él, el nombre de su nivel."""
    level = getattr(user, "level", None)
    if level is None:
        return ""
    return position_name(user.area_id, user.level_id, fallback=level.name)


# Cargo (posición) por área; el nivel (Jr/Mid/Snr/Lead) va aparte. Spec 009.
DEFAULT_CARGOS = {
    "CD": "Científico de Datos", "CONS": "Consultor", "ID": "Ingeniero de Datos",
    "PM": "Project Manager", "UXUI": "Diseñador UX/UI",
}


def ensure_default_positions() -> int:
    """Crea los puestos que falten para cada área × nivel (nombre del nivel; escalera propia en CONS).

    Idempotente; no toca los existentes. Devuelve cuántos creó.
    """
    from apps.catalog.models import Area, Position, SeniorityLevel

    levels = list(SeniorityLevel.objects.all())
    created = 0
    for area in Area.objects.all():
        for level in levels:
            name = DEFAULT_CARGOS.get(area.code, area.name)
            _, was_created = Position.objects.get_or_create(area=area, level=level, defaults={"name": name})
            created += was_created
    return created
