"""Pantallas de administración de catálogos para Talento (periodos y proyectos)."""

from datetime import date

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.vigencia import is_evaluable, open_period
from apps.core.http import back_to_list, is_partial_request
from apps.core.services import period_lifecycle
from apps.core.services import projects as project_service
from apps.core.services import permissions as perm_service

from .forms import PeriodForm, ProjectForm
from .models import EvaluationPeriod, Project, ProjectMembership
from apps.access import services as access
from apps.access.decorators import requires

User = get_user_model()


def _project_has_evals(project) -> bool:
    """True si ya se capturó alguna evaluación de este proyecto (Ownership o Entrega
    de Valor): distingue "Cerrar proyecto" (reversible) de "Eliminar" (definitivo)."""
    from apps.evaluations.models import OwnershipEvaluation, ValueDeliveryEvaluation

    return (
        OwnershipEvaluation.objects.filter(project=project).exists()
        or ValueDeliveryEvaluation.objects.filter(project=project).exists()
    )


@login_required
@requires("projects.edit")
def project_admin(request):
    """Índice de proyectos: búsqueda en vivo (htmx), filtros y acciones por proyecto."""
    params = {k: request.GET.get(k, "").strip() for k in ("q", "state", "duration", "focus", "sort")}
    today = date.today()
    period = open_period()
    projects = list(project_service.search_projects(**params, today=today))
    for p in projects:
        p.delivery = project_service.delivery_info(p, today)
        p.evaluable = is_evaluable(p, period)
        p.close_confirm_id = f"close-project-{p.pk}"
        p.delete_confirm_id = f"delete-project-{p.pk}"
        p.reopen_confirm_id = f"reopen-project-{p.pk}"
        p.close_message = (f"¿Cerrar «{p.name}»? Ya no aparecerá para hacer evaluaciones del periodo Abierto. "
                           "Puedes reabrirlo cuando quieras.")
        p.reopen_message = f"¿Reabrir «{p.name}»? Volverá a aparecer para hacer evaluaciones en el periodo Abierto."
        p.delete_message = f"¿Eliminar «{p.name}»? Esta acción no se puede deshacer."
    context = {
        "page_title": "Proyectos",
        "projects": projects,
        "total": len(projects),
        "filtered": any(v for k, v in params.items() if k != "sort"),
        "states": project_service.STATE_CHOICES,
        "durations": project_service.DURATION_CHOICES,
        "focuses": project_service.FOCUS_CHOICES,
        "sorts": project_service.SORT_CHOICES,
        "can_close": access.has(request.user, "projects.close"),
        **params,
    }
    template = "catalog/_project_results.html" if is_partial_request(request) else "catalog/project_admin.html"
    return render(request, template, context)


@login_required
@requires("projects.edit")
def project_edit(request, pk=None):
    """Crea o edita un proyecto y gestiona su equipo (solo Talento/admin)."""
    if not access.has(request.user, "projects.edit"):
        return render(request, "errors/403.html", {
            "titulo": "No tienes acceso a Proyectos",
            "mensaje": "Solo Talento, Leads y Directores administran los proyectos.",
        }, status=403)

    project = get_object_or_404(Project, pk=pk) if pk else None

    if request.method == "POST":
        action = request.POST.get("action", "save")

        if action == "add_member" and project:
            user = get_object_or_404(User, pk=request.POST.get("user"))
            ProjectMembership.objects.get_or_create(project=project, user=user)
            messages.success(request, f"Agregaste a {user.full_name} al equipo.")
            return redirect("catalog:project_edit", pk=project.pk)

        if action == "remove_member" and project:
            ProjectMembership.objects.filter(
                project=project, pk=request.POST.get("membership")
            ).delete()
            messages.info(request, "Quitaste a la persona del equipo.")
            return redirect("catalog:project_edit", pk=project.pk)

        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            project = form.save()
            messages.success(request, f"Guardaste el proyecto «{project.name}».")
            return redirect("catalog:project_edit", pk=project.pk)
    else:
        form = ProjectForm(instance=project)

    members = available = None
    if project:
        members = project.memberships.select_related("user").order_by("user__full_name")
        member_ids = members.values_list("user_id", flat=True)
        available = access.assignable_users("assign.project_role").exclude(pk__in=member_ids).order_by("full_name")

    return render(request, "catalog/project_form.html", {
        "page_title": project.name if project else "Nuevo proyecto",
        "form": form,
        "project": project,
        "members": members,
        "available": available,
    })


