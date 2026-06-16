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
    """Inyecta `nav_items` en el contexto de todas las plantillas."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"nav_items": []}

    items: list[dict] = []
    current = request.path
    home_url = _safe_url("dashboards:home") or "/"

    def add(label, url_name, icon=""):
        url = _safe_url(url_name)
        if not url:
            return
        if url == home_url:
            active = current == url
        else:
            active = current == url or current.startswith(url)
        items.append(
            {"label": label, "url": url, "icon": icon, "name": url_name, "active": active}
        )

    # Pantallas para todos los autenticados
    add("Mi tablero", "dashboards:home", "home")

    # Colaborador / Lead / Líder de proyecto: capturar Ownership
    if not user.is_talento and not user.is_director or user.is_superuser:
        add("Mis evaluaciones", "evaluations:ownership_list", "clipboard")

    # Lead de área
    if user.is_lead or user.is_admin or user.is_director:
        add("Mi área", "dashboards:my_area", "users")

    # Evaluador de Ownership — solo si tiene al menos una evaluación asignada (primaria o secundaria)
    from apps.evaluations.models import OwnershipEvaluator
    if OwnershipEvaluator.objects.filter(user=user).exists():
        add("Validación de Ownership", "evaluations:ownership_validation", "check")

    # Líder de proyecto — captura de Entrega de Valor
    if user.leads_projects or user.is_superuser:
        add("Entrega de Valor", "evaluations:value_delivery_list", "package")

    # Comité de Talento y Dirección — Mesa de Talento
    if user.is_admin or user.is_director:
        add("Mesa de Talento", "dashboards:talent_table", "table")

    # Director — cola de validación de Entrega de Valor
    if user.is_director or user.is_superuser:
        add("Validar Entrega de Valor", "evaluations:value_delivery_review", "shield")

    # Proyectos — Talento, Leads y Directores (crear/editar todos)
    from apps.core.services.permissions import can_edit_project
    if can_edit_project(user):
        add("Proyectos", "catalog:project_admin", "folder")

    # Talento — captura de Impacto Arena y administración
    if user.is_admin:
        add("Impacto Arena", "evaluations:arena_impact", "star")
        add("Avance del periodo", "dashboards:period_progress", "chart")
        add("Cuestionarios", "questionnaires:admin_list", "list")
        add("Usuarios", "accounts:user_admin", "id")
        add("Periodos", "catalog:period_admin", "calendar")
        add("Ponderaciones", "catalog:weight_admin", "scale")

    return {"nav_items": items}


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

    if period:
        memberships = user.memberships.select_related("project").filter(project__is_active=True)
        evals = {
            e.project_id: e
            for e in OwnershipEvaluation.objects.filter(user=user, period=period)
        }
        list_url = _safe_url("evaluations:ownership_list") or "#"
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
    return {"pending_items": items, "pending_count": len(items)}


def _safe_url_args(name: str, *args) -> str | None:
    try:
        return reverse(name, args=args)
    except NoReverseMatch:
        return None
