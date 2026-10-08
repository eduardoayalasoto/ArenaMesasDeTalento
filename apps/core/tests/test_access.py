"""Spec 005: matriz de permisos por perfiles — pruebas compactas por escenario."""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.access import services as access
from apps.access.legacy import EXPECTED_CHANGES, legacy_for
from apps.access.models import AccessAuditLog, Profile
from apps.access.registry import Scope
from apps.access.seed import PROFILE_ORDER, matrix_for
from apps.core.tests.conftest import make_learn_user

User = get_user_model()


def prof(slug):
    return Profile.objects.get(slug=slug)


@pytest.fixture
def people(db, learn_area, learn_levels):
    from apps.catalog.models import Area

    other = Area.objects.create(code="PM", name="PM")
    p = {
        "colab": make_learn_user("camila.cienciadatos@arena-analytics.com", area=learn_area, level=learn_levels["JR"]),
        "lead": make_learn_user("l@arena-analytics.com", area=learn_area, level=learn_levels["LEAD"]),
        "director": make_learn_user("d@arena-analytics.com", role="DIRECTOR"),
        "talento": make_learn_user("t@arena-analytics.com", role="TALENTO"),
        "outsider": make_learn_user("octavio.otraarea@arena-analytics.com", area=other, level=learn_levels["JR"]),
    }
    for key, slug in (("colab", "colaborador"), ("lead", "lead"), ("director", "director"),
                      ("talento", "talento"), ("outsider", "colaborador")):
        p[key].profile = prof(slug)
        p[key].save(update_fields=["profile"])
    return p


@pytest.mark.django_db
def test_seed_parity_with_expected_changes_only():
    """FR-011/FR-012: la semilla en BD = seed-matrix, y difiere del as-is solo en FR-011a."""
    unexpected = []
    for slug in PROFILE_ORDER:
        db = dict(prof(slug).grants.values_list("permission_key", "scope"))
        assert db == matrix_for(slug), f"La BD no coincide con la semilla para {slug}"
        old = legacy_for(slug)
        for key, value in db.items():
            if value != old[key] and (key, slug) not in EXPECTED_CHANGES:
                unexpected.append(f"{slug}/{key}: {Scope(old[key]).label} → {Scope(value).label}")
    assert not unexpected, "Cambios no esperados: " + "; ".join(unexpected)
    assert prof("superusuario").is_system


@pytest.mark.django_db
def test_decisions_fallback_superuser_and_cache(people, learn_levels):
    p = people
    assert access.has(p["talento"], "access.manage") and not access.has(p["director"], "access.manage")
    assert access.scope(p["lead"], "people.results.view") == Scope.AREA
    assert not access.has(p["colab"], "people.results.view")
    # Sin perfil explícito: el sugerido por rol/nivel (nunca más que su rol).
    t2 = make_learn_user("t2@arena-analytics.com", role="TALENTO")
    l2 = make_learn_user("l2@arena-analytics.com", level=learn_levels["LEAD"])
    assert access.has(t2, "access.manage") and access.scope(l2, "people.results.view") == Scope.AREA
    su = User.objects.create_superuser(email="su@arena-analytics.com", password=None, full_name="SU")
    assert access.scope(su, "weights.manage") == Scope.TODOS
    with pytest.raises(KeyError):
        access.has(p["colab"], "no.existe")
    # Caché por request: el cambio aplica en el siguiente request (objeto nuevo).
    access.save_matrix(prof("director"), {"talent_table.view": 0}, p["talento"])
    assert access.has(p["director"], "talent_table.view")  # mismo objeto: caché del request
    assert not access.has(User.objects.get(pk=p["director"].pk), "talent_table.view")


