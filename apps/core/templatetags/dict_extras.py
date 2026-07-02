"""Filtros utilitarios de plantilla."""

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Acceso a un dict por clave dinámica: {{ mydict|get_item:some_id }}."""
    if mapping is None:
        return None
    return mapping.get(key)


_SCALE_LABELS = {1: "No cumple", 2: "Cumple parcial", 3: "Cumple", 4: "Excede"}


@register.filter
def scale_label(value):
    """Etiqueta de la escala 1–4 (RN-03): {{ value|scale_label }}."""
    try:
        return _SCALE_LABELS.get(int(value))
    except (TypeError, ValueError):
        return None
