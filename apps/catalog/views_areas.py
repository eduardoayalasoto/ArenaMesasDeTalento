"""Administración de Áreas: CRUD con drawer (spec 009) y Director por área (Arena Learn, spec 004)."""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.access import services as access
from apps.access.decorators import requires
from apps.core.services import catalogs

User = get_user_model()


@login_required
@requires("areas.manage")
def area_admin(request):
    """Índice de áreas; crear y editar (clave, nombre, Director, estado) en el drawer."""
    if not access.has(request.user, "areas.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento administra las áreas.",
        }, status=403)

    from apps.catalog.forms import AreaDirectorForm, AreaForm
    from apps.catalog.models import Area

    directors = access.assignable_users("assign.area_director").order_by("full_name")
    if request.method == "POST":
        if "name" not in request.POST:  # cambio rápido de Director (flujo de spec 004)
            form = AreaDirectorForm(request.POST)
            if form.is_valid():
                area = get_object_or_404(Area, pk=form.cleaned_data["area"])
                director_id = form.cleaned_data.get("director")
                if director_id and not directors.filter(pk=director_id).exists():
                    messages.error(request, "Esa persona no puede ser Director de área según su perfil.")
                else:
                    area.director_id = director_id or None
                    area.save(update_fields=["director"])
                    messages.success(request, f"Actualicé el Director de {area.name}.")
            return redirect("catalog:area_admin")
        form = AreaForm(request.POST)
        if not form.is_valid():
            messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
            return redirect("catalog:area_admin")
        data = form.cleaned_data
        director_id = data.get("director")
        if director_id and not directors.filter(pk=director_id).exists():
            messages.error(request, "Esa persona no puede ser Director de área según su perfil.")
            return redirect("catalog:area_admin")
        try:
            area = catalogs.save_area(
                pk=data.get("area"), code=data["code"], name=data["name"],
                director_id=director_id, is_active=data["is_active"],
            )
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.success(request, f"Guardé el área «{area.name}».")
        return redirect("catalog:area_admin")

    areas = list(Area.objects.select_related("director").order_by("code"))
    for a in areas:
        a.usage = catalogs.usage(a)
        a.position_count = a.positions.count()
        a.delete_url = reverse("catalog:area_delete", args=[a.pk])
        a.delete_confirm_id = f"delete-area-{a.pk}"
        a.delete_confirm_message = f"Se borra el área «{a.name}». Si algo la usa, no se borra: desactívala."
    return render(request, "catalog/area_admin.html", {
        "page_title": "Áreas", "areas": areas, "directors": directors,
    })


@login_required
@requires("areas.manage")
@require_POST
def area_delete(request, pk):
    from apps.catalog.models import Area

    area = get_object_or_404(Area, pk=pk)
    try:
        catalogs.delete_area(area)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, f"Borré el área «{area.name}».")
    return redirect("catalog:area_admin")
