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

    # Resolver URL name actual para detección precisa (evita startswith ambiguo).
    try:
        _rm = request.resolver_match
        current_resolved = (
            f"{_rm.namespace}:{_rm.url_name}" if _rm and _rm.namespace
            else (_rm.url_name if _rm else "")
        )
    except AttributeError:
        current_resolved = ""

    def add(label, url_name, icon="", also_active=(), target=None):
        url = _safe_url(url_name)
        if not url:
            return
        if url == home_url:
            active = current == url
        elif current_resolved:
            active = current_resolved == url_name or current_resolved in also_active
        else:
            # Fallback (p.ej. página 404): comparación por ruta
            active = current == url or current.startswith(url)
        (target if target is not None else items).append(
            {"label": label, "url": url, "icon": icon, "name": url_name, "active": active}
        )

    # Menú derivado de la matriz de perfiles (spec 005, FR-016): nunca se muestra un acceso que la
    # pantalla luego niegue. Donde el alcance es "Asignado", además se exige tener la relación.
    from apps.access import services as access
    from apps.access.registry import Scope

    def can(key, at_least=Scope.PROPIO):
        return access.has(user, key, at_least)

    if can("dashboard.home.view"):
        add("Mi tablero", "dashboards:home", "home")

    if can("ownership.self.manage"):
        add("Mis evaluaciones", "evaluations:ownership_list", "clipboard", also_active=(
            "evaluations:ownership_start",
            "evaluations:ownership_lead_start",
            "evaluations:ownership_edit",
            "evaluations:ownership_view",
            "evaluations:ownership_set_evaluator",
            "evaluations:ownership_add_evaluator",
            "evaluations:ownership_remove_evaluator",
            "evaluations:ownership_autosave",
            "evaluations:ownership_save",
            "evaluations:ownership_reopen",
            "evaluations:ownership_reset",
        ))

    if can("people.results.view", Scope.AREA):
        add("Mi área", "dashboards:my_area", "users")

    from apps.evaluations.models import OwnershipEvaluator
    if can("ownership.validate", Scope.TODOS) or (
        can("ownership.validate", Scope.ASIGNADO) and OwnershipEvaluator.objects.filter(user=user).exists()
    ):
        add("Validación de Ownership", "evaluations:ownership_validation", "check")

    # Retroalimentación: la doy, asisto o la recibo (en cualquier periodo), o alcance Todos.
    from apps.evaluations.models import FeedbackResponsible, TalentSessionNote
    if can("feedback.view", Scope.TODOS) or (can("feedback.view", Scope.ASIGNADO) and (
        FeedbackResponsible.objects.filter(user=user).exists()
        or TalentSessionNote.objects.filter(user=user).exists()
    )):
        add("Retroalimentación", "dashboards:feedback_session_list", "message-circle")

    if can("value_delivery.capture", Scope.TODOS) or (
        can("value_delivery.capture", Scope.ASIGNADO) and user.leads_projects
    ):
        add("Entrega de Valor", "evaluations:value_delivery_list", "package", also_active=(
            "evaluations:value_delivery_capture",
        ))

    if can("learn.self") or can("learn.public.view"):
        add("Arena Learn", "learning:my_courses", "graduation-cap", also_active=(
            "learning:request_start", "learning:request_create", "learning:request_edit", "learning:request_detail",
            "learning:request_complete", "learning:review_edit", "learning:direct_create",
            "learning:catalog_list", "learning:catalog_detail",
            "learning:catalog_create", "learning:catalog_edit", "learning:people_list",
            "learning:person_profile", "learning:course_public", "learning:tracking",
            "learning:historic_create", "learning:settings_edit",
        ))

    from apps.core.services.learning_flow import approvals_for, is_course_approver
    if is_course_approver(user):
        add("Aprobar cursos", "learning:approvals_inbox", "check")
        if items and items[-1]["name"] == "learning:approvals_inbox":
            items[-1]["badge"] = len(approvals_for(user))

    if can("talent_table.view", Scope.AREA):
        add("Mesa de Talento", "dashboards:talent_table", "table")
    if can("current_scenario.view", Scope.AREA):
        add("Escenario Actual", "dashboards:current_scenario_board", "move")

    from apps.core.services.permissions import can_edit_project, has_value_delivery_validations
    if has_value_delivery_validations(user):
        add("Validar Entrega de Valor", "evaluations:value_delivery_review", "shield")

    if can_edit_project(user):
        add("Proyectos", "catalog:project_admin", "folder")

    if can("arena_impact.edit"):
        add("Impacto Arena", "evaluations:arena_impact", "star")
    if can("period_progress.view"):
        add("Avance del periodo", "dashboards:period_progress", "chart")

    # Catálogos administrables — cada uno según su permiso, agrupados en un folder colapsable.
    catalog_children: list[dict] = []
    if can("questionnaires.manage"):
        add("Cuestionarios", "questionnaires:admin_list", "list", target=catalog_children)
    if can("users.manage"):
        add("Usuarios", "accounts:user_admin", "id", target=catalog_children)
    if can("scenarios.manage"):
        add("Escenarios", "catalog:scenario_admin", "layers", target=catalog_children)
    if can("periods.manage"):
        add("Periodos", "catalog:period_admin", "calendar", target=catalog_children)
    if can("areas.manage"):
        add("Áreas", "catalog:area_admin", "map", target=catalog_children)
    if can("access.manage"):
        add("Perfiles y permisos", "access:profile_list", "shield-user", target=catalog_children,
            also_active=("access:profile_matrix", "access:effective_access"))
    if catalog_children:
        items.append({
            "type": "group",
            "label": "Catálogos",
            "icon": "catalog",
            "children": catalog_children,
            "active": any(c["active"] for c in catalog_children),
        })

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
