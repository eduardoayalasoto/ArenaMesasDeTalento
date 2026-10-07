"""Tags de Arena Learn para incrustar el resumen en otras pantallas (perfil, Mesa de Talento)."""

from django import template

register = template.Library()


@register.inclusion_tag("learning/_profile_summary.html")
def arena_learn_summary(person, title="Arena Learn", limit=6):
    """Resumen público de los cursos de `person` (solo campos públicos, R6)."""
    from apps.core.services import learning_flow

    reqs = list(learning_flow.learning_public_requests(person)[:limit])
    return {"person": person, "courses": reqs, "title": title}
