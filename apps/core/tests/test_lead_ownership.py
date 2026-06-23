"""Pruebas del flujo Lead Ownership Unificado.

Cubre: propiedad is_lead, modelo con project=None, constraints únicos,
servicio get_or_create, vista de lista y scoring del pilar.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Project, ProjectMembership
from apps.core.services import ownership_flow, scoring
from apps.evaluations.models import OwnershipAnswer, OwnershipEvaluation, OwnershipEvaluator

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _close_lead_eval(ev, evaluator):
    """Llena todas las respuestas y cierra la evaluación."""
    from apps.questionnaires.models import Question
    OwnershipEvaluator.objects.get_or_create(evaluation=ev, user=evaluator, defaults={"is_primary": True})
    for q in Question.objects.filter(section__template=ev.template).order_by("order"):
        OwnershipAnswer.objects.get_or_create(evaluation=ev, question=q, defaults={"value": 4})
    ev.strengths = "Liderazgo transversal"
    ev.opportunities = "Delegación"
    ev.save()
    errors = ownership_flow.close_ownership_evaluation(ev)
    assert errors == [], errors
    ev.refresh_from_db()


# ---------------------------------------------------------------------------
# 1. Propiedad is_lead
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_is_lead_property_true(lead_collab):
    assert lead_collab.is_lead is True


@pytest.mark.django_db
def test_is_lead_property_false(collaborator):
    assert collaborator.is_lead is False


# ---------------------------------------------------------------------------
# 2. Modelo — OwnershipEvaluation con project=None
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_model_lead_eval_project_null(lead_collab, period, ownership_template_lead):
    ev = OwnershipEvaluation.objects.create(
        user=lead_collab, project=None, period=period, template=ownership_template_lead,
    )
    ev.refresh_from_db()
    assert ev.project is None


@pytest.mark.django_db
def test_constraint_rejects_duplicate_lead_eval(lead_collab, period, ownership_template_lead):
    OwnershipEvaluation.objects.create(
        user=lead_collab, project=None, period=period, template=ownership_template_lead,
    )
    with pytest.raises(IntegrityError):
        OwnershipEvaluation.objects.create(
            user=lead_collab, project=None, period=period, template=ownership_template_lead,
        )


@pytest.mark.django_db
def test_constraint_allows_normal_eval_alongside_lead_eval(
    lead_collab, period, ownership_template_lead, lead, project_finite
):
    """Un Lead puede tener eval transversal (project=None) y también una de Entrega de Valor normal."""
    OwnershipEvaluation.objects.create(
        user=lead_collab, project=None, period=period, template=ownership_template_lead,
    )
    # Segundo registro con proyecto distinto debe ser aceptado (normal eval rules)
    ev2 = OwnershipEvaluation.objects.create(
        user=lead_collab, project=project_finite, period=period, template=ownership_template_lead,
    )
    assert ev2.pk is not None


# ---------------------------------------------------------------------------
# 3. Servicio get_or_create bifurcado
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_service_creates_lead_eval_with_project_none(lead_collab, period, ownership_template_lead):
    ev, err = ownership_flow.get_or_create_ownership_evaluation(lead_collab, period, project=None)
    assert err is None
    assert ev is not None
    assert ev.project is None
    assert ev.user == lead_collab


@pytest.mark.django_db
def test_service_returns_existing_lead_eval(lead_collab, period, ownership_template_lead):
    ev1, _ = ownership_flow.get_or_create_ownership_evaluation(lead_collab, period, project=None)
    ev2, _ = ownership_flow.get_or_create_ownership_evaluation(lead_collab, period, project=None)
    assert ev1.pk == ev2.pk


# ---------------------------------------------------------------------------
# 4. Vista ownership_list — rama Lead
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_ownership_list_lead_context(lead_collab, period, project_finite):
    ProjectMembership.objects.create(project=project_finite, user=lead_collab)
    lead_collab.photo_data = b"fake"
    lead_collab.save()
    c = Client()
    c.force_login(lead_collab)
    resp = c.get(reverse("evaluations:ownership_list"))
    assert resp.status_code == 200
    assert resp.context["is_lead"] is True
    assert len(resp.context["lead_projects"]) == 1


# ---------------------------------------------------------------------------
# 5. Scoring — pilar Ownership con eval transversal
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_pillar_score_uses_lead_transversal_eval(lead_collab, period, ownership_template_lead, lead):
    ev, _ = ownership_flow.get_or_create_ownership_evaluation(lead_collab, period, project=None)
    _close_lead_eval(ev, lead)
    score = scoring.ownership_pillar_score(lead_collab, period)
    assert score == Decimal("4.00")
