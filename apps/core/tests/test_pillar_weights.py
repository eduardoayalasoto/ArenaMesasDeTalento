"""Ponderación de pilares por área × posición × nivel (spec 009)."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.catalog.models import Area, EvaluationPeriod, PillarWeight, Position, PositionPillarWeight, SeniorityLevel
from apps.core.services import pillar_weights, scoring

User = get_user_model()


@pytest.fixture
def setup(db):
    level = SeniorityLevel.objects.create(code="JR", name="Junior", order=1)
    PillarWeight.objects.create(level=level, w_ownership=Decimal("0.60"), w_value_delivery=Decimal("0.20"), w_arena_impact=Decimal("0.20"))
    area = Area.objects.create(code="PM", name="Gestión de Proyectos")
    position = Position.objects.create(area=area, level=level, name="Project Manager")
    user = User.objects.create_user(email="pm1@arena-analytics.com", password=None, full_name="PM Uno",
                                    area=area, level=level)
    return position, user


@pytest.mark.django_db
def test_falls_back_to_level_then_uses_position_weights(setup):
    position, user = setup
    assert pillar_weights.effective_weights(user) == (Decimal("0.60"), Decimal("0.20"), Decimal("0.20"))
    pillar_weights.save_weights(position, "50.0", "30.0", "20.0")
    assert pillar_weights.effective_weights(user) == (Decimal("0.500"), Decimal("0.300"), Decimal("0.200"))
    # El cálculo final usa los pesos de la posición.
    result = scoring.final_score(user, None, ownership=4, value_delivery=2, arena=2)
    assert result.final_score == Decimal("3.00")
    pillar_weights.reset_to_level(position)
    assert not PositionPillarWeight.objects.exists()


@pytest.mark.django_db
def test_weights_must_sum_100_and_stay_editable_with_final_scores(setup):
    from apps.evaluations.models import FinalScore

    position, user = setup
    with pytest.raises(ValidationError):
        pillar_weights.save_weights(position, "50", "30", "30")
    with pytest.raises(ValidationError):
        pillar_weights.save_weights(position, "110", "-5", "-5")
    pillar_weights.save_weights(position, "33.4", "33.3", "33.3")

    period = EvaluationPeriod.objects.create(name="2026", start_date="2026-01-01", end_date="2026-12-31")
    FinalScore.objects.create(user=user, period=period)
    # El catálogo siempre se puede editar: la historia vive en el FinalScore de cada periodo cerrado.
    pillar_weights.save_weights(position, "60", "20", "20")
    pillar_weights.reset_to_level(position)
    assert not PositionPillarWeight.objects.exists()


@pytest.mark.django_db
def test_closed_period_keeps_the_weights_it_was_calculated_with(setup):
    from decimal import Decimal

    from apps.core.services import final_flow
    from apps.evaluations.models import ArenaImpactScore, FinalScore

    position, user = setup
    pillar_weights.save_weights(position, "50", "30", "20")
    period = EvaluationPeriod.objects.create(
        name="2026", start_date="2026-01-01", end_date="2026-12-31", status=EvaluationPeriod.Status.CERRADO)
    ArenaImpactScore.objects.create(user=user, period=period, score=Decimal("3.00"))
    # Congela la ponderación vigente en una calificación ya calculada del periodo cerrado
    FinalScore.objects.create(user=user, period=period, w_ownership=Decimal("0.500"),
                              w_value_delivery=Decimal("0.300"), w_arena_impact=Decimal("0.200"))
    pillar_weights.save_weights(position, "10", "10", "80")  # cambio posterior del catálogo
    fs = final_flow.recompute_final_score(user, period)
    assert (fs.w_ownership, fs.w_value_delivery, fs.w_arena_impact) == (Decimal("0.500"), Decimal("0.300"), Decimal("0.200"))


@pytest.mark.django_db
def test_weight_screen_lists_and_saves(setup, client):
    position, _ = setup
    talento = User.objects.create_user(email="t.pesos@arena-analytics.com", password=None, full_name="Talento",
                                       role=User.Role.TALENTO, photo_data=b"x", photo_mime="image/jpeg")
    client.force_login(talento)
    response = client.get(reverse("catalog:weight_admin"))
    assert response.status_code == 200 and "Project Manager" in response.content.decode()
    response = client.post(reverse("catalog:weight_save"), {
        "position": position.pk, "w_ownership": "40", "w_value_delivery": "40", "w_arena_impact": "20",
    })
    assert response.status_code == 302
    assert PositionPillarWeight.objects.get(position=position).w_ownership == Decimal("0.400")
