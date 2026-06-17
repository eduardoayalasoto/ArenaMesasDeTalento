"""Pruebas del servicio de flujo de Ownership: resolución de plantilla y envío (RN-06)."""

from decimal import Decimal

import pytest

from apps.core.services import ownership_flow
from apps.evaluations.models import OwnershipAnswer, OwnershipEvaluation, OwnershipEvaluator
from apps.questionnaires.models import Question, QuestionnaireTemplate


@pytest.mark.django_db
def test_resolve_template_returns_published_for_area_level(collaborator, ownership_template):
    assert ownership_flow.resolve_ownership_template(collaborator) == ownership_template


@pytest.mark.django_db
def test_resolve_template_ignores_archived(collaborator, ownership_template):
    ownership_template.status = QuestionnaireTemplate.Status.ARCHIVADO
    ownership_template.save()
    assert ownership_flow.resolve_ownership_template(collaborator) is None


def _draft(collaborator, project_finite, period, ownership_template):
    ev = OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period,
        template=ownership_template,
    )
    OwnershipEvaluator.objects.create(evaluation=ev, user=project_finite.responsable, is_primary=True)
    qs = Question.objects.filter(section__template=ownership_template).order_by("order")
    for q in qs:
        OwnershipAnswer.objects.create(evaluation=ev, question=q, value=3)
    return ev


@pytest.mark.django_db
def test_close_blocked_without_strengths_and_opportunities(collaborator, project_finite, period, ownership_template):
    ev = _draft(collaborator, project_finite, period, ownership_template)
    errors = ownership_flow.close_ownership_evaluation(ev)
    assert any("fortalezas" in e.lower() for e in errors)
    assert any("oportunidades" in e.lower() for e in errors)
    ev.refresh_from_db()
    assert ev.status == OwnershipEvaluation.Status.BORRADOR


@pytest.mark.django_db
def test_close_succeeds_and_locks(collaborator, project_finite, period, ownership_template):
    ev = _draft(collaborator, project_finite, period, ownership_template)
    ev.strengths = "Fortaleza (la complementa el líder)"
    ev.opportunities = "Oportunidad"; ev.save()
    errors = ownership_flow.close_ownership_evaluation(ev)
    assert errors == []
    ev.refresh_from_db()
    assert ev.status == OwnershipEvaluation.Status.ENVIADA
    assert ev.score == Decimal("3.00")
    assert ev.submitted_at is not None


@pytest.mark.django_db
def test_close_is_idempotent_guard(collaborator, project_finite, period, ownership_template):
    ev = _draft(collaborator, project_finite, period, ownership_template)
    ev.strengths = "F"; ev.opportunities = "O"; ev.save()
    ownership_flow.close_ownership_evaluation(ev)
    errors = ownership_flow.close_ownership_evaluation(ev)
    assert any("cerrada" in e.lower() for e in errors)


@pytest.mark.django_db
def test_reopen_returns_to_draft_and_recomputes_final(collaborator, project_finite, period, ownership_template):
    from apps.catalog.models import ProjectMembership
    from apps.evaluations.models import FinalScore

    ProjectMembership.objects.get_or_create(project=project_finite, user=collaborator)
    ev = _draft(collaborator, project_finite, period, ownership_template)
    ev.strengths = "F"; ev.opportunities = "O"; ev.save()
    ownership_flow.close_ownership_evaluation(ev)
    fs = FinalScore.objects.get(user=collaborator, period=period)
    assert fs.ownership_score == Decimal("3.00")

    ownership_flow.reopen_ownership_evaluation(ev)
    ev.refresh_from_db()
    assert ev.status == OwnershipEvaluation.Status.BORRADOR
    assert ev.submitted_at is None
    # Al reabrir, la evaluación deja de contar: el pilar de Ownership se recalcula.
    fs.refresh_from_db()
    assert fs.ownership_score is None
