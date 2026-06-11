"""Recálculo y materialización de la calificación final por colaborador-periodo (RN-12/19/20)."""

from apps.core.services import scoring


def recompute_final_score(user, period):
    """Recalcula los 3 pilares y materializa el FinalScore. Devuelve la instancia."""
    from apps.evaluations.models import ArenaImpactScore, FinalScore

    ownership = scoring.ownership_pillar_score(user, period)
    value_delivery = scoring.value_delivery_pillar_score(user, period)
    arena_row = ArenaImpactScore.objects.filter(user=user, period=period).first()
    arena = arena_row.score if arena_row else None

    result = scoring.final_score(
        user, period, ownership=ownership, value_delivery=value_delivery, arena=arena
    )

    fs, _ = FinalScore.objects.update_or_create(
        user=user, period=period,
        defaults={
            "ownership_score": ownership,
            "value_delivery_score": value_delivery,
            "arena_impact_score": arena,
            "final_score": result.final_score,
            "band": result.band,
            "is_complete": result.is_complete,
        },
    )
    return fs


def recompute_for_project_members(project, period):
    """Recalcula el final de todos los miembros de un proyecto (tras validar su Entrega de Valor)."""
    for membership in project.memberships.select_related("user"):
        recompute_final_score(membership.user, period)
