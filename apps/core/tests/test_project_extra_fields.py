"""Campos nuevos de Project (responsable, fechas, status) y su edición."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Project

User = get_user_model()


@pytest.fixture
def lead(db):
    return User.objects.create_user(
        email="lead@arena-analytics.com", password="x", full_name="Líder Proyecto",
    )


@pytest.mark.django_db
def test_project_acepta_responsable_fechas_status(lead):
    resp = User.objects.create_user(
        email="resp@arena-analytics.com", password="x", full_name="Responsable Uno",
    )
    p = Project.objects.create(
        name="Demo", owner=lead, responsable=resp,
        kickoff=date(2026, 1, 1), target_close=date(2026, 6, 30),
        status=Project.Status.DELAYED,
    )
    p.refresh_from_db()
    assert p.responsable == resp
    assert p.kickoff == date(2026, 1, 1)
    assert p.target_close == date(2026, 6, 30)
    assert p.status == Project.Status.DELAYED


@pytest.mark.django_db
def test_project_status_default_on_track(lead):
    p = Project.objects.create(name="Demo2", owner=lead, responsable=lead)
    assert p.status == Project.Status.ON_TRACK
    assert p.responsable == lead
    assert p.kickoff is None


from datetime import date as _date

from apps.catalog.forms import ProjectForm


@pytest.mark.django_db
def test_projectform_guarda_campos_nuevos(lead):
    resp = User.objects.create_user(
        email="resp2@arena-analytics.com", password="x", full_name="Responsable Dos",
    )
    form = ProjectForm(data={
        "name": "Con Form", "client": "C", "owner": lead.pk, "responsable": resp.pk,
        "duration_type": Project.Duration.FINITO, "is_active": "on",
        "kickoff": "2026-01-01", "target_close": "2026-06-30", "status": "DELAYED",
    })
    assert form.is_valid(), form.errors
    p = form.save()
    assert p.responsable == resp
    assert p.kickoff == _date(2026, 1, 1)
    assert p.status == Project.Status.DELAYED
