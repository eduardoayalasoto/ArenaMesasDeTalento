"""La ficha de Mesa de Talento debe mostrar el bloque 'Mesa de Talento — Comentarios',
editable para Talento y de solo lectura para Director."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.evaluations.models import TalentSessionNote

User = get_user_model()


@pytest.fixture
def talento_ui(db):
    u = User.objects.create_user(
        email="talento-ui-comentarios@arena-analytics.com", password="x",
        full_name="Talento UI", role=User.Role.TALENTO,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.fixture
def director_ui(db):
    u = User.objects.create_user(
        email="director-ui-comentarios@arena-analytics.com", password="x",
        full_name="Director UI", role=User.Role.DIRECTOR,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.mark.django_db
def test_talento_ve_textarea_editable_de_comentarios(
    client, talento_ui, collaborator, project_finite, period, ownership_template
):
    from apps.evaluations.models import OwnershipEvaluation
    OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period, template=ownership_template,
    )
    TalentSessionNote.objects.create(
        user=collaborator, period=period, comentarios="Va bien encaminado.",
    )
    client.force_login(talento_ui)
    resp = client.get(reverse("dashboards:talent_person", kwargs={"pk": collaborator.pk}))
    html = resp.content.decode("utf-8")
    assert resp.status_code == 200
    assert "Mesa de Talento — Comentarios" in html
    assert 'name="comentarios"' in html
    assert "Va bien encaminado." in html


@pytest.mark.django_db
def test_director_ve_comentarios_solo_lectura(
    client, director_ui, collaborator, project_finite, period, ownership_template
):
    from apps.evaluations.models import OwnershipEvaluation
    OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period, template=ownership_template,
    )
    TalentSessionNote.objects.create(
        user=collaborator, period=period, comentarios="Comentario visible para Director.",
    )
    client.force_login(director_ui)
    resp = client.get(reverse("dashboards:talent_person", kwargs={"pk": collaborator.pk}))
    html = resp.content.decode("utf-8")
    assert resp.status_code == 200
    assert "Mesa de Talento — Comentarios" in html
    assert 'name="comentarios"' not in html
    assert "Comentario visible para Director." in html
