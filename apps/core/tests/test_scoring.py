"""Pruebas de la capa de scoring (RN-03/04/05/08/09/12/19/20)."""

from decimal import Decimal

import pytest

from apps.core.services import scoring
from apps.evaluations.models import (
    ArenaImpactScore,
    OwnershipAnswer,
    OwnershipEvaluation,
    ValueDeliveryEvaluation,
)
from apps.questionnaires.models import Question


def _answer(evaluation, values):
    """Crea respuestas: int = valor 1-4; None = N/A."""
    questions = list(Question.objects.filter(section__template=evaluation.template).order_by("order"))
    for q, v in zip(questions, values):
        OwnershipAnswer.objects.create(
            evaluation=evaluation, question=q,
            value=v, is_na=(v is None),
        )


def _ownership_eval(user, project, period, template, status="BORRADOR"):
    return OwnershipEvaluation.objects.create(
        user=user, project=project, period=period, template=template, status=status,
    )


# --- ownership_evaluation_score -------------------------------------------

@pytest.mark.django_db
def test_ownership_score_excludes_na(collaborator, project_finite, period, ownership_template):
    ev = _ownership_eval(collaborator, project_finite, period, ownership_template)
    _answer(ev, [4, 3, 2, None])  # promedio de [4,3,2] = 3.00
    assert scoring.ownership_evaluation_score(ev) == Decimal("3.00")


@pytest.mark.django_db
def test_ownership_score_rounds_half_up(collaborator, project_finite, period, ownership_template):
    ev = _ownership_eval(collaborator, project_finite, period, ownership_template)
    _answer(ev, [2, 2, 2, 2, 2, 2, 2, 3])  # 17/8 = 2.125 -> 2.13
    assert scoring.ownership_evaluation_score(ev) == Decimal("2.13")


@pytest.mark.django_db
def test_ownership_score_all_na_is_none(collaborator, project_finite, period, ownership_template):
    ev = _ownership_eval(collaborator, project_finite, period, ownership_template)
    _answer(ev, [None, None, None])
    assert scoring.ownership_evaluation_score(ev) is None


# --- ownership_pillar_score -----------------------------------------------

@pytest.mark.django_db
def test_ownership_pillar_averages_only_submitted(collaborator, project_finite, project_indefinite, period, ownership_template):
    e1 = _ownership_eval(collaborator, project_finite, period, ownership_template, status="ENVIADA")
    e1.score = Decimal("3.00"); e1.save()
    e2 = _ownership_eval(collaborator, project_indefinite, period, ownership_template, status="ENVIADA")
    e2.score = Decimal("4.00"); e2.save()
    # Un borrador no debe contar.
    assert scoring.ownership_pillar_score(collaborator, period) == Decimal("3.50")


@pytest.mark.django_db
def test_ownership_pillar_none_when_no_submissions(collaborator, period):
    assert scoring.ownership_pillar_score(collaborator, period) is None


# --- value_delivery_project_score (RN-08) ---------------------------------

@pytest.mark.django_db
def test_vd_project_score_finite_uses_time_finite(project_finite, period):
    vd = ValueDeliveryEvaluation.objects.create(
        project=project_finite, period=period,
        client_satisfaction=4, deliverables=3, time_finite=4,
    )
    # (4 + 3 + 4) / 3 = 3.666... -> 3.67
    assert scoring.value_delivery_project_score(vd) == Decimal("3.67")


@pytest.mark.django_db
def test_vd_project_score_indefinite_uses_time_indefinite(project_indefinite, period):
    vd = ValueDeliveryEvaluation.objects.create(
        project=project_indefinite, period=period,
        client_satisfaction=2, deliverables=2, time_indefinite=2,
    )
    assert scoring.value_delivery_project_score(vd) == Decimal("2.00")


# --- value_delivery_pillar_score (RN-09) ----------------------------------

@pytest.mark.django_db
def test_vd_pillar_averages_validated_projects_of_member(collaborator, lead, project_finite, project_indefinite, period):
    from apps.catalog.models import ProjectMembership
    ProjectMembership.objects.create(project=project_finite, user=collaborator)
    ProjectMembership.objects.create(project=project_indefinite, user=collaborator)
    ValueDeliveryEvaluation.objects.create(
        project=project_finite, period=period, status="VALIDADA", score=Decimal("3.00"),
    )
    ValueDeliveryEvaluation.objects.create(
        project=project_indefinite, period=period, status="VALIDADA", score=Decimal("4.00"),
    )
    assert scoring.value_delivery_pillar_score(collaborator, period) == Decimal("3.50")


# --- interpretation_band (RN-20) ------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("score,band", [
    ("4.00", "Excede"),
    ("3.50", "Excede"),
    ("3.49", "Cumple"),
    ("3.00", "Cumple"),
    ("2.99", "Cumple parcial"),
    ("2.00", "Cumple parcial"),
    ("1.99", "No cumple"),
    ("1.00", "No cumple"),
])
def test_interpretation_band(score, band):
    assert scoring.interpretation_band(Decimal(score)) == band


# --- final_score (RN-12/19) -----------------------------------------------

@pytest.mark.django_db
def test_final_score_weighted_by_level(collaborator, period):
    # JR: O .60, EV .20, IA .20 ; O=4, EV=3, IA=2 -> 2.4+.6+.4 = 3.40
    result = scoring.final_score(
        collaborator, period,
        ownership=Decimal("4.00"), value_delivery=Decimal("3.00"), arena=Decimal("2.00"),
    )
    assert result.final_score == Decimal("3.40")
    assert result.band == "Cumple"
    assert result.is_complete is True


@pytest.mark.django_db
def test_final_score_incomplete_when_a_pillar_missing(collaborator, period):
    result = scoring.final_score(
        collaborator, period,
        ownership=Decimal("4.00"), value_delivery=None, arena=Decimal("2.00"),
    )
    assert result.is_complete is False
