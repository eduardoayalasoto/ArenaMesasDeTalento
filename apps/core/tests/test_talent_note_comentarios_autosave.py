"""Autosave de Mesa de Talento debe aceptar field='comentarios', con los mismos
permisos que 'fortalezas'/'oportunidades' (solo Talento/superusuario)."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.evaluations.models import TalentSessionNote

User = get_user_model()


@pytest.fixture
def talento_user(db):
    u = User.objects.create_user(
        email="talento-comentarios@arena-analytics.com", password="x",
        full_name="Talento Comentarios", role=User.Role.TALENTO,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.fixture
def director_user(db):
    u = User.objects.create_user(
        email="director-comentarios@arena-analytics.com", password="x",
        full_name="Director Comentarios", role=User.Role.DIRECTOR,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.mark.django_db
def test_talento_guarda_comentarios(client, talento_user, collaborator, period):
    client.force_login(talento_user)
    resp = client.post(
        reverse("dashboards:talent_note_autosave", kwargs={"pk": collaborator.pk}),
        data=json.dumps({"field": "comentarios", "value": "Buen desempeño general."}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    note = TalentSessionNote.objects.get(user=collaborator, period=period)
    assert note.comentarios == "Buen desempeño general."


@pytest.mark.django_db
def test_director_no_puede_guardar_comentarios(client, director_user, collaborator, period):
    client.force_login(director_user)
    resp = client.post(
        reverse("dashboards:talent_note_autosave", kwargs={"pk": collaborator.pk}),
        data=json.dumps({"field": "comentarios", "value": "Intento no permitido."}),
        content_type="application/json",
    )
    assert resp.status_code == 403
    assert not TalentSessionNote.objects.filter(user=collaborator, period=period).exists()
