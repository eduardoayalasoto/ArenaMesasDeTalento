"""Tests de control de acceso HTTP para todos los roles del sistema.

Cubre el status code esperado de cada vista para cada rol:
  - colab:       Colaborador sin nivel lead (perfil base)
  - colab_lead:  Colaborador con nivel LEAD (debe poder editar proyectos)
  - talento:     Rol Talento y Cultura (admin)
  - director:    Rol Director
  - superuser:   Superusuario (acceso total)
  - anon:        No autenticado (debe redirigir a login)
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Area, EvaluationPeriod, PillarWeight, Project, SeniorityLevel
from apps.core.services import permissions as perm_service

User = get_user_model()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email, *, role=User.Role.COLABORADOR, level=None, area=None, superuser=False):
    """Crea un usuario con photo_data para evitar el redirect de PhotoRequiredMiddleware."""
    if superuser:
        u = User.objects.create_superuser(email=email, password="x", full_name="Superusuario")
    else:
        u = User.objects.create_user(
            email=email, password="x",
            full_name=email.split("@")[0],
            role=role, level=level, area=area,
        )
    if not superuser:
        u.photo_data = b"fake-photo"
        u.photo_mime = "image/jpeg"
        u.save(update_fields=["photo_data", "photo_mime"])
    return u


def _get(client, user, url_name, kwargs=None):
    """Hace GET autenticado y devuelve el status code (resolviendo redirects)."""
    client.force_login(user)
    response = client.get(reverse(url_name, kwargs=kwargs or {}))
    return response.status_code


def _anon_get(client, url_name, kwargs=None):
    """GET sin autenticar."""
    client.logout()
    response = client.get(reverse(url_name, kwargs=kwargs or {}))
    return response.status_code


# ---------------------------------------------------------------------------
# Fixtures de rol
# ---------------------------------------------------------------------------

@pytest.fixture
def area_v(db):
    return Area.objects.create(code="VP", name="Vista Permisos")


@pytest.fixture
def level_jr_v(db):
    lvl = SeniorityLevel.objects.create(code="JR", name="Junior", order=1)
    PillarWeight.objects.create(
        level=lvl,
        w_ownership=Decimal("0.60"),
        w_value_delivery=Decimal("0.20"),
        w_arena_impact=Decimal("0.20"),
    )
    return lvl


@pytest.fixture
def level_lead_v(db):
    return SeniorityLevel.objects.create(code="LEAD", name="Lead", order=4)


@pytest.fixture
def colab(db, area_v, level_jr_v):
    return _make_user("vp.colab@arena-analytics.com", area=area_v, level=level_jr_v)


@pytest.fixture
def colab_lead(db, area_v, level_lead_v):
    return _make_user(
        "vp.colablead@arena-analytics.com",
        role=User.Role.COLABORADOR,
        area=area_v,
        level=level_lead_v,
    )


@pytest.fixture
def talento(db):
    return _make_user("vp.talento@arena-analytics.com", role=User.Role.TALENTO)


@pytest.fixture
def director(db):
    return _make_user("vp.director@arena-analytics.com", role=User.Role.DIRECTOR)


@pytest.fixture
def superuser(db):
    return _make_user("vp.super@arena-analytics.com", superuser=True)


@pytest.fixture
def client_obj():
    return Client()


# ---------------------------------------------------------------------------
# 1. Acceso anónimo — todas las vistas redirigen al login
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("url_name,kwargs", [
    ("dashboards:home", {}),
    ("dashboards:my_area", {}),
    ("dashboards:talent_table", {}),
    ("dashboards:period_progress", {}),
    ("evaluations:ownership_list", {}),
    ("evaluations:ownership_validation", {}),
    ("evaluations:value_delivery_list", {}),
    ("evaluations:value_delivery_review", {}),
    ("evaluations:arena_impact", {}),
    ("catalog:project_admin", {}),
    ("catalog:project_create", {}),
    ("catalog:period_admin", {}),
    ("catalog:period_create", {}),
    ("accounts:user_admin", {}),
    ("accounts:user_create", {}),
    ("accounts:profile", {}),
    ("dashboards:help", {}),
    ("questionnaires:admin_list", {}),
])
def test_anon_redirects_to_login(url_name, kwargs):
    c = Client()
    response = c.get(reverse(url_name, kwargs=kwargs))
    assert response.status_code == 302
    assert "/ingresar/" in response["Location"] or "/login/" in response["Location"]


# ---------------------------------------------------------------------------
# 2. can_edit_project — servicio de permisos
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_can_edit_project_colab_lead(colab_lead):
    assert perm_service.can_edit_project(colab_lead) is True


@pytest.mark.django_db
def test_can_edit_project_colab_no_lead(colab):
    assert perm_service.can_edit_project(colab) is False


@pytest.mark.django_db
def test_can_edit_project_talento(talento):
    assert perm_service.can_edit_project(talento) is True


@pytest.mark.django_db
def test_can_edit_project_director(director):
    assert perm_service.can_edit_project(director) is True


@pytest.mark.django_db
def test_can_edit_project_superuser(superuser):
    assert perm_service.can_edit_project(superuser) is True


# ---------------------------------------------------------------------------
# 3. /catalogo/proyectos/ — acceso por rol
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_project_admin_colab_denied(colab, client_obj):
    assert _get(client_obj, colab, "catalog:project_admin") == 403


@pytest.mark.django_db
def test_project_admin_colab_lead_allowed(colab_lead, client_obj):
    assert _get(client_obj, colab_lead, "catalog:project_admin") == 200


@pytest.mark.django_db
def test_project_admin_talento_allowed(talento, client_obj):
    assert _get(client_obj, talento, "catalog:project_admin") == 200


@pytest.mark.django_db
def test_project_admin_director_allowed(director, client_obj):
    assert _get(client_obj, director, "catalog:project_admin") == 200


@pytest.mark.django_db
def test_project_admin_superuser_allowed(superuser, client_obj):
    assert _get(client_obj, superuser, "catalog:project_admin") == 200


# ---------------------------------------------------------------------------
# 4. /catalogo/proyectos/nuevo/ — crear proyecto
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_project_create_colab_denied(colab, client_obj):
    assert _get(client_obj, colab, "catalog:project_create") == 403


@pytest.mark.django_db
def test_project_create_colab_lead_allowed(colab_lead, client_obj):
    assert _get(client_obj, colab_lead, "catalog:project_create") == 200


@pytest.mark.django_db
def test_project_create_talento_allowed(talento, client_obj):
    assert _get(client_obj, talento, "catalog:project_create") == 200


@pytest.mark.django_db
def test_project_create_director_allowed(director, client_obj):
    assert _get(client_obj, director, "catalog:project_create") == 200


# ---------------------------------------------------------------------------
# 5. /catalogo/proyectos/<pk>/ — editar proyecto existente
# ---------------------------------------------------------------------------

@pytest.fixture
def existing_project(db, colab_lead):
    return Project.objects.create(name="Proyecto Test VP", lead=colab_lead)


@pytest.mark.django_db
def test_project_edit_colab_denied(colab, existing_project, client_obj):
    assert _get(client_obj, colab, "catalog:project_edit", {"pk": existing_project.pk}) == 403


@pytest.mark.django_db
def test_project_edit_colab_lead_allowed(colab_lead, existing_project, client_obj):
    assert _get(client_obj, colab_lead, "catalog:project_edit", {"pk": existing_project.pk}) == 200


@pytest.mark.django_db
def test_project_edit_talento_allowed(talento, existing_project, client_obj):
    assert _get(client_obj, talento, "catalog:project_edit", {"pk": existing_project.pk}) == 200


@pytest.mark.django_db
def test_project_edit_director_allowed(director, existing_project, client_obj):
    assert _get(client_obj, director, "catalog:project_edit", {"pk": existing_project.pk}) == 200


# ---------------------------------------------------------------------------
# 6. Vistas solo-Talento (is_admin = Talento o superusuario)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("url_name", [
    "catalog:period_admin",
    "catalog:period_create",
    "accounts:user_admin",
    "accounts:user_create",
    "evaluations:arena_impact",
    "dashboards:period_progress",
    "questionnaires:admin_list",
])
def test_admin_only_colab_denied(url_name, colab, client_obj):
    assert _get(client_obj, colab, url_name) == 403


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", [
    "catalog:period_admin",
    "catalog:period_create",
    "accounts:user_admin",
    "accounts:user_create",
    "evaluations:arena_impact",
    "dashboards:period_progress",
    "questionnaires:admin_list",
])
def test_admin_only_colab_lead_denied(url_name, colab_lead, client_obj):
    assert _get(client_obj, colab_lead, url_name) == 403


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", [
    "catalog:period_admin",
    "catalog:period_create",
    "accounts:user_admin",
    "accounts:user_create",
    "evaluations:arena_impact",
    "dashboards:period_progress",
    "questionnaires:admin_list",
])
def test_admin_only_director_denied(url_name, director, client_obj):
    assert _get(client_obj, director, url_name) == 403


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", [
    "catalog:period_admin",
    "catalog:period_create",
    "accounts:user_admin",
    "accounts:user_create",
    "evaluations:arena_impact",
    "dashboards:period_progress",
    "questionnaires:admin_list",
])
def test_admin_only_talento_allowed(url_name, talento, client_obj):
    assert _get(client_obj, talento, url_name) == 200


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", [
    "catalog:period_admin",
    "catalog:period_create",
    "accounts:user_admin",
    "accounts:user_create",
    "evaluations:arena_impact",
    "dashboards:period_progress",
    "questionnaires:admin_list",
])
def test_admin_only_superuser_allowed(url_name, superuser, client_obj):
    assert _get(client_obj, superuser, url_name) == 200


# ---------------------------------------------------------------------------
# 7. Mesa de Talento — Talento + Director (no Lead ni Colab)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_talent_table_colab_denied(colab, client_obj):
    assert _get(client_obj, colab, "dashboards:talent_table") == 403


@pytest.mark.django_db
def test_talent_table_colab_lead_denied(colab_lead, client_obj):
    assert _get(client_obj, colab_lead, "dashboards:talent_table") == 403


@pytest.mark.django_db
def test_talent_table_talento_allowed(talento, client_obj):
    assert _get(client_obj, talento, "dashboards:talent_table") == 200


@pytest.mark.django_db
def test_talent_table_director_allowed(director, client_obj):
    assert _get(client_obj, director, "dashboards:talent_table") == 200


@pytest.mark.django_db
def test_talent_table_superuser_allowed(superuser, client_obj):
    assert _get(client_obj, superuser, "dashboards:talent_table") == 200


# ---------------------------------------------------------------------------
# 8. Validar Entrega de Valor — solo Director (o superusuario)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_vd_review_colab_denied(colab, client_obj):
    assert _get(client_obj, colab, "evaluations:value_delivery_review") == 403


@pytest.mark.django_db
def test_vd_review_colab_lead_denied(colab_lead, client_obj):
    assert _get(client_obj, colab_lead, "evaluations:value_delivery_review") == 403


@pytest.mark.django_db
def test_vd_review_talento_denied(talento, client_obj):
    assert _get(client_obj, talento, "evaluations:value_delivery_review") == 403


@pytest.mark.django_db
def test_vd_review_director_allowed(director, client_obj):
    assert _get(client_obj, director, "evaluations:value_delivery_review") == 200


@pytest.mark.django_db
def test_vd_review_superuser_allowed(superuser, client_obj):
    assert _get(client_obj, superuser, "evaluations:value_delivery_review") == 200


# ---------------------------------------------------------------------------
# 9. Vistas abiertas a todos los autenticados
# ---------------------------------------------------------------------------

@pytest.mark.django_db
@pytest.mark.parametrize("url_name", [
    "dashboards:home",
    "dashboards:my_area",
    "dashboards:help",
    "evaluations:ownership_list",
    "evaluations:value_delivery_list",
    "evaluations:ownership_validation",
    "accounts:profile",
])
def test_open_views_accessible_to_all_roles(url_name, colab, colab_lead, talento, director, superuser, client_obj):
    for user in (colab, colab_lead, talento, director, superuser):
        assert _get(client_obj, user, url_name) == 200, f"{user.email} debería poder acceder a {url_name}"


# ---------------------------------------------------------------------------
# 10. Reabrir evaluación de Ownership — solo Talento/admin (RN-06)
# ---------------------------------------------------------------------------

@pytest.fixture
def period_v(db):
    from datetime import date
    return EvaluationPeriod.objects.create(
        name="2026-VP", start_date=date(2026, 1, 1), end_date=date(2026, 6, 30),
        status=EvaluationPeriod.Status.ABIERTO,
    )


@pytest.fixture
def ownership_eval(db, colab, existing_project, period_v, level_jr_v):
    from apps.questionnaires.models import QuestionnaireTemplate
    tpl = QuestionnaireTemplate.objects.create(
        kind=QuestionnaireTemplate.Kind.OWNERSHIP,
        area=colab.area, level=level_jr_v,
        version=1, status=QuestionnaireTemplate.Status.PUBLICADO,
    )
    from apps.evaluations.models import OwnershipEvaluation, OwnershipEvaluator
    ev = OwnershipEvaluation.objects.create(
        user=colab, project=existing_project, period=period_v,
        template=tpl, status=OwnershipEvaluation.Status.ENVIADA,
    )
    OwnershipEvaluator.objects.create(evaluation=ev, user=colab, is_primary=True)
    return ev


@pytest.mark.django_db
def test_reopen_ownership_colab_denied(colab, ownership_eval, client_obj):
    client_obj.force_login(colab)
    resp = client_obj.post(reverse("evaluations:ownership_reopen", kwargs={"pk": ownership_eval.pk}))
    # El POST redirige; pero la evaluación NO debería haberse reabierto
    from apps.evaluations.models import OwnershipEvaluation
    ev = OwnershipEvaluation.objects.get(pk=ownership_eval.pk)
    assert ev.is_submitted, "Un colaborador no debe poder reabrir una evaluación"


@pytest.mark.django_db
def test_reopen_ownership_talento_allowed(talento, ownership_eval, client_obj):
    client_obj.force_login(talento)
    client_obj.post(reverse("evaluations:ownership_reopen", kwargs={"pk": ownership_eval.pk}))
    from apps.evaluations.models import OwnershipEvaluation
    ev = OwnershipEvaluation.objects.get(pk=ownership_eval.pk)
    assert not ev.is_submitted, "Talento debe poder reabrir una evaluación"


# ---------------------------------------------------------------------------
# 11. Autosave de Impacto Arena — solo Talento/admin (JSON 403)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_arena_impact_autosave_colab_denied(colab, client_obj):
    client_obj.force_login(colab)
    resp = client_obj.post(
        reverse("evaluations:arena_impact_autosave"),
        data=b'{"user_id": 1, "score": "3"}',
        content_type="application/json",
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_arena_impact_autosave_talento_needs_period(talento, client_obj):
    client_obj.force_login(talento)
    resp = client_obj.post(
        reverse("evaluations:arena_impact_autosave"),
        data=b'{"user_id": 999, "score": "3"}',
        content_type="application/json",
    )
    # Sin periodo abierto devuelve 400, no 403
    assert resp.status_code in (400, 404)
