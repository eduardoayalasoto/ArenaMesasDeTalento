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


# ============================================================================
# spec 003-salvaguardas-cierre-periodo
# ============================================================================

# --- Foundational: funciones compartidas nuevas ----------------------------

@pytest.mark.django_db
def test_pending_activity_counts_reflects_incomplete_activity(
    period, project_finite, ownership_template, collaborator
):
    from apps.evaluations.models import OwnershipEvaluation

    OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period, template=ownership_template,
        status=OwnershipEvaluation.Status.BORRADOR,
    )
    ValueDeliveryEvaluation.objects.create(project=project_finite, period=period)

    counts = period_lifecycle.pending_activity_counts(period)
    assert counts["own_total"] == 1
    assert counts["own_submitted"] == 0
    assert counts["vd_total"] == 1
    assert counts["vd_validated"] == 0


@pytest.mark.django_db
def test_pending_activity_counts_zero_when_no_activity(period):
    counts = period_lifecycle.pending_activity_counts(period)
    assert counts == {
        "own_total": 0, "own_submitted": 0,
        "vd_total": 0, "vd_validated": 0,
        "finals_total": 0, "finals_complete": 0,
    }


def _decode_js_unicode_escapes(html):
    """El filtro `escapejs` codifica caracteres no alfanuméricos (p. ej. '-' -> '\\u002D')
    dentro de los `onclick="confirm('...')"`; válido en JS, pero no compara igual como
    texto plano. Lo revierte para poder hacer asserts de contenido legibles."""
    import re
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), html)


class _FakeRequest:
    def __init__(self, periodo=None):
        self.GET = {"periodo": periodo} if periodo else {}


@pytest.mark.django_db
def test_resolve_requested_period_uses_query_param(period, next_period):
    resolved = period_lifecycle.resolve_requested_period(
        _FakeRequest(periodo=str(next_period.pk)), fallback=lambda: period
    )
    assert resolved == next_period


@pytest.mark.django_db
def test_resolve_requested_period_falls_back_when_missing(period):
    resolved = period_lifecycle.resolve_requested_period(_FakeRequest(), fallback=lambda: period)
    assert resolved == period


@pytest.mark.django_db
def test_resolve_requested_period_falls_back_when_invalid_id(period):
    resolved = period_lifecycle.resolve_requested_period(_FakeRequest(periodo="999999"), fallback=lambda: period)
    assert resolved == period


# --- US1: confirmación antes de Abrir/Cerrar --------------------------------

@pytest.mark.django_db
def test_period_admin_close_button_has_confirm_with_period_names(client, talento, period, next_period):
    client.force_login(talento)
    resp = client.get(reverse("catalog:period_admin"))
    html = _decode_js_unicode_escapes(resp.content.decode())
    assert f"confirm(" in html
    assert period.name in html
    assert next_period.name in html
    assert "no se puede deshacer" in html


@pytest.mark.django_db
def test_period_admin_open_button_has_confirm_with_period_name(client, talento, next_period):
    """`next_period` (Planeado) es el único periodo: se le ofrece "Abrir", con su nombre en el confirm()."""
    client.force_login(talento)
    resp = client.get(reverse("catalog:period_admin"))
    html = _decode_js_unicode_escapes(resp.content.decode())
    assert f"¿Abrir el periodo «{next_period.name}»?" in html


# --- US2: aviso de actividad pendiente al cerrar ----------------------------

@pytest.mark.django_db
def test_period_admin_close_confirm_shows_pending_counts(
    client, talento, period, next_period, project_finite, ownership_template, collaborator
):
    from apps.evaluations.models import OwnershipEvaluation

    OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period, template=ownership_template,
        status=OwnershipEvaluation.Status.BORRADOR,
    )
    client.force_login(talento)
    resp = client.get(reverse("catalog:period_admin"))
    html = _decode_js_unicode_escapes(resp.content.decode())
    assert "1 evaluaci" in html and "Ownership sin enviar" in html


@pytest.mark.django_db
def test_period_admin_close_confirm_shows_no_pending_when_complete(client, talento, period, next_period):
    client.force_login(talento)
    resp = client.get(reverse("catalog:period_admin"))
    html = _decode_js_unicode_escapes(resp.content.decode())
    assert "No hay actividad registrada en este periodo." in html


@pytest.mark.django_db
def test_period_admin_close_still_succeeds_with_pending_activity(
    client, talento, period, next_period, project_finite, ownership_template, collaborator
):
    """El aviso de US2 es informativo: cerrar procede igual con actividad pendiente."""
    from apps.evaluations.models import OwnershipEvaluation

    OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period, template=ownership_template,
        status=OwnershipEvaluation.Status.BORRADOR,
    )
    client.force_login(talento)
    resp = client.post(reverse("catalog:period_admin"), data={"period": period.pk, "action": "close"})
    assert resp.status_code == 302
    period.refresh_from_db()
    next_period.refresh_from_db()
    assert period.status == EvaluationPeriod.Status.CERRADO
    assert next_period.status == EvaluationPeriod.Status.ABIERTO


# --- US3: motivo real (Ownership) + navegación histórica -------------------

