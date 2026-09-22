"""Ciclo de vida y continuidad de Periodos de Evaluación (spec 002-ciclo-vida-periodos)."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.catalog.models import EvaluationPeriod
from apps.core.services import ownership_flow, period_lifecycle
from apps.evaluations.models import ValueDeliveryEvaluation

User = get_user_model()


@pytest.fixture
def talento(db):
    """Con foto: PhotoRequiredMiddleware, si no, redirige cualquier request a /cuenta/perfil/."""
    return User.objects.create_user(
        email="talento@arena-analytics.com", password="x", full_name="Talento y Cultura",
        role=User.Role.TALENTO, photo_data=b"fake-photo", photo_mime="image/jpeg",
    )


@pytest.fixture
def lead_with_photo(lead):
    lead.photo_data = b"fake-photo"
    lead.photo_mime = "image/jpeg"
    lead.save(update_fields=["photo_data", "photo_mime"])
    return lead


@pytest.fixture
def collaborator_with_photo(collaborator):
    collaborator.photo_data = b"fake-photo"
    collaborator.photo_mime = "image/jpeg"
    collaborator.save(update_fields=["photo_data", "photo_mime"])
    return collaborator


@pytest.fixture
def next_period(db, period):
    """Planeado, contiguo al fixture `period` (termina 2026-06-30)."""
    return EvaluationPeriod.objects.create(
        name="2026-S2", start_date=date(2026, 7, 1), end_date=date(2026, 12, 31),
        status=EvaluationPeriod.Status.PLANEADO,
    )


# --- FR-001/FR-002: un solo periodo Abierto ---------------------------------

@pytest.mark.django_db
def test_unique_open_period_constraint_at_db_level(period):
    """El constraint de BD impide 2 periodos Abiertos incluso sin pasar por period_lifecycle."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            EvaluationPeriod.objects.create(
                name="2026-S2-directo", start_date=date(2026, 7, 1), end_date=date(2026, 12, 31),
                status=EvaluationPeriod.Status.ABIERTO,
            )


@pytest.mark.django_db
def test_open_period_rejects_when_another_is_open(period, next_period):
    with pytest.raises(ValidationError):
        period_lifecycle.open_period(next_period)
    next_period.refresh_from_db()
    assert next_period.status == EvaluationPeriod.Status.PLANEADO


@pytest.mark.django_db
def test_open_period_succeeds_when_none_open(db):
    solo = EvaluationPeriod.objects.create(
        name="2026-S1-solo", start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
        status=EvaluationPeriod.Status.PLANEADO,
    )
    period_lifecycle.open_period(solo)
    solo.refresh_from_db()
    assert solo.status == EvaluationPeriod.Status.ABIERTO


# --- FR-003/FR-004: continuidad sin huecos ni traslapes, solo prospectiva ---

@pytest.mark.django_db
def test_continuity_rejects_gap(period):
    gap = EvaluationPeriod(
        name="2026-S2-hueco", start_date=date(2026, 7, 5), end_date=date(2026, 12, 31),
        status=EvaluationPeriod.Status.PLANEADO,
    )
    with pytest.raises(ValidationError):
        gap.full_clean()


@pytest.mark.django_db
def test_continuity_rejects_overlap(period):
    overlap = EvaluationPeriod(
        name="2026-S2-traslape", start_date=date(2026, 6, 15), end_date=date(2026, 12, 31),
        status=EvaluationPeriod.Status.PLANEADO,
    )
    with pytest.raises(ValidationError):
        overlap.full_clean()


@pytest.mark.django_db
def test_continuity_accepts_contiguous(period):
    contiguous = EvaluationPeriod(
        name="2026-S2", start_date=date(2026, 7, 1), end_date=date(2026, 12, 31),
        status=EvaluationPeriod.Status.PLANEADO,
    )
    contiguous.full_clean()  # no debe levantar


@pytest.mark.django_db
def test_continuity_not_retroactive_for_untouched_historical_periods(db):
    """FR-004: un periodo histórico con hueco preexistente frente a su vecino se puede
    seguir editando (p. ej. renombrar) sin que la continuidad se re-valide, mientras
    no se toquen sus fechas."""
    EvaluationPeriod.objects.create(
        name="2024-S2", start_date=date(2024, 7, 1), end_date=date(2024, 12, 31),
        status=EvaluationPeriod.Status.CERRADO,
    )
    # Hueco preexistente deliberado: todo 2025 sin periodo.
    con_hueco = EvaluationPeriod.objects.create(
        name="2026-S1", start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
        status=EvaluationPeriod.Status.CERRADO,
    )

    con_hueco.name = "2026-S1-renombrado"
    con_hueco.full_clean()  # no debe levantar: el hueco ya existía y las fechas no cambian


