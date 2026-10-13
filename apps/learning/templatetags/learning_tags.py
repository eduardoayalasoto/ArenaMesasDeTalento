"""Tags de Arena Learn para incrustar el resumen en otras pantallas (perfil, Mesa de Talento)."""

from django import template

register = template.Library()


@register.inclusion_tag("learning/_profile_summary.html")
def arena_learn_summary(person, title="Arena Learn", limit=6):
    """Resumen público de los cursos de `person` (solo campos públicos, R6)."""
    from apps.core.services import learning_flow

    reqs = list(learning_flow.learning_public_requests(person)[:limit])
    return {"person": person, "courses": reqs, "title": title}


@register.filter
def hours(value):
    """Decimal('2.0') -> '2 h'; Decimal('1.5') -> '1.5 h'; None -> ''."""
    if value in (None, ""):
        return ""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return ""
    text = f"{num:g}" if num != int(num) else str(int(num))
    return f"{text} h"
