"""Catálogos → Perfiles y permisos (spec 005, US1/US2/US7). Diseño tomado de arena-crm (research R10b).

Vistas: validar entrada → servicio (`apps.access.services`) → renderizar. Todas exigen `access.manage`.
"""

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import registry, services
from .decorators import requires
from .models import AccessAuditLog, Profile
from .registry import Scope

User = get_user_model()


class ProfileNameForm(forms.Form):
    name = forms.CharField(label="Nombre del perfil", max_length=80,
                           widget=forms.TextInput(attrs={"class": "input w-full", "placeholder": "p. ej. Lead extendido"}))
    description = forms.CharField(label="Descripción", max_length=240, required=False,
                                  widget=forms.TextInput(attrs={"class": "input w-full"}))


def _error(exc: ValidationError) -> str:
    return " ".join(exc.messages)


@login_required
@requires("access.manage")
def profile_list(request):
    form = ProfileNameForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            profile = services.create_profile(form.cleaned_data["name"], request.user,
                                              description=form.cleaned_data["description"])
            messages.success(request, f"Creaste el perfil «{profile.name}». Configura sus permisos.")
            return redirect("access:profile_matrix", slug=profile.slug)
        except ValidationError as exc:
            form.add_error("name", _error(exc))
    profiles = Profile.objects.filter(is_system=False).annotate(
        n_users=Count("users", distinct=True),
    ).order_by("name")
    return render(request, "access/profile_list.html", {
        "page_title": "Perfiles y permisos",
        "form": form,
        "profiles": profiles,
        "unassigned": User.objects.filter(profile__isnull=True, is_superuser=False,
                                          deleted_at__isnull=True).count(),
        "out_of_profile": services.out_of_profile_assignments(),
        "recent": AccessAuditLog.objects.select_related("actor", "target_user")[:8],
    })


@login_required
@requires("access.manage")
def profile_matrix(request, slug):
    """Editor de UN perfil: nombre, matriz por módulo y personas con este perfil."""
    profile = get_object_or_404(Profile, slug=slug, is_system=False)
    name_form = ProfileNameForm(initial={"name": profile.name, "description": profile.description})

    if request.method == "POST":
        action = request.POST.get("action", "matrix")
        try:
            if action == "rename":
                name_form = ProfileNameForm(request.POST)
                if name_form.is_valid():
                    services.rename_profile(profile, name_form.cleaned_data["name"],
                                            name_form.cleaned_data["description"], request.user)
                    messages.success(request, "Guardaste el nombre del perfil.")
                    return redirect("access:profile_matrix", slug=profile.slug)
            else:
                data = {}
                for perm in registry.PERMISSIONS:
                    raw = request.POST.get(f"perm-{perm.key}")
                    if raw is not None and perm.is_active:
                        data[perm.key] = int(raw)
                n = services.save_matrix(profile, data, request.user)
                messages.success(request, f"Guardaste la matriz: {n} cambio{'s' if n != 1 else ''}."
                                 if n else "No hubo cambios en la matriz.")
                return redirect("access:profile_matrix", slug=profile.slug)
        except (ValidationError, ValueError) as exc:
            messages.error(request, _error(exc) if isinstance(exc, ValidationError) else str(exc))

    current = dict(profile.grants.values_list("permission_key", "scope"))
    modules = []
    for module, perms in registry.grouped():
        rows = []
        for p in perms:
            value = Scope(current.get(p.key, Scope.NINGUNO))
            rows.append({"perm": p, "value": int(value), "options": [(int(s), s.label) for s in p.scopes]})
        modules.append({"module": module, "rows": rows,
                        "granted": sum(1 for r in rows if r["value"] > 0)})
    members = profile.users.filter(deleted_at__isnull=True).select_related("area", "level").order_by("full_name")
    candidates = User.objects.filter(is_superuser=False, deleted_at__isnull=True, is_active=True).exclude(
        profile=profile).select_related("profile").order_by("full_name")
    return render(request, "access/profile_matrix.html", {
        "page_title": f"Perfil · {profile.name}",
        "profile": profile,
        "name_form": name_form,
        "modules": modules,
        "members": members,
        "candidates": candidates,
        "scope_legend": [(s.short, s.label) for s in Scope],
    })


@login_required
@require_POST
@requires("access.manage")
def profile_duplicate(request, slug):
    source = get_object_or_404(Profile, slug=slug, is_system=False)
    name = (request.POST.get("name") or f"{source.name} (copia)").strip()
    try:
        profile = services.create_profile(name, request.user, copy_from=source)
    except ValidationError as exc:
        messages.error(request, _error(exc))
        return redirect("access:profile_matrix", slug=source.slug)
    messages.success(request, f"Duplicaste «{source.name}» como «{profile.name}».")
    return redirect("access:profile_matrix", slug=profile.slug)


@login_required
@require_POST
@requires("access.manage")
def profile_delete(request, slug):
    profile = get_object_or_404(Profile, slug=slug, is_system=False)
    try:
        name = profile.name
        services.delete_profile(profile, request.user)
    except ValidationError as exc:
        messages.error(request, _error(exc))
        return redirect("access:profile_matrix", slug=profile.slug)
    messages.success(request, f"Eliminaste el perfil «{name}».")
    return redirect("access:profile_list")


@login_required
@require_POST
@requires("access.manage")
def profile_assign(request, slug):
    """Asigna (mueve) a una persona a este perfil desde el editor del perfil."""
    profile = get_object_or_404(Profile, slug=slug, is_system=False)
    person = get_object_or_404(User, pk=request.POST.get("user"), is_superuser=False)
    try:
        if services.assign_profile(person, profile, request.user):
            messages.success(request, f"{person.full_name} ahora tiene el perfil «{profile.name}».")
    except ValidationError as exc:
        messages.error(request, _error(exc))
    return redirect("access:profile_matrix", slug=profile.slug)


@login_required
@requires("access.manage")
def effective_access(request, user_pk):
    """Qué puede hacer esta persona: perfil, permisos con alcance y relaciones vigentes (FR-022)."""
    person = get_object_or_404(User.objects.select_related("profile", "area", "level"), pk=user_pk)
    return render(request, "access/effective_access.html", {
        "page_title": f"Acceso de {person.full_name}",
        "data": services.effective_access(person),
        "person": person,
    })
