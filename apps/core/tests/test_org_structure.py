"""Área → Posición → Nivel (opcional): marcas Lead/Director, cuestionario por coincidencia exacta y migración de datos."""

from datetime import date
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from apps.accounts.models import UserAuditLog
from apps.catalog.models import (
    Area, Department, EvaluationPeriod, PillarWeight, Position, PositionPillarWeight, SeniorityLevel,
)
from apps.core.services import ownership_flow, pillar_weights
from apps.core.tests.conftest import make_learn_user
from apps.evaluations.models import OwnershipEvaluation
from apps.questionnaires.models import QuestionnaireTemplate as T, Question, Section

User = get_user_model()
HX = {"HTTP_HX_REQUEST": "true"}

_WEIGHTS = {
    "JR": ("0.60", "0.20", "0.20"), "MID": ("0.50", "0.25", "0.25"),
    "SNR": ("0.40", "0.30", "0.30"), "LEAD": ("0.30", "0.35", "0.35"),
}


def _run(*args):
    call_command("restructure_org", *args, stdout=StringIO())


@pytest.fixture
def levels(db):
    out = {}
    for order, (code, w) in enumerate(_WEIGHTS.items(), 1):
        out[code] = SeniorityLevel.objects.create(code=code, name=code.title(), order=order)
        PillarWeight.objects.create(level=out[code], w_ownership=w[0], w_value_delivery=w[1], w_arena_impact=w[2])
    return out


@pytest.fixture
def cons(db, levels):
    """Consultoría como está hoy: un área CONS con la escalera Jr/Mid/Snr/Lead, 4 cuestionarios y una evaluación de prueba."""
    area = Area.objects.create(code="CONS", name="Consultoría")
    Area.objects.create(code="CD", name="Ciencia de Datos")
    period = EvaluationPeriod.objects.create(
        name="2026-S2", start_date=date(2026, 7, 1), end_date=date(2026, 12, 31),
        status=EvaluationPeriod.Status.ABIERTO)
    people, templates = {}, {}
    for code, level in levels.items():
        Position.objects.create(area=area, level=level, name=f"CONS {code}")
        people[code] = make_learn_user(f"{code.lower()}@arena-analytics.com", area=area, level=level)
        template = T.objects.create(kind=T.Kind.OWNERSHIP, area=area, level=level, version=1, status=T.Status.PUBLICADO)
        Question.objects.create(section=Section.objects.create(template=template, title="S", order=1), order=1, title="P")
        templates[code] = template
    director = make_learn_user("dir@arena-analytics.com", area=area, role=User.Role.DIRECTOR)
    OwnershipEvaluation.objects.create(user=people["JR"], period=period, template=templates["JR"],
                                       status=OwnershipEvaluation.Status.ENVIADA)
    return {"area": area, "people": people, "templates": templates, "director": director, "period": period}


@pytest.mark.django_db
def test_restructure_org_dry_run_changes_nothing_and_apply_moves_consultoria(cons, levels):
    _run()
    assert Department.objects.count() == 0 and Area.objects.filter(code="CONS").exists()          # simulación

    _run("--apply", "--no-backup")
    assert set(Department.objects.values_list("name", flat=True)) == {"Analítica", "Consultoría"}
    assert Area.objects.get(code="CD").department.name == "Analítica"
    assert not Area.objects.filter(code="CONS").exists()
    where = {}
    for code, person in cons["people"].items():
        user = User.objects.get(pk=person.pk)
        where[code] = (user.area.name, user.level.code if user.level_id else None, user.is_lead_flag)
    assert where == {"JR": ("Analista", None, False), "MID": ("Consultor", None, False),
                     "SNR": ("Consultor", "SNR", False), "LEAD": ("Gerente", None, True)}
    director = User.objects.get(pk=cons["director"].pk)
    assert director.is_director_flag and director.area_id is None                                    # Director: sin posición
    # Los cuestionarios siguen a su puesto y la evaluación de prueba se borra
    moved = {code: T.objects.get(pk=t.pk) for code, t in cons["templates"].items()}
    assert (moved["SNR"].area.code, moved["SNR"].level.code) == ("CONSUL", "SNR") and moved["MID"].level_id is None
    assert not OwnershipEvaluation.objects.exists()
    assert UserAuditLog.objects.filter(kind=UserAuditLog.Kind.EVALUATION_RESET).exists()
    # La ponderación de pilares de cada puesto es la de su nivel de antes
    senior = Position.objects.get(area__code="CONSUL", level__code="SNR")
    assert PositionPillarWeight.objects.get(position=senior).w_ownership == PillarWeight.objects.get(level=levels["SNR"]).w_ownership
    analyst = User.objects.get(pk=cons["people"]["JR"].pk)
    assert pillar_weights.effective_weights(analyst)[0] == PillarWeight.objects.get(level=levels["JR"]).w_ownership
    # Idempotente
    _run("--apply", "--no-backup")
    assert Area.objects.filter(code="CONSUL").count() == 1 and Position.objects.filter(area__code="CONSUL").count() == 2


@pytest.mark.django_db
def test_template_matches_position_and_optional_level_exactly(cons, levels):
    _run("--apply", "--no-backup")

    def resolve(email):
        return ownership_flow.resolve_ownership_template(User.objects.get(email=email))

    assert resolve("jr@arena-analytics.com").area.code == "ANAL" and resolve("jr@arena-analytics.com").level_id is None
    assert resolve("snr@arena-analytics.com").level.code == "SNR"          # Consultor + Senior ≠ Consultor
    assert resolve("mid@arena-analytics.com").level_id is None
    consultor = User.objects.get(email="mid@arena-analytics.com")
    consultor.level = levels["JR"]                                          # nivel sin cuestionario → sin coincidencia
    assert ownership_flow.resolve_ownership_template(consultor) is None


@pytest.mark.django_db
def test_lead_and_director_marks_are_edited_in_the_user_drawer(client, cons):
    talento = make_learn_user("t@arena-analytics.com", role="TALENTO")
    client.force_login(talento)
    person = cons["people"]["MID"]
    payload = {"full_name": person.full_name, "email": person.email, "area": person.area_id, "level": person.level_id,
               "role": "COLABORADOR", "is_active": "on", "is_lead_flag": "on", "is_director_flag": "on"}
    client.post(reverse("accounts:user_edit", args=[person.pk]), payload, **HX)
    person.refresh_from_db()
    assert person.is_lead and person.is_director_flag
    assert "Lead / Gerente: No → Sí" in UserAuditLog.objects.get(target_user=person, kind="UPDATED").detail
