"""Mesa de Talento debe mostrar comentarios de Entrega de Valor en vivo (no solo Validada)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.evaluations.models import OwnershipEvaluation, ValueDeliveryEvaluation

User = get_user_model()


@pytest.fixture
def talento_tp(db):
    u = User.objects.create_user(
        email="talento-tp@arena-analytics.com", password="x", full_name="Talento TP",
        role=User.Role.TALENTO,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.mark.django_db
def test_talent_person_muestra_comentario_de_vd_en_borrador(
    talento_tp, collaborator, project_finite, period, ownership_template, client
):
    OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period, template=ownership_template,
    )
    ValueDeliveryEvaluation.objects.create(
        project=project_finite, period=period,
        comments="Buen avance, falta cerrar el entregable X.",
    )

    client.force_login(talento_tp)
    resp = client.get(reverse("dashboards:talent_person", kwargs={"pk": collaborator.pk}))
    assert resp.status_code == 200
    assert "Buen avance, falta cerrar el entregable X." in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_talent_person_sin_comentario_no_muestra_seccion(
    talento_tp, collaborator, project_finite, period, ownership_template, client
):
    OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period, template=ownership_template,
    )
    ValueDeliveryEvaluation.objects.create(project=project_finite, period=period)

    client.force_login(talento_tp)
    resp = client.get(reverse("dashboards:talent_person", kwargs={"pk": collaborator.pk}))
    assert resp.status_code == 200
    assert resp.context["vd_comment_rows"] == []
