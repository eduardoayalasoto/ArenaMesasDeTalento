"""Pantallas de cuenta: perfil (foto + contraseña) y administración de usuarios (Talento)."""

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.db import ProtectedError
from django.http import Http404, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.catalog.models import Area, SeniorityLevel

from .forms import ProfileInfoForm, SpanishPasswordChangeForm, UserCreateForm

User = get_user_model()


@login_required
def user_create(request):
    """Alta de un usuario nuevo (solo Talento/admin)."""
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento y Cultura crea usuarios.",
        }, status=403)

    form = UserCreateForm()
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Creaste a {user.full_name} ({user.email}).")
            return redirect("accounts:user_admin")

    return render(request, "accounts/user_create.html", {
        "page_title": "Nuevo usuario",
        "form": form,
    })


@login_required
def user_photo(request, pk):
    """Sirve la foto guardada en la BD (Vercel no tiene FS de escritura)."""
    u = User.objects.filter(pk=pk).only("photo_data", "photo_mime").first()
    if not u or not u.photo_data:
        raise Http404("Sin foto")
    resp = HttpResponse(bytes(u.photo_data), content_type=u.photo_mime or "image/jpeg")
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


@login_required
def user_admin(request):
    """Asignación masiva de área, nivel y rol (criterio de salida de Fase 1)."""
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento y Cultura administra a los colaboradores.",
        }, status=403)

    areas = {a.code: a for a in Area.objects.all()}
    levels = {l.code: l for l in SeniorityLevel.objects.all()}

    if request.method == "POST":
        updated = 0
        for user in User.objects.filter(is_superuser=False, deleted_at__isnull=True):
            if f"area-{user.id}" not in request.POST:
                continue  # usuario no estaba visible en el form (filtro activo)
            area_code = request.POST.get(f"area-{user.id}", "")
            level_code = request.POST.get(f"level-{user.id}", "")
            role = request.POST.get(f"role-{user.id}", user.role)
            new_area = areas.get(area_code)
            new_level = levels.get(level_code)
            if (user.area_id != (new_area.id if new_area else None)
                    or user.level_id != (new_level.id if new_level else None)
                    or user.role != role):
                user.area = new_area
                user.level = new_level
                user.role = role
                user.save(update_fields=["area", "level", "role"])
                updated += 1
        messages.success(request, f"Actualizaste {updated} colaborador(es).")
        return redirect("accounts:user_admin")

    q = request.GET.get("q", "").strip()
    users = User.objects.filter(is_superuser=False, deleted_at__isnull=True).select_related("area", "level")
    if q:
        users = users.filter(full_name__icontains=q)

    return render(request, "accounts/user_admin.html", {
        "page_title": "Usuarios",
        "users": users.order_by("full_name"),
        "areas": Area.objects.all(),
        "levels": SeniorityLevel.objects.all(),
        "roles": User.Role.choices,
        "q": q,
    })


@login_required
def user_reset_password(request, pk):
    """Restablece la contraseña de un colaborador a Arena2026! (solo Talento/admin)."""
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Acción reservada a Talento",
            "mensaje": "Solo Talento y Cultura puede resetear contraseñas.",
        }, status=403)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    user = get_object_or_404(User, pk=pk, is_superuser=False)
    user.set_password("Arena2026!")
    user.must_change_password = True
    user.save(update_fields=["password", "must_change_password"])
    if request.headers.get("HX-Request"):
        return HttpResponse(
            '<span class="inline-flex items-center gap-1 text-xs font-medium text-emerald-600">'
            '<i data-lucide="check-circle" class="w-3.5 h-3.5"></i>Reseteada</span>'
        )
    messages.success(request, f"Contraseña de {user.full_name} restablecida a Arena2026!.")
    return redirect("accounts:user_admin")


@login_required
def user_delete(request, pk):
    """Elimina o desactiva un usuario (solo Talento/admin). Soft delete si tiene historial."""
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Acción reservada a Talento",
            "mensaje": "Solo Talento y Cultura puede eliminar usuarios.",
        }, status=403)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = get_object_or_404(User, pk=pk, is_superuser=False)

    if user.pk == request.user.pk:
        error_msg = "No puedes eliminarte a ti mismo."
        if request.headers.get("HX-Request"):
            return HttpResponse(
                f'<tr id="user-row-{pk}"><td colspan="5" class="px-4 py-2 text-sm text-rose-600">'
                f'{error_msg}</td></tr>'
            )
        messages.error(request, error_msg)
        return redirect("accounts:user_admin")

    from apps.evaluations.models import ArenaImpactScore, FinalScore, OwnershipEvaluation
    has_history = (
        OwnershipEvaluation.objects.filter(user=user).exists()
        or ArenaImpactScore.objects.filter(user=user).exists()
        or FinalScore.objects.filter(user=user).exists()
    )

    if has_history:
        user.is_active = False
        user.deleted_at = timezone.now()
        user.save(update_fields=["is_active", "deleted_at"])
        msg = f"{user.full_name} eliminado/a. Sus evaluaciones históricas se conservan."
    else:
        try:
            nombre = user.full_name
            user.delete()
            msg = f"{nombre} eliminado/a permanentemente."
        except ProtectedError as e:
            protected = list(e.protected_objects)[:3]
            detalle = ", ".join(str(o) for o in protected)
            error_msg = f"No se puede eliminar: hay registros vinculados ({detalle}…). Reasigna primero."
            if request.headers.get("HX-Request"):
                return HttpResponse(
                    f'<tr id="user-row-{pk}"><td colspan="5" class="px-4 py-2 text-sm text-rose-600">'
                    f'{error_msg}</td></tr>'
                )
            messages.error(request, error_msg)
            return redirect("accounts:user_admin")

    if request.headers.get("HX-Request"):
        return HttpResponse("")
    messages.success(request, msg)
    return redirect("accounts:user_admin")
