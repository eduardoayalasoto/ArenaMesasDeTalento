"""Navegación histórica por periodo en Mi tablero, Mi área y Resultados de persona
(mismo patrón `?periodo=<id>` ya usado en Retroalimentación / Avance del periodo)."""

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


@pytest.fixture
def closed_note(db, collaborator, closed_period):
    return TalentSessionNote.objects.create(
        user=collaborator, period=closed_period,
        objetivo_desarrollo_1="Certificarse en Airflow.",
    )


@pytest.mark.django_db
def test_home_view_muestra_periodo_cerrado_via_query_param(client, collaborator, closed_note, closed_period):
    client.force_login(collaborator)
    resp = client.get(reverse("dashboards:home"), {"periodo": closed_period.pk})
    assert resp.status_code == 200
    assert resp.context["period"] == closed_period
    assert "Certificarse en Airflow." in resp.content.decode()


@pytest.mark.django_db
def test_home_view_sin_periodo_abierto_y_sin_query_param_no_revienta(client, collaborator):
    client.force_login(collaborator)
    resp = client.get(reverse("dashboards:home"))
    assert resp.status_code == 200
    assert resp.context["period"] is None


@pytest.mark.django_db
def test_user_results_acepta_periodo_historico_para_si_mismo(client, collaborator, closed_note, closed_period):
    client.force_login(collaborator)
    resp = client.get(reverse("dashboards:user_results", kwargs={"pk": collaborator.pk}), {"periodo": closed_period.pk})
    assert resp.status_code == 200
    assert resp.context["period"] == closed_period
    assert "Certificarse en Airflow." in resp.content.decode()


@pytest.mark.django_db
def test_my_area_acepta_periodo_historico(client, collaborator, closed_period):
    client.force_login(collaborator)
    resp = client.get(reverse("dashboards:my_area"), {"periodo": closed_period.pk})
    assert resp.status_code == 200
    assert resp.context["period"] == closed_period
