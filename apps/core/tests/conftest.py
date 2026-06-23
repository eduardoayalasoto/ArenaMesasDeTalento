"""Fixtures compartidas para las pruebas del dominio de evaluaciones."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import (
    Area,
    EvaluationPeriod,
    PillarWeight,
    Project,
    ProjectMembership,
    SeniorityLevel,
)
from apps.questionnaires.models import Question, QuestionnaireTemplate, Section

User = get_user_model()


@pytest.fixture
def area(db):
    return Area.objects.create(code="ID", name="Ingeniería de Datos")


@pytest.fixture
def level_jr(db):
    lvl = SeniorityLevel.objects.create(code="JR", name="Junior", order=1)
    PillarWeight.objects.create(
        level=lvl, w_ownership=Decimal("0.60"),
        w_value_delivery=Decimal("0.20"), w_arena_impact=Decimal("0.20"),
    )
    return lvl


@pytest.fixture
def period(db):
    return EvaluationPeriod.objects.create(
        name="2026-S1", start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
        status=EvaluationPeriod.Status.ABIERTO,
    )


@pytest.fixture
def lead(db, area):
    return User.objects.create_user(
        email="lead@arena-analytics.com", password="x", full_name="Líder Proyecto",
    )


@pytest.fixture
def collaborator(db, area, level_jr):
    return User.objects.create_user(
        email="colab@arena-analytics.com", password="x", full_name="Colaboradora Uno",
        area=area, level=level_jr,
    )


@pytest.fixture
def project_finite(db, lead):
    return Project.objects.create(
        name="Proyecto Finito", owner=lead, responsable=lead, duration_type=Project.Duration.FINITO,
    )


@pytest.fixture
def project_indefinite(db, lead):
    return Project.objects.create(
        name="Servicio Continuo", owner=lead, responsable=lead, duration_type=Project.Duration.INDEFINIDO,
    )


@pytest.fixture
def ownership_template(db, area, level_jr):
    """Plantilla de Ownership publicada con `make_questions` preguntas de escala."""
    tpl = QuestionnaireTemplate.objects.create(
        kind=QuestionnaireTemplate.Kind.OWNERSHIP, area=area, level=level_jr,
        version=1, status=QuestionnaireTemplate.Status.PUBLICADO,
    )
    section = Section.objects.create(template=tpl, title="Checklist", order=1)
    for i in range(1, 11):
        Question.objects.create(section=section, order=i, title=f"P{i}", qtype="SCALE")
    return tpl


@pytest.fixture
def level_lead(db):
    lvl = SeniorityLevel.objects.create(code="LEAD", name="Lead", order=5)
    PillarWeight.objects.create(
        level=lvl, w_ownership=Decimal("0.60"),
        w_value_delivery=Decimal("0.20"), w_arena_impact=Decimal("0.20"),
    )
    return lvl


@pytest.fixture
def lead_collab(db, area, level_lead):
    return User.objects.create_user(
        email="lead_collab@arena-analytics.com", password="x", full_name="Lead Transversal",
        area=area, level=level_lead,
    )


@pytest.fixture
def ownership_template_lead(db, area, level_lead):
    """Plantilla de Ownership publicada para nivel Lead."""
    tpl = QuestionnaireTemplate.objects.create(
        kind=QuestionnaireTemplate.Kind.OWNERSHIP, area=area, level=level_lead,
        version=1, status=QuestionnaireTemplate.Status.PUBLICADO,
    )
    section = Section.objects.create(template=tpl, title="Checklist Lead", order=1)
    for i in range(1, 11):
        Question.objects.create(section=section, order=i, title=f"PL{i}", qtype="SCALE")
    return tpl


def make_membership(project, user, period=None):
    return ProjectMembership.objects.create(project=project, user=user)
