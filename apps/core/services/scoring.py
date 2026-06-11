"""Capa de cálculo del modelo de desempeño. Funciones puras y testeadas (RN-03/04/05/08/09/12/19/20).

Regla transversal: la escala es 1–4, los N/A se excluyen de todo promedio (RN-03),
y los promedios se redondean a 2 decimales con ROUND_HALF_UP.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

TWO_DP = Decimal("0.01")


def _avg(values) -> Decimal | None:
    """Promedio de una lista de números (Decimal a 2 dp), o None si está vacía."""
    nums = [Decimal(str(v)) for v in values if v is not None]
    if not nums:
        return None
    return (sum(nums) / Decimal(len(nums))).quantize(TWO_DP, rounding=ROUND_HALF_UP)


# --- Pilar 1: Ownership ----------------------------------------------------

def ownership_evaluation_score(evaluation) -> Decimal | None:
    """Promedio de las respuestas numéricas de una evaluación, excluyendo N/A (RN-03/04)."""
    values = [
        a.value
        for a in evaluation.answers.all()
        if not a.is_na and a.value is not None
    ]
    return _avg(values)


def ownership_pillar_score(user, period) -> Decimal | None:
    """Promedio simple de las evaluaciones ENVIADAS del usuario en el periodo (RN-05)."""
    from apps.evaluations.models import OwnershipEvaluation

    scores = OwnershipEvaluation.objects.filter(
        user=user, period=period, status=OwnershipEvaluation.Status.ENVIADA,
        score__isnull=False,
    ).values_list("score", flat=True)
    return _avg(list(scores))


# --- Pilar 2: Entrega de Valor --------------------------------------------

def value_delivery_project_score(vd_eval) -> Decimal | None:
    """Promedio de satisfacción, entregables y el criterio de tiempo aplicable (RN-08)."""
    applicable_time = vd_eval.time_finite if vd_eval.project.is_finite else vd_eval.time_indefinite
    return _avg([vd_eval.client_satisfaction, vd_eval.deliverables, applicable_time])


def value_delivery_pillar_score(user, period) -> Decimal | None:
    """Promedio de los scores VALIDADOS de los proyectos donde el usuario fue miembro (RN-09)."""
    from apps.evaluations.models import ValueDeliveryEvaluation

    scores = ValueDeliveryEvaluation.objects.filter(
        period=period,
        status=ValueDeliveryEvaluation.Status.VALIDADA,
        score__isnull=False,
        project__memberships__user=user,
    ).values_list("score", flat=True)
    return _avg(list(scores))


# --- Bandas de interpretación (RN-20) -------------------------------------

def interpretation_band(score) -> str:
    """≥3.50 Excede · 3.00–3.49 Cumple · 2.00–2.99 Cumple parcial · <2.00 No cumple."""
    s = Decimal(str(score))
    if s >= Decimal("3.50"):
        return "Excede"
    if s >= Decimal("3.00"):
        return "Cumple"
    if s >= Decimal("2.00"):
        return "Cumple parcial"
    return "No cumple"


# --- Calificación final (RN-12/19) ----------------------------------------

@dataclass
class FinalScoreResult:
    ownership: Decimal | None
    value_delivery: Decimal | None
    arena_impact: Decimal | None
    final_score: Decimal | None
    band: str
    is_complete: bool


def final_score(user, period, ownership, value_delivery, arena) -> FinalScoreResult:
    """Promedio ponderado de los 3 pilares según la ponderación del nivel del usuario (RN-12/19)."""
    is_complete = None not in (ownership, value_delivery, arena)

    final = None
    band = ""
    if is_complete:
        weight = user.level.weight  # PillarWeight (OneToOne)
        final = (
            Decimal(str(ownership)) * weight.w_ownership
            + Decimal(str(value_delivery)) * weight.w_value_delivery
            + Decimal(str(arena)) * weight.w_arena_impact
        ).quantize(TWO_DP, rounding=ROUND_HALF_UP)
        band = interpretation_band(final)

    return FinalScoreResult(
        ownership=ownership, value_delivery=value_delivery, arena_impact=arena,
        final_score=final, band=band, is_complete=is_complete,
    )
