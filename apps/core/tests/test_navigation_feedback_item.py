"""El item 'Retroalimentación' del navbar debe aparecer aunque la única nota
del colaborador sea de un periodo ya Cerrado (no solo del Abierto vigente)."""

from datetime import date

import pytest
from django.urls import reverse

from apps.catalog.models import EvaluationPeriod
from apps.evaluations.models import TalentSessionNote


@pytest.fixture
def collaborator(collaborator):
    """El middleware de foto obligatoria redirige a quien no tenga `photo_data`."""
    collaborator.photo_data = b"fake-photo"
    collaborator.photo_mime = "image/jpeg"
    collaborator.save(update_fields=["photo_data", "photo_mime"])
    return collaborator


@pytest.fixture
def closed_period(db):
    return EvaluationPeriod.objects.create(
        name="2025-S2", start_date=date(2025, 7, 1), end_date=date(2025, 12, 31),
        status=EvaluationPeriod.Status.CERRADO,
    )


@pytest.mark.django_db
def test_retroalimentacion_aparece_con_nota_solo_en_periodo_cerrado(client, collaborator, closed_period):
    TalentSessionNote.objects.create(user=collaborator, period=closed_period)
    client.force_login(collaborator)
    resp = client.get(reverse("dashboards:home"))
    labels = [item["label"] for item in resp.context["nav_items"]]
    assert "Retroalimentación" in labels


@pytest.mark.django_db
def test_retroalimentacion_no_aparece_sin_ningun_rol(client, collaborator, period):
    client.force_login(collaborator)
    resp = client.get(reverse("dashboards:home"))
    labels = [item["label"] for item in resp.context["nav_items"]]
    assert "Retroalimentación" not in labels
