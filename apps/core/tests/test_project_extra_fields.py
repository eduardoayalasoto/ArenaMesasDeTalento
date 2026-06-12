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
        name="Demo", lead=lead, responsable=resp,
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
    p = Project.objects.create(name="Demo2", lead=lead)
    assert p.status == Project.Status.ON_TRACK
    assert p.responsable is None
    assert p.kickoff is None
