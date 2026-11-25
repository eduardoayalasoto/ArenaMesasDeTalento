"""Áreas, Posiciones y Niveles: búsqueda en vivo, drawer «Ver y editar», bitácora y borrado protegido."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.catalog.models import Area, CatalogAuditLog, Department, PillarWeight, Position, SeniorityLevel
from apps.core.tests.conftest import make_learn_user

User = get_user_model()
HX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def talento(db):
    return make_learn_user("t.org@arena-analytics.com", role="TALENTO")


@pytest.fixture
def org(db):
    analitica = Department.objects.create(code="ANALIT", name="Analítica", order=1)
    consultoria = Department.objects.create(code="CONSUL", name="Consultoría", order=2)
    de = Area.objects.create(code="ID", name="Ingeniero de Datos", department=analitica)
    analista = Area.objects.create(code="ANAL", name="Analista", department=consultoria)
    jr = SeniorityLevel.objects.create(code="JR", name="Jr", order=1)
    PillarWeight.objects.create(level=jr, w_ownership="0.60", w_value_delivery="0.20", w_arena_impact="0.20")
    Position.objects.create(area=de, level=jr, name="Ingeniero de Datos Jr")
    Position.objects.create(area=analista, level=None, name="Analista")
    return {"analitica": analitica, "consultoria": consultoria, "de": de, "analista": analista, "jr": jr}


def _get(client, url, **params):
    return client.get(url, params, **HX).content.decode()


@pytest.mark.django_db
def test_department_search_edit_audit_and_delete_guard(client, talento, org):
    client.force_login(talento)
    url = reverse("catalog:department_admin")
    html = _get(client, url, q="analista")
    assert "Consultoría" in html and "Analítica" not in html
    assert "<html" not in client.get(url, **HX).content.decode() and "<html" in client.get(url).content.decode()

    edit = reverse("catalog:department_edit", args=[org["consultoria"].pk])
    payload = {"name": "Consultoría y Estrategia", "code": "CONSUL", "order": 2, "is_active": "on"}
    resp = client.post(edit, payload, **HX)
    assert "org-changed" in resp["HX-Trigger"] and "close-org-drawer" in resp["HX-Trigger"]
    entry = CatalogAuditLog.objects.get(entity="Área", entity_id=org["consultoria"].pk, action="UPDATED")
    assert entry.actor == talento and "Nombre: Consultoría → Consultoría y Estrategia" in entry.detail
    client.post(edit, payload, **HX)                                                  # sin cambios: sin bitácora nueva
    assert CatalogAuditLog.objects.filter(entity="Área", action="UPDATED").count() == 1

    client.post(reverse("catalog:department_delete", args=[org["analitica"].pk]))     # tiene una posición: no se borra
    assert Department.objects.filter(pk=org["analitica"].pk).exists()
    Position.objects.filter(area=org["de"]).delete()
    org["de"].delete()
    client.post(reverse("catalog:department_delete", args=[org["analitica"].pk]))
    assert not Department.objects.filter(pk=org["analitica"].pk).exists()
    assert CatalogAuditLog.objects.filter(entity="Área", action="DELETED", label="Analítica").exists()


@pytest.mark.django_db
def test_position_screen_filters_by_area_and_shows_levels(client, talento, org):
    client.force_login(talento)
    url = reverse("catalog:area_admin")
    html = _get(client, url, department=org["consultoria"].pk)
    assert "Analista" in html and "Sin nivel" in html and "Ingeniero de Datos" not in html
    html = _get(client, url, q="jr")                                                  # busca por nivel
    assert "Ingeniero de Datos" in html and "Analista" not in html
    resp = client.post(reverse("catalog:area_edit"), {
        "name": "Gerente", "code": "GER", "department": org["consultoria"].pk, "is_active": "on"}, **HX)
    assert "org-changed" in resp["HX-Trigger"]
    gerente = Area.objects.get(code="GER")
    assert gerente.department == org["consultoria"]
    assert CatalogAuditLog.objects.filter(entity="Posición", entity_id=gerente.pk, action="CREATED").exists()
    resp = client.post(reverse("catalog:area_edit"), {"name": "Huérfana", "code": "HUE", "is_active": "on"}, **HX)
    assert "HX-Trigger" not in resp and not Area.objects.filter(code="HUE").exists()  # sin Área: no guarda


@pytest.mark.django_db
def test_level_crud_inherits_pillar_weights_and_guards_delete(client, talento, org):
    client.force_login(talento)
    resp = client.post(reverse("catalog:level_edit"), {"name": "Senior", "code": "snr", "order": 3}, **HX)
    assert "org-changed" in resp["HX-Trigger"]
    senior = SeniorityLevel.objects.get(code="SNR")
    assert PillarWeight.objects.get(level=senior).w_ownership == PillarWeight.objects.get(level=org["jr"]).w_ownership
    assert CatalogAuditLog.objects.filter(entity="Nivel", entity_id=senior.pk, action="CREATED").exists()
    assert "Senior" in _get(client, reverse("catalog:level_admin"), q="sen")
    person = make_learn_user("p@arena-analytics.com", area=org["analista"], level=senior)
    client.post(reverse("catalog:level_delete", args=[senior.pk]))                    # lo usa una persona
    assert SeniorityLevel.objects.filter(pk=senior.pk).exists()
    person.level = None
    person.save(update_fields=["level"])
    client.post(reverse("catalog:level_delete", args=[senior.pk]))
    assert not SeniorityLevel.objects.filter(pk=senior.pk).exists()
    assert not PillarWeight.objects.filter(level_id=senior.pk).exists()


@pytest.mark.django_db
def test_org_screens_are_for_admins_only_and_drawer_needs_htmx(client, talento, org):
    colab = make_learn_user("c@arena-analytics.com", area=org["analista"])
    client.force_login(colab)
    for name in ("catalog:department_admin", "catalog:area_admin", "catalog:level_admin"):
        assert client.get(reverse(name)).status_code == 403
    assert client.post(reverse("catalog:level_delete", args=[org["jr"].pk])).status_code == 403
    client.force_login(talento)
    assert client.get(reverse("catalog:level_edit")).status_code == 302              # sin htmx no hay drawer
    assert "Editar nivel" in client.get(reverse("catalog:level_edit", args=[org["jr"].pk]), **HX).content.decode()


@pytest.mark.django_db
def test_area_director_falls_back_to_the_department_director(learn_people, learn_area):
    from apps.core.services import learning_flow as flow
    from apps.core.tests.test_learning import submit
    from apps.learning.models import CourseRequest

    p = learn_people
    dept = Department.objects.create(code="ANALIT", name="Analítica", director=p["director"])
    learn_area.department = dept
    learn_area.save(update_fields=["department"])                    # la posición no tiene Director propio
    req = submit(p["colab"])
    assert list(flow.eligible_approvers(req, CourseRequest.Stage.DIRECCION)) == [p["director"]]


@pytest.mark.django_db
def test_history_restore_returns_the_full_page_not_the_partial(client, talento, org):
    """Al volver con «Atrás» htmx pide la URL con HX-History-Restore-Request: debe llegar la página completa."""
    client.force_login(talento)
    for name in ("catalog:department_admin", "catalog:area_admin", "catalog:level_admin",
                 "catalog:project_admin", "accounts:user_admin"):
        url = reverse(name)
        assert "<html" not in client.get(url, **HX).content.decode()                    # parcial normal
        restored = client.get(url, **HX, HTTP_HX_HISTORY_RESTORE_REQUEST="true").content.decode()
        assert "<html" in restored, name


@pytest.mark.django_db
def test_icon_only_buttons_carry_a_tooltip_and_attention_text_is_readable(client, talento, org):
    client.force_login(talento)
    html = client.get(reverse("catalog:level_admin"), **HX).content.decode()
    assert 'class="tooltip tooltip-left" data-tip="Eliminar nivel"' in html            # tooltip del componente
    org["analista"].department = None
    org["analista"].save(update_fields=["department"])
    html = client.get(reverse("catalog:area_admin"), **HX).content.decode()
    assert "Sin área" in html and "text-warning\">Sin área" not in html                # el aviso ya no es texto amarillo
