"""Pruebas de evaluadores múltiples en Ownership (primario + secundarios)."""

import pytest
from django.contrib.auth import get_user_model

from apps.core.services import ownership_flow, permissions
from apps.evaluations.models import OwnershipAnswer, OwnershipEvaluation, OwnershipEvaluator
from apps.questionnaires.models import Question

User = get_user_model()


def _make_secondary(area, level_jr):
    return User.objects.create_user(
        email="secondary@arena-analytics.com", password="x",
        full_name="Evaluador Secundario", area=area, level=level_jr,
    )


def _draft_with_evaluator(collaborator, project_finite, period, ownership_template, evaluator):
    ev = OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period,
        template=ownership_template,
    )
    OwnershipEvaluator.objects.create(evaluation=ev, user=evaluator, is_primary=True)
    for q in Question.objects.filter(section__template=ownership_template).order_by("order"):
        OwnershipAnswer.objects.create(evaluation=ev, question=q, value=3)
    return ev


# --- add_evaluator / remove_evaluator / set_primary -----------------------

@pytest.mark.django_db
def test_add_secondary_evaluator(collaborator, project_finite, period, ownership_template, lead, area, level_jr):
    secondary = _make_secondary(area, level_jr)
    ev = _draft_with_evaluator(collaborator, project_finite, period, ownership_template, lead)

    ownership_flow.add_evaluator(ev, secondary, is_primary=False)

    assert ev.evaluators.filter(user=secondary, is_primary=False).exists()
    assert ev.evaluators.count() == 2


@pytest.mark.django_db
def test_add_evaluator_is_idempotent(collaborator, project_finite, period, ownership_template, lead, area, level_jr):
    secondary = _make_secondary(area, level_jr)
    ev = _draft_with_evaluator(collaborator, project_finite, period, ownership_template, lead)

    ownership_flow.add_evaluator(ev, secondary)
    ownership_flow.add_evaluator(ev, secondary)  # segunda vez no duplica

    assert ev.evaluators.filter(user=secondary).count() == 1


@pytest.mark.django_db
def test_remove_secondary_evaluator(collaborator, project_finite, period, ownership_template, lead, area, level_jr):
    secondary = _make_secondary(area, level_jr)
    ev = _draft_with_evaluator(collaborator, project_finite, period, ownership_template, lead)
    ownership_flow.add_evaluator(ev, secondary)

    ownership_flow.remove_evaluator(ev, secondary)

    assert not ev.evaluators.filter(user=secondary).exists()


@pytest.mark.django_db
def test_remove_primary_evaluator_is_noop(collaborator, project_finite, period, ownership_template, lead):
    ev = _draft_with_evaluator(collaborator, project_finite, period, ownership_template, lead)

    ownership_flow.remove_evaluator(ev, lead)  # es primario, no debe eliminarse

    assert ev.evaluators.filter(user=lead, is_primary=True).exists()


@pytest.mark.django_db
def test_set_primary_evaluator_promotes_secondary(collaborator, project_finite, period, ownership_template, lead, area, level_jr):
    secondary = _make_secondary(area, level_jr)
    ev = _draft_with_evaluator(collaborator, project_finite, period, ownership_template, lead)
    ownership_flow.add_evaluator(ev, secondary)

    ownership_flow.set_primary_evaluator(ev, secondary)

    secondary_rec = ev.evaluators.get(user=secondary)
    lead_rec = ev.evaluators.get(user=lead)
    assert secondary_rec.is_primary is True
    assert lead_rec.is_primary is False


@pytest.mark.django_db
def test_set_primary_with_new_user(collaborator, project_finite, period, ownership_template, lead, area, level_jr):
    new_user = _make_secondary(area, level_jr)
    ev = _draft_with_evaluator(collaborator, project_finite, period, ownership_template, lead)

    ownership_flow.set_primary_evaluator(ev, new_user)

    assert ev.evaluators.get(user=new_user).is_primary is True
    assert ev.evaluators.get(user=lead).is_primary is False


# --- permissions -----------------------------------------------------------

@pytest.mark.django_db
def test_secondary_can_view_evaluation(collaborator, project_finite, period, ownership_template, lead, area, level_jr):
    secondary = _make_secondary(area, level_jr)
    ev = _draft_with_evaluator(collaborator, project_finite, period, ownership_template, lead)
    ownership_flow.add_evaluator(ev, secondary)

    assert permissions.can_view_evaluation(secondary, ev) is True


@pytest.mark.django_db
def test_secondary_can_validate_ownership(collaborator, project_finite, period, ownership_template, lead, area, level_jr):
    secondary = _make_secondary(area, level_jr)
    ev = _draft_with_evaluator(collaborator, project_finite, period, ownership_template, lead)
    ownership_flow.add_evaluator(ev, secondary)

    assert permissions.can_validate_ownership(secondary, ev) is True


@pytest.mark.django_db
def test_removed_secondary_loses_access(collaborator, project_finite, period, ownership_template, lead, area, level_jr):
    secondary = _make_secondary(area, level_jr)
    ev = _draft_with_evaluator(collaborator, project_finite, period, ownership_template, lead)
    ownership_flow.add_evaluator(ev, secondary)
    ownership_flow.remove_evaluator(ev, secondary)

    assert permissions.can_validate_ownership(secondary, ev) is False
    assert permissions.can_view_evaluation(secondary, ev) is False


@pytest.mark.django_db
def test_secondary_can_close_evaluation(collaborator, project_finite, period, ownership_template, lead, area, level_jr):
    secondary = _make_secondary(area, level_jr)
    ev = _draft_with_evaluator(collaborator, project_finite, period, ownership_template, lead)
    ev.strengths = "F"; ev.opportunities = "O"; ev.save()
    ownership_flow.add_evaluator(ev, secondary)

    errors = ownership_flow.close_ownership_evaluation(ev)

    assert errors == []
    ev.refresh_from_db()
    assert ev.is_submitted
