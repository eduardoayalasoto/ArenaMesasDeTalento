"""Mesa de Talento: revisión por proyecto (MesaProjectReview), estado general
derivado, avance por equipo y filtro exclusivo por equipo en el índice."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.core.tests.conftest import make_membership
from apps.dashboards.views import (
    _general_ready_ids,
    _person_team_projects,
    _project_progress,
    _project_team_ids,
)
from apps.evaluations.models import MesaProjectReview

User = get_user_model()


@pytest.fixture
def talento(db):
    u = User.objects.create_user(
        email="talento-mesa@arena-analytics.com", password="x", full_name="Talento Mesa",
        role=User.Role.TALENTO,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.fixture
def director(db, area):
    u = User.objects.create_user(
        email="director-mesa@arena-analytics.com", password="x", full_name="Director Mesa",
        area=area, role=User.Role.DIRECTOR,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


def _review(user, project, period, by):
    MesaProjectReview.objects.get_or_create(
        period=period, user=user, project=project, defaults={"reviewed_by": by},
    )


# --- Equipo del proyecto ---------------------------------------------------

@pytest.mark.django_db
def test_equipo_es_miembros_mas_owner_sin_duplicar(lead, collaborator, project_finite):
    make_membership(project_finite, lead)  # owner también miembro
    make_membership(project_finite, collaborator)

    assert _project_team_ids(project_finite) == {lead.id, collaborator.id}


@pytest.mark.django_db
def test_owner_sin_membresia_cuenta_como_equipo(lead, collaborator, project_finite):
    make_membership(project_finite, collaborator)

    assert _project_team_ids(project_finite) == {lead.id, collaborator.id}


# --- Avance por proyecto ---------------------------------------------------

@pytest.mark.django_db
def test_avance_cuenta_revisiones_por_proyecto(lead, collaborator, project_finite, period, talento):
    make_membership(project_finite, collaborator)  # equipo: lead (owner) + collaborator
    _review(collaborator, project_finite, period, talento)

    r = {row["project"].id: row for row in _project_progress(period)}[project_finite.id]

    assert r["total"] == 2
    assert r["listos"] == 1
    assert r["pendientes"] == 1
    assert r["pct"] == 50


@pytest.mark.django_db
def test_revision_es_por_proyecto_no_global(
    lead, collaborator, project_finite, project_indefinite, period, talento
):
    make_membership(project_finite, collaborator)
    make_membership(project_indefinite, collaborator)
    # Revisada solo en un proyecto: cuenta en ese, no en el otro.
    _review(collaborator, project_finite, period, talento)

    rows = {row["project"].id: row for row in _project_progress(period)}

    assert collaborator.id in _project_team_ids(project_finite)
    assert rows[project_finite.id]["listos"] == 1
    assert rows[project_indefinite.id]["listos"] == 0


@pytest.mark.django_db
def test_orden_por_pct_ascendente(lead, collaborator, project_finite, project_indefinite, period, talento):
    make_membership(project_finite, collaborator)
    _review(collaborator, project_finite, period, talento)  # finite 50%, indefinite 0%

    order = [row["project"].id for row in _project_progress(period)]

    assert order == [project_indefinite.id, project_finite.id]


@pytest.mark.django_db
def test_sin_periodo_no_rompe():
    assert _project_progress(None) == []


# --- Estado general derivado ----------------------------------------------

@pytest.mark.django_db
def test_general_listo_requiere_todos_los_equipos(
    lead, collaborator, project_finite, project_indefinite, period, talento
):
    make_membership(project_finite, collaborator)
    make_membership(project_indefinite, collaborator)

    _review(collaborator, project_finite, period, talento)
    assert collaborator.id not in _general_ready_ids(period, [collaborator])  # falta uno

    _review(collaborator, project_indefinite, period, talento)
    assert collaborator.id in _general_ready_ids(period, [collaborator])  # todos listos


@pytest.mark.django_db
def test_person_team_projects_deriva_all_ready(lead, collaborator, project_finite, period, talento):
    make_membership(project_finite, collaborator)

    ctx = _person_team_projects(collaborator, period)
    assert [r["project"] for r in ctx["project_reviews"]] == [project_finite]
    assert ctx["mesa_all_ready"] is False

    _review(collaborator, project_finite, period, talento)
    ctx = _person_team_projects(collaborator, period)
    assert ctx["mesa_all_ready"] is True


@pytest.mark.django_db
def test_persona_sin_equipos_no_esta_lista(collaborator, period):
    ctx = _person_team_projects(collaborator, period)
    assert ctx["project_reviews"] == []
    assert ctx["mesa_all_ready"] is False


# --- Filtro exclusivo por proyecto en el índice ----------------------------

@pytest.mark.django_db
def test_filtro_proyecto_muestra_solo_el_equipo(talento, lead, collaborator, project_finite, period, area, level_jr, client):
    make_membership(project_finite, collaborator)
    ajena = User.objects.create_user(
        email="ajena@arena-analytics.com", password="x", full_name="Persona Ajena",
        area=area, level=level_jr,
    )

    client.force_login(talento)
    resp = client.get(reverse("dashboards:talent_table") + f"?proyecto={project_finite.pk}")

    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert collaborator.full_name in body
    assert lead.full_name in body
    assert ajena.full_name not in body


@pytest.mark.django_db
def test_peticion_htmx_devuelve_solo_el_fragmento(talento, collaborator, project_finite, period, client):
    make_membership(project_finite, collaborator)

    client.force_login(talento)
    resp = client.get(
        reverse("dashboards:talent_table") + f"?proyecto={project_finite.pk}",
        HTTP_HX_REQUEST="true",
    )

    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert "<html" not in body.lower()
    assert collaborator.full_name in body


@pytest.mark.django_db
def test_badge_general_listo_en_lista(talento, lead, collaborator, project_finite, period, client):
    make_membership(project_finite, collaborator)
    _review(collaborator, project_finite, period, talento)  # único equipo -> general listo

    client.force_login(talento)
    resp = client.get(reverse("dashboards:talent_table") + f"?proyecto={project_finite.pk}")

    assert "Listo" in resp.content.decode("utf-8")


# --- Toggle de revisión por proyecto ---------------------------------------

@pytest.mark.django_db
def test_toggle_talento_crea_revision(talento, collaborator, project_finite, period, client):
    make_membership(project_finite, collaborator)
    client.force_login(talento)
    url = reverse("dashboards:talent_mesa_project_toggle",
                  kwargs={"pk": collaborator.pk, "project_id": project_finite.pk})

    resp = client.post(url)

    assert resp.status_code == 200
    review = MesaProjectReview.objects.get(period=period, user=collaborator, project=project_finite)
    assert review.reviewed_by == talento


@pytest.mark.django_db
def test_toggle_desmarca_borra_revision(talento, collaborator, project_finite, period, client):
    make_membership(project_finite, collaborator)
    _review(collaborator, project_finite, period, talento)
    client.force_login(talento)
    url = reverse("dashboards:talent_mesa_project_toggle",
                  kwargs={"pk": collaborator.pk, "project_id": project_finite.pk})

    client.post(url)

    assert not MesaProjectReview.objects.filter(
        period=period, user=collaborator, project=project_finite
    ).exists()


@pytest.mark.django_db
def test_toggle_persona_ajena_al_equipo_rechazada(talento, collaborator, project_finite, period, area, level_jr, client):
    # collaborator NO es miembro ni owner de project_finite.
    ajena = User.objects.create_user(
        email="ajena2@arena-analytics.com", password="x", full_name="Ajena Dos",
        area=area, level=level_jr,
    )
    client.force_login(talento)
    url = reverse("dashboards:talent_mesa_project_toggle",
                  kwargs={"pk": ajena.pk, "project_id": project_finite.pk})

    resp = client.post(url)

    assert resp.status_code == 400
    assert not MesaProjectReview.objects.filter(user=ajena).exists()


@pytest.mark.django_db
def test_toggle_director_recibe_403(director, collaborator, project_finite, period, client):
    make_membership(project_finite, collaborator)
    client.force_login(director)
    url = reverse("dashboards:talent_mesa_project_toggle",
                  kwargs={"pk": collaborator.pk, "project_id": project_finite.pk})

    resp = client.post(url)

    assert resp.status_code == 403
    assert not MesaProjectReview.objects.exists()
