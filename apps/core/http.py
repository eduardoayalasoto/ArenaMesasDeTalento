"""Utilidades HTTP compartidas por las pantallas de administración."""

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