@pytest.mark.django_db
def test_matrix_change_drives_menu_and_403(client, people):
    """US1: quitar Mesa de Talento al Director → desaparece del menú y la URL responde 403."""
    p = people
    client.force_login(p["director"])
    html = client.get(reverse("dashboards:talent_table")).content.decode()
    assert "Mesa de Talento" in html
    client.force_login(p["talento"])
    resp = client.post(reverse("access:profile_matrix", args=["director"]),
                       {"action": "matrix", "perm-talent_table.view": "0"})
    assert resp.status_code == 302
    assert AccessAuditLog.objects.filter(kind="GRANT_CHANGED", permission_key="talent_table.view").exists()
    client.force_login(p["director"])
    assert client.get(reverse("dashboards:talent_table")).status_code == 403
    assert reverse("dashboards:talent_table") not in client.get(reverse("dashboards:home")).content.decode()
    # FR-011a: Director ya no abre Mis evaluaciones; Colaborador no exporta.
    assert client.get(reverse("evaluations:ownership_list")).status_code == 403
    client.force_login(p["colab"])
    assert client.get(reverse("dashboards:export_scores_xlsx")).status_code == 403
    assert client.get(reverse("access:profile_list")).status_code == 403


@pytest.mark.django_db
def test_lead_flexible_by_area(client, people):
    """US4: Lead con Mesa de Talento = Su área ve solo su área."""
    p = people
    access.save_matrix(prof("lead"), {"talent_table.view": int(Scope.AREA)}, p["talento"])
    client.force_login(p["lead"])
    html = client.get(reverse("dashboards:talent_table")).content.decode()
    assert p["colab"].full_name in html and p["outsider"].full_name not in html
    assert client.get(reverse("dashboards:talent_person", args=[p["colab"].pk])).status_code == 200
    assert client.get(reverse("dashboards:talent_person", args=[p["outsider"].pk])).status_code == 403


@pytest.mark.django_db
def test_profile_crud_assignment_and_lockout(client, people):
    p = people
    client.force_login(p["talento"])
    client.post(reverse("access:profile_list"), {"name": "Lead extendido", "description": ""})
    ext = Profile.objects.get(name="Lead extendido")
    assert not ext.grants.exists()
    client.post(reverse("access:profile_duplicate", args=["lead"]), {"name": "Lead + Learn"})
    dup = Profile.objects.get(name="Lead + Learn")
    assert dict(dup.grants.values_list("permission_key", "scope")) == matrix_for("lead")
    # Asignar desde el perfil mueve a la persona; el perfil con gente no se elimina.
    client.post(reverse("access:profile_assign", args=[dup.slug]), {"user": p["lead"].pk})
    p["lead"].refresh_from_db()
    assert p["lead"].profile == dup
    client.post(reverse("access:profile_delete", args=[dup.slug]))
    assert Profile.objects.filter(pk=dup.pk).exists()
    client.post(reverse("access:profile_delete", args=[ext.slug]))
    assert not Profile.objects.filter(pk=ext.pk).exists()
    # Selector en Usuarios (solo filas presentes en el POST).
    c = p["colab"]
    client.post(reverse("accounts:user_admin"), {
        f"area-{c.id}": "CD", f"level-{c.id}": "JR", f"role-{c.id}": "COLABORADOR",
        f"profile-{c.id}": prof("lead").pk,
    })
    c.refresh_from_db()
    assert c.profile.slug == "lead"
    assert AccessAuditLog.objects.filter(kind="PROFILE_ASSIGNED", target_user=c).exists()
    # Auto-bloqueo (FR-007): no se puede dejar sin quien administre la matriz.
    with pytest.raises(ValidationError):
        access.save_matrix(prof("talento"), {"access.manage": 0}, p["talento"])
    with pytest.raises(ValidationError):
        access.assign_profile(p["talento"], prof("colaborador"), p["talento"])
    assert client.get(reverse("access:effective_access", args=[c.pk])).status_code == 200


@pytest.mark.django_db
def test_assignables_filter_selectors(people):
    """US5: los selectores listan solo a quien su perfil permite asignar."""
    p = people
    direct_leads = set(access.assignable_users("assign.direct_lead"))
    assert p["lead"] in direct_leads and p["colab"] not in direct_leads and p["talento"] not in direct_leads
    assert set(access.assignable_users("assign.area_director")) == {p["director"]}
    access.save_matrix(prof("lead"), {"assign.direct_lead": 0}, p["talento"])
    assert p["lead"] not in set(access.assignable_users("assign.direct_lead"))
