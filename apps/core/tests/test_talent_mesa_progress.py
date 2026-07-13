"""Mesa de Talento: estado 'Listo en Mesa', avance por proyecto y filtro
exclusivo por equipo en el índice (talent_table)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.core.tests.conftest import make_membership
from apps.dashboards.views import _project_progress, _project_team_ids
from apps.evaluations.models import TalentSessionNote

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


def _mark_ready(user, period, by):
    TalentSessionNote.objects.update_or_create(
        user=user, period=period,
        defaults={"mesa_ready": True, "mesa_ready_by": by, "created_by": by},
    )


# --- Equipo del proyecto ---------------------------------------------------

@pytest.mark.django_db
def test_equipo_es_miembros_mas_owner_sin_duplicar(lead, collaborator, project_finite):
    # owner (lead) también es miembro: no debe contarse dos veces.
    make_membership(project_finite, lead)
    make_membership(project_finite, collaborator)

    ids = _project_team_ids(project_finite)

    assert ids == {lead.id, collaborator.id}


@pytest.mark.django_db
def test_owner_sin_membresia_cuenta_como_equipo(lead, collaborator, project_finite):
    make_membership(project_finite, collaborator)

    ids = _project_team_ids(project_finite)

    assert ids == {lead.id, collaborator.id}


# --- Avance por proyecto ---------------------------------------------------

@pytest.mark.django_db
def test_avance_cuenta_listos_y_pendientes(lead, collaborator, project_finite, period, talento):
    make_membership(project_finite, collaborator)  # equipo: lead (owner) + collaborator = 2
    _mark_ready(collaborator, period, talento)

    rows = {r["project"].id: r for r in _project_progress(period)}
    r = rows[project_finite.id]

    assert r["total"] == 2
    assert r["listos"] == 1
    assert r["pendientes"] == 1
    assert r["pct"] == 50


@pytest.mark.django_db
def test_persona_en_dos_proyectos_se_refleja_en_ambos(
    lead, collaborator, project_finite, project_indefinite, period, talento
):
    make_membership(project_finite, collaborator)
    make_membership(project_indefinite, collaborator)
    _mark_ready(collaborator, period, talento)

    rows = {r["project"].id: r for r in _project_progress(period)}

    # collaborator cuenta como listo en ambos equipos.
    assert rows[project_finite.id]["listos"] == 1
    assert rows[project_indefinite.id]["listos"] == 1


@pytest.mark.django_db
def test_orden_por_pct_ascendente(lead, collaborator, project_finite, project_indefinite, period, talento):
    # project_finite: equipo {lead, collaborator}, 1 listo -> 50%.
    make_membership(project_finite, collaborator)
    _mark_ready(collaborator, period, talento)
    # project_indefinite: equipo {lead}, nadie listo -> 0%.

    order = [r["project"].id for r in _project_progress(period)]

    assert order == [project_indefinite.id, project_finite.id]


@pytest.mark.django_db
def test_sin_periodo_no_rompe(period):
    assert _project_progress(None) == []


# --- Filtro exclusivo por proyecto en el índice ----------------------------

@pytest.mark.django_db
def test_filtro_proyecto_muestra_solo_el_equipo(talento, lead, collaborator, project_finite, period, area, level_jr, client):
    # collaborator es del equipo; 'ajena' no.
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
def test_filtro_proyecto_ignora_area_y_busqueda(talento, lead, collaborator, project_finite, period, client):
    make_membership(project_finite, collaborator)

    client.force_login(talento)
    # q que no coincide con nadie del equipo: se ignora por venir con proyecto.
    resp = client.get(
        reverse("dashboards:talent_table") + f"?proyecto={project_finite.pk}&q=zzz&area=NOPE"
    )

    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert collaborator.full_name in body


@pytest.mark.django_db
def test_badge_refleja_mesa_ready(talento, collaborator, project_finite, period, client):
    make_membership(project_finite, collaborator)
    _mark_ready(collaborator, period, talento)

    client.force_login(talento)
    resp = client.get(reverse("dashboards:talent_table") + f"?proyecto={project_finite.pk}")

    assert "Listo" in resp.content.decode("utf-8")


# --- Toggle 'Listo en Mesa' ------------------------------------------------

@pytest.mark.django_db
def test_toggle_talento_marca_y_setea_metadatos(talento, collaborator, period, client):
    client.force_login(talento)
    url = reverse("dashboards:talent_mesa_ready_toggle", kwargs={"pk": collaborator.pk})

    resp = client.post(url)

    assert resp.status_code == 200
    note = TalentSessionNote.objects.get(user=collaborator, period=period)
    assert note.mesa_ready is True
    assert note.mesa_ready_by == talento
    assert note.mesa_ready_at is not None


@pytest.mark.django_db
def test_toggle_desmarca_y_limpia_metadatos(talento, collaborator, period, client):
    _mark_ready(collaborator, period, talento)
    client.force_login(talento)
    url = reverse("dashboards:talent_mesa_ready_toggle", kwargs={"pk": collaborator.pk})

    client.post(url)

    note = TalentSessionNote.objects.get(user=collaborator, period=period)
    assert note.mesa_ready is False
    assert note.mesa_ready_by is None
    assert note.mesa_ready_at is None


@pytest.mark.django_db
def test_toggle_director_recibe_403(director, collaborator, period, client):
    client.force_login(director)
    url = reverse("dashboards:talent_mesa_ready_toggle", kwargs={"pk": collaborator.pk})

    resp = client.post(url)

    assert resp.status_code == 403
    assert not TalentSessionNote.objects.filter(user=collaborator, mesa_ready=True).exists()