@login_required
@requires("periods.manage")
def period_create(request):
    """Alta de un periodo (solo Talento/admin)."""
    if not access.has(request.user, "periods.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento administra los periodos.",
        }, status=403)
    form = PeriodForm()
    if request.method == "POST":
        form = PeriodForm(request.POST)
        if form.is_valid():
            period = form.save()
            messages.success(request, f"Creaste el periodo {period.name}.")
            return redirect("catalog:period_admin")
    return render(request, "catalog/period_form.html", {
        "page_title": "Nuevo periodo",
        "form": form,
    })


@login_required
@requires("periods.manage")
def period_edit(request, pk):
    """Edita un periodo existente (solo Talento/admin)."""
    if not access.has(request.user, "periods.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento administra los periodos.",
        }, status=403)
    period = get_object_or_404(EvaluationPeriod, pk=pk)
    form = PeriodForm(instance=period)
    if request.method == "POST":
        form = PeriodForm(request.POST, instance=period)
        if form.is_valid():
            form.save()
            messages.success(request, f"Periodo «{period.name}» actualizado.")
            return redirect("catalog:period_admin")
    return render(request, "catalog/period_form.html", {
        "page_title": f"Editar {period.name}",
        "form": form,
        "period": period,
    })


@login_required
@requires("periods.manage")
def period_delete(request, pk):
    """Borra un periodo si no tiene datos vinculados (solo Talento/admin)."""
    if not access.has(request.user, "periods.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento administra los periodos.",
        }, status=403)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    period = get_object_or_404(EvaluationPeriod, pk=pk)
    nombre = period.name
    try:
        period.delete()
        messages.success(request, f"Periodo «{nombre}» eliminado.")
    except ProtectedError:
        messages.error(
            request,
            f"No se puede eliminar «{nombre}»: tiene evaluaciones o notas vinculadas.",
        )
    return redirect("catalog:period_admin")


@login_required
@requires("periods.manage")
def period_admin(request):
    """Lista de periodos con apertura/cierre (solo Talento/admin) — RN-13."""
    if not access.has(request.user, "periods.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento y Cultura administra los periodos.",
        }, status=403)

    if request.method == "POST":
        period = get_object_or_404(EvaluationPeriod, pk=request.POST.get("period"))
        action = request.POST.get("action")
        if action == "open":
            try:
                period_lifecycle.open_period(period, actor=request.user)
                messages.success(request, f"Abriste el periodo {period.name}.")
            except ValidationError as e:
                messages.error(request, " ".join(e.messages))
        elif action == "close":
            try:
                next_period = period_lifecycle.close_and_open_next(period, actor=request.user)
                messages.info(
                    request,
                    f"Cerraste el periodo {period.name}. Queda en solo lectura. "
                    f"Se abrió automáticamente «{next_period.name}».",
                )
            except ValidationError as e:
                messages.error(request, " ".join(e.messages))
        return redirect("catalog:period_admin")

    open_period = EvaluationPeriod.objects.filter(status=EvaluationPeriod.Status.ABIERTO).first()
    close_confirm_message = None
    if open_period:
        next_period = period_lifecycle.find_contiguous_next(open_period)
        pending = period_lifecycle.pending_activity_counts(open_period)
        lines = [f"¿Cerrar el periodo «{open_period.name}»?", ""]
        if pending["own_total"] or pending["vd_total"] or pending["finals_total"]:
            lines.append("Actividad pendiente:")
            own_pending = pending["own_total"] - pending["own_submitted"]
            vd_pending = pending["vd_total"] - pending["vd_validated"]
            finals_pending = pending["finals_total"] - pending["finals_complete"]
            if own_pending:
                lines.append(f"• {own_pending} evaluación(es) de Ownership sin enviar")
            if vd_pending:
                lines.append(f"• {vd_pending} Entrega(s) de Valor sin validar")
            if finals_pending:
                lines.append(f"• {finals_pending} calificación(es) final(es) incompleta(s)")
            if not (own_pending or vd_pending or finals_pending):
                lines.append("• Ninguna: toda la actividad de este periodo ya está completa.")
        else:
            lines.append("No hay actividad registrada en este periodo.")
        lines.append("")
        if next_period:
            lines.append(f"Se abrirá automáticamente «{next_period.name}».")
        lines.append("Esta acción no se puede deshacer desde aquí.")
        close_confirm_message = "\n".join(lines)

    periods = list(EvaluationPeriod.objects.all())
    for p in periods:  # datos de los diálogos de confirmación (components/_confirm.html)
        p.close_confirm_id, p.open_confirm_id, p.delete_confirm_id = (
            f"close-period-{p.pk}", f"open-period-{p.pk}", f"delete-period-{p.pk}")
        p.close_fields = {"period": p.pk, "action": "close"}
        p.open_fields = {"period": p.pk, "action": "open"}
        p.open_message = f"¿Abrir el periodo «{p.name}»?"
        p.delete_message = f"¿Eliminar el periodo «{p.name}»? Si tiene evaluaciones no se podrá borrar."
    return render(request, "catalog/period_admin.html", {
        "page_title": "Periodos",
        "periods": periods,
        "close_confirm_message": close_confirm_message,
    })


