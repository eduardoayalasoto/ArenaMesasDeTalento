"""Botones de CRUD estándar (solo ícono + tooltip; «+ Nuevo …») y altas funcionando en cada catálogo."""

import re

import pytest
from django.urls import reverse

from apps.catalog.models import Area, Department, EvaluationPeriod, PillarWeight, Position, ScenarioOption, SeniorityLevel
from apps.core.tests.conftest import make_learn_user

LISTS = ["questionnaires:block_admin", "catalog:department_admin", "catalog:area_admin", "catalog:level_admin", "catalog:position_admin",
         "catalog:weight_admin", "catalog:category_admin", "catalog:scenario_admin", "catalog:period_admin",
         "catalog:project_admin", "accounts:user_admin", "questionnaires:admin_list", "access:profile_list"]
# Un botón de fila con texto visible (Ver / Editar / Ver y editar) es lo que se prohíbe.
TEXT_BUTTON = re.compile(r'<(?:button|a)[^>]*class="btn[^"]*"[^>]*>\s*(?:<i[^>]*></i>\s*)?(Ver y editar|Ver|Editar)\s*</', re.S)


@pytest.fixture
def talento(db):
    user = make_learn_user("t.crud@arena-analytics.com", role="TALENTO")
    dep = Department.objects.create(code="ANALIT", name="Analítica", order=1)
    area = Area.objects.create(code="ID", name="Ingeniero de Datos", department=dep)
    jr = SeniorityLevel.objects.create(code="JR", name="Jr", order=1)
    PillarWeight.objects.create(level=jr, w_ownership="0.60", w_value_delivery="0.20", w_arena_impact="0.20")
    Position.objects.create(area=area, level=jr, name="Ingeniero de Datos Jr")
    ScenarioOption.objects.create(name="Escenario A")
    EvaluationPeriod.objects.create(name="2026", start_date="2026-01-01", end_date="2026-12-31")
    return user


@pytest.mark.django_db
@pytest.mark.parametrize("name", LISTS)
def test_lists_use_icon_only_row_actions_and_plus_new(client, talento, name):
    client.force_login(talento)
    html = client.get(reverse(name)).content.decode()
    assert not TEXT_BUTTON.search(html), f"{name}: botón de fila con texto"
    assert "confirm(" not in html, f"{name}: confirm() nativo"
    if name == "catalog:weight_admin":  # solo edita: las posiciones se crean en Posición × nivel
        return
    assert re.search(r'<(?:a|button)[^>]*class="btn[^"]*btn-primary[^"]*"[^>]*>\s*<i data-lucide="plus"[^>]*></i>\s*<span>Nuev[oa] ', html), \
        f"{name}: falta el botón «+ Nuevo …»"


@pytest.mark.django_db
def test_row_icons_have_tooltips(client, talento):
    client.force_login(talento)
    html = client.get(reverse("catalog:position_admin")).content.decode()
    for tip in ('data-tip="Ver"', 'data-tip="Editar"', 'data-tip="Eliminar'):
        assert tip in html
    assert "text-error" in html


@pytest.mark.django_db
def test_every_create_works(client, talento):
    client.force_login(talento)
    hx = {"HTTP_HX_REQUEST": "true"}
    dep = Department.objects.get()
    area = Area.objects.get()
    assert client.get(reverse("catalog:department_edit"), **hx).status_code == 200
    r = client.post(reverse("catalog:department_edit"), {"name": "Consultoría", "code": "CONSUL", "order": 2, "is_active": "on"}, **hx)
    assert r.status_code == 200 and Department.objects.filter(code="CONSUL").exists()
    r = client.post(reverse("catalog:area_edit"), {"name": "Analista", "code": "ANAL", "department": dep.pk, "is_active": "on"}, **hx)
    assert Area.objects.filter(code="ANAL").exists(), r.content
    r = client.post(reverse("catalog:level_edit"), {"name": "Mid", "code": "MID", "order": 2}, **hx)
    assert SeniorityLevel.objects.filter(code="MID").exists(), r.content
    client.post(reverse("catalog:position_admin"), {"area": area.pk, "level": SeniorityLevel.objects.get(code="MID").pk,
                                                      "name": "Ingeniero de Datos Mid", "is_active": "on"})
    assert Position.objects.filter(name="Ingeniero de Datos Mid").exists()
    client.post(reverse("catalog:category_admin"), {"name": "Nueva cat", "order": 50, "is_active": "on"})
    from apps.questionnaires.models import Category
    assert Category.objects.filter(name="Nueva cat").exists()
    r = client.post(reverse("catalog:scenario_create"), {"name": "Escenario B", "description": "x", "is_active": "on"})
    assert ScenarioOption.objects.filter(name="Escenario B").exists(), r.status_code
    r = client.post(reverse("catalog:period_create"), {"name": "2027", "start_date": "2027-01-01", "end_date": "2027-12-31",
                                                         "kind": "SEMESTRAL"})
    assert EvaluationPeriod.objects.filter(name="2027").exists(), r.status_code
    client.post(reverse("access:profile_list"), {"name": "Perfil X", "description": ""})
    from apps.access.models import Profile
    assert Profile.objects.filter(name="Perfil X").exists()


@pytest.mark.django_db
def test_period_open_via_confirm_dialog_fields(client, talento):
    client.force_login(talento)
    period = EvaluationPeriod.objects.get()
    html = client.get(reverse("catalog:period_admin")).content.decode()
    assert f'name="period" value="{period.pk}"' in html and 'name="action" value="open"' in html
    client.post(reverse("catalog:period_admin"), {"period": period.pk, "action": "open"})
    period.refresh_from_db()
    assert period.status == EvaluationPeriod.Status.ABIERTO


@pytest.mark.django_db
def test_menu_is_split_in_three_admin_categories(client, talento):
    client.force_login(talento)
    labels = [c["label"] for c in client.get(reverse("catalog:category_admin")).context["nav_categories"]]
    assert labels[-3:] == ["Organización", "Modelo de evaluación", "Administración"]

