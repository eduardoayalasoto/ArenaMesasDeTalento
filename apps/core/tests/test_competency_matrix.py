"""Matriz de competencias: ponderación automática en enteros, preguntas que no ponderan y carga del Excel."""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.catalog.models import Area, Department, Position, SeniorityLevel
from apps.core.services import competency_matrix as matrix
from apps.core.services import ownership_weights as ow
from apps.core.services import scoring
from apps.questionnaires.models import (
    BlockSkill, Category, CompetencyBlock, Question, QuestionnaireTemplate as T, ScaleOption, Section, TemplateCategory,
)


def test_integer_shares_sum_100_and_last_absorbs_the_difference():
    assert ow.integer_shares([1, 1, 1]) == [33, 33, 34]
    assert ow.integer_shares([2]) == [100]
    assert ow.integer_shares([7, 10, 1, 4]) == [32, 45, 5, 18]                  # Analista: Persona/Proyecto/Cliente/Metodología
    for raw in ([1, 2, 3], [4, 4, 4, 4, 4, 4, 4], [1, 1, 1, 1, 1, 1, 9]):
        shares = ow.integer_shares(raw)
        assert sum(shares) == 100 and all(s > 0 for s in shares)


@pytest.fixture
def draft(db):
    area = Area.objects.create(code="CONSUL", name="Consultor")
    template = T.objects.create(kind=T.Kind.OWNERSHIP, area=area, level=None, version=1)
    persona, _ = Category.objects.get_or_create(code="persona", defaults={"name": "Persona", "order": 10})
    proyecto, _ = Category.objects.get_or_create(code="proyecto", defaults={"name": "Proyecto", "order": 20})
    for category in (persona, proyecto):
        TemplateCategory.objects.create(template=template, category=category, weight_pct=0)
    section = Section.objects.create(template=template, title="S", order=1)

    def question(title, category, level, weighted=True):
        return Question.objects.create(section=section, order=Question.objects.count() + 1, title=title,
                                       category=category, target_level=level, is_weighted=weighted)

    return {"template": template, "q": question, "persona": persona, "proyecto": proyecto}


@pytest.mark.django_db
def test_auto_distribute_by_target_level_with_unweighted_questions(draft):
    q = draft["q"]
    q("Comunicación", draft["persona"], 1)
    q("Proactividad", draft["persona"], 2)
    q("Valores", draft["persona"], None, weighted=False)           # solo se califica
    q("Alcance", draft["proyecto"], 3)
    q("Análisis", draft["proyecto"], 3)
    result = ow.auto_distribute(draft["template"])
    assert result["categories"] == {"Persona": 33, "Proyecto": 67} and result["unweighted"] == 1
    weights = {x.title: x.weight_pct for x in Question.objects.filter(section__template=draft["template"])}
    assert weights == {"Comunicación": Decimal("33"), "Proactividad": Decimal("67"), "Valores": Decimal("0"),
                       "Alcance": Decimal("50"), "Análisis": Decimal("50")}
    assert ow.validate_template_weights(draft["template"]) == []    # lo que no pondera no cuenta como «0%»


@pytest.mark.django_db
def test_auto_distribute_requires_a_level_for_weighted_questions(draft):
    draft["q"]("Sin nivel", draft["persona"], None)
    with pytest.raises(ValidationError, match="nivel de dominio"):
        ow.auto_distribute(draft["template"])


@pytest.mark.django_db
def test_unweighted_question_is_graded_but_does_not_move_the_score(draft, django_user_model):
    from apps.evaluations.models import OwnershipAnswer, OwnershipEvaluation
    from apps.catalog.models import EvaluationPeriod
    from datetime import date

    a, b = draft["q"]("Pesa", draft["persona"], 2), draft["q"]("Solo se califica", draft["persona"], None, weighted=False)
    ow.auto_distribute(draft["template"])
    user = django_user_model.objects.create_user(email="u@arena-analytics.com", password=None, full_name="U")
    period = EvaluationPeriod.objects.create(name="P", start_date=date(2026, 1, 1), end_date=date(2026, 6, 30))
    evaluation = OwnershipEvaluation.objects.create(user=user, period=period, template=draft["template"])
    OwnershipAnswer.objects.create(evaluation=evaluation, question=a, value=4)
    OwnershipAnswer.objects.create(evaluation=evaluation, question=b, value=1)
    assert scoring.ownership_evaluation_score(evaluation) == Decimal("4.00")


