"""Cuestionarios de Ownership de Consultoría cargados desde la matriz (spec 008, US3)."""

import random
from decimal import Decimal
from io import StringIO
from pathlib import Path

import openpyxl
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.catalog.models import Area, PillarWeight, SeniorityLevel
from apps.core.services import ownership_flow, positions, questionnaire_import, scoring
from apps.evaluations.models import OwnershipAnswer, OwnershipEvaluation
from apps.questionnaires.models import Question, QuestionnaireTemplate as T

User = get_user_model()
MATRIX = Path(settings.BASE_DIR) / "docs" / "Matrices" / "Matriz de Competencias y Pesos por Puesto v1.1.xlsx"
CONS_DIR = Path(settings.BASE_DIR) / "fixtures" / "questionnaires" / "cons"
PUESTOS = {"Analista": "JR", "Consultor": "MID", "Consultor Sr": "SNR", "Gerente": "LEAD"}

# Pesos de categoría (FR-023): delivery, producto, gestión, actitud.
EXPECTED = {
    "JR": {"delivery_cliente": "13.6", "desarrollo_producto": "22.7", "herramientas_gestion": "18.2", "actitud_persona": "45.5"},
    "MID": {"delivery_cliente": "30.2", "desarrollo_producto": "20.9", "herramientas_gestion": "14.0", "actitud_persona": "34.9"},
    "SNR": {"delivery_cliente": "32.7", "desarrollo_producto": "18.2", "herramientas_gestion": "21.8", "actitud_persona": "27.3"},
    "LEAD": {"delivery_cliente": "32.3", "desarrollo_producto": "16.1", "herramientas_gestion": "19.3", "actitud_persona": "32.3"},
}
COUNTS = {"JR": 16, "MID": 18, "SNR": 19, "LEAD": 19}


@pytest.fixture
def cons(db, level_jr):
    area = Area.objects.create(code="CONS", name="Consultoría")
    levels = {}
    for order, (code, name) in enumerate([("JR", "Junior"), ("MID", "Mid"), ("SNR", "Senior"), ("LEAD", "Lead")], 1):
        levels[code], _ = SeniorityLevel.objects.get_or_create(code=code, defaults={"name": name, "order": order})
        PillarWeight.objects.get_or_create(
            level=levels[code], defaults={"w_ownership": "0.60", "w_value_delivery": "0.20", "w_arena_impact": "0.20"},
        )
    positions.ensure_default_positions()
    return area, levels


def _matrix_rows():
    """{nivel: [(competencia, peso original)]} directo de la hoja 01 de la matriz."""
    sheet = next(ws for ws in openpyxl.load_workbook(MATRIX, data_only=True).worksheets if ws.title.startswith("01"))
    rows = {code: [] for code in PUESTOS.values()}
    for row in sheet.iter_rows(min_row=6, values_only=True):
        if row[1] in PUESTOS and row[4]:
            weight = row[8] if isinstance(row[8], (int, float)) else 0.0
            rows[PUESTOS[row[1]]].append((str(row[4]).strip(), float(weight)))
    return rows


@pytest.mark.django_db
def test_cons_import_builds_four_weighted_questionnaires(cons, collaborator, period, project_finite):
    area, levels = cons
    call_command("import_questionnaire_version", dir=str(CONS_DIR), target_version=1, dry_run=True, stdout=StringIO())
    assert not T.objects.filter(area=area).exists()

    # Se importan como BORRADOR: el YAML aún trae competencias en 0% y publicar las rechaza (ver abajo).
    out = StringIO()
    call_command("import_questionnaire_version", dir=str(CONS_DIR), target_version=1, stdout=out)
    templates = {t.level.code: t for t in T.objects.filter(area=area).select_related("level")}
    assert set(templates) == {"JR", "MID", "SNR", "LEAD"}
    assert all(t.version == 1 and t.status == T.Status.BORRADOR for t in templates.values())

    for code, template in templates.items():
        links = {l.category.code: str(l.weight_pct) for l in template.template_categories.select_related("category")}
        assert links == EXPECTED[code]
        questions = list(Question.objects.filter(section__template=template).select_related("category"))
        assert len(questions) == COUNTS[code]
        titles = {q.title for q in questions}
        # Las dos competencias nuevas se califican y no pesan; «Apego a los valores» tampoco pondera.
        by_title = {q.title: q for q in questions}
        for title in ("IA como productividad", "Disciplina de forma de trabajo", "Apego a los valores de Arena Analytics"):
            assert by_title[title].weight_pct == Decimal("0.0")
        assert by_title["Apego a los valores de Arena Analytics"].category.code == "actitud_persona"
        assert by_title["IA como productividad"].category.code == "desarrollo_producto"
        assert by_title["Planificación del trabajo"].category.code == "herramientas_gestion"
        assert by_title["Habilidad de comunicación"].category.code == "delivery_cliente"
        assert template.sections.count() == 4 and template.scale_options.count() == 5
        labels = list(template.scale_options.order_by("order").values_list("label", flat=True))
        assert labels == ["No cumple", "Necesita mejorar", "Cumple satisfactoriamente", "Excede", "N/A"]
        assert "Administración de recursos" in titles or code in ("JR", "MID")
    jr_titles = {q.title for q in Question.objects.filter(section__template=templates["JR"])}
    assert not jr_titles & {"Transformación organizacional", "Sentido de negocio", "Administración de recursos"}
    mid_titles = {q.title for q in Question.objects.filter(section__template=templates["MID"])}
    assert "Administración de recursos" not in mid_titles and "Sentido de negocio" in mid_titles

    # Idempotente.
    before = (T.objects.count(), Question.objects.count())
    call_command("import_questionnaire_version", dir=str(CONS_DIR), target_version=1, stdout=StringIO())
    assert (T.objects.count(), Question.objects.count()) == before

    # A un Analista de CONS se le asigna el cuestionario de su puesto; el Gerente (LEAD) sigue siendo Lead.
    # La asignación solo ve cuestionarios publicados; se simula el estado ya publicado de producción.
    T.objects.filter(area=area).update(status=T.Status.PUBLICADO)
    collaborator.area, collaborator.level = area, levels["JR"]
    collaborator.save()
    assert ownership_flow.resolve_ownership_template(collaborator) == templates["JR"]
    assert User(area=area, level=levels["LEAD"], is_lead_flag=True).is_lead and not collaborator.is_lead

    # Con respuestas capturadas el puesto se rechaza y no se modifica.
    evaluation = OwnershipEvaluation.objects.create(user=collaborator, project=project_finite, period=period, template=templates["JR"])
    OwnershipAnswer.objects.create(evaluation=evaluation, question=Question.objects.filter(section__template=templates["JR"]).first(), value=3)
    with pytest.raises(CommandError, match="ya tiene respuestas"):
        call_command("import_questionnaire_version", dir=str(CONS_DIR), target_version=1, stdout=StringIO())
    assert Question.objects.filter(section__template=templates["JR"]).count() == COUNTS["JR"]


