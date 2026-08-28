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


@pytest.fixture
def director(db, area):
    u = User.objects.create_user(
        email="director-fb@arena-analytics.com", password="x", full_name="Director",
        area=area, role=User.Role.DIRECTOR,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.fixture
def huerfano(db, area, level_jr):
    """Persona con una nota del periodo activo sin ningún FeedbackResponsible asignado."""
    return User.objects.create_user(
        email="huerfano-fb@arena-analytics.com", password="x", full_name="Sin Responsable",
        area=area, level=level_jr,
    )


@pytest.fixture
def note_huerfana(db, huerfano, period):
    return TalentSessionNote.objects.create(user=huerfano, period=period)


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
def test_responsable_y_talento_pueden_reabrir_tercero_no(
    note, responsable_primario, talento, collaborator_with_photo, target, client
):
    note.feedback_agreed = True
    from django.utils import timezone
    note.feedback_agreed_at = timezone.now()
    note.save()

    url = reverse("dashboards:feedback_session_detail", kwargs={"pk": target.pk})

    # Un tercero sin asignación ni perfil de superusuario de Talento: 403, sin cambios.
    client.force_login(collaborator_with_photo)
    resp = client.post(url, data={"action": "reopen"})
    assert resp.status_code == 403
    note.refresh_from_db()
    assert note.feedback_agreed is True

    # El responsable principal ahora sí puede reabrir su propia retroalimentación.
    client.force_login(responsable_primario)
    client.post(url, data={"action": "reopen"})
    note.refresh_from_db()
    assert note.feedback_agreed is False

    # Talento/superusuario conserva la capacidad de reabrir cualquiera.
    note.feedback_agreed = True
    note.feedback_agreed_at = timezone.now()
    note.save()
    client.force_login(talento)
    client.post(url, data={"action": "reopen"})
    note.refresh_from_db()
    assert note.feedback_agreed is False


@pytest.mark.django_db
def test_reopen_redirige_al_listado_via_next_y_es_idempotente(note, responsable_primario, target, client):
    note.feedback_agreed = True
    from django.utils import timezone
    note.feedback_agreed_at = timezone.now()
    note.save()

    url = reverse("dashboards:feedback_session_detail", kwargs={"pk": target.pk})
    list_url = reverse("dashboards:feedback_session_list")

    client.force_login(responsable_primario)
    resp = client.post(url, data={"action": "reopen", "next": list_url})
    assert resp.status_code == 302
    assert resp.url == list_url
    note.refresh_from_db()
    assert note.feedback_agreed is False

    # Reabrir una nota que ya está abierta no cambia nada ni produce error (idempotente).
    resp = client.post(url, data={"action": "reopen", "next": list_url})
    assert resp.status_code == 302
    note.refresh_from_db()
    assert note.feedback_agreed is False
    assert note.feedback_agreed_at is None
    assert note.feedback_agreed_by is None


@pytest.mark.django_db
def test_tarjeta_muestra_boton_reabrir_solo_a_quien_puede_editar(
    note, responsable_primario, collaborator_with_photo, target, client
):
    note.feedback_agreed = True
    from django.utils import timezone
    note.feedback_agreed_at = timezone.now()
    note.save()

    client.force_login(responsable_primario)
    resp = client.get(reverse("dashboards:feedback_session_list"))
    assert b'value="reopen"' in resp.content

    client.force_login(collaborator_with_photo)
    resp = client.get(reverse("dashboards:feedback_session_list"))
    assert b'value="reopen"' not in resp.content


@pytest.mark.django_db
def test_tarjeta_nunca_muestra_boton_de_cerrar(note, responsable_primario, client):
    """FR-011: cerrar el acuerdo sigue siendo exclusivo del detalle, nunca un botón directo en la tarjeta."""
    client.force_login(responsable_primario)
    resp = client.get(reverse("dashboards:feedback_session_list"))
    assert resp.status_code == 200
    assert b'value="agree"' not in resp.content


@pytest.mark.django_db
def test_reopen_deja_rastro_de_auditoria(note, responsable_primario, talento, target, client):
    """FR-004/SC-004: aunque `feedback_agreed_by` se limpia al reabrir, el historial
    (simple_history + HistoryRequestMiddleware) conserva quién cerró y quién reabrió."""
    url = reverse("dashboards:feedback_session_detail", kwargs={"pk": target.pk})

    client.force_login(responsable_primario)
    client.post(url, data={"action": "agree"})
    note.refresh_from_db()
    assert note.feedback_agreed is True

    client.force_login(talento)
    client.post(url, data={"action": "reopen"})
    note.refresh_from_db()
    assert note.feedback_agreed is False

    history = list(note.history.order_by("history_date", "history_id"))
    closed_rows = [h for h in history if h.feedback_agreed is True]
    assert closed_rows, "debe existir una fila histórica del momento en que quedó cerrada"
    assert closed_rows[-1].history_user == responsable_primario

    reopened_row = history[-1]
    assert reopened_row.feedback_agreed is False
    assert reopened_row.history_user == talento


@pytest.mark.django_db
def test_list_muestra_solo_asignaciones_propias(note, responsable_primario, collaborator_with_photo, client):
    client.force_login(responsable_primario)
    resp = client.get(reverse("dashboards:feedback_session_list"))
    assert resp.status_code == 200
    assert resp.context["primary_cards"][0]["target"] == note.user

    client.force_login(collaborator_with_photo)
    resp = client.get(reverse("dashboards:feedback_session_list"))
    assert resp.status_code == 200
    assert resp.context["primary_cards"] == []
    assert resp.context["secondary_cards"] == []
    assert resp.context["own_cards"] == []
    assert resp.context.get("all_cards", []) == []


# --- Historia 2: vista de superusuario de Talento ("Todas") ------------------

@pytest.mark.django_db
def test_nota_huerfana_invisible_para_lead_visible_para_talento(
    note_huerfana, huerfano, collaborator_with_photo, talento, client
):
    # Un Lead cualquiera, sin ninguna asignación, no ve la nota huérfana.
    client.force_login(collaborator_with_photo)
    resp = client.get(reverse("dashboards:feedback_session_list"))
    assert resp.context.get("all_cards", []) == []
    assert huerfano.full_name not in resp.content.decode("utf-8")

    # Talento sí la ve, en la sección ampliada, con su estado real.
    client.force_login(talento)
    resp = client.get(reverse("dashboards:feedback_session_list"))
    all_targets = [c["target"] for c in resp.context["all_cards"]]
    assert huerfano in all_targets
    assert huerfano.full_name in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_all_cards_no_duplica_notas_donde_talento_ya_es_responsable(note, talento, target, client):
    FeedbackResponsible.objects.create(note=note, user=talento, is_primary=True)

    client.force_login(talento)
    resp = client.get(reverse("dashboards:feedback_session_list"))

    primary_targets = [c["target"] for c in resp.context["primary_cards"]]
    all_targets = [c["target"] for c in resp.context["all_cards"]]
    assert target in primary_targets
    assert target not in all_targets


@pytest.mark.django_db
def test_director_no_ve_seccion_ampliada(note_huerfana, director, client):
    client.force_login(director)
    resp = client.get(reverse("dashboards:feedback_session_list"))
    assert resp.status_code == 200
    assert resp.context.get("all_cards", []) == []
