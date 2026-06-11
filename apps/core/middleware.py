"""Middleware transversal."""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse


class PasswordChangeRequiredMiddleware:
    """Si el usuario tiene must_change_password, lo obliga a crear una nueva contraseña."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and getattr(user, "must_change_password", False):
            path = request.path
            if not path.startswith(("/static/", "/media/", "/admin/")):
                change_url = reverse("accounts:password_change")
                logout_url = reverse("accounts:logout")
                if path not in (change_url, logout_url):
                    return redirect("accounts:password_change")
        return self.get_response(request)


class PhotoRequiredMiddleware:
    """Obliga a subir la fotografía: redirige al perfil hasta que exista (RN de producto)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated and not user.is_superuser and not user.photo:
            path = request.path
            exempt_prefixes = ("/static/", "/media/", "/admin/")
            if not path.startswith(exempt_prefixes):
                allowed = {
                    reverse("accounts:profile"),
                    reverse("accounts:logout"),
                    reverse("accounts:password_change"),
                }
                if path not in allowed:
                    messages.info(request, "Sube tu fotografía para continuar; es obligatoria.")
                    return redirect("accounts:profile")
        return self.get_response(request)
