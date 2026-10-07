"""Administración de Áreas: Director por área (Arena Learn, spec 004)."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

User = get_user_model()


@login_required
def area_admin(request):
    """Áreas y su Director (Arena Learn, spec 004). Solo Talento/admin."""
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento administra las áreas.",
        }, status=403)

    from apps.catalog.forms import AreaDirectorForm
    from apps.catalog.models import Area

    directors = User.objects.filter(
        role=User.Role.DIRECTOR, is_active=True, deleted_at__isnull=True,
    ).order_by("full_name")
    if request.method == "POST":
        form = AreaDirectorForm(request.POST)
        if form.is_valid():
            area = get_object_or_404(Area, pk=form.cleaned_data["area"])
            director_id = form.cleaned_data.get("director")
            if director_id and not directors.filter(pk=director_id).exists():
                messages.error(request, "El usuario elegido no es un Director activo.")
            else:
                area.director_id = director_id or None
                area.save(update_fields=["director"])
                messages.success(request, f"Actualizaste el Director de {area.name}.")
        return redirect("catalog:area_admin")

    return render(request, "catalog/area_admin.html", {
        "page_title": "Áreas",
        "areas": Area.objects.select_related("director").order_by("code"),
        "directors": directors,
    })
