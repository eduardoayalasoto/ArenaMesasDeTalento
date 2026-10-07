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


# --- Arena Learn (spec 004) --------------------------------------------------------------

def make_learn_user(email, *, area=None, level=None, role=None, **extra):
    """Usuario con foto (evita el redirect de PhotoRequiredMiddleware en pruebas de vista)."""
    # password=None → contraseña inutilizable: evita el hash PBKDF2 (lento) en cada usuario.
    return User.objects.create_user(
        email=email, password=None, full_name=email.split("@")[0].replace(".", " ").title(),
        area=area, level=level, role=role or User.Role.COLABORADOR,
        photo_data=b"x", photo_mime="image/jpeg", **extra,
    )


@pytest.fixture
def learn_area(db):
    return Area.objects.create(code="CD", name="Ciencia de Datos")


@pytest.fixture
def learn_levels(db):
    jr = SeniorityLevel.objects.create(code="JR", name="Junior", order=1)
    lead = SeniorityLevel.objects.create(code="LEAD", name="Lead", order=4)
    return {"JR": jr, "LEAD": lead}


@pytest.fixture
def learn_people(db, learn_area, learn_levels):
    """Colaborador, Lead del área, Director, Talento y otro colaborador de la misma área."""
    return {
        "colab": make_learn_user("ana@arena-analytics.com", area=learn_area, level=learn_levels["JR"]),
        "other": make_learn_user("beto@arena-analytics.com", area=learn_area, level=learn_levels["JR"]),
        "lead": make_learn_user("lia@arena-analytics.com", area=learn_area, level=learn_levels["LEAD"]),
        "director": make_learn_user("dora@arena-analytics.com", role=User.Role.DIRECTOR),
        "talento": make_learn_user("tito@arena-analytics.com", role=User.Role.TALENTO),
    }


@pytest.fixture
def catalog_course(db):
    from apps.learning.models import CatalogCourse

    return CatalogCourse.objects.create(
        name="Spark para analítica", provider="Databricks Academy", kind="CURSO",
        reference_cost=Decimal("3500.00"), currency="MXN", duration_hours=20, tags="Spark, Big Data",
    )


def learn_request_data(**overrides):
    data = {
        "name": "Curso de dbt", "provider": "dbt Labs", "url": "https://learn.getdbt.com",
        "kind": "CURSO", "duration_hours": 12, "pillar": "ENTREGA_VALOR", "tags": "dbt",
        "estimated_cost": Decimal("2500.00"), "currency": "MXN",
        "start_date_planned": date(2026, 10, 1), "end_date_planned": date(2026, 11, 1),
        "justification": "Modelado de datos para el proyecto X.",
    }
    data.update(overrides)
    return data


def learn_review_data(**overrides):
    data = {
        "rating": 5, "opinion": "Muy práctico.", "recommends": "SI",
        "recommend_why": "Aplica directo a nuestros pipelines.", "learnings": "Tests de dbt y snapshots.",
        "audience_areas": [], "audience_levels": [], "audience_notes": "",
    }
    data.update(overrides)
    return data
