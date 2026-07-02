"""Pantalla de Retroalimentación de Mesa de Talento (TalentSessionNote + FeedbackResponsible)."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.core.services import permissions as perm_service
from apps.evaluations.models import FeedbackResponsible, TalentSessionNote

User = get_user_model()


@pytest.fixture
def target(db, area, level_jr):
    return User.objects.create_user(
        email="target@arena-analytics.com", password="x", full_name="Colaborador Objetivo",
        area=area, level=level_jr,
    )


@pytest.fixture
def responsable_primario(db):
    u = User.objects.create_user(
        email="resp-primario@arena-analytics.com", password="x", full_name="Responsable Primario",
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.fixture
def responsable_secundario(db):
    u = User.objects.create_user(
        email="resp-secundario@arena-analytics.com", password="x", full_name="Responsable Secundario",
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.fixture
def note(db, target, period, responsable_primario, responsable_secundario):
    n = TalentSessionNote.objects.create(user=target, period=period, created_by=responsable_primario)
    FeedbackResponsible.objects.create(note=n, user=responsable_primario, is_primary=True)
    FeedbackResponsible.objects.create(note=n, user=responsable_secundario, is_primary=False)
    return n


@pytest.fixture
def collaborator_with_photo(collaborator):
    """El middleware de foto obligatoria redirige a quien no tenga `photo_data`."""
    collaborator.photo_data = b"fake-photo"
    collaborator.photo_mime = "image/jpeg"
    collaborator.save(update_fields=["photo_data", "photo_mime"])
    return collaborator


@pytest.fixture
def talento(db):
    u = User.objects.create_user(
        email="talento-fb@arena-analytics.com", password="x", full_name="Talento",
        role=User.Role.TALENTO,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


# --- has_feedback_session (modelo) ------------------------------------------

@pytest.mark.django_db
def test_note_sin_contenido_no_tiene_feedback_session(note):
    assert note.has_feedback_session is False


@pytest.mark.django_db
def test_note_con_contenido_tiene_feedback_session(note):
    note.objetivo_desarrollo_1 = "Mejorar comunicación con el cliente."
    note.save(update_fields=["objetivo_desarrollo_1"])
    assert note.has_feedback_session is True


# --- permissions -------------------------------------------------------------

@pytest.mark.django_db
def test_primario_puede_editar(note, responsable_primario):
    assert perm_service.can_edit_feedback_session(responsable_primario, note) is True


@pytest.mark.django_db
def test_secundario_puede_editar(note, responsable_secundario):
    assert perm_service.can_edit_feedback_session(responsable_secundario, note) is True


@pytest.mark.django_db
def test_talento_puede_editar_cualquier_nota(note, talento):
    assert perm_service.can_edit_feedback_session(talento, note) is True


@pytest.mark.django_db
def test_ajeno_no_puede_editar(note, collaborator):
    assert perm_service.can_edit_feedback_session(collaborator, note) is False


@pytest.mark.django_db
def test_has_feedback_sessions(responsable_primario, collaborator, note):
    assert perm_service.has_feedback_sessions(responsable_primario) is True
    assert perm_service.has_feedback_sessions(collaborator) is False


# --- vistas --------------------------------------------------------------------

@pytest.mark.django_db
def test_detail_get_primario_ok(note, responsable_primario, target, client):
    client.force_login(responsable_primario)
    resp = client.get(reverse("dashboards:feedback_session_detail", kwargs={"pk": target.pk}))
    assert resp.status_code == 200


@pytest.mark.django_db
def test_detail_get_ajeno_denegado(note, collaborator_with_photo, target, client):
    client.force_login(collaborator_with_photo)
    resp = client.get(reverse("dashboards:feedback_session_detail", kwargs={"pk": target.pk}))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_detail_post_secundario_guarda(note, responsable_secundario, target, client):
    client.force_login(responsable_secundario)
    resp = client.post(
        reverse("dashboards:feedback_session_detail", kwargs={"pk": target.pk}),
        data={
            "objetivo_desarrollo_1": "Objetivo 1",
            "objetivo_desarrollo_2": "",
            "objetivo_desarrollo_3": "",
            "expectativas_profesionales": "Crecer a Senior",
            "expectativas_personales": "",
            "comentarios_adicionales": "",
        },
    )
    assert resp.status_code == 302
    note.refresh_from_db()
    assert note.objetivo_desarrollo_1 == "Objetivo 1"
    assert note.expectativas_profesionales == "Crecer a Senior"


@pytest.mark.django_db
def test_agree_cierra_y_bloquea(note, responsable_primario, target, client):
    client.force_login(responsable_primario)
    url = reverse("dashboards:feedback_session_detail", kwargs={"pk": target.pk})
    client.post(url, data={"objetivo_desarrollo_1": "Objetivo X", "objetivo_desarrollo_2": "", "objetivo_desarrollo_3": "", "expectativas_profesionales": "", "expectativas_personales": "", "comentarios_adicionales": ""})
    resp = client.post(url, data={"action": "agree"})
    assert resp.status_code == 302
    note.refresh_from_db()
    assert note.feedback_agreed is True
    assert note.feedback_agreed_by == responsable_primario
    assert note.feedback_agreed_at is not None


@pytest.mark.django_db
def test_no_se_puede_editar_una_vez_acordada(note, responsable_primario, target, client):
    note.feedback_agreed = True
    from django.utils import timezone
    note.feedback_agreed_at = timezone.now()
    note.feedback_agreed_by = responsable_primario
    note.save()

    client.force_login(responsable_primario)
    url = reverse("dashboards:feedback_session_detail", kwargs={"pk": target.pk})
    client.post(url, data={"objetivo_desarrollo_1": "Intento de cambio", "objetivo_desarrollo_2": "", "objetivo_desarrollo_3": "", "expectativas_profesionales": "", "expectativas_personales": "", "comentarios_adicionales": ""})
    note.refresh_from_db()
    assert note.objetivo_desarrollo_1 == ""


@pytest.mark.django_db
def test_solo_talento_puede_reabrir(note, responsable_primario, talento, target, client):
    note.feedback_agreed = True
    from django.utils import timezone
    note.feedback_agreed_at = timezone.now()
    note.save()

    url = reverse("dashboards:feedback_session_detail", kwargs={"pk": target.pk})

    client.force_login(responsable_primario)
    client.post(url, data={"action": "reopen"})
    note.refresh_from_db()
    assert note.feedback_agreed is True  # el responsable no puede reabrir

    client.force_login(talento)
    client.post(url, data={"action": "reopen"})
    note.refresh_from_db()
    assert note.feedback_agreed is False


@pytest.mark.django_db
def test_list_muestra_solo_asignaciones_propias(note, responsable_primario, collaborator_with_photo, client):
    client.force_login(responsable_primario)
    resp = client.get(reverse("dashboards:feedback_session_list"))
    assert resp.status_code == 200
    assert resp.context["rows"][0]["target"] == note.user

    client.force_login(collaborator_with_photo)
    resp = client.get(reverse("dashboards:feedback_session_list"))
    assert resp.status_code == 200
    assert resp.context["rows"] == []
