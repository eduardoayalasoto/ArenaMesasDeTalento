"""Calificación de Ownership ponderada por categorías (spec 008)."""

import random
from decimal import Decimal

import pytest

from apps.core.services import scoring
from apps.evaluations.models import OwnershipAnswer, OwnershipEvaluation
from apps.questionnaires.models import Category, Question, QuestionnaireTemplate, Section, TemplateCategory


def build_template(area, level, spec, version=1):
    """spec = [(código, nombre, peso_categoría, [peso_pregunta | None, ...]), ...]. Devuelve (template, preguntas)."""
    tpl = QuestionnaireTemplate.objects.create(
        kind=QuestionnaireTemplate.Kind.OWNERSHIP, area=area, level=level, version=version,
        status=QuestionnaireTemplate.Status.BORRADOR,
    )
    section = Section.objects.create(template=tpl, title="S", order=1)
    questions, order = [], 0
    for idx, (code, name, weight, qweights) in enumerate(spec):
        cat, _ = Category.objects.get_or_create(code=code, defaults={"name": name, "order": idx})
        TemplateCategory.objects.create(template=tpl, category=cat, weight_pct=weight)
        for qw in qweights:
            order += 1
            questions.append(Question.objects.create(
                section=section, order=order, title=f"{code}-{order}", qtype="SCALE",
                category=cat, weight_pct=qw,
            ))
    return tpl, questions


def evaluation_with(user, project, period, template, questions, values):
    ev = OwnershipEvaluation.objects.create(user=user, project=project, period=period, template=template)
    OwnershipAnswer.objects.bulk_create([
        OwnershipAnswer(evaluation=ev, question=q, value=v, is_na=v is None)
        for q, v in zip(questions, values)
    ])
    return ev


@pytest.mark.django_db
def test_weighted_scenarios(collaborator, project_finite, period, area, level_jr):
    # 60/40: A promedia 4.00, B promedia 2.00 → 3.20.
    tpl, qs = build_template(area, level_jr, [
        ("a", "A", "60.0", [None, None]), ("b", "B", "40.0", [None, None]),
    ])
    ev = evaluation_with(collaborator, project_finite, period, tpl, qs, [4, 4, 2, 2])
    assert scoring.ownership_evaluation_score(ev) == Decimal("3.20")
    rows = scoring.ownership_category_breakdown(ev)
    assert [(r.code, r.score, r.answered, r.total) for r in rows] == [
        ("a", Decimal("4.00"), 2, 2), ("b", Decimal("2.00"), 2, 2)]

    # Categoría toda N/A: se excluye y el 100% se redistribuye → solo cuenta A.
    ev.answers.filter(question__category__code="b").update(value=None, is_na=True)
    assert scoring.ownership_evaluation_score(ev) == Decimal("4.00")
    assert [r.score for r in scoring.ownership_category_breakdown(ev)] == [Decimal("4.00"), None]

    # Todo N/A → sin score.
    ev.answers.update(value=None, is_na=True)
    assert scoring.ownership_evaluation_score(ev) is None

    ev.delete()

    # Peso de pregunta dentro de la categoría y peso 0 (se califica pero no pondera).
    tpl2, qs2 = build_template(area, level_jr, [
        ("c", "C", "100.0", ["75.0", "25.0", "0.0"]),
    ], version=2)
    ev2 = evaluation_with(collaborator, project_finite, period, tpl2, qs2, [4, 2, 1])
    assert scoring.ownership_evaluation_score(ev2) == Decimal("3.50")   # 4*.75 + 2*.25; el 1 no pondera
    assert scoring.ownership_category_breakdown(ev2)[0].answered == 3
    ev2.delete()

    # Categoría con peso 0%: se califica y se ve, pero no mueve el total.
    tpl3, qs3 = build_template(area, level_jr, [
        ("d", "D", "100.0", [None]), ("e", "E", "0.0", [None]),
    ], version=3)
    ev3 = evaluation_with(collaborator, project_finite, period, tpl3, qs3, [3, 1])
    assert scoring.ownership_evaluation_score(ev3) == Decimal("3.00")
    # Solo la categoría de peso 0 calificada → sin evidencia ponderada.
    ev3.answers.filter(question__category__code="d").update(value=None, is_na=True)
    assert scoring.ownership_evaluation_score(ev3) is None


@pytest.mark.django_db
def test_general_equals_simple_average_and_fallback(collaborator, project_finite, period, area, level_jr):
    """Una categoría «General» (o un cuestionario sin categorías) = promedio simple de siempre."""
    tpl, qs = build_template(area, level_jr, [("general", "General", "100.0", [None] * 8)])
    legacy = QuestionnaireTemplate.objects.create(
        kind=QuestionnaireTemplate.Kind.OWNERSHIP, area=area, level=level_jr, version=2,
        status=QuestionnaireTemplate.Status.BORRADOR,
    )
    section = Section.objects.create(template=legacy, title="S", order=1)
    legacy_qs = [Question.objects.create(section=section, order=i, title=f"L{i}", qtype="SCALE") for i in range(1, 9)]

    rng = random.Random(8)
    for _ in range(12):
        values = [rng.choice([1, 2, 3, 4, None]) for _ in qs]
        expected = scoring._avg([v for v in values if v is not None])
        for template, questions in ((tpl, qs), (legacy, legacy_qs)):
            ev = evaluation_with(collaborator, project_finite, period, template, questions, values)
            assert scoring.ownership_evaluation_score(ev) == expected
            ev.delete()


@pytest.mark.django_db
def test_pillar_breakdown_averages_categories(collaborator, project_finite, project_indefinite, period, area, level_jr):
    tpl, qs = build_template(area, level_jr, [
        ("a", "A", "60.0", [None]), ("b", "B", "40.0", [None]),
    ])
    for project, values in ((project_finite, [4, 2]), (project_indefinite, [2, 4])):
        ev = evaluation_with(collaborator, project, period, tpl, qs, values)
        ev.score = scoring.ownership_evaluation_score(ev)
        ev.status = OwnershipEvaluation.Status.ENVIADA
        ev.save()
    rows = scoring.ownership_pillar_breakdown(collaborator, period)
    assert [(r["code"], r["score"]) for r in rows] == [("a", Decimal("3.00")), ("b", Decimal("3.00"))]
