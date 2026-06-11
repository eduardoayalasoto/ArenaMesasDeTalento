"""Vistas transversales: páginas de error amigables en español (RN: error handling)."""

from django.shortcuts import render


def error_403(request, exception=None):
    """Sin permiso. Explica el porqué en términos del modelo y ofrece una salida."""
    return render(
        request,
        "errors/403.html",
        {
            "titulo": "No tienes acceso a esta página",
            "mensaje": "Esta sección pertenece a otra área o rol. "
            "Si crees que deberías verla, contacta a Talento y Cultura.",
        },
        status=403,
    )


def error_404(request, exception=None):
    return render(
        request,
        "errors/404.html",
        {
            "titulo": "No encontramos esta página",
            "mensaje": "Es posible que el enlace haya cambiado o que la "
            "evaluación ya no exista.",
        },
        status=404,
    )


def error_500(request):
    return render(
        request,
        "errors/500.html",
        {
            "titulo": "Algo salió mal de nuestro lado",
            "mensaje": "Ya registramos el problema. Intenta de nuevo en unos "
            "minutos; si persiste, avísale a Talento y Cultura.",
        },
        status=500,
    )
