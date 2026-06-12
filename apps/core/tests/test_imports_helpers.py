"""Funciones puras de importación: normalización y resolución de usuarios."""

from apps.core.text import normalize_name


def test_normalize_quita_acentos_y_colapsa_espacios():
    assert normalize_name("  José   Antonio  ") == "jose antonio"


def test_normalize_minusculas():
    assert normalize_name("MARÍA Magdalena") == "maria magdalena"


def test_normalize_none_y_vacio():
    assert normalize_name(None) == ""
    assert normalize_name("") == ""
