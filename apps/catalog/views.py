"""Pantallas de administración de catálogos para Talento (periodos y proyectos)."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import ProtectedError
from django.db.models import Count
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.services import permissions as perm_service

from .forms import PeriodForm, ProjectForm
from .models import EvaluationPeriod, Project, ProjectMembership

User = get_user_model()


def _require_admin(request):
    return request.user.is_admin


@login_required
def project_admin(request):
    """Lista de proyectos (solo Talento/admin)."""
    if not perm_service.can_edit_project(request.user):
        return render(request, "errors/403.html", {
            "titulo": "No tienes acceso a Proyectos",
            "mensaje": "Solo Talento, Leads y Directores administran los proyectos.",
        }, status=403)
    projects = (
        Project.objects.select_related("owner")
        .annotate(members=Count("memberships"))
        .order_by("name")
    )
    return render(request, "catalog/project_admin.html", {
        "page_title": "Proyectos",
        "projects": projects,
    })


@login_required
def project_edit(request, pk=None):
    """Crea o edita un proyecto y gestiona su equipo (solo Talento/admin)."""
    if not perm_service.can_edit_project(request.user):
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
        available = User.objects.filter(is_active=True).exclude(pk__in=member_ids).order_by("full_name")

    return render(request, "catalog/project_form.html", {
        "page_title": project.name if project else "Nuevo proyecto",
        "form": form,
        "project": project,
        "members": members,
        "available": available,
    })


@login_required
def period_create(request):
    """Alta de un periodo (solo Talento/admin)."""
    if not _require_admin(request):
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
def period_admin(request):
    """Lista de periodos con apertura/cierre (solo Talento/admin) — RN-13."""
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento y Cultura administra los periodos.",
        }, status=403)

    if request.method == "POST":
        period = get_object_or_404(EvaluationPeriod, pk=request.POST.get("period"))
        action = request.POST.get("action")
        if action == "open":
            period.status = EvaluationPeriod.Status.ABIERTO
            period.save(update_fields=["status"])
            messages.success(request, f"Abriste el periodo {period.name}.")
        elif action == "close":
            period.status = EvaluationPeriod.Status.CERRADO
            period.save(update_fields=["status"])
            messages.info(request, f"Cerraste el periodo {period.name}. Queda en solo lectura.")
        return redirect("catalog:period_admin")

    return render(request, "catalog/period_admin.html", {
        "page_title": "Periodos",
        "periods": EvaluationPeriod.objects.all(),
    })


@login_required
def project_delete(request, pk):
    """Borra o desactiva un proyecto (solo Talento/admin).

    Sin evaluaciones → hard delete. Con evaluaciones → is_active=False.
    """
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Acción reservada a Talento",
            "mensaje": "Solo Talento y Cultura puede eliminar proyectos.",
        }, status=403)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    project = get_object_or_404(Project, pk=pk)

    from apps.evaluations.models import OwnershipEvaluation, ValueDeliveryEvaluation
    has_evals = (
        OwnershipEvaluation.objects.filter(project=project).exists()
        or ValueDeliveryEvaluation.objects.filter(project=project).exists()
    )

    if has_evals:
        project.is_active = False
        project.save(update_fields=["is_active"])
        if request.headers.get("HX-Request"):
            edit_url = f"/catalogo/proyectos/{pk}/"
            reactivar_url = f"/catalogo/proyectos/{pk}/reactivar/"
            client_html = f'<p class="text-xs text-slate-500">{project.client}</p>' if project.client else ""
            return HttpResponse(
                f'<tr id="project-row-{pk}">'
                f'<td class="px-4 py-3"><p class="font-medium text-slate-900">{project.name}</p>{client_html}</td>'
                f'<td class="px-4 py-3 text-slate-600">{project.owner.full_name}</td>'
                f'<td class="px-4 py-3 text-slate-600">{project.get_duration_type_display()}</td>'
                f'<td class="px-4 py-3 text-center tabular-nums">—</td>'
                f'<td class="px-4 py-3"><span class="badge bg-slate-100 text-slate-500">Inactivo</span></td>'
                f'<td class="px-4 py-3 text-right flex items-center justify-end gap-1">'
                f'<a href="{edit_url}" class="btn-soft">Editar</a>'
                f'<button type="button" hx-post="{reactivar_url}" hx-target="#project-row-{pk}" hx-swap="outerHTML" hx-confirm="¿Reactivar «{project.name}»?" class="btn-soft">'
                f'<i data-lucide="rotate-ccw" class="w-3.5 h-3.5 inline mr-1"></i>Reactivar</button>'
                f'</td></tr>'
            )
        messages.info(request, f"Proyecto «{project.name}» desactivado. Puedes reactivarlo desde la lista.")
    else:
        nombre = project.name
        project.delete()
        if request.headers.get("HX-Request"):
            return HttpResponse("")
        messages.success(request, f"Proyecto «{nombre}» eliminado permanentemente.")

    return redirect("catalog:project_admin")


@login_required
def project_reactivate(request, pk):
    """Reactiva un proyecto desactivado (solo Talento/admin)."""
    if not request.user.is_admin:
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
        client_html = f'<p class="text-xs text-slate-500">{project.client}</p>' if project.client else ""
        return HttpResponse(
            f'<tr id="project-row-{pk}">'
            f'<td class="px-4 py-3"><p class="font-medium text-slate-900">{project.name}</p>{client_html}</td>'
            f'<td class="px-4 py-3 text-slate-600">{project.owner.full_name}</td>'
            f'<td class="px-4 py-3 text-slate-600">{project.get_duration_type_display()}</td>'
            f'<td class="px-4 py-3 text-center tabular-nums">{members_count}</td>'
            f'<td class="px-4 py-3"><span class="badge bg-emerald-50 text-emerald-700">Activo</span></td>'
            f'<td class="px-4 py-3 text-right flex items-center justify-end gap-1">'
            f'<a href="{edit_url}" class="btn-soft mr-1">Editar</a>'
            f'<span class="relative group/ptip">'
            f'<button type="button" hx-post="{delete_url}" hx-target="#project-row-{pk}" hx-swap="outerHTML" hx-confirm="¿Eliminar «{project.name}»? Esta acción no se puede deshacer." class="p-1.5 rounded-lg text-red-600 hover:bg-red-50 border border-transparent hover:border-red-200 transition cursor-pointer">'
            f'<i data-lucide="trash-2" class="w-4 h-4 inline"></i></button>'
            f'<span class="pointer-events-none absolute bottom-full right-0 mb-1.5 whitespace-nowrap rounded-md bg-slate-800 px-2 py-1 text-xs text-white opacity-0 transition-opacity duration-150 group-hover/ptip:opacity-100 z-20">Eliminar proyecto</span>'
            f'</span></td></tr>'
        )
    messages.success(request, f"Proyecto «{project.name}» reactivado.")
    return redirect("catalog:project_admin")
