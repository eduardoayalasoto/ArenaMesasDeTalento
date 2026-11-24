"""Índice de usuarios: búsqueda en vivo, drawer ver/editar/alta, baja, contraseña y bitácora."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.access.models import Profile
from apps.accounts.models import UserAuditLog
from apps.catalog.models import Position
from apps.core.tests.conftest import make_learn_user

User = get_user_model()
HX = {"HTTP_HX_REQUEST": "true"}


@pytest.fixture
def staff(db, learn_area, learn_levels):
    talento = make_learn_user("t@arena-analytics.com", role="TALENTO")
    talento.profile = Profile.objects.get(slug="talento")
    talento.save(update_fields=["profile"])
    ana = make_learn_user("ana.perez@arena-analytics.com", area=learn_area, level=learn_levels["JR"])
    luis = make_learn_user("luis.gomez@arena-analytics.com", area=learn_area, level=learn_levels["LEAD"])
    for area, level in ((learn_area, learn_levels["JR"]), (learn_area, learn_levels["LEAD"])):
        Position.objects.get_or_create(area=area, level=level, defaults={"name": level.name})
    return {"talento": talento, "ana": ana, "luis": luis}


def _edit_payload(user, **over):
    data = {"full_name": user.full_name, "email": user.email, "area": user.area_id or "", "level": user.level_id or "",
            "role": user.role, "is_active": "on"}
    data.update(over)
    return data


@pytest.mark.django_db
def test_search_any_word_across_fields(client, staff):
    client.force_login(staff["talento"])
    url = reverse("accounts:user_admin")

    def names(**params):
        html = client.get(url, params, **HX).content.decode()
        return {n for n in ("Ana Perez", "Luis Gomez") if n in html}

    assert names(q="perez") == {"Ana Perez"}                  # nombre
    assert names(q="LUIS.GOMEZ@") == {"Luis Gomez"}           # correo, sin importar mayúsculas
    assert names(q="ciencia") == {"Ana Perez", "Luis Gomez"}  # área
    assert names(q="lead ciencia") == {"Luis Gomez"}          # varias palabras (AND) en campos distintos
    assert names(q="colaborador") == {"Ana Perez", "Luis Gomez"}  # etiqueta del rol
    assert names(q="zzz") == set()
    assert names(level="LEAD") == {"Luis Gomez"}              # filtro por nivel
    # El parcial htmx no trae el layout completo; la página completa sí.
    assert "<html" not in client.get(url, **HX).content.decode()
    assert "<html" in client.get(url).content.decode()


@pytest.mark.django_db
def test_edit_drawer_saves_changes_and_audits(client, staff, learn_area, learn_levels):
    ana = staff["ana"]
    client.force_login(staff["talento"])
    url = reverse("accounts:user_edit", args=[ana.pk])
    assert client.get(url).status_code == 302                      # sin htmx no hay drawer
    assert ana.full_name in client.get(url, **HX).content.decode()

    resp = client.post(url, _edit_payload(ana, level=learn_levels["LEAD"].pk, direct_lead=staff["luis"].pk), **HX)
    ana.refresh_from_db()
    assert resp.status_code == 200 and resp["HX-Reswap"] == "none"
    trigger = json.loads(resp["HX-Trigger"])
    assert trigger["users-changed"] and trigger["close-user-drawer"] and trigger["toast"]["variant"] == "success"
    assert ana.level == learn_levels["LEAD"] and ana.direct_lead == staff["luis"]
    entry = UserAuditLog.objects.get(target_user=ana, kind=UserAuditLog.Kind.UPDATED)
    assert entry.actor == staff["talento"] and "Nivel: Junior → Lead" in entry.detail

    # Sin cambios no ensucia la bitácora.
    client.post(url, _edit_payload(ana, level=learn_levels["LEAD"].pk, direct_lead=staff["luis"].pk), **HX)
    assert UserAuditLog.objects.filter(target_user=ana, kind=UserAuditLog.Kind.UPDATED).count() == 1


@pytest.mark.django_db
def test_edit_validation_errors_rerender_drawer(client, staff, learn_levels):
    ana, talento = staff["ana"], staff["talento"]
    client.force_login(talento)
    # Correo duplicado → el formulario vuelve con el error (200, sin cerrar).
    resp = client.post(reverse("accounts:user_edit", args=[ana.pk]), _edit_payload(ana, email=talento.email), **HX)
    assert resp.status_code == 200 and "HX-Trigger" not in resp and "ya existe" in resp.content.decode().lower()
    # No puedes desactivar tu propia cuenta.
    payload = _edit_payload(talento)
    payload.pop("is_active")
    resp = client.post(reverse("accounts:user_edit", args=[talento.pk]), payload, **HX)
    assert "HX-Trigger" not in resp and "propia cuenta" in resp.content.decode()
    talento.refresh_from_db()
    assert talento.is_active


@pytest.mark.django_db
def test_create_user_via_drawer(client, staff, learn_area, learn_levels):
    client.force_login(staff["talento"])
    url = reverse("accounts:user_create")
    resp = client.post(url, {
        "full_name": "Nora Nueva", "email": "Nora@Arena-Analytics.com", "area": learn_area.pk,
        "level": learn_levels["JR"].pk, "role": "COLABORADOR", "is_active": "on",
        "password": "Arena2026!", "must_change_password": "on",
        "direct_lead": staff["luis"].pk, "profile": Profile.objects.get(slug="colaborador").pk,
    }, **HX)
    assert json.loads(resp["HX-Trigger"])["users-changed"]
    nora = User.objects.get(email="nora@arena-analytics.com")
    assert nora.must_change_password and nora.check_password("Arena2026!")
    assert nora.direct_lead == staff["luis"] and nora.profile.slug == "colaborador"
    assert UserAuditLog.objects.filter(target_user=nora, kind=UserAuditLog.Kind.CREATED).exists()


@pytest.mark.django_db
def test_reset_password_and_delete_are_audited(client, staff):
    ana, talento = staff["ana"], staff["talento"]
    client.force_login(talento)
    assert client.get(reverse("accounts:user_reset_password", args=[ana.pk])).status_code == 405  # solo POST
    client.post(reverse("accounts:user_reset_password", args=[ana.pk]))
    ana.refresh_from_db()
    assert ana.check_password("Arena2026!") and ana.must_change_password
    assert UserAuditLog.objects.filter(target_user=ana, kind=UserAuditLog.Kind.PASSWORD_RESET).exists()

    # No puede eliminarse a sí mismo.
    client.post(reverse("accounts:user_delete", args=[talento.pk]))
    assert User.objects.filter(pk=talento.pk, deleted_at__isnull=True).exists()
    # Sin historial: se borra y la bitácora conserva quién era.
    luis_pk = staff["luis"].pk
    client.post(reverse("accounts:user_delete", args=[luis_pk]))
    assert not User.objects.filter(pk=luis_pk).exists()
    entry = UserAuditLog.objects.get(kind=UserAuditLog.Kind.DELETED)
    assert entry.target_user is None and "luis.gomez@arena-analytics.com" in entry.target_label


@pytest.mark.django_db
def test_non_admin_cannot_manage_users(client, staff):
    client.force_login(staff["ana"])
    for name, args in (("accounts:user_admin", []), ("accounts:user_edit", [staff["luis"].pk]),
                       ("accounts:user_create", [])):
        assert client.get(reverse(name, args=args), **HX).status_code == 403
    assert client.post(reverse("accounts:user_reset_password", args=[staff["luis"].pk])).status_code == 403
    assert client.post(reverse("accounts:user_delete", args=[staff["luis"].pk])).status_code == 403
