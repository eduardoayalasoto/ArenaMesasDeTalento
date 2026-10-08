"""Spec 005 (US6, FR-003): toda ruta está protegida por un permiso registrado, y viceversa.

Base del futuro agente auditor de permisos. Sin BD: recorre el URLconf y el registro.
"""

from django.urls import get_resolver

from apps.access import legacy, registry, seed
from apps.access.registry import Scope


def _routes():
    def walk(patterns, ns=None):
        for p in patterns:
            if hasattr(p, "url_patterns"):
                yield from walk(p.url_patterns, p.namespace or ns)
            elif p.name:
                yield (f"{ns}:{p.name}" if ns else p.name), p.callback

    return [(name, cb) for name, cb in walk(get_resolver().url_patterns) if not name.startswith("admin:")]


def test_every_route_is_protected_and_registered():
    missing, unregistered, mismatched = [], [], []
    for name, cb in _routes():
        if name in registry.EXEMPT_ROUTES:
            continue
        keys = getattr(cb, "_access_keys", None)
        if not keys:
            missing.append(name)
            continue
        for k in keys:
            if k not in registry.BY_KEY:
                unregistered.append(f"{name} → {k}")
        if not set(keys) & registry.ROUTE_TO_KEYS.get(name, set()):
            mismatched.append(f"{name} usa {keys}, el registro dice {sorted(registry.ROUTE_TO_KEYS.get(name, []))}")
    assert not missing, "Rutas sin @requires (agrega su permiso al registro y a la vista): " + ", ".join(missing)
    assert not unregistered, "Claves inexistentes en el registro: " + ", ".join(unregistered)
    assert not mismatched, "Ruta y registro no coinciden: " + "; ".join(mismatched)


def test_every_registered_permission_is_used():
    route_names = {name for name, _ in _routes()}
    orphan = []
    for p in registry.PERMISSIONS:
        if p.kind != "screen" or not p.is_active:
            continue
        if not p.routes:
            orphan.append(f"{p.key} (sin rutas)")
        for r in p.routes:
            if r not in route_names:
                orphan.append(f"{p.key} → {r} (ruta inexistente)")
    assert not orphan, "Permisos huérfanos: " + ", ".join(orphan)


def test_seed_and_legacy_cover_registry_with_valid_scopes():
    assert set(seed.SEED_MATRIX) == set(registry.BY_KEY), "La semilla debe cubrir exactamente el registro."
    assert set(legacy.LEGACY) == set(registry.BY_KEY), "El as-is debe cubrir exactamente el registro."
    for key, values in seed.SEED_MATRIX.items():
        perm = registry.get(key)
        for v in values:
            assert Scope(v) in perm.scopes, f"Semilla: {key} no admite {Scope(v).label}"
