"""Navegación lateral construida según las capacidades del usuario (segregación de pantallas)."""

from django.urls import NoReverseMatch, reverse


def _safe_url(name: str) -> str | None:
    """Devuelve la URL si la ruta existe; None si aún no está registrada.

    Permite construir el menú de forma incremental mientras se desarrollan las fases:
    una entrada cuya vista todavía no existe simplemente no se muestra.
    """
    try:
        return reverse(name)
    except NoReverseMatch:
        return None


def navigation(request):
    """Menú (navbar) desde el registro de apps/core/navigation.py, filtrado por la matriz de permisos.

    Inyecta `nav_categories` (para el navbar) y `nav_items` (lista plana: buscador Ctrl+K y pruebas).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"nav_categories": [], "nav_items": []}
    from apps.core.navigation import build_nav

    return build_nav(request)


def asset_version(request):
    """Versión del CSS compilado (mtime) para cache-busting del navegador."""
    from pathlib import Path

    from django.conf import settings

    css = Path(settings.BASE_DIR) / "static" / "css" / "app.css"
    try:
        return {"asset_version": int(css.stat().st_mtime)}
    except OSError:
        return {"asset_version": 0}


def notifications(request):
    """Pendientes del usuario (cuestionarios por llenar) para el dropdown de la campana."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"pending_items": [], "pending_count": 0}

    from apps.catalog.models import EvaluationPeriod
    from apps.evaluations.models import OwnershipEvaluation

    period = EvaluationPeriod.objects.filter(
        status=EvaluationPeriod.Status.ABIERTO
    ).first()
    items: list[dict] = []

    # Recordatorio: subir fotografía (obligatoria).
    if not user.has_photo:
        items.append({
            "project": "Tu fotografía",
            "text": "Sube tu foto de perfil (obligatoria)",
            "url": _safe_url("accounts:profile") or "#",
            "icon": "camera",
        })

    from apps.access import services as access

    if period and access.has(user, "ownership.self.manage"):
        list_url = _safe_url("evaluations:ownership_list") or "#"
        if user.is_lead:
            # Lead: una sola evaluación transversal (project=None)
            lead_eval = OwnershipEvaluation.objects.filter(
                user=user, period=period, project__isnull=True
            ).first()
            if lead_eval is None:
                items.append({
                    "project": "Todos tus proyectos",
                    "text": "Comienza tu evaluación de Ownership",
                    "url": list_url,
                })
            elif not lead_eval.is_submitted:
                items.append({
                    "project": "Todos tus proyectos",
                    "text": "Continúa tu evaluación de Ownership",
                    "url": _safe_url_args("evaluations:ownership_edit", lead_eval.pk) or list_url,
                })
        else:
            memberships = user.memberships.select_related("project").filter(project__is_active=True)
            evals = {
                e.project_id: e
                for e in OwnershipEvaluation.objects.filter(user=user, period=period)
            }
            for m in memberships:
                ev = evals.get(m.project_id)
                if ev is None:
                    items.append({
                        "project": m.project.name,
                        "text": "Comienza tu evaluación de Ownership",
                        "url": list_url,
                    })
                elif not ev.is_submitted:
                    items.append({
                        "project": m.project.name,
                        "text": "Continúa tu evaluación de Ownership",
                        "url": _safe_url_args("evaluations:ownership_edit", ev.pk) or list_url,
                    })
    # Arena Learn: solicitudes por aprobar, ajustes, cursos por cerrar, evidencias.
    from apps.core.services.learning_flow import pending_for

    items.extend(pending_for(user))
    return {"pending_items": items, "pending_count": len(items)}


def _safe_url_args(name: str, *args) -> str | None:
    try:
        return reverse(name, args=args)
    except NoReverseMatch:
        return None