def _rows():
    skills = ["Prompting estructurado", "Revisión crítica de salida de IA"]
    base = dict(order=1, skills=[], description="Descripción")
    return [
        {**base, "puesto": "Gerente", "family": "Persona", "competency": "Valores", "block": None, "target_level": None, "weight": None},
        {**base, "puesto": "Gerente", "family": "Persona", "competency": "Proactividad", "block": "Competencia de persona", "target_level": 4, "weight": 0.5, "order": 2},
        {**base, "puesto": "Gerente", "family": "Proyecto", "competency": "Alcance", "block": "Dimensionamiento de alcance", "target_level": 4, "weight": 0.5, "order": 3,
         "skills": ["Definición de alcance"]},
        {**base, "puesto": "Gerente", "family": "Proyecto", "competency": "IA como productividad", "block": "IA como productividad",
         "target_level": 3, "weight": 0, "order": 4, "skills": skills},
    ]


@pytest.mark.django_db
def test_load_matrix_creates_published_versions_with_blocks_families_and_integer_weights():
    SeniorityLevel.objects.create(code="SNR", name="Snr", order=3)
    department = Department.objects.create(code="CONSUL", name="Consultoría")
    area = Area.objects.create(code="GERENTE", name="Gerente", department=department)
    Position.objects.create(area=area, level=None, name="Gerente")
    old = T.objects.create(kind=T.Kind.OWNERSHIP, area=area, level=None, version=1, status=T.Status.PUBLICADO)
    ScaleOption.objects.create(template=old, value=1, label="No cumple", order=1)
    Category.objects.get_or_create(code="delivery_cliente", defaults={"name": "Delivery al cliente", "order": 1})

    report = matrix.load(_rows())
    assert len(report) == 1 and report[0]["template"].version == 2
    new = T.objects.get(pk=report[0]["template"].pk)
    old.refresh_from_db()
    assert new.status == T.Status.PUBLICADO and old.status == T.Status.ARCHIVADO
    assert report[0]["categories"] == {"Persona": 50, "Proyecto": 50}
    assert set(Category.objects.filter(code__in=["persona", "proyecto", "cliente", "metodologia-tecnica"]).values_list("name", flat=True)) \
        == {"Persona", "Proyecto", "Cliente", "Metodología y técnica"}
    ia = Question.objects.get(section__template=new, title="IA como productividad")
    assert not ia.is_weighted and ia.target_level == 3 and ia.skills == ["Prompting estructurado", "Revisión crítica de salida de IA"]
    assert ia.category.name == "Proyecto" and ia.weight_pct == 0
    assert not Question.objects.get(section__template=new, title="Valores").is_weighted
    assert BlockSkill.objects.filter(block__name="IA como productividad").count() == 2
    assert CompetencyBlock.objects.count() == 3
    assert not Category.objects.filter(code="delivery_cliente").exists()               # categorías de antes, eliminadas
    assert report[0]["max_deviation"] == 0


def test_read_matrix_parses_the_excel_layout(tmp_path):
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = matrix.SHEET
    for _ in range(4):
        ws.append([])
    ws.append([None, "Puesto", "Orden", "Familia", "Competencia", "Bloque", "Skills", "Nivel", "Peso", "Escala", "Descripción"])
    ws.append([None, "Analista", 1, "Persona", "Valores", "— (filtro de valores)", "", "No pondera (filtro)", "—", "Cumple / No cumple", "Texto"])
    ws.append([None, "Analista", 2, "Proyecto", "Alcance", "Dimensionamiento", "A · B", "N2 · Contribuye", 0.25, "1 - 4", "Texto 2"])
    ws.append([None, "Total Analista", None, None, None, None, None, None, 1, None, None])
    path = tmp_path / "m.xlsx"
    wb.save(path)
    rows = matrix.read_matrix(path)
    assert [r["competency"] for r in rows] == ["Valores", "Alcance"]
    assert rows[0]["block"] is None and rows[0]["target_level"] is None and rows[0]["weight"] is None
    assert rows[1]["skills"] == ["A", "B"] and rows[1]["target_level"] == 2 and rows[1]["weight"] == 0.25
