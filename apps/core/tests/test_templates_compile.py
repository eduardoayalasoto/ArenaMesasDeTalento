"""Toda plantilla compila: atrapa errores de sintaxis en parciales que solo se renderizan con
datos (p. ej. un codemod de clases que tocó una variable `{% if card.x %}`)."""

from django.conf import settings
from django.template.loader import get_template


def test_todas_las_plantillas_compilan():
    root = settings.BASE_DIR / "templates"
    errores = []
    for path in root.rglob("*.html"):
        name = path.relative_to(root).as_posix()
        try:
            get_template(name)
        except Exception as exc:  # noqa: BLE001 -- se reporta cualquier falla de compilación
            errores.append(f"{name}: {exc}")
    assert not errores, "\n".join(errores)