@pytest.mark.django_db
def test_cons_score_matches_the_original_matrix(cons, collaborator, period, project_finite):
    """Con respuestas completas, el score cargado coincide con la matriz original (pesos sin redondear).

    Los N/A no existen en la matriz (una competencia que no aplica no está en el puesto); en el modelo se
    redistribuyen dentro de su categoría (ver test_scoring_weighted).
    """
    area, levels = cons
    call_command("import_questionnaire_version", dir=str(CONS_DIR), target_version=1, stdout=StringIO())
    originals = _matrix_rows()
    rng = random.Random(2026)
    for code, template in {t.level.code: t for t in T.objects.filter(area=area).select_related("level")}.items():
        questions = {q.title: q for q in Question.objects.filter(section__template=template)}
        for _ in range(3):
            values = {title: rng.choice([1, 2, 3, 4, 4, 3]) for title in questions}   # la matriz no tiene N/A
            evaluation = OwnershipEvaluation.objects.create(user=collaborator, project=project_finite, period=period, template=template)
            OwnershipAnswer.objects.bulk_create([
                OwnershipAnswer(evaluation=evaluation, question=questions[t], value=v, is_na=v is None)
                for t, v in values.items()
            ])
            graded = [(w, values[title]) for title, w in originals[code] if values.get(title) is not None]
            denominator = sum(w for w, _ in graded)
            expected = sum(w * v for w, v in graded) / denominator if denominator else None
            got = scoring.ownership_evaluation_score(evaluation)
            assert (got is None) == (expected is None)
            if expected is not None:
                assert abs(float(got) - expected) <= 0.011, (code, got, expected)
            evaluation.delete()


@pytest.mark.django_db
def test_cons_cannot_be_published_while_competencies_weigh_zero(cons):
    """Toda pregunta de una categoría debe pesar más de 0%: el YAML actual (que replica el Excel con
    IA como productividad, Disciplina de forma de trabajo y Apego en 0%) no se puede publicar."""
    area, _levels = cons
    with pytest.raises(CommandError, match="ponderación 0%") as exc:
        call_command("import_questionnaire_version", dir=str(CONS_DIR), target_version=1, publish=True, stdout=StringIO())
    for title in ("IA como productividad", "Disciplina de forma de trabajo", "Apego a los valores de Arena Analytics"):
        assert title in str(exc.value)
    assert not T.objects.filter(area=area, status=T.Status.PUBLICADO).exists()


@pytest.mark.django_db
def test_import_rejects_weights_that_do_not_sum_100(cons):
    questions = [{"title": "A", "category": "a", "weight": 60}, {"title": "B", "category": "a", "weight": 39.9}]
    categories = [{"code": "a", "name": "A", "weight": 100}]
    scale = [{"value": 3, "label": "Cumple", "order": 1}]
    with pytest.raises(questionnaire_import.ImportRejected, match="suman 99.9%"):
        questionnaire_import.import_version("CONS", "JR", questions, 1, categories=categories, scale=scale)
    with pytest.raises(questionnaire_import.ImportRejected, match="categoría válida"):
        questionnaire_import.import_version("CONS", "JR", [{"title": "A", "category": "zzz"}], 1,
                                            categories=[{"code": "a", "name": "A", "weight": 100}, {"code": "b", "name": "B", "weight": 0}],
                                            scale=scale)
    with pytest.raises(questionnaire_import.ImportRejected, match="no hay ningún cuestionario de Ownership publicado"):
        questionnaire_import.import_version("CONS", "JR", questions, 1)
    assert not T.objects.filter(area__code="CONS").exists()
