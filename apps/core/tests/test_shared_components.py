"""Paridad con arena-crm: componentes que deben ser el MISMO archivo en ambos sistemas (DESIGN_SYSTEM.md).

Se omite si el repo hermano no está junto a este (p. ej. en CI).
"""

from pathlib import Path

import pytest
from django.conf import settings

SIBLING = Path(settings.BASE_DIR).parent / "arena-crm"
HOME_URLS = ("{% url 'dashboards:home' %}", "{% url 'core:home' %}")  # única diferencia permitida


def _norm(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    for url in HOME_URLS:
        text = text.replace(url, "{% url HOME %}")
    return text


@pytest.mark.skipif(not SIBLING.exists(), reason="arena-crm no está junto a este repo")
@pytest.mark.parametrize("component", ["_nav_menu.html", "_breadcrumb.html"])
def test_shared_component_is_identical_in_arena_crm(component):
    mine = Path(settings.BASE_DIR) / "templates" / "components" / component
    theirs = SIBLING / "templates" / "components" / component
    assert _norm(mine) == _norm(theirs), (
        f"{component} difiere de arena-crm: aplica el mismo cambio en ambos repos")
