"""Permisos en plantillas: `{% load access_tags %}` y luego `{% if user|can:"clave" %}`.

Para exigir un alcance mínimo: `{% if user|can_scope:"clave:AREA" %}`.
"""

from django import template

from apps.access import services
from apps.access.registry import Scope

register = template.Library()


@register.filter
def can(user, key):
    return services.has(user, key)


@register.filter
def can_scope(user, spec):
    key, _, level = str(spec).partition(":")
    return services.has(user, key, Scope[level or "PROPIO"])


@register.filter
def scope_label(value):
    return Scope(int(value)).label


@register.filter
def scope_short(value):
    return Scope(int(value)).short
