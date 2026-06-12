"""Pruebas del autoguardado de Impacto Arena (vista): guarda al instante y recalcula."""

from decimal import Decimal

import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.evaluations.models import ArenaImpactScore, FinalScore

User = get_user_model()


@pytest.fixture
def talento(db):
    return User.objects.create_user(
        email="talento@arena-analytics.com", password="x",
        full_name="Persona Talento", role="TALENTO",
        photo_data=b"x", photo_mime="image/jpeg",  # evita el redirect de PhotoRequiredMiddleware
    )


def _post(client, user_id, score="", notes=""):
    return client.post(
        reverse("evaluations:arena_impact_autosave"),
        data=json.dumps({"user_id": user_id, "score": score, "notes": notes}),
        content_type="application/json",
    )


@pytest.mark.django_db
def test_autosave_persists_score_and_recomputes(client, talento, collaborator, period):
    client.force_login(talento)
    r = _post(client, collaborator.id, score="3.5", notes="Buen aporte")
    assert r.status_code == 200 and r.json()["ok"] is True

    row = ArenaImpactScore.objects.get(user=collaborator, period=period)
    assert row.score == Decimal("3.5")
    assert row.notes == "Buen aporte"
    assert row.captured_by == talento
    # Se materializó la calificación final (aunque incompleta).
    assert FinalScore.objects.filter(user=collaborator, period=period).exists()


@pytest.mark.django_db
def test_autosave_rejects_out_of_range(client, talento, collaborator, period):
    client.force_login(talento)
    r = _post(client, collaborator.id, score="9")
    assert r.status_code == 400
    assert not ArenaImpactScore.objects.filter(user=collaborator, period=period).exists()


@pytest.mark.django_db
def test_arena_impact_page_renders(client, talento, collaborator, period):
    """La tabla de captura se dibuja sin error y trae el dato ya guardado de la BD."""
    ArenaImpactScore.objects.create(user=collaborator, period=period, score=Decimal("3.00"))
    client.force_login(talento)
    r = client.get(reverse("evaluations:arena_impact"))
    assert r.status_code == 200
    assert b"arena-saved-ids" in r.content
    assert collaborator.full_name.encode() in r.content


@pytest.mark.django_db
def test_autosave_forbidden_for_non_admin(client, collaborator, period):
    collaborator.photo_data = b"x"; collaborator.photo_mime = "image/jpeg"; collaborator.save()
    client.force_login(collaborator)
    r = _post(client, collaborator.id, score="3")
    assert r.status_code == 403
    assert not ArenaImpactScore.objects.filter(user=collaborator, period=period).exists()
