"""Ponderación de pilares por área × posición × nivel (spec 009).

Una posición con fila propia (`PositionPillarWeight`) usa esos pesos; sin ella, rige la
ponderación del nivel (`PillarWeight`, RN-19). Una vez que hay calificaciones finales de personas de
esa posición, los pesos ya no se pueden cambiar (la calificación ya se calculó con ellos).
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

PILLARS = ("w_ownership", "w_value_delivery", "w_arena_impact")


def _tenths(value) -> int:
    """Décimas de porcentaje de una fracción (0.600 -> 600)."""
    return int((Decimal(str(value)) * 1000).to_integral_value())


def effective_weights(user):
    """(w_ownership, w_value_delivery, w_arena_impact) vigentes de una persona."""
    from apps.catalog.models import PositionPillarWeight

    own = PositionPillarWeight.objects.filter(
        position__area_id=user.area_id, position__level_id=user.level_id, position__is_active=True,
    ).first()
    if own is None and user.level_id is None:
        raise ValidationError(
            "Esta posición no usa niveles y no tiene ponderación de pilares propia: "
            "defínela en Catálogos → Ponderación de pilares."
        )
    row = own or user.level.weight
    return row.w_ownership, row.w_value_delivery, row.w_arena_impact


def is_locked(position) -> bool:
    """True si ya hay calificaciones finales de personas con esta área × nivel."""
    from apps.evaluations.models import FinalScore

    return FinalScore.objects.filter(user__area_id=position.area_id, user__level_id=position.level_id).exists()


def matrix():
    """Filas para la pantalla: una por posición, con su ponderación propia o heredada del nivel."""
    from apps.catalog.models import PillarWeight, Position

    inherited = {w.level_id: w for w in PillarWeight.objects.all()}
    rows = []
    for position in Position.objects.select_related("area", "level", "pillar_weight").order_by(
        "area__code", "level__order"
    ):
        own = getattr(position, "pillar_weight", None)
        source = own or (inherited.get(position.level_id) if position.level_id else None)
        rows.append({
            "position": position,
            "own": own is not None,
            "locked": is_locked(position),
            "ownership": _pct(source.w_ownership) if source else "",
            "value_delivery": _pct(source.w_value_delivery) if source else "",
            "arena_impact": _pct(source.w_arena_impact) if source else "",
        })
    return rows


def _pct(fraction) -> str:
    return f"{Decimal(str(fraction)) * 100:.1f}"


@transaction.atomic
def save_weights(position, ownership, value_delivery, arena_impact):
    """Guarda (crea o actualiza) los pesos en % de una posición. Falla si no suman 100.0, si hay
    un pilar en negativo o si la posición ya tiene calificaciones finales."""
    from apps.catalog.models import PositionPillarWeight

    pcts = [Decimal(str(v)) for v in (ownership, value_delivery, arena_impact)]
    if any(p < 0 or p > 100 for p in pcts):
        raise ValidationError("Cada peso debe estar entre 0 y 100%.")
    if sum(int((p * 10).to_integral_value()) for p in pcts) != 1000:
        raise ValidationError("Los tres pesos deben sumar exactamente 100%.")
    if is_locked(position):
        raise ValidationError(
            "Esta posición ya tiene calificaciones finales: sus pesos ya no se pueden cambiar."
        )
    fractions = [(p / 100).quantize(Decimal("0.001")) for p in pcts]
    obj, _ = PositionPillarWeight.objects.update_or_create(
        position=position, defaults=dict(zip(PILLARS, fractions)),
    )
    return obj


@transaction.atomic
def reset_to_level(position):
    """Quita los pesos propios: la posición vuelve a heredar la ponderación de su nivel."""
    if is_locked(position):
        raise ValidationError("Esta posición ya tiene calificaciones finales: no se puede cambiar.")
    from apps.catalog.models import PositionPillarWeight

    PositionPillarWeight.objects.filter(position=position).delete()