@pytest.mark.django_db
def test_continuity_applies_to_new_period_even_with_preexisting_gap(db):
    """Un periodo NUEVO sí debe respetar continuidad contra su vecino más cercano,
    aunque ese vecino ya tuviera un hueco previo con otro periodo distinto."""
    EvaluationPeriod.objects.create(
        name="2024-S2", start_date=date(2024, 7, 1), end_date=date(2024, 12, 31),
        status=EvaluationPeriod.Status.CERRADO,
    )
    nuevo_con_hueco = EvaluationPeriod(
        name="2026-S1", start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
        status=EvaluationPeriod.Status.PLANEADO,
    )
    with pytest.raises(ValidationError):
        nuevo_con_hueco.full_clean()


# --- FR-013: fechas/tipo inmutables fuera de Planeado -----------------------

@pytest.mark.django_db
def test_dates_immutable_once_not_planeado(period):
    period.start_date = date(2026, 1, 2)
    with pytest.raises(ValidationError):
        period.full_clean()


@pytest.mark.django_db
def test_name_editable_regardless_of_status(period):
    period.name = "2026-S1-renombrado"
    period.full_clean()  # no debe levantar: solo fechas/tipo están bloqueadas


# --- FR-005: cierre abre automáticamente el siguiente contiguo -------------

@pytest.mark.django_db
def test_find_contiguous_next(period, next_period):
    assert period_lifecycle.find_contiguous_next(period) == next_period


@pytest.mark.django_db
def test_find_contiguous_next_none(period):
    assert period_lifecycle.find_contiguous_next(period) is None


@pytest.mark.django_db
def test_close_and_open_next_success(period, next_period):
    result = period_lifecycle.close_and_open_next(period)
    period.refresh_from_db()
    next_period.refresh_from_db()
    assert period.status == EvaluationPeriod.Status.CERRADO
    assert next_period.status == EvaluationPeriod.Status.ABIERTO
    assert result == next_period


@pytest.mark.django_db
def test_close_and_open_next_recorded_in_history(period, next_period):
    """FR-016: cada transición de estatus queda auditada en HistoricalRecords."""
    period_lifecycle.close_and_open_next(period)
    period.refresh_from_db()
    last = period.history.order_by("-history_date").first()
    assert last.status == EvaluationPeriod.Status.CERRADO


@pytest.mark.django_db
def test_close_and_open_next_without_contiguous_raises(period):
    with pytest.raises(ValidationError):
        period_lifecycle.close_and_open_next(period)
    period.refresh_from_db()
    assert period.status == EvaluationPeriod.Status.ABIERTO  # nada cambió (rollback)


# --- FR-006: inmutabilidad con excepción auditada ---------------------------

@pytest.mark.django_db
def test_assert_record_editable_noop_when_period_open(period, project_finite):
    vd = ValueDeliveryEvaluation.objects.create(project=project_finite, period=period)
    period_lifecycle.assert_record_editable(vd, actor=None)  # no debe levantar


@pytest.mark.django_db
def test_assert_record_editable_blocks_normal_user_when_closed(period, project_finite, collaborator):
    vd = ValueDeliveryEvaluation.objects.create(project=project_finite, period=period)
    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])

    with pytest.raises(PermissionDenied):
        period_lifecycle.assert_record_editable(vd, actor=collaborator)


@pytest.mark.django_db
def test_assert_record_editable_blocks_when_actor_is_none_and_closed(period, project_finite):
    vd = ValueDeliveryEvaluation.objects.create(project=project_finite, period=period)
    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])

    with pytest.raises(PermissionDenied):
        period_lifecycle.assert_record_editable(vd, actor=None)


@pytest.mark.django_db
def test_assert_record_editable_requires_reason_for_admin(period, project_finite, talento):
    vd = ValueDeliveryEvaluation.objects.create(project=project_finite, period=period)
    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])

    with pytest.raises(ValidationError):
        period_lifecycle.assert_record_editable(vd, actor=talento, reason="")


@pytest.mark.django_db
def test_assert_record_editable_allows_admin_with_reason(period, project_finite, talento):
    vd = ValueDeliveryEvaluation.objects.create(project=project_finite, period=period)
    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])

    period_lifecycle.assert_record_editable(vd, actor=talento, reason="Corrección de captura")
    assert vd._change_reason == "Corrección de captura"


# --- FR-008/FR-009: bloqueo de creación sin periodo Abierto -----------------

@pytest.mark.django_db
def test_require_open_period_raises_when_none(db):
    EvaluationPeriod.objects.create(
        name="2026-S1-planeado", start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
        status=EvaluationPeriod.Status.PLANEADO,
    )
    with pytest.raises(period_lifecycle.NoOpenPeriodError):
        period_lifecycle.require_open_period()


@pytest.mark.django_db
def test_require_open_period_returns_it_when_present(period):
    assert period_lifecycle.require_open_period() == period


# --- Integración: ownership_flow respeta la inmutabilidad -------------------

