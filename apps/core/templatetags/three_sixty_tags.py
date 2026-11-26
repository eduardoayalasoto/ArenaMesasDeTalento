"""Mini score de la 360 al owner para Mesa de Talento (spec 010)."""

from django import template

from apps.core.services import three_sixty

register = template.Library()


@register.simple_tag
def three_sixty_for(project, person, viewer):
    """{index, band, n_sent, n_expected} si `person` es el owner de un proyecto con 360 activa, `viewer` puede
    verla y ya hay respuestas; {"pending": True} si está activa pero sin respuestas; si no, None."""
    if not (project.three_sixty_enabled and project.owner_id == person.pk and three_sixty.can_view_results(viewer, project)):
        return None
    period = three_sixty.open_period()
    summary = three_sixty.owner_summary(project, period)
    return summary or {"pending": True}
