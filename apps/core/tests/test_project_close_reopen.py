"""'Cerrar proyecto' (is_active=False): deja de ser evaluable en el periodo Abierto.

Cubre el bug de `projects_led_by` (no filtraba is_active pese a decirlo en su
docstring) y la distincion "Cerrar proyecto" (reversible, hay evaluaciones)
vs "Eliminar" (definitivo, sin evaluaciones) en `catalog.project_admin`.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.catalog.models import Project
from apps.core.services import permissions as perm_service
from apps.evaluations.models import OwnershipEvaluation

User = get_user_model()


@pytest.fixture
def talento(db):
    u = User.objects.create_user(
        email="talento-proj@arena-analytics.com", password="x", full_name="Talento",
        role=User.Role.TALENTO,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.fixture
def responsable(db):
    u = User.objects.create_user(
        email="responsable-proj@arena-analytics.com", password="x", full_name="Responsable Proyecto",
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.fixture
def open_project(db, responsable):
    return Project.objects.create(
        name="Proyecto Abierto", owner=responsable, responsable=responsable, is_active=True,
    )


@pytest.fixture
def closed_project(db, responsable):
    return Project.objects.create(
        name="Proyecto Cerrado", owner=responsable, responsable=responsable, is_active=False,
    )


@pytest.mark.django_db
def test_projects_led_by_excluye_proyecto_cerrado(responsable, open_project, closed_project):
    led = perm_service.projects_led_by(responsable)
    assert list(led) == [open_project]


@pytest.mark.django_db
def test_value_delivery_list_no_ofrece_proyecto_cerrado(client, responsable, open_project, closed_project, period):
    client.force_login(responsable)
    resp = client.get(reverse("evaluations:value_delivery_list"))
    projects_shown = [row["project"] for row in resp.context["rows"]]
    assert open_project in projects_shown
    assert closed_project not in projects_shown


@pytest.mark.django_db
def test_project_admin_has_evals_distingue_cerrar_de_eliminar(client, talento, open_project, closed_project, period, collaborator, ownership_template):
    OwnershipEvaluation.objects.create(user=collaborator, project=open_project, period=period, template=ownership_template)
    client.force_login(talento)
    resp = client.get(reverse("catalog:project_admin"))
    by_pk = {p.pk: p for p in resp.context["projects"]}
    assert by_pk[open_project.pk].has_evals is True
    assert by_pk[closed_project.pk].has_evals is False


@pytest.mark.django_db
def test_project_delete_con_evaluaciones_cierra_en_vez_de_eliminar(client, talento, open_project, period, collaborator, ownership_template):
    OwnershipEvaluation.objects.create(user=collaborator, project=open_project, period=period, template=ownership_template)
    client.force_login(talento)
    client.post(reverse("catalog:project_delete", kwargs={"pk": open_project.pk}))
    open_project.refresh_from_db()
    assert open_project.is_active is False


@pytest.mark.django_db
def test_project_delete_sin_evaluaciones_elimina_definitivo(client, talento, open_project):
    client.force_login(talento)
    client.post(reverse("catalog:project_delete", kwargs={"pk": open_project.pk}))
    assert not Project.objects.filter(pk=open_project.pk).exists()
