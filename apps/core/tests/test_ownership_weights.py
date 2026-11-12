"""Reglas de pesos de Ownership (spec 008): décimas enteras, suma 100.0, reparto y validación."""

from decimal import Decimal

import pytest

from apps.core.services import ownership_weights as w
from apps.questionnaires.models import Category, Question, QuestionnaireTemplate, Section, TemplateCategory


def test_pure_weight_rules():
    assert w.to_tenths("33.3") == 333 and w.to_tenths(Decimal("100")) == 1000 and w.to_tenths("4,5") == 45
    for bad in ("33.33", "-1", "100.1", "abc", "", None):
        with pytest.raises(w.WeightError):
            w.to_tenths(bad)

    assert w.split_equal(3) == [Decimal("33.4"), Decimal("33.3"), Decimal("33.3")]
    assert w.split_equal(1) == [Decimal("100.0")]
    for n in range(1, 20):
        assert w.group_total_tenths(w.split_equal(n)) == 1000

    # Pesos crudos de la matriz (nunca más de un decimal y siempre suman 100.0).
    normalized = w.normalize_to_100([0.0454545454545497, 0.0909090909090898, 0.0454545454545497, 0.0909090909090898])
    assert w.group_total_tenths(normalized) == 1000
    assert all(w.to_tenths(x) == w.to_tenths(str(x)) for x in normalized)
    assert w.normalize_to_100([0, 0]) == [Decimal("0.0"), Decimal("0.0")]

    assert w.group_error("Categorías", ["60.0", "40.0"]) is None
    assert w.group_error("Categorías", ["60.0", "39.9"]) == "Los pesos de «Categorías» suman 99.9%; deben sumar 100%."
    assert "no son válidos" in w.group_error("Categorías", ["60.0", "40.05"])


@pytest.fixture
def draft(db, area, level_jr):
    tpl = QuestionnaireTemplate.objects.create(
        kind=QuestionnaireTemplate.Kind.OWNERSHIP, area=area, level=level_jr, version=2,
    )
    section = Section.objects.create(template=tpl, title="S", order=1)
    cats = [Category.objects.create(code=c, name=c.title(), order=i) for i, c in enumerate(["a", "b"])]
    for cat, weight in zip(cats, ["60.0", "40.0"]):
        TemplateCategory.objects.create(template=tpl, category=cat, weight_pct=weight)
    for i, cat in enumerate([cats[0], cats[0], cats[1]], start=1):
        Question.objects.create(section=section, order=i, title=f"Q{i}", qtype="SCALE", category=cat)
    return tpl


@pytest.mark.django_db
def test_validate_template_weights_scenarios(draft):
    assert w.validate_template_weights(draft) == []

    # Categorías que no suman 100.
    link = draft.template_categories.get(category__code="b")
    link.weight_pct = Decimal("39.9")
    link.save()
    assert w.validate_template_weights(draft) == ["Los pesos de «Categorías del cuestionario» suman 99.9%; deben sumar 100%."]
    link.weight_pct = Decimal("40.0")
    link.save()

    # Pesos de preguntas todos definidos y sumando 100: válido; parcial: inválido; 99.9: inválido.
    qa1, qa2 = Question.objects.filter(category__code="a").order_by("order")
    qa1.weight_pct, qa2.weight_pct = Decimal("70.0"), Decimal("30.0")
    qa1.save(); qa2.save()
    assert w.validate_template_weights(draft) == []
    qa2.weight_pct = None
    qa2.save()
    assert "hay preguntas con peso y otras sin peso" in " ".join(w.validate_template_weights(draft))
    qa2.weight_pct = Decimal("29.9")
    qa2.save()
    assert "suman 99.9%" in " ".join(w.validate_template_weights(draft))

    # Categoría con peso pero todas sus preguntas en 0.
    qa1.weight_pct, qa2.weight_pct = Decimal("0.0"), Decimal("100.0")
    qa1.save(); qa2.save()
    assert w.validate_template_weights(draft) == []
    qa2.weight_pct, qa1.weight_pct = Decimal("0.0"), Decimal("0.0")
    qa1.save(); qa2.save()
    assert "suman 0.0%" in " ".join(w.validate_template_weights(draft))
    qa1.weight_pct = qa2.weight_pct = None
    qa1.save(); qa2.save()

    # Pregunta sin categoría y categoría con peso pero sin preguntas.
    Question.objects.filter(category__code="b").update(category=None)
    errors = " ".join(w.validate_template_weights(draft))
    assert "sin categoría" in errors and "pesa 40.0% pero no tiene preguntas" in errors
