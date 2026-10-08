"""Administración de Áreas: Director por área (Arena Learn, spec 004)."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from apps.access import services as access
from apps.access.decorators import requires

User = get_user_model()


@login_required
@requires("areas.manage")
def area_admin(request):
    """Áreas y su Director (Arena Learn, spec 004). Solo Talento/admin."""
    if not access.has(request.user, "areas.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento administra las áreas.",
        }, status=403)

    from apps.catalog.forms import AreaDirectorForm
    from apps.catalog.models import Area

    directors = access.assignable_users("assign.area_director").order_by("full_name")
    if request.method == "POST":
        form = AreaDirectorForm(request.POST)
        if form.is_valid():
            area = get_object_or_404(Area, pk=form.cleaned_data["area"])
            director_id = form.cleaned_data.get("director")
            if director_id and not directors.filter(pk=director_id).exists():
                messages.error(request, "Esa persona no puede ser Director de área según su perfil.")
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
