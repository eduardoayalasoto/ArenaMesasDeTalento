"""Recálculo y materialización de la calificación final por colaborador-periodo (RN-12/19/20)."""

from apps.core.services import scoring


def recompute_final_score(user, period):
    """Recalcula los 3 pilares y materializa el FinalScore. Devuelve la instancia."""
    from apps.evaluations.models import ArenaImpactScore, FinalScore

    ownership = scoring.ownership_pillar_score(user, period)
    value_delivery = scoring.value_delivery_pillar_score(user, period)
    arena_row = ArenaImpactScore.objects.filter(user=user, period=period).first()
    arena = arena_row.score if arena_row else None

    # Periodo cerrado con ponderación ya congelada: se respeta aunque el catálogo haya cambiado.
    from apps.catalog.models import EvaluationPeriod

    frozen = None
    if period.status == EvaluationPeriod.Status.CERRADO:
        prev = FinalScore.objects.filter(user=user, period=period, w_ownership__isnull=False).first()
        if prev:
            frozen = (prev.w_ownership, prev.w_value_delivery, prev.w_arena_impact)

    result = scoring.final_score(
        user, period, ownership=ownership, value_delivery=value_delivery, arena=arena, weights=frozen
    )
    applied = frozen or (_current_weights(user) if result.is_complete else (None, None, None))

    fs, _ = FinalScore.objects.update_or_create(
        user=user, period=period,
        defaults={
            "w_ownership": applied[0], "w_value_delivery": applied[1], "w_arena_impact": applied[2],
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


def _current_weights(user):
    from apps.core.services import pillar_weights

    return pillar_weights.effective_weights(user)
