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
        if user and user.is_authenticated and not user.is_superuser and not user.has_photo:
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


class SecurityHeadersMiddleware:
    """Encabezados de seguridad en TODA respuesta (incluidos estáticos): CSP, Permissions-Policy y CORP.

    HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy y COOP los pone Django (settings).
    La CSP bloquea todo origen que no sea el propio (más Google Fonts) y prohíbe plugins, <base> ajeno,
    formularios hacia otros sitios y que otra página nos enmarque. Se conservan 'unsafe-inline' y
    'unsafe-eval' en scripts porque la interfaz usa Alpine (evalúa expresiones) y atributos on*/hx-on;
    quitarlos exige migrar a la build CSP de Alpine y a nonces.
    """

    def __init__(self, get_response):
        from django.conf import settings

        self.get_response = get_response
        directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com data:",
            "img-src 'self' data: blob:",
            "connect-src 'self'",
            "media-src 'self'",
            "manifest-src 'self'",
            "worker-src 'self'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
        ]
        if not settings.DEBUG:
            directives.append("upgrade-insecure-requests")
        self.csp = "; ".join(directives)
        self.permissions = ", ".join(f"{f}=()" for f in (
            "accelerometer", "autoplay", "camera", "display-capture", "encrypted-media", "fullscreen", "geolocation",
            "gyroscope", "magnetometer", "microphone", "midi", "payment", "picture-in-picture", "publickey-credentials-get",
            "usb", "xr-spatial-tracking"))

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", self.csp)
        response.setdefault("Permissions-Policy", self.permissions)
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        return response
