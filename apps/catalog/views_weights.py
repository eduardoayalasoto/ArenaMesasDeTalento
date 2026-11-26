"""Ponderación de los 3 pilares por área × posición × nivel (spec 009)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.access.decorators import requires
from apps.core.services import pillar_weights

from .forms import PillarWeightForm
from .models import Position


@login_required
@requires("weights.manage")
def weight_admin(request):
    """Índice de ponderaciones: una fila por posición; el drawer edita (y crea) su ponderación propia."""
    return render(request, "catalog/weight_admin.html", {
        "page_title": "Ponderación de pilares", "rows": pillar_weights.matrix(),
    })


@login_required
@requires("weights.manage")
@require_POST
def weight_save(request):
    form = PillarWeightForm(request.POST)
    if not form.is_valid():
        messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
        return redirect("catalog:weight_admin")
    position = get_object_or_404(Position, pk=form.cleaned_data["position"])
    try:
        if request.POST.get("action") == "reset":
            pillar_weights.reset_to_level(position)
            messages.success(request, f"{position.name} vuelve a usar la ponderación de su nivel.")
        else:
            pillar_weights.save_weights(
                position, form.cleaned_data["w_ownership"], form.cleaned_data["w_value_delivery"],
                form.cleaned_data["w_arena_impact"],
            )
            messages.success(request, f"Guardé la ponderación de {position.area.name} · {position.name}.")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    return redirect("catalog:weight_admin")


@login_required
@requires("weights.manage")
def weight_edit(request, pk):
    """Drawer (htmx) de la ponderación de una posición: ver y editar; guardar o volver a la del nivel."""
    from django.http import HttpResponseRedirect
    from django.urls import reverse

    from .views_org import _done

    if not request.headers.get("HX-Request"):
        return HttpResponseRedirect(reverse("catalog:weight_admin"))
    position = get_object_or_404(Position.objects.select_related("area", "level"), pk=pk)
    error = ""
    if request.method == "POST":
        form = PillarWeightForm({**request.POST.dict(), "position": position.pk})
        if not form.is_valid():
            error = " ".join(e for errs in form.errors.values() for e in errs)
        else:
            try:
                if request.POST.get("action") == "reset":
                    pillar_weights.reset_to_level(position)
                    return _done(f"{position.name} vuelve a usar la ponderación de su nivel.")
                pillar_weights.save_weights(
                    position, form.cleaned_data["w_ownership"], form.cleaned_data["w_value_delivery"],
                    form.cleaned_data["w_arena_impact"])
                return _done(f"Guardaste la ponderación de {position.area.name} · {position.name}.")
            except ValidationError as exc:
                error = " ".join(exc.messages)
    row = next(r for r in pillar_weights.matrix() if r["position"].pk == position.pk)
    vals = ([request.POST.get("w_ownership"), request.POST.get("w_value_delivery"), request.POST.get("w_arena_impact")]
            if error and request.method == "POST" else [row["ownership"] or "0.0", row["value_delivery"] or "0.0", row["arena_impact"] or "0.0"])
    return render(request, "catalog/_weight_form.html", {
        "position": position, "row": row, "vals": vals, "error": error,
        "frozen": pillar_weights.frozen_scores(position),
        "post_url": reverse("catalog:weight_edit", args=[position.pk]),
    })
