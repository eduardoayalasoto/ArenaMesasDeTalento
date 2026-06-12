"""Funciones puras de importación: normalización y resolución de usuarios."""

import pytest
from django.contrib.auth import get_user_model

from apps.core.text import normalize_name
from apps.core.services import imports

User = get_user_model()


def test_normalize_quita_acentos_y_colapsa_espacios():
    assert normalize_name("  José   Antonio  ") == "jose antonio"


def test_normalize_minusculas():
    assert normalize_name("MARÍA Magdalena") == "maria magdalena"


def test_normalize_none_y_vacio():
    assert normalize_name(None) == ""
    assert normalize_name("") == ""


@pytest.mark.django_db
def test_build_index_y_resolve_por_nombre_completo():
    u = User.objects.create_user(
        email="oscar@arena-analytics.com", password="x",
        full_name="Oscar Andrés Mancha",
    )
    index = imports.build_user_index([u])
    # substring bidireccional: el nombre del Excel trae apellido extra
    assert imports.resolve_user("Oscar Andrés Mancha Mendoza", index) == u


@pytest.mark.django_db
def test_resolve_por_alias_de_correo():
    u = User.objects.create_user(
        email="abad.arellano@arena-analytics.com", password="x",
        full_name="Ramiro Abad Arellano Carmona",
    )
    index = imports.build_user_index(
        [u], alias_pairs=[("Abad Arellano Cardona", "abad.arellano@arena-analytics.com")]
    )
    assert imports.resolve_user("Abad Arellano Cardona", index) == u


def test_resolve_devuelve_none_si_no_encuentra():
    assert imports.resolve_user("Nadie Existe", {}) is None


def test_mapas_de_duracion_y_usuarios_a_crear():
    from apps.core.text import normalize_name
    assert imports.DURATION_BY_PROJECT[normalize_name("Data Ops / MPM")] == "INDEFINIDO"
    assert imports.DURATION_BY_PROJECT[normalize_name("Weather")] == "FINITO"
    assert normalize_name("Carolina Palacio") in imports.USERS_TO_CREATE


@pytest.mark.django_db
def test_resolve_or_create_crea_usuario_faltante():
    index = {}
    user, action = imports.resolve_or_create_user(
        "Carolina Palacio", index, password="x", dry=False
    )
    assert action == "created"
    assert user.email == "cpalacio@arena-analytics.com"
    user2, action2 = imports.resolve_or_create_user(
        "Carolina Palacio", index, password="x", dry=False
    )
    assert action2 == "found" and user2 == user


@pytest.mark.django_db
def test_resolve_or_create_dry_no_crea():
    user, action = imports.resolve_or_create_user(
        "Carolina Palacio", {}, password="x", dry=True
    )
    assert action == "would_create" and user is None


def test_resolve_or_create_desconocido_unmatched():
    user, action = imports.resolve_or_create_user(
        "Persona Inexistente", {}, password="x", dry=False
    )
    assert action == "unmatched" and user is None
