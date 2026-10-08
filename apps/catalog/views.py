"""Pantallas de administración de catálogos para Talento (periodos y proyectos)."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.db.models import Count, Exists, OuterRef
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.services import period_lifecycle
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
    """Lista de proyectos (solo Talento/admin)."""
    if not access.has(request.user, "projects.edit"):
        return render(request, "errors/403.html", {
            "titulo": "No tienes acceso a Proyectos",
            "mensaje": "Solo Talento, Leads y Directores administran los proyectos.",
        }, status=403)
    from apps.evaluations.models import OwnershipEvaluation, ValueDeliveryEvaluation

    projects = (
        Project.objects.select_related("owner", "validador")
        .annotate(
            members=Count("memberships"),
            has_evals=(
                Exists(OwnershipEvaluation.objects.filter(project=OuterRef("pk")))
                | Exists(ValueDeliveryEvaluation.objects.filter(project=OuterRef("pk")))
            ),
        )
        .order_by("name")
    )
    return render(request, "catalog/project_admin.html", {
        "page_title": "Proyectos",
        "projects": projects,
    })


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

    return render(request, "catalog/period_admin.html", {
        "page_title": "Periodos",
        "periods": EvaluationPeriod.objects.all(),
        "close_confirm_message": close_confirm_message,
    })


@login_required
@requires("projects.close")
def project_delete(request, pk):
    """Borra o desactiva un proyecto (solo Talento/admin).

    Sin evaluaciones → hard delete. Con evaluaciones → is_active=False.
    """
    if not access.has(request.user, "projects.close"):
        return render(request, "errors/403.html", {
            "titulo": "Acción reservada a Talento",
            "mensaje": "Solo Talento y Cultura puede eliminar proyectos.",
        }, status=403)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    project = get_object_or_404(Project, pk=pk)
    has_evals = _project_has_evals(project)

    if has_evals:
        project.is_active = False
        project.save(update_fields=["is_active"])
        if request.headers.get("HX-Request"):
            edit_url = f"/catalogo/proyectos/{pk}/"
            reactivar_url = f"/catalogo/proyectos/{pk}/reactivar/"
            client_html = f'<p class="text-base text-slate-500">{project.client}</p>' if project.client else ""
            validador_html = (
                project.validador.full_name if project.validador
                else '<span class="text-slate-400 italic text-base">Sin asignar</span>'
            )
            return HttpResponse(
                f'<tr id="project-row-{pk}">'
                f'<td class="px-4 py-3"><p class="font-medium text-slate-900">{project.name}</p>{client_html}</td>'
                f'<td class="px-4 py-3 text-slate-600">{project.owner.full_name}</td>'
                f'<td class="px-4 py-3 text-slate-600">{validador_html}</td>'
                f'<td class="px-4 py-3 text-slate-600">{project.get_duration_type_display()}</td>'
                f'<td class="px-4 py-3 text-center tabular-nums">—</td>'
                f'<td class="px-4 py-3"><span class="ui-badge bg-slate-100 text-slate-500">Cerrado</span></td>'
                f'<td class="px-4 py-3 text-right flex items-center justify-end gap-1">'
                f'<a href="{edit_url}" class="ui-btn-soft">Editar</a>'
                f'<button type="button" hx-post="{reactivar_url}" hx-target="#project-row-{pk}" hx-swap="outerHTML" hx-confirm="¿Reabrir «{project.name}»? Volverá a aparecer para hacer evaluaciones en el periodo Abierto." class="ui-btn-soft">'
                f'<i data-lucide="rotate-ccw" class="w-3.5 h-3.5 inline mr-1"></i>Reabrir</button>'
                f'</td></tr>'
            )
        messages.info(request, f"Proyecto «{project.name}» cerrado: ya no aparece para hacer evaluaciones del periodo Abierto. Puedes reabrirlo desde la lista.")
    else:
        nombre = project.name
        project.delete()
        if request.headers.get("HX-Request"):
            return HttpResponse("")
        messages.success(request, f"Proyecto «{nombre}» eliminado permanentemente.")

    return redirect("catalog:project_admin")


@login_required
@requires("projects.close")
def project_reactivate(request, pk):
    """Reactiva un proyecto desactivado (solo Talento/admin)."""
    if not access.has(request.user, "projects.close"):
        return render(request, "errors/403.html", {
            "titulo": "Acción reservada a Talento",
            "mensaje": "Solo Talento y Cultura puede reactivar proyectos.",
        }, status=403)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    project = get_object_or_404(Project, pk=pk)
    project.is_active = True
    project.save(update_fields=["is_active"])

    if request.headers.get("HX-Request"):
        members_count = ProjectMembership.objects.filter(project=project).count()
        edit_url = f"/catalogo/proyectos/{pk}/"
        delete_url = f"/catalogo/proyectos/{pk}/eliminar/"
        client_html = f'<p class="text-base text-slate-500">{project.client}</p>' if project.client else ""
        validador_html = (
            project.validador.full_name if project.validador
            else '<span class="text-slate-400 italic text-base">Sin asignar</span>'
        )
        return HttpResponse(
            f'<tr id="project-row-{pk}">'
            f'<td class="px-4 py-3"><p class="font-medium text-slate-900">{project.name}</p>{client_html}</td>'
            f'<td class="px-4 py-3 text-slate-600">{project.owner.full_name}</td>'
            f'<td class="px-4 py-3 text-slate-600">{validador_html}</td>'
            f'<td class="px-4 py-3 text-slate-600">{project.get_duration_type_display()}</td>'
            f'<td class="px-4 py-3 text-center tabular-nums">{members_count}</td>'
            f'<td class="px-4 py-3"><span class="ui-badge bg-emerald-50 text-emerald-700">Abierto</span></td>'
            f'<td class="px-4 py-3 text-right flex items-center justify-end gap-1">'
            f'<a href="{edit_url}" class="ui-btn-soft mr-1">Editar</a>'
            f'<button type="button" hx-post="{delete_url}" hx-target="#project-row-{pk}" hx-swap="outerHTML" hx-confirm="¿Cerrar «{project.name}»? Ya no aparecera para hacer evaluaciones del periodo Abierto. Puedes reabrirlo cuando quieras." class="ui-btn-soft">'
            f'<i data-lucide="lock" class="w-3.5 h-3.5 inline mr-1"></i>Cerrar proyecto</button>'
            f'</td></tr>'
        )
    messages.success(request, f"Proyecto «{project.name}» reabierto: vuelve a aparecer para hacer evaluaciones del periodo Abierto.")
    return redirect("catalog:project_admin")


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

    return render(request, "catalog/scenario_admin.html", {
        "page_title": "Escenarios",
        "options": ScenarioOption.objects.all(),
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
