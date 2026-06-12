"""Helpers para importar proyectos y membresías desde el xlsx de Talento."""

from datetime import date, datetime

from apps.core.text import normalize_name

# Personas que aparecen en el Excel pero no existen como usuario: se crean.
# clave: nombre normalizado -> (nombre completo, correo)
USERS_TO_CREATE = {
    normalize_name("Carolina Palacio"): (
        "Carolina Palacio", "cpalacio@arena-analytics.com",
    ),
    normalize_name("Carlos Alejandro Rodríguez Ochoa"): (
        "Carlos Alejandro Rodríguez Ochoa", "crodriguez@arena-analytics.com",
    ),
    normalize_name("Arturo Carranza Lucio"): (
        "Arturo Carranza Lucio", "arturo.carranza@arena-analytics.com",
    ),
}

# Clasificación FINITO/INDEFINIDO validada (spec 2026-06-12).
_DURATION_RAW = {
    "MSI": "FINITO",
    "Share Forecast LATAM / Apollo 2.0": "INDEFINIDO",
    "Data Ops / MPM": "INDEFINIDO",
    "GenAI": "FINITO",
    "AI Latam Office Program Manager": "INDEFINIDO",
    "OBPPC": "INDEFINIDO",
    "Weather": "FINITO",
    "Migración 360 a 720": "FINITO",
    "CCL Engineering Cell": "INDEFINIDO",
    "Hypercare Migración 360 a 720": "FINITO",
    "Business Terms Harmonization & SSOT": "FINITO",
    "Rodin": "INDEFINIDO",
    "Urrea Bolsa de Horas": "INDEFINIDO",
    "Coppel Portal (Sistema de Gestión de Categorías)": "FINITO",
    "NSR PM & Comm": "FINITO",
    "Prime Partners Support": "INDEFINIDO",
    "C&CL Report": "FINITO",
}
DURATION_BY_PROJECT = {normalize_name(k): v for k, v in _DURATION_RAW.items()}


def build_user_index(users, alias_pairs=()):
    """Devuelve {nombre_normalizado: user}.

    alias_pairs: iterable de (nombre_corto, correo) del HC Total para
    resolver nombres que no empatan por el nombre completo.
    """
    index = {}
    for u in users:
        key = normalize_name(u.full_name)
        if key:
            index[key] = u
    by_email = {u.email.lower(): u for u in users}
    for short, email in alias_pairs:
        u = by_email.get((email or "").strip().lower())
        if u:
            index.setdefault(normalize_name(short), u)
    return index


def resolve_user(name, index):
    """Resuelve un nombre a User por igualdad y por substring bidireccional."""
    norm = normalize_name(name)
    if not norm:
        return None
    if norm in index:
        return index[norm]
    for key, u in index.items():
        if key and (key in norm or norm in key):
            return u
    return None


def resolve_or_create_user(name, index, *, password, dry):
    """Resuelve un nombre; si está en USERS_TO_CREATE y no existe, lo crea.

    Devuelve (user|None, action) con action en
    {'found', 'created', 'would_create', 'unmatched', 'empty'}.
    Muta `index` al crear, para que llamadas siguientes lo encuentren.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    if not name or not str(name).strip():
        return None, "empty"
    user = resolve_user(name, index)
    if user:
        return user, "found"
    key = normalize_name(name)
    if key in USERS_TO_CREATE:
        full_name, email = USERS_TO_CREATE[key]
        if dry:
            return None, "would_create"
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"full_name": full_name, "role": User.Role.COLABORADOR},
        )
        user.set_password(password)
        user.must_change_password = False
        user.save()
        index[key] = user
        return user, "created"
    return None, "unmatched"


def to_date(value):
    """Convierte celdas datetime/date/str(ISO)/None a date o None.

    Algunas hojas guardan las fechas como texto 'YYYY-MM-DD' (p. ej.
    'Proyectos Dueños'); otras como datetime. Toleramos ambas.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return date.fromisoformat(s[:10])
        except ValueError:
            return None
    return None