@pytest.mark.django_db
def test_ownership_edit_allows_correction_of_closed_submitted_evaluation(
    client, period, project_finite, ownership_template, collaborator, talento
):
    from apps.evaluations.models import OwnershipEvaluation

    evaluation, error = ownership_flow.get_or_create_ownership_evaluation(
        collaborator, period, project=project_finite,
    )
    assert error is None
    evaluation.strengths = "Fortalezas originales"
    evaluation.opportunities = "Oportunidades originales"
    evaluation.status = OwnershipEvaluation.Status.ENVIADA
    evaluation.save()

    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])

    client.force_login(talento)
    url = reverse("evaluations:ownership_edit", kwargs={"pk": evaluation.pk})
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["can_correct_closed"] is True
    assert resp.context["can_reset"] is False

    save_url = reverse("evaluations:ownership_save", kwargs={"pk": evaluation.pk})
    resp = client.post(save_url, data={
        "strengths": "Fortalezas corregidas", "opportunities": "Oportunidades originales",
        "comments": "", "action": "save",
    })
    assert resp.status_code == 302
    evaluation.refresh_from_db()
    assert evaluation.strengths == "Fortalezas originales"  # sin motivo: no se guardó

    resp = client.post(save_url, data={
        "strengths": "Fortalezas corregidas", "opportunities": "Oportunidades originales",
        "comments": "", "action": "save", "reason": "Corrección de captura",
    })
    assert resp.status_code == 302
    evaluation.refresh_from_db()
    assert evaluation.strengths == "Fortalezas corregidas"
    assert evaluation.status == OwnershipEvaluation.Status.ENVIADA  # no se reabrió el flujo de cierre
    latest = evaluation.history.order_by("-history_date").first()
    assert latest.history_change_reason == "Corrección de captura"


@pytest.mark.django_db
def test_ownership_reset_blocked_on_closed_period_even_with_reason(
    client, period, project_finite, ownership_template, collaborator, talento
):
    """FR-011a: reiniciar (eliminar) nunca aplica sobre un periodo Cerrado, ni con motivo."""
    evaluation, error = ownership_flow.get_or_create_ownership_evaluation(
        collaborator, period, project=project_finite,
    )
    assert error is None
    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])

    client.force_login(talento)
    resp = client.post(
        reverse("evaluations:ownership_reset", kwargs={"pk": evaluation.pk}),
        data={"reason": "Intento de reinicio"},
    )
    assert resp.status_code == 302
    from apps.evaluations.models import OwnershipEvaluation
    assert OwnershipEvaluation.objects.filter(pk=evaluation.pk).exists()


@pytest.mark.django_db
def test_ownership_validation_shows_all_evaluations_for_admin_on_closed_period(
    client, period, project_finite, ownership_template, collaborator, lead, talento
):
    evaluation, error = ownership_flow.get_or_create_ownership_evaluation(
        collaborator, period, project=project_finite, evaluator=lead,
    )
    assert error is None
    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])

    client.force_login(talento)
    resp = client.get(reverse("evaluations:ownership_validation") + f"?periodo={period.pk}")
    assert resp.status_code == 200
    assert evaluation in [rec.evaluation for rec in resp.context["ev_records"]]


# --- US3: motivo real (Entrega de Valor) + navegación histórica ------------

@pytest.mark.django_db
def test_value_delivery_capture_allows_correction_of_closed_validated_vd(
    client, period, project_finite, talento
):
    vd = ValueDeliveryEvaluation.objects.create(
        project=project_finite, period=period,
        client_satisfaction=3, deliverables=3, time_finite=3,
        status=ValueDeliveryEvaluation.Status.VALIDADA,
    )
    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])

    client.force_login(talento)
    url = reverse("evaluations:value_delivery_capture", kwargs={"project_id": project_finite.pk}) + f"?periodo={period.pk}"
    resp = client.get(url)
    assert resp.status_code == 200
    assert resp.context["can_correct_closed"] is True

    resp = client.post(url, data={
        "client_satisfaction": "4", "deliverables": "4", "time_value": "4",
        "comments": "", "reason": "Ajuste de calificación",
    })
    assert resp.status_code == 302
    vd.refresh_from_db()
    assert vd.deliverables == 4
    assert vd.status == ValueDeliveryEvaluation.Status.VALIDADA  # no se reabrió validación
    latest = vd.history.order_by("-history_date").first()
    assert latest.history_change_reason == "Ajuste de calificación"


@pytest.mark.django_db
def test_value_delivery_capture_never_creates_vd_on_closed_period(client, period, project_finite, lead_with_photo):
    period.status = EvaluationPeriod.Status.CERRADO
    period.save(update_fields=["status"])
    assert not ValueDeliveryEvaluation.objects.filter(project=project_finite, period=period).exists()

    client.force_login(lead_with_photo)
    url = reverse("evaluations:value_delivery_capture", kwargs={"project_id": project_finite.pk}) + f"?periodo={period.pk}"
    resp = client.get(url)
    assert resp.status_code == 302
    assert not ValueDeliveryEvaluation.objects.filter(project=project_finite, period=period).exists()
