"""Avance del periodo debe listar personas con pendientes (Ownership, Entrega
de Valor, validación, retroalimentación), ordenadas por cuántas les faltan,
y excluir a quien ya está completo."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.core.tests.conftest import make_membership
from apps.dashboards.views import _pending_people
from apps.evaluations.models import (
    FeedbackResponsible,
    OwnershipEvaluation,
    TalentSessionNote,
    ValueDeliveryEvaluation,
)

User = get_user_model()


@pytest.fixture
def talento(db):
    u = User.objects.create_user(
        email="talento-pp@arena-analytics.com", password="x", full_name="Talento PP",
        role=User.Role.TALENTO,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.mark.django_db
def test_persona_sin_ownership_enviada_aparece_como_pendiente(collaborator, project_finite, period):
    make_membership(project_finite, collaborator)

    rows = _pending_people(period)

    by_user = {r["user"]: r for r in rows}
    assert by_user[collaborator]["ownership_missing"] == [project_finite.name]
    assert by_user[collaborator]["total"] == 1


@pytest.mark.django_db
def test_persona_con_ownership_enviada_no_aparece(collaborator, project_finite, period, ownership_template):
    make_membership(project_finite, collaborator)
    OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period, template=ownership_template,
        status=OwnershipEvaluation.Status.ENVIADA,
    )

    rows = _pending_people(period)

    # El lead (responsable del proyecto) puede seguir pendiente de su propia
    # Entrega de Valor; lo que importa aquí es que collaborator ya no aparece.
    assert all(r["user"] != collaborator for r in rows)


@pytest.mark.django_db
def test_lead_con_vd_sin_capturar_aparece_como_pendiente(lead, project_finite, period):
    # project_finite.responsable == lead (fixture), sin membresías ni ValueDeliveryEvaluation.
    rows = _pending_people(period)

    assert len(rows) == 1
    assert rows[0]["user"] == lead
    assert rows[0]["vd_capture_missing"] == [project_finite.name]
    assert rows[0]["total"] == 1


@pytest.mark.django_db
def test_validador_con_vd_en_validacion_aparece_como_pendiente(lead, collaborator, project_finite, period):
    project_finite.validador = collaborator
    project_finite.save(update_fields=["validador"])
    ValueDeliveryEvaluation.objects.create(
        project=project_finite, period=period,
        status=ValueDeliveryEvaluation.Status.EN_VALIDACION,
    )

    rows = _pending_people(period)

    by_user = {r["user"]: r for r in rows}
    assert by_user[collaborator]["vd_validation_missing"] == [project_finite.name]
    # La Entrega de Valor ya fue capturada (está EN_VALIDACION, no BORRADOR), así
    # que el lead (responsable) ya no tiene pendiente de captura.
    assert lead not in by_user


@pytest.mark.django_db
def test_vd_validada_no_deja_pendiente_de_validacion(lead, collaborator, project_finite, period):
    project_finite.validador = collaborator
    project_finite.save(update_fields=["validador"])
    ValueDeliveryEvaluation.objects.create(
        project=project_finite, period=period,
        status=ValueDeliveryEvaluation.Status.VALIDADA,
    )

    rows = _pending_people(period)

    assert all(r["user"] != collaborator for r in rows)


@pytest.mark.django_db
def test_responsable_de_retroalimentacion_sin_cerrar_aparece_como_pendiente(collaborator, lead, period):
    note = TalentSessionNote.objects.create(user=collaborator, period=period, created_by=lead)
    FeedbackResponsible.objects.create(note=note, user=lead, is_primary=True)

    rows = _pending_people(period)

    by_user = {r["user"]: r for r in rows}
    assert by_user[lead]["feedback_missing"] == [collaborator.full_name]


@pytest.mark.django_db
def test_retroalimentacion_acordada_no_deja_pendiente(collaborator, lead, period):
    note = TalentSessionNote.objects.create(
        user=collaborator, period=period, created_by=lead, feedback_agreed=True,
    )
    FeedbackResponsible.objects.create(note=note, user=lead, is_primary=True)

    rows = _pending_people(period)

    assert all(r["user"] != lead for r in rows)


@pytest.mark.django_db
def test_orden_por_total_de_pendientes_descendente(collaborator, lead, project_finite, project_indefinite, period):
    # collaborator: 2 pendientes (ownership de 2 proyectos).
    make_membership(project_finite, collaborator)
    make_membership(project_indefinite, collaborator)
    # lead es responsable de ambos proyectos por fixture; cerramos la Entrega de
    # Valor de uno para que solo le quede 1 pendiente (menos que collaborator).
    ValueDeliveryEvaluation.objects.create(
        project=project_indefinite, period=period,
        status=ValueDeliveryEvaluation.Status.VALIDADA,
    )

    rows = _pending_people(period)

    assert [r["user"] for r in rows] == [collaborator, lead]
    assert rows[0]["total"] == 2
    assert rows[1]["total"] == 1


@pytest.mark.django_db
def test_vista_avance_periodo_muestra_tabla_de_pendientes(talento, collaborator, project_finite, period, client):
    make_membership(project_finite, collaborator)

    client.force_login(talento)
    resp = client.get(reverse("dashboards:period_progress"))

    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert collaborator.full_name in body
    assert "Ownership" in body
