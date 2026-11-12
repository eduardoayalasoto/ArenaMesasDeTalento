"""Migración a «General» al 100% y verificación de no regresión (spec 008, US1)."""

import importlib
from decimal import Decimal
from io import StringIO

import pytest
from django.apps import apps as global_apps
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.core.services import ownership_flow, scoring
from apps.evaluations.models import OwnershipAnswer, OwnershipEvaluation
from apps.questionnaires.models import Category, Question, QuestionnaireTemplate, Section, TemplateCategory

migration = importlib.import_module("apps.questionnaires.migrations.0004_seed_general_category")


@pytest.mark.django_db
def test_general_seed_equivalence_and_verification(collaborator, project_finite, period, area, level_jr):
    # Cuestionario «antiguo»: sin categoría ni configuración, con respuestas y score ya guardado.
    old = QuestionnaireTemplate.objects.create(
        kind=QuestionnaireTemplate.Kind.OWNERSHIP, area=area, level=level_jr, version=1,
        status=QuestionnaireTemplate.Status.PUBLICADO,
    )
    section = Section.objects.create(template=old, title="Checklist", order=1)
    questions = [Question.objects.create(section=section, order=i, title=f"P{i}", qtype="SCALE") for i in range(1, 6)]
    text_q = Question.objects.create(section=section, order=6, title="Comentario", qtype="TEXT_LONG")
    vd = QuestionnaireTemplate.objects.create(kind=QuestionnaireTemplate.Kind.VALUE_DELIVERY, version=1)
    vd_q = Question.objects.create(
        section=Section.objects.create(template=vd, title="VD", order=1), order=1, title="Sat", qtype="SCALE",
    )
    evaluation = OwnershipEvaluation.objects.create(user=collaborator, project=project_finite, period=period, template=old)
    for q, v in zip(questions, [4, 3, 3, None, 2]):
        OwnershipAnswer.objects.create(evaluation=evaluation, question=q, value=v, is_na=v is None)
    before = scoring.ownership_evaluation_score(evaluation)
    assert before == Decimal("3.00")
    evaluation.score = before
    evaluation.status = OwnershipEvaluation.Status.ENVIADA
    evaluation.save()

    migration.seed(global_apps, None)
    migration.seed(global_apps, None)   # idempotente

    general = Category.objects.get(code=Category.GENERAL_CODE)
    link = TemplateCategory.objects.get(template=old)
    assert link.category == general and link.weight_pct == Decimal("100.0")
    assert all(Question.objects.get(pk=q.pk).category == general for q in questions)
    # Texto largo y Entrega de Valor no se tocan.
    assert Question.objects.get(pk=text_q.pk).category is None and Question.objects.get(pk=vd_q.pk).category is None
    assert not TemplateCategory.objects.filter(template=vd).exists()
    assert {c.code for c in Category.objects.all()} >= {
        "general", "delivery_cliente", "desarrollo_producto", "herramientas_gestion", "actitud_persona"}

    # El cálculo con «General» sigue siendo el de antes y el desglose no aporta nada que mostrar.
    evaluation = OwnershipEvaluation.objects.get(pk=evaluation.pk)
    assert scoring.ownership_evaluation_score(evaluation) == before
    assert len(scoring.ownership_category_breakdown(evaluation)) == 1

    out = StringIO()
    call_command("verify_ownership_scores", stdout=out)
    assert "0 diferencias." in out.getvalue() and "1 contra score guardado" in out.getvalue()

    # Si el score guardado no coincide, el comando lo detecta y falla.
    OwnershipEvaluation.objects.filter(pk=evaluation.pk).update(score=Decimal("3.10"))
    with pytest.raises(CommandError):
        call_command("verify_ownership_scores", stdout=StringIO())


@pytest.mark.django_db
def test_close_and_reopen_use_weighted_score(collaborator, project_finite, period, area, level_jr):
    from apps.core.tests.test_scoring_weighted import build_template, evaluation_with

    template, questions = build_template(area, level_jr, [
        ("a", "A", "60.0", [None, None]), ("b", "B", "40.0", [None, None]),
    ])
    evaluation = evaluation_with(collaborator, project_finite, period, template, questions, [4, 4, 2, 2])
    evaluation.strengths, evaluation.opportunities = "Fortaleza", "Oportunidad"
    evaluation.save()

    assert ownership_flow.close_ownership_evaluation(evaluation) == []
    evaluation.refresh_from_db()
    assert evaluation.score == Decimal("3.20") and evaluation.status == OwnershipEvaluation.Status.ENVIADA

    ownership_flow.reopen_ownership_evaluation(evaluation)
    evaluation.refresh_from_db()
    assert evaluation.status == OwnershipEvaluation.Status.BORRADOR
    assert scoring.ownership_evaluation_score(evaluation) == Decimal("3.20")
