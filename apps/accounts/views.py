"""Pantallas de cuenta: perfil (foto + contraseña) y administración de usuarios (Talento)."""

import json

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.models import Area, Department, SeniorityLevel
from apps.core.http import back_to_list, hx_done, is_partial_request
from apps.core.services import users as user_service

from .forms import ProfileInfoForm, SpanishPasswordChangeForm, UserAdminForm
from apps.access import services as access
from apps.access.decorators import requires

User = get_user_model()


@login_required
def user_photo(request, pk):
    """Sirve la foto guardada en la BD (Vercel no tiene FS de escritura).

    `?mini=1` sirve la miniatura chica (64x64); si aún no se generó (usuario
    con foto de antes de este campo), cae a la foto completa.
    """
    u = User.objects.filter(pk=pk).only("photo_data", "photo_thumb_data", "photo_mime").first()
    if not u:
        raise Http404("Sin foto")
    mini = request.GET.get("mini") == "1"
    data = (u.photo_thumb_data or u.photo_data) if mini else u.photo_data
    if not data:
        raise Http404("Sin foto")
    resp = HttpResponse(bytes(data), content_type=u.photo_mime or "image/jpeg")
    resp["Cache-Control"] = "private, max-age=86400"
    return resp


@login_required
def password_change(request):
    """Cambio de contraseña; obligatorio cuando must_change_password está activo."""
    forced = request.user.must_change_password
    form = SpanishPasswordChangeForm(user=request.user)
    if request.method == "POST":
        form = SpanishPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            user.must_change_password = False
            user.save(update_fields=["must_change_password"])
            update_session_auth_hash(request, user)
            messages.success(request, "Actualizaste tu contraseña.")
            return redirect("dashboards:home")
    return render(request, "accounts/password_change.html", {
        "page_title": "Cambiar contraseña",
        "form": form,
        "forced": forced,
    })


@login_required
def profile(request):
    """Mi perfil: información personal (nombre + foto) y cambio de contraseña, en pestañas."""
    info_form = ProfileInfoForm(instance=request.user)
    password_form = SpanishPasswordChangeForm(user=request.user)
    active_tab = "info"

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "info":
            info_form = ProfileInfoForm(request.POST, request.FILES, instance=request.user)
            if info_form.is_valid():
                info_form.save()
                messages.success(request, "Actualizaste tu información.")
                return redirect("accounts:profile")
        elif action == "password":
            active_tab = "password"
            password_form = SpanishPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                if user.must_change_password:
                    user.must_change_password = False
                    user.save(update_fields=["must_change_password"])
                update_session_auth_hash(request, user)
                messages.success(request, "Actualizaste tu contraseña.")
                return redirect("accounts:profile")

    return render(request, "accounts/profile.html", {
        "page_title": "Mi perfil",
        "info_form": info_form,
        "password_form": password_form,
        "active_tab": active_tab,
    })


# --- Administración de usuarios (Talento) ---------------------------------------------------------


@login_required
@requires("users.manage")
def user_admin(request):
    """Índice de usuarios: búsqueda en vivo (htmx), filtros y acciones por persona."""
    params = {k: request.GET.get(k, "").strip() for k in ("q", "department", "area", "level", "role", "status")}
    users = list(user_service.search_users(**params))
    context = {
        "page_title": "Usuarios",
        "users": users,
        "total": len(users),
        "filtered": any(params.values()),
        "departments": Department.objects.order_by("order"),
        "areas": Area.objects.select_related("department").order_by("department__order", "name"),
        "levels": SeniorityLevel.objects.all(),
        "roles": User.Role.choices,
        "statuses": user_service.STATUS_CHOICES,
        "can_reset_password": access.has(request.user, "users.reset_password"),
        "can_delete": access.has(request.user, "users.delete"),
        **params,
    }
    for u in users:
        u.reset_confirm_id = f"reset-pwd-{u.pk}"
        u.reset_message = (f"¿Restablecer la contraseña de {u.full_name} a la contraseña inicial? "
                           "Tendrá que cambiarla al iniciar sesión.")
        u.delete_confirm_id = f"delete-user-{u.pk}"
        u.delete_message = (f"¿Eliminar a {u.full_name}? Si tiene evaluaciones se da de baja y se conserva su "
                            "historial; si no, se borra de forma permanente.")
    template = "accounts/_user_results.html" if is_partial_request(request) else "accounts/user_admin.html"
    return render(request, template, context)


def _render_drawer(request, form, target=None):
    from apps.evaluations.models import OwnershipEvaluation

    evaluations = history = ()
    if target is not None:
        evaluations = OwnershipEvaluation.objects.filter(user=target).select_related(
            "period", "project").order_by("-period__start_date", "project__name")
        history = user_service.history_for(target)
    return render(request, "accounts/_user_drawer_form.html", {
        "form": form,
        "target": target,
        "evaluations": evaluations,
        "history": history,
    })


def _drawer_form(request, instance=None):
    kwargs = {
        "actor": request.user,
        "can_assign_profiles": access.has(request.user, "access.manage"),
        "instance": instance,
    }
    return UserAdminForm(request.POST, **kwargs) if request.method == "POST" else UserAdminForm(**kwargs)


@login_required
@requires("users.manage")
def user_create(request):
    """Alta de un usuario nuevo (drawer del índice)."""
    if not request.headers.get("HX-Request"):
        return redirect("accounts:user_admin")
    form = _drawer_form(request)
    if request.method == "POST" and form.is_valid():
        try:
            user = user_service.create_user(form, request.user)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            return hx_done(f"Creaste a {user.full_name} ({user.email}).")
    return _render_drawer(request, form)


@login_required
@requires("users.manage")
def user_edit(request, pk):
    """Ver y editar a una persona (drawer del índice)."""
    if not request.headers.get("HX-Request"):
        return redirect("accounts:user_admin")
    target = get_object_or_404(user_service.base_queryset(), pk=pk)
    form = _drawer_form(request, instance=target)
    if request.method == "POST" and form.is_valid():
        try:
            user, changed = user_service.update_user(form, request.user)
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            if changed:
                return hx_done(f"Actualizaste a {user.full_name}.")
            return hx_done("No hubo cambios que guardar.", "info")
    return _render_drawer(request, form, target)


@login_required
@require_POST
@requires("users.reset_password")
def user_reset_password(request, pk):
    """Restablece la contraseña de un colaborador a la inicial (solo Talento/admin)."""
    user = get_object_or_404(User, pk=pk, is_superuser=False)
    user_service.reset_password(user, request.user)
    messages.success(request, f"Contraseña de {user.full_name} restablecida a {user_service.DEFAULT_PASSWORD}.")
    return back_to_list(request, "accounts:user_admin")


@login_required
@require_POST
@requires("users.delete")
def user_delete(request, pk):
    """Elimina o da de baja a un usuario (solo Talento/admin). Baja lógica si tiene historial."""
    user = get_object_or_404(User, pk=pk, is_superuser=False)
    try:
        messages.success(request, user_service.delete_user(user, request.user))
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return back_to_list(request, "accounts:user_admin")
