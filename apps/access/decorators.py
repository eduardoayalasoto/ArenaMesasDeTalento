"""Decorador de permisos por pantalla (spec 005, research R5).

`@requires("clave")` verifica el permiso en el servidor, marca la vista con `_access_keys`
(la prueba de cobertura lo exige en cada ruta) y deja el alcance en `request.access_scope`.
Úsese debajo de `@login_required`.
"""

from functools import wraps

from django.shortcuts import render

from . import registry, services
from .registry import Scope


def forbidden(request, perm_label: str = ""):
    return render(request, "errors/403.html", {
        "titulo": "No tienes acceso a esta sección",
        "mensaje": (f"Tu perfil no incluye «{perm_label}». " if perm_label else "")
        + "Si lo necesitas, pídelo a Talento y Cultura.",
    }, status=403)


def requires_any(*keys: str, at_least: Scope = Scope.PROPIO):
    for k in keys:
        registry.get(k)  # falla al importar si la clave no existe

    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                # El login lo resuelve @login_required / LoginRequiredMixin (redirige a ingresar).
                return view(request, *args, **kwargs)
            granted = [k for k in keys if services.has(user, k, at_least)]
            if not granted:
                return forbidden(request, registry.get(keys[0]).screen)
            request.access_scope = max(services.scope(user, k) for k in granted)
            return view(request, *args, **kwargs)

        wrapped._access_keys = tuple(keys)
        return wrapped

    return decorator


def requires(key: str, at_least: Scope = Scope.PROPIO):
    return requires_any(key, at_least=at_least)
