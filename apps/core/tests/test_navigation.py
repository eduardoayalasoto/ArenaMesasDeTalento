"""Navbar de arena-talento (docs/PLAN_MIGRACION_DISENO.md §3.3): el menú es datos y sale de la matriz."""

import pytest
from django.test import RequestFactory
from django.urls import reverse

from apps.access import registry
from apps.core.navigation import NAV, build_nav
from apps.core.tests.conftest import make_learn_user


def test_every_nav_item_points_to_a_protected_route():
    """Todo ítem del menú apunta a una ruta con permiso registrado (extiende la cobertura de la spec 005)."""
    names = [it.url_name for cat in NAV for it in cat.items]
    assert len(names) == len(set(names)), "Ítems duplicados en el menú"
    missing = [n for n in names if n not in registry.ROUTE_TO_KEYS]
    assert not missing, "Ítems de menú sin permiso registrado: " + ", ".join(missing)
    assert [c.label for c in NAV] == ["Inicio", "Arena Learn", "Mesa de Talento", "Administración"]
    assert all(it.perm or it.visible for cat in NAV for it in cat.items), "Todo ítem necesita permiso o regla"


def _nav(user, url_name="dashboards:home"):
    req = RequestFactory().get(reverse(url_name))
    req.user = user
    from django.urls import resolve

    req.resolver_match = resolve(req.path)
    return build_nav(req)


@pytest.mark.django_db
def test_menu_by_profile_and_active_state(learn_area, learn_levels, client):
    colab = make_learn_user("colab.nav@arena-analytics.com", area=learn_area, level=learn_levels["JR"])
    talento = make_learn_user("talento.nav@arena-analytics.com", role="TALENTO")
    cats = {c["label"]: [i["label"] for i in c["items"]] for c in _nav(colab)["nav_categories"]}
    assert set(cats) == {"Inicio", "Arena Learn", "Mesa de Talento"}  # sin Administración
    assert "Mis evaluaciones" in cats["Mesa de Talento"] and "Mesa de Talento" not in cats["Mesa de Talento"]
    assert "Aprobar cursos" not in cats["Arena Learn"]
    nav = _nav(talento, "access:profile_list")
    cats = {c["label"]: c for c in nav["nav_categories"]}
    assert set(cats) == {"Inicio", "Arena Learn", "Mesa de Talento", "Administración"}
    assert cats["Administración"]["active"] and any(i["active"] and i["label"] == "Perfiles y permisos"
                                                   for i in cats["Administración"]["items"])
    assert "Mis evaluaciones" not in [i["label"] for i in cats["Mesa de Talento"]["items"]]
    # El navbar (copia del de arena-crm) renderiza la marca y solo las categorías permitidas.
    client.force_login(colab)
    html = client.get(reverse("dashboards:home")).content.decode()
    assert "from-talento-300" in html and "Mesa de Talento" in html and "Administración" not in html


@pytest.mark.django_db
def test_breadcrumb_and_open_category_follow_the_current_screen(learn_area, learn_levels, client):
    """Migas y menú salen del mismo registro: categoría activa desplegada e ítem resaltado."""
    talento = make_learn_user("talento.bc@arena-analytics.com", role="TALENTO")
    nav = _nav(talento, "catalog:project_admin")
    assert nav["nav_active_category"] == "admin"
    assert nav["nav_breadcrumb"] == {"trail": [{"label": "Administración", "icon": "settings", "url": ""}],
                                     "current": "Proyectos", "current_icon": "folder"}
    sub = _nav(talento, "catalog:project_create")["nav_breadcrumb"]
    assert [c["label"] for c in sub["trail"]] == ["Administración", "Proyectos"] and sub["trail"][1]["url"]
    assert _nav(talento)["nav_breadcrumb"]["trail"] == []  # Inicio no repite categoría

    talento.photo_data, talento.photo_mime = b"x", "image/jpeg"
    talento.save()
    client.force_login(talento)
    html = client.get(reverse("catalog:project_create")).content.decode()
    assert 'aria-label="Ruta de navegación"' in html and 'openCategory: "admin"' in html
    assert 'aria-current="page"' in html and "Nuevo proyecto" in html


def test_breadcrumb_skips_category_with_same_name_as_item():
    from apps.core.navigation import _breadcrumb

    cat = {"key": "mesa", "label": "Mesa de Talento", "icon": "table-2"}
    item = {"label": "Mesa de Talento", "icon": "layout-list", "url": "/mesa/", "name": "dashboards:talent_table"}
    assert _breadcrumb(cat, item, True)["trail"] == []
    assert [c["label"] for c in _breadcrumb(cat, item, False)["trail"]] == ["Mesa de Talento"]
