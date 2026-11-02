"""Callouts: siempre con ícono Lucide según el tono y sin markup escrito a mano (DESIGN_SYSTEM.md § 6)."""

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template import Context, Template, TemplateSyntaxError


def _render(src, **ctx):
    return Template("{% load callout_tags %}" + src).render(Context(ctx))


@pytest.mark.parametrize("tone,icon", [
    ("info", "info"), ("success", "circle-check"), ("warning", "triangle-alert"),
    ("error", "circle-alert"), ("neutral", "info"),
])
def test_each_tone_renders_its_icon_and_rich_body(tone, icon):
    html = _render(f'{{% callout "{tone}" title="Aviso" %}}Hola <b>{{{{ name }}}}</b>{{% endcallout %}}', name="<x>")
    assert f'data-lucide="{icon}"' in html
    assert "Aviso" in html and "Hola <b>&lt;x&gt;</b>" in html  # el cuerpo conserva el autoescape


def test_icon_override_and_unknown_tone():
    assert 'data-lucide="lock"' in _render('{% callout "neutral" icon="lock" %}x{% endcallout %}')
    with pytest.raises(TemplateSyntaxError):
        _render('{% callout "rojo" %}x{% endcallout %}')


# Caja de aviso hecha a mano: fondo tenue de color semántico + borde (el componente es la única excepción).
RAW_CALLOUT = re.compile(
    r'class="[^"]*rounded-lg[^"]*\bbg-(primary|info|warning|success|error)/10\b[^"]*\bborder\b'
    r'|class="[^"]*\bbg-(primary|info|warning|success|error)/10\b[^"]*\bborder\b[^"]*rounded-lg'
)


def test_no_hand_written_callouts_in_templates():
    root = Path(settings.BASE_DIR) / "templates"
    offenders = []
    for path in root.rglob("*.html"):
        if path.name == "_callout.html":
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "hover:" not in line and RAW_CALLOUT.search(line):
                offenders.append(f"{path.relative_to(root)}:{n}")
    assert not offenders, "Usa {% callout %} (components/_callout.html): " + ", ".join(offenders)