@login_required
@require_POST
@requires("projects.close")
def project_delete(request, pk):
    """Borra o cierra un proyecto (solo Talento/admin).

    Sin evaluaciones → se elimina. Con evaluaciones → se cierra (is_active=False), reversible.
    """
    project = get_object_or_404(Project, pk=pk)
    if _project_has_evals(project):
        project.is_active = False
        project.save(update_fields=["is_active"])
        messages.info(request, f"Proyecto «{project.name}» cerrado: ya no aparece para hacer evaluaciones del periodo Abierto. Puedes reabrirlo desde la lista.")
    else:
        nombre = project.name
        project.delete()
        messages.success(request, f"Proyecto «{nombre}» eliminado permanentemente.")
    return back_to_list(request, "catalog:project_admin")


@login_required
@require_POST
@requires("projects.close")
def project_reactivate(request, pk):
    """Reactiva un proyecto cerrado (solo Talento/admin)."""
    project = get_object_or_404(Project, pk=pk)
    project.is_active = True
    project.save(update_fields=["is_active"])
    messages.success(request, f"Proyecto «{project.name}» reabierto: vuelve a aparecer para hacer evaluaciones del periodo Abierto.")
    return back_to_list(request, "catalog:project_admin")


@login_required
@requires("scenarios.manage")
def scenario_admin(request):
    """Lista de escenarios con toggle/delete (solo Talento/admin)."""
    if not access.has(request.user, "scenarios.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento administra el catálogo de escenarios.",
        }, status=403)

    from apps.catalog.models import ScenarioOption

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "toggle":
            opt = get_object_or_404(ScenarioOption, pk=request.POST.get("pk"))
            opt.is_active = not opt.is_active
            opt.save(update_fields=["is_active"])
            messages.success(request, f"«{opt.name}» {'activado' if opt.is_active else 'desactivado'}.")
        elif action == "delete":
            opt = get_object_or_404(ScenarioOption, pk=request.POST.get("pk"))
            try:
                nombre = opt.name
                opt.delete()
                messages.success(request, f"«{nombre}» eliminado.")
            except ProtectedError:
                messages.error(request, "No se puede eliminar: hay notas que lo usan.")
        return redirect("catalog:scenario_admin")

    options = list(ScenarioOption.objects.all())
    for opt in options:  # diálogo de confirmación (components/_confirm.html)
        opt.delete_confirm_id = f"delete-scenario-{opt.pk}"
        opt.delete_fields = {"action": "delete", "pk": opt.pk}
        opt.delete_message = f"¿Eliminar «{opt.name}»?"
    return render(request, "catalog/scenario_admin.html", {
        "page_title": "Escenarios",
        "options": options,
    })


@login_required
@requires("scenarios.manage")
def scenario_create(request):
    """Alta de un escenario nuevo (solo Talento/admin)."""
    if not access.has(request.user, "scenarios.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento administra el catálogo de escenarios.",
        }, status=403)

    from apps.catalog.models import ScenarioOption

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        order = request.POST.get("order", 1)
        if name:
            ScenarioOption.objects.create(name=name, description=description, order=order)
            messages.success(request, f"Escenario «{name}» creado.")
            return redirect("catalog:scenario_admin")

    return render(request, "catalog/scenario_form.html", {
        "page_title": "Nuevo escenario",
    })


@login_required
@requires("scenarios.manage")
def scenario_edit(request, pk):
    """Edita un escenario existente (solo Talento/admin)."""
    if not access.has(request.user, "scenarios.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento administra el catálogo de escenarios.",
        }, status=403)

    from apps.catalog.models import ScenarioOption

    opt = get_object_or_404(ScenarioOption, pk=pk)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        order = request.POST.get("order", opt.order)
        if name:
            opt.name = name
            opt.description = description
            opt.order = order
            opt.save(update_fields=["name", "description", "order"])
            messages.success(request, f"Escenario «{opt.name}» actualizado.")
            return redirect("catalog:scenario_admin")

    return render(request, "catalog/scenario_form.html", {
        "page_title": f"Editar {opt.name}",
        "option": opt,
    })
