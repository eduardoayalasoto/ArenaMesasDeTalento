"""Pruebas de la segregación de visibilidad y capacidades por rol (RN-14/15, KB §9)."""

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Area, SeniorityLevel
from apps.core.services import permissions
from apps.evaluations.models import OwnershipEvaluation

User = get_user_model()


@pytest.fixture
def level_lead(db):
    return SeniorityLevel.objects.create(code="LEAD", name="Lead", order=4)


@pytest.fixture
def other_area(db):
    return Area.objects.create(code="CD", name="Ciencia de Datos")


@pytest.fixture
def area_lead(db, area, level_lead):
    return User.objects.create_user(
        email="arealead@arena-analytics.com", password="x", full_name="Lead de Área",
        area=area, level=level_lead,
    )


@pytest.fixture
def talento(db):
    return User.objects.create_user(
        email="talento@arena-analytics.com", password="x", full_name="Talento",
        role=User.Role.TALENTO,
    )


@pytest.fixture
def director(db):
    return User.objects.create_user(
        email="director@arena-analytics.com", password="x", full_name="Director",
        role=User.Role.DIRECTOR,
    )


def _eval(user, project, period, template):
    return OwnershipEvaluation.objects.create(
        user=user, project=project, period=period, template=template,
        validator=project.lead,
    )


# --- visible_users ---------------------------------------------------------

@pytest.mark.django_db
def test_collaborator_sees_only_self(collaborator):
    assert list(permissions.visible_users(collaborator)) == [collaborator]


@pytest.mark.django_db
def test_area_lead_sees_own_area(area_lead, collaborator, other_area):
    other = User.objects.create_user(
        email="cd@arena-analytics.com", password="x", full_name="Otro", area=other_area,
    )
    visible = set(permissions.visible_users(area_lead))
    assert collaborator in visible       # misma área
    assert area_lead in visible
    assert other not in visible          # otra área


@pytest.mark.django_db
def test_talento_sees_everyone(talento, collaborator, area_lead):
    visible = set(permissions.visible_users(talento))
    assert {talento, collaborator, area_lead} <= visible


# --- can_view_evaluation ---------------------------------------------------

@pytest.mark.django_db
def test_owner_can_view_own_evaluation(collaborator, project_finite, period, ownership_template):
    ev = _eval(collaborator, project_finite, period, ownership_template)
    assert permissions.can_view_evaluation(collaborator, ev) is True


@pytest.mark.django_db
def test_area_lead_can_view_area_evaluation(area_lead, collaborator, project_finite, period, ownership_template):
    ev = _eval(collaborator, project_finite, period, ownership_template)
    assert permissions.can_view_evaluation(area_lead, ev) is True


@pytest.mark.django_db
def test_peer_cannot_view_others_evaluation(collaborator, area, level_jr, project_finite, period, ownership_template):
    peer = User.objects.create_user(
        email="peer@arena-analytics.com", password="x", full_name="Par", area=area, level=level_jr,
    )
    ev = _eval(collaborator, project_finite, period, ownership_template)
    assert permissions.can_view_evaluation(peer, ev) is False


@pytest.mark.django_db
def test_talento_can_view_any_evaluation(talento, collaborator, project_finite, period, ownership_template):
    ev = _eval(collaborator, project_finite, period, ownership_template)
    assert permissions.can_view_evaluation(talento, ev) is True


# --- can_validate_ownership ------------------------------------------------

@pytest.mark.django_db
def test_validator_can_validate(lead, collaborator, project_finite, period, ownership_template):
    ev = _eval(collaborator, project_finite, period, ownership_template)
    assert permissions.can_validate_ownership(lead, ev) is True


@pytest.mark.django_db
def test_random_user_cannot_validate(collaborator, project_finite, period, ownership_template):
    ev = _eval(collaborator, project_finite, period, ownership_template)
    assert permissions.can_validate_ownership(collaborator, ev) is False


# --- Entrega de Valor ------------------------------------------------------

@pytest.mark.django_db
def test_project_lead_can_capture_value_delivery(lead, project_finite):
    assert permissions.can_capture_value_delivery(lead, project_finite) is True


@pytest.mark.django_db
def test_collaborator_cannot_capture_value_delivery(collaborator, project_finite):
    assert permissions.can_capture_value_delivery(collaborator, project_finite) is False


@pytest.mark.django_db
def test_only_director_validates_value_delivery(director, collaborator):
    assert permissions.can_validate_value_delivery(director) is True
    assert permissions.can_validate_value_delivery(collaborator) is False


# --- projects_led_by -------------------------------------------------------

@pytest.mark.django_db
def test_projects_led_by(lead, project_finite, project_indefinite):
    led = set(permissions.projects_led_by(lead))
    assert led == {project_finite, project_indefinite}
