"""Filtros utilitarios de plantilla."""

from django import template

register = template.Library()


@register.filter
def get_item(mapping, key):
    """Acceso a un dict por clave dinámica: {{ mydict|get_item:some_id }}."""
    if mapping is None:
        return None
    return mapping.get(key)
