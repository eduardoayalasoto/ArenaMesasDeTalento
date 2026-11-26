"""Spec 011: Centro de ayuda contextual: botón en la barra y contenido por perfil y por lo que cada persona puede hacer."""

import re
from datetime import date

import pytest
from django.urls import reverse

from apps.access.models import Profile
from apps.catalog.models import (
    Area, Department, EvaluationPeriod, PillarWeight, Position, PositionPillarWeight, SeniorityLevel,
)
from apps.core.tests.conftest import make_learn_user
from apps.evaluations.models import OwnershipEvaluation, OwnershipEvaluator
from apps.questionnaires.models import QuestionnaireTemplate


def _profiled(email, slug, **kw):
    user = make_learn_user(email, **kw)
    user.profile = Profile.objects.get(slug=slug)
    user.save(update_fields=["profile"])
    return user


@pytest.fixture
def org(db):
    consul = Department.objects.create(code="CONSUL", name="Consultoría", order=1)
    analit = Department.objects.create(code="ANALIT", name="Analítica", order=2)
    analista = Area.objects.create(code="ANAL", name="Analista", department=consul)
    ing = Area.objects.create(code="ID", name="Ingeniería de Datos", department=analit)
    lead_lvl = SeniorityLevel.objects.create(code="LEAD", name="Lead", order=4)
    PillarWeight.objects.create(level=lead_lvl, w_ownership="0.300", w_value_delivery="0.350", w_arena_impact="0.350")
    pos_analista = Position.objects.create(area=analista, level=None, name="Analista")
    Position.objects.create(area=ing, level=lead_lvl, name="Ingeniero de Datos Lead")
    PositionPillarWeight.objects.create(position=pos_analista, w_ownership="0.500", w_value_delivery="0.300", w_arena_impact="0.200")
    period = EvaluationPeriod.objects.create(
        name="2026-S2", start_date=date(2026, 7, 1), end_date=date(2026, 12, 31), status=EvaluationPeriod.Status.ABIERTO)
    return {"analista": analista, "ing": ing, "lead_lvl": lead_lvl, "period": period}


@pytest.fixture
def people(org):
    return {
        "analista": _profiled("ana.analista@arena-analytics.com", "colaborador", area=org["analista"]),
        "lead": _profiled("leo.lead@arena-analytics.com", "lead", area=org["ing"], level=org["lead_lvl"]),
        "talento": _profiled("tali.talento@arena-analytics.com", "talento", role="TALENTO"),
    }


def _tabs(client, user):
    client.force_login(user)
    r = client.get(reverse("dashboards:help"))
    assert r.status_code == 200
    return [t["key"] for t in r.context["h"]["tabs"]], r.content.decode()


@pytest.mark.django_db
def test_help_button_lives_in_the_bar_not_in_the_user_menu(client, people):
    client.force_login(people["analista"])
    html = client.get(reverse("dashboards:help")).content.decode()
    assert "aria-label='Centro de ayuda'" in html and "data-tip='Centro de ayuda'" in html
    assert not re.search(r"<li><a href='[^']*ayuda[^']*'>", html)          # ya no está en el menú de usuario
    assert html.index("aria-label='Centro de ayuda'") < html.index("aria-label='Notificaciones'")   # junto a la campana


@pytest.mark.django_db
def test_analista_sees_own_weights_and_personal_guide_only(client, people):
    keys, html = _tabs(client, people["analista"])
    assert "mi_evaluacion" in keys and "modelo" in keys
    assert not {"org", "cuestionarios", "periodo", "lider", "direccion"} & set(keys)
    assert "Tu ponderación de pilares" in html and "Analista" in html and "Consultoría" in html
    assert re.search(r">\s*50%\s*<", html) and re.search(r">\s*20%\s*<", html)
    assert "avísale a tu evaluador" in html.lower().replace("<b>", "").replace("</b>", "") or "avisa a tu evaluador" in html.lower()
    assert "Quién contiene a quién" not in html


@pytest.mark.django_db
def test_lead_sees_leadership_and_lead_weights(client, people):
    keys, html = _tabs(client, people["lead"])
    assert "lider" in keys and "mi_evaluacion" in keys
    assert re.search(r">\s*30%\s*<", html) and re.search(r">\s*35%\s*<", html)
    assert "Ingeniero de Datos Lead" in html


@pytest.mark.django_db
def test_evaluator_narrative_appears_for_who_is_evaluator(client, people, org):
    template = QuestionnaireTemplate.objects.create(kind="OWNERSHIP", area=org["analista"], level=None, version=1, status="PUBLICADO")
    ev = OwnershipEvaluation.objects.create(user=people["analista"], project=None, period=org["period"], template=template)
    OwnershipEvaluator.objects.create(evaluation=ev, user=people["lead"], is_primary=True)
    keys, html = _tabs(client, people["lead"])
    assert "evaluador" in keys
    assert "Cuando te agenden una sesión de validación" in html and "ana analista".title() in html
    keys, html = _tabs(client, people["analista"])
    assert "evaluador" not in keys
    assert "Leo Lead" in html            # la persona ve quién es su evaluador y qué hacer con él


@pytest.mark.django_db
def test_talento_sees_catalog_guides_and_org_diagram_not_the_personal_guide(client, people, org):
    keys, html = _tabs(client, people["talento"])
    assert keys[:3] == ["org", "cuestionarios", "periodo"]
    assert not {"mi_evaluacion", "evaluador", "lider", "direccion"} & set(keys)
    assert "Quién contiene a quién" in html and "Consultoría" in html and "Ingeniero de Datos Lead" in html
    assert "Crear una Área nueva" in html and "Crear un Nivel nuevo" in html
    assert "Tu ponderación de pilares" not in html


@pytest.mark.django_db
def test_help_tab_query_param_selects_the_tab(client, people):
    client.force_login(people["talento"])
    r = client.get(reverse("dashboards:help") + "?tab=periodo")
    assert r.context["active_tab"] == "periodo"
    assert client.get(reverse("dashboards:help") + "?tab=inexistente").context["active_tab"] == "org"
