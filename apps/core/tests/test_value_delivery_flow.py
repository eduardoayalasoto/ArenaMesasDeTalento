"""Comentarios y descripción de criterios de la Entrega de Valor."""

import pytest

from apps.core.services import value_delivery_flow
from apps.evaluations.models import ValueDeliveryEvaluation


@pytest.mark.django_db
def test_save_vd_criteria_saves_comments(project_finite, period):
    vd = value_delivery_flow.get_or_create_vd(project_finite, period)
    value_delivery_flow.save_vd_criteria(
        vd, client_satisfaction=3, deliverables=4, time_value=3,
        comments="Entrega dentro de lo esperado.",
    )
    vd.refresh_from_db()
    assert vd.comments == "Entrega dentro de lo esperado."


@pytest.mark.django_db
def test_save_vd_criteria_without_comments_keeps_existing(project_finite, period):
    """comments=None (valor por defecto) no debe borrar un comentario ya guardado."""
    vd = value_delivery_flow.get_or_create_vd(project_finite, period)
    value_delivery_flow.save_vd_criteria(
        vd, client_satisfaction=3, deliverables=3, time_value=3, comments="Nota original.",
    )
    value_delivery_flow.save_vd_criteria(vd, client_satisfaction=4, deliverables=4, time_value=4)
    vd.refresh_from_db()
    assert vd.comments == "Nota original."


@pytest.mark.django_db
def test_save_vd_comment_updates_only_comment(project_finite, period):
    vd = value_delivery_flow.get_or_create_vd(project_finite, period)
    value_delivery_flow.save_vd_criteria(vd, client_satisfaction=2, deliverables=2, time_value=2)
    value_delivery_flow.save_vd_comment(vd, "Comentario del Validador.")
    vd.refresh_from_db()
    assert vd.comments == "Comentario del Validador."
    assert vd.client_satisfaction == 2  # no se tocan los criterios ya capturados


@pytest.mark.django_db
def test_criteria_summary_finite_project(project_finite, period):
    vd = value_delivery_flow.get_or_create_vd(project_finite, period)
    value_delivery_flow.save_vd_criteria(vd, client_satisfaction=3, deliverables=4, time_value=2)
    summary = value_delivery_flow.criteria_summary(vd)
    labels = [c["label"] for c in summary]
    assert "Tiempo — cumplimiento de la fecha de entrega" in labels
    time_criterion = next(c for c in summary if c["value"] == 2)
    assert "fecha de cierre" in time_criterion["help"]


@pytest.mark.django_db
def test_criteria_summary_indefinite_project(project_indefinite, period):
    vd = value_delivery_flow.get_or_create_vd(project_indefinite, period)
    value_delivery_flow.save_vd_criteria(vd, client_satisfaction=3, deliverables=3, time_value=4)
    summary = value_delivery_flow.criteria_summary(vd)
    labels = [c["label"] for c in summary]
    assert "Tiempo — consistencia del servicio" in labels
