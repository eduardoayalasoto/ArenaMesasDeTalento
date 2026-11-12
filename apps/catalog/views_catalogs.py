"""Catálogos de Puestos y de Categorías de pregunta (spec 008)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from apps.access.decorators import requires
from apps.core.services import positions

from .forms import CategoryForm, PositionForm
from .models import Area, Position, SeniorityLevel


def _form_errors(form):
    return " ".join(e for errs in form.errors.values() for e in errs)


@login_required
@requires("catalog.positions.manage")
def position_admin(request):
    """Puestos por área × nivel: nombre visible y estado. Los niveles globales no cambian."""
    if request.method == "POST":
        if request.POST.get("action") == "complete":
            created = positions.ensure_default_positions()
            messages.success(request, f"Agregué {created} puesto(s) faltante(s) con su nombre por defecto.")
        else:
            form = PositionForm(request.POST)
            if form.is_valid():
                area = get_object_or_404(Area, pk=form.cleaned_data["area"])
                level = get_object_or_404(SeniorityLevel, pk=form.cleaned_data["level"])
                Position.objects.update_or_create(
                    area=area, level=level,
                    defaults={"name": form.cleaned_data["name"], "is_active": form.cleaned_data["is_active"]},
                )
                messages.success(request, f"Guardé el puesto «{form.cleaned_data['name']}» de {area.name}.")
            else:
                messages.error(request, _form_errors(form))
        return redirect("catalog:position_admin")

    levels = list(SeniorityLevel.objects.order_by("order"))
    existing = {(p.area_id, p.level_id): p for p in Position.objects.all()}
    blocks = [
        {
            "area": area,
            "rows": [{"level": level, "position": existing.get((area.pk, level.pk))} for level in levels],
        }
        for area in Area.objects.order_by("code")
    ]
    missing = sum(1 for b in blocks for r in b["rows"] if r["position"] is None)
    return render(request, "catalog/position_admin.html", {
        "page_title": "Puestos", "blocks": blocks, "missing": missing,
    })


@login_required
@requires("catalog.categories.manage")
def category_admin(request):
    """Categorías de pregunta (catálogo común). Los pesos viven en cada cuestionario."""
    from apps.questionnaires.models import Category

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if not form.is_valid():
            messages.error(request, _form_errors(form))
            return redirect("catalog:category_admin")
        data = form.cleaned_data
        with transaction.atomic():
            if data.get("category"):
                category = get_object_or_404(Category, pk=data["category"])
                category.name, category.order, category.is_active = data["name"], data["order"], data["is_active"]
                category.save()
                messages.success(request, f"Actualicé la categoría «{category.name}».")
            else:
                category = Category.objects.create(
                    code=_unique_code(slugify(data["name"]) or "categoria"),
                    name=data["name"], order=data["order"], is_active=True,
                )
                messages.success(request, f"Creé la categoría «{category.name}».")
        return redirect("catalog:category_admin")

    return render(request, "catalog/category_admin.html", {
        "page_title": "Categorías",
        "categories": Category.objects.prefetch_related("questions", "template_links").order_by("order", "name"),
    })


def _unique_code(base):
    from apps.questionnaires.models import Category

    code, n = base[:40], 2
    while Category.objects.filter(code=code).exists():
        suffix = f"-{n}"
        code, n = base[:40 - len(suffix)] + suffix, n + 1
    return code
