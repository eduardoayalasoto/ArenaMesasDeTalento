"""Utilidades HTTP compartidas por las pantallas de administración."""

import json

from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def back_to_list(request, fallback: str):
    """Vuelve al listado conservando búsqueda y filtros (vienen en el Referer de la página).

    Solo acepta referers del mismo host; si no hay, redirige a la ruta `fallback` (nombre de URL).
    """
    referer = request.META.get("HTTP_REFERER", "")
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}):
        return redirect(referer)
    return redirect(fallback)


def hx_done(message: str, variant: str = "success", *, refresh: str = "users-changed",
            close: str = "close-user-drawer") -> HttpResponse:
    """Respuesta htmx de un guardado: toast, cierra el drawer y refresca la lista (sin tocar el cuerpo)."""
    response = HttpResponse("")
    response["HX-Reswap"] = "none"
    response["HX-Trigger"] = json.dumps({
        "toast": {"message": message, "variant": variant},
        refresh: True,
        close: True,
    })
    return response
