"""Pruebas del recálculo materializado de la calificación final (RN-12/19/20, KB §7.3)."""

from decimal import Decimal

import pytest

from apps.catalog.models import ProjectMembership
from apps.core.services import final_flow
from apps.evaluations.models import (
    ArenaImpactScore,
    FinalScore,
    OwnershipEvaluation,
    ValueDeliveryEvaluation,
)


def _submitted_ownership(user, project, period, template, score):
    return OwnershipEvaluation.objects.create(
        user=user, project=project, period=period, template=template,
        status=OwnershipEvaluation.Status.ENVIADA, score=Decimal(score),
    )


@pytest.mark.django_db
def test_recompute_materializes_complete_final(collaborator, project_finite, period, ownership_template):
    ProjectMembership.objects.create(project=project_finite, user=collaborator)
    _submitted_ownership(collaborator, project_finite, period, ownership_template, "4.00")
    ValueDeliveryEvaluation.objects.create(
        project=project_finite, period=period,
        status=ValueDeliveryEvaluation.Status.VALIDADA, score=Decimal("3.00"),
    )
    ArenaImpactScore.objects.create(user=collaborator, period=period, score=Decimal("2.00"))

    fs = final_flow.recompute_final_score(collaborator, period)

    assert fs.ownership_score == Decimal("4.00")
    assert fs.value_delivery_score == Decimal("3.00")
    assert fs.arena_impact_score == Decimal("2.00")
    assert fs.final_score == Decimal("3.40")  # JR: .6*4 + .2*3 + .2*2
    assert fs.band == "Cumple"
    assert fs.is_complete is True
    # Persistido
    assert FinalScore.objects.get(user=collaborator, period=period).final_score == Decimal("3.40")


@pytest.mark.django_db
def test_recompute_incomplete_when_missing_pillar(collaborator, project_finite, period, ownership_template):
    ProjectMembership.objects.create(project=project_finite, user=collaborator)
    _submitted_ownership(collaborator, project_finite, period, ownership_template, "4.00")
    # Sin Entrega de Valor ni Impacto Arena.
    fs = final_flow.recompute_final_score(collaborator, period)
    assert fs.is_complete is False
    assert fs.final_score is None
