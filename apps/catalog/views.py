"""Pantallas de administración de catálogos para Talento (periodos y proyectos)."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count
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
