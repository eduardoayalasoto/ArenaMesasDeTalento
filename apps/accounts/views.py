"""Pantallas de cuenta: perfil (foto + contraseña) y administración de usuarios (Talento)."""

from django.contrib import messages
from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

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
        for user in User.objects.filter(is_superuser=False):
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
    users = User.objects.filter(is_superuser=False).select_related("area", "level")
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
