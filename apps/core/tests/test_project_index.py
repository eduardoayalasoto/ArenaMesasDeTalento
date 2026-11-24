"""Índice de proyectos: búsqueda en vivo, filtros, fecha de entrega y cierre/eliminación con confirmación."""

from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.catalog.models import Project
from apps.core.services import projects as project_service

User = get_user_model()
HX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def talento(db):
    return User.objects.create_user(
        email="talento.proj@arena-analytics.com", password=None, full_name="Talento",
        role=User.Role.TALENTO, photo_data=b"x", photo_mime="image/jpeg",
    )


@pytest.fixture
def people(db):
    mk = lambda n: User.objects.create_user(email=f"{n}@arena-analytics.com", password=None,
                                            full_name=n.title(), photo_data=b"x", photo_mime="image/jpeg")
    return mk("rosa"), mk("pablo")


@pytest.fixture
def projects(db, people):
    rosa, pablo = people
    today = date.today()
    return {
        "tablero": Project.objects.create(name="Tablero Comercial", client="Retail Norte", owner=rosa, responsable=rosa,
                                          validador=pablo, target_close=today + timedelta(days=5)),
        "late": Project.objects.create(name="Migración ERP", client="Industrial", owner=pablo, responsable=pablo,
                                       target_close=today - timedelta(days=3), status=Project.Status.DELAYED),
        "servicio": Project.objects.create(name="Soporte BI", owner=rosa, responsable=rosa,
                                           duration_type=Project.Duration.INDEFINIDO, is_active=False),
    }


@pytest.mark.django_db
def test_search_any_word_and_filters(client, talento, projects):
    client.force_login(talento)
    url = reverse("catalog:project_admin")

    def names(**params):
        html = client.get(url, params, **HX).content.decode()
        return {n for n in ("Tablero Comercial", "Migración ERP", "Soporte BI") if n in html}

    assert names(q="retail") == {"Tablero Comercial"}                     # cliente
    assert names(q="pablo") == {"Tablero Comercial", "Migración ERP"}     # validador / owner
    assert names(q="rosa tablero") == {"Tablero Comercial"}               # varias palabras
    assert names(state="cerrados") == {"Soporte BI"}
    assert names(duration="INDEFINIDO") == {"Soporte BI"}
    assert names(focus="retrasados") == {"Migración ERP"}
    assert names(focus="vencidos") == {"Migración ERP"}
    assert names(focus="sin_validador") == {"Migración ERP", "Soporte BI"}
    assert "<html" not in client.get(url, **HX).content.decode()
    assert "<html" in client.get(url).content.decode()


@pytest.mark.django_db
def test_delivery_date_is_shown_instead_of_duration_type(client, talento, projects):
    client.force_login(talento)
    html = client.get(reverse("catalog:project_admin"), **HX).content.decode()
    assert projects["tablero"].target_close.strftime("%d") in html
    assert "En 5 días" in html and "Vencida hace 3 días" in html and "Servicio continuo" in html
    assert "Tiempo finito" not in html


@pytest.mark.django_db
def test_sort_by_delivery_puts_nearest_first_and_undated_last(talento, projects):
    names = [p.name for p in project_service.search_projects(sort="entrega")]
    assert names == ["Migración ERP", "Tablero Comercial", "Soporte BI"]


@pytest.mark.django_db
def test_close_and_delete_go_back_to_the_filtered_list(client, talento, projects):
    client.force_login(talento)
    back = reverse("catalog:project_admin") + "?q=erp"
    resp = client.post(reverse("catalog:project_delete", args=[projects["late"].pk]), HTTP_REFERER="http://testserver" + back)
    assert resp.status_code == 302 and resp["Location"].endswith(back)
    assert not Project.objects.filter(pk=projects["late"].pk).exists()    # sin evaluaciones: se elimina
    resp = client.post(reverse("catalog:project_reactivate", args=[projects["servicio"].pk]))
    assert resp.status_code == 302 and Project.objects.get(pk=projects["servicio"].pk).is_active
    assert client.get(reverse("catalog:project_delete", args=[projects["tablero"].pk])).status_code == 405