@pytest.mark.django_db
def test_close_ownership_evaluation_blocked_when_period_closed(
    period, collaborator, project_finite, ownership_template
):
    evaluation, error = ownership_flow.get_or_create_ownership_evaluation(
        collaborator, period, project=project_finite,
    )
    assert error is None
    evaluation.strengths = "Fortalezas"
    evaluation.opportunities = "Oportunidades"
    evaluation.save()

    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])

    with pytest.raises(PermissionDenied):
        ownership_flow.close_ownership_evaluation(evaluation, actor=collaborator)


# --- Integración: vista de administración de periodos (US1) ----------------

@pytest.mark.django_db
def test_period_admin_view_rejects_open_while_another_open(client, talento, period, next_period):
    client.force_login(talento)
    resp = client.post(
        reverse("catalog:period_admin"), data={"period": next_period.pk, "action": "open"}
    )
    assert resp.status_code == 302
    next_period.refresh_from_db()
    assert next_period.status == EvaluationPeriod.Status.PLANEADO


@pytest.mark.django_db
def test_period_admin_view_close_opens_next_automatically(client, talento, period, next_period):
    client.force_login(talento)
    resp = client.post(
        reverse("catalog:period_admin"), data={"period": period.pk, "action": "close"}
    )
    assert resp.status_code == 302
    period.refresh_from_db()
    next_period.refresh_from_db()
    assert period.status == EvaluationPeriod.Status.CERRADO
    assert next_period.status == EvaluationPeriod.Status.ABIERTO


@pytest.mark.django_db
def test_period_admin_view_close_without_contiguous_shows_error(client, talento, period):
    client.force_login(talento)
    resp = client.post(
        reverse("catalog:period_admin"), data={"period": period.pk, "action": "close"}
    )
    assert resp.status_code == 302
    period.refresh_from_db()
    assert period.status == EvaluationPeriod.Status.ABIERTO


# --- Integración: creación bloqueada sin periodo Abierto (US5, FR-009) -----

@pytest.mark.django_db
def test_value_delivery_capture_blocks_creation_without_open_period(client, lead_with_photo, project_finite):
    assert not EvaluationPeriod.objects.exists()  # sin ningún periodo, mucho menos Abierto
    client.force_login(lead_with_photo)
    resp = client.get(
        reverse("evaluations:value_delivery_capture", kwargs={"project_id": project_finite.pk})
    )
    assert resp.status_code == 302
    assert not ValueDeliveryEvaluation.objects.filter(project=project_finite).exists()


# --- Integración: histórico de solo lectura (US3) ---------------------------

@pytest.mark.django_db
def test_feedback_session_detail_readonly_for_closed_period(client, period, talento, collaborator, lead_with_photo):
    from apps.evaluations.models import FeedbackResponsible, TalentSessionNote

    note = TalentSessionNote.objects.create(user=collaborator, period=period, created_by=talento)
    FeedbackResponsible.objects.create(note=note, user=lead_with_photo, is_primary=True)
    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])

    # `lead` es responsable asignado: en un periodo Abierto SÍ podría editar,
    # pero el periodo Cerrado debe bloquearlo igualmente (sin ser Talento/superusuario).
    client.force_login(lead_with_photo)
    resp = client.get(
        reverse("dashboards:feedback_session_detail", kwargs={"pk": collaborator.pk})
        + f"?periodo={period.pk}"
    )
    assert resp.status_code == 200
    assert resp.context["can_edit"] is False

    resp = client.post(
        reverse("dashboards:feedback_session_detail", kwargs={"pk": collaborator.pk})
        + f"?periodo={period.pk}",
        data={"comentarios_adicionales": "intento de edición"},
    )
    assert resp.status_code == 403
    note.refresh_from_db()
    assert note.comentarios_adicionales != "intento de edición"


@pytest.mark.django_db
def test_feedback_session_detail_admin_can_correct_closed_with_reason(
    client, period, talento, collaborator
):
    from apps.evaluations.models import TalentSessionNote

    note = TalentSessionNote.objects.create(user=collaborator, period=period, created_by=talento)
    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])

    client.force_login(talento)
    url = reverse("dashboards:feedback_session_detail", kwargs={"pk": collaborator.pk}) + f"?periodo={period.pk}"

    resp = client.post(url, data={"comentarios_adicionales": "corrección sin motivo"})
    assert resp.status_code == 302
    note.refresh_from_db()
    assert note.comentarios_adicionales != "corrección sin motivo"

    resp = client.post(
        url, data={"comentarios_adicionales": "corrección con motivo", "reason": "Error de captura"}
    )
    assert resp.status_code == 302
    note.refresh_from_db()
    assert note.comentarios_adicionales == "corrección con motivo"
    latest_history = note.history.order_by("-history_date").first()
    assert latest_history.history_change_reason == "Error de captura"
