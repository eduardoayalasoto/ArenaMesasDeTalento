"""Catálogos de Posiciones y de Categorías de pregunta: CRUD con drawer (specs 008 y 009)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.access.decorators import requires
from apps.core.services import catalogs, positions

from .forms import CategoryForm, PositionForm
from .models import Area, Position, SeniorityLevel


def _form_errors(form):
    return " ".join(e for errs in form.errors.values() for e in errs)


@login_required
@requires("catalog.positions.manage")
def position_admin(request):
    """Posiciones (área × nivel): índice con personas y ponderación; crear/editar en el drawer."""
    if request.method == "POST":
        if request.POST.get("action") == "complete":
            created = positions.ensure_default_positions()
            messages.success(request, f"Agregué {created} posición(es) faltante(s) con su nombre por defecto.")
        else:
            form = PositionForm(request.POST)
            if form.is_valid():
                area = get_object_or_404(Area, pk=form.cleaned_data["area"])
                level = (get_object_or_404(SeniorityLevel, pk=form.cleaned_data["level"])
                         if form.cleaned_data.get("level") else None)
                try:
                    catalogs.save_position(
                        pk=form.cleaned_data.get("position"), area=area, level=level,
                        name=form.cleaned_data["name"], is_active=form.cleaned_data["is_active"],
                    )
                except ValidationError as exc:
                    messages.error(request, " ".join(exc.messages))
                else:
                    messages.success(request, f"Guardé la posición «{form.cleaned_data['name']}» de {area.name}.")
            else:
                messages.error(request, _form_errors(form))
        return redirect("catalog:position_admin")

    rows = [
        {"position": p, "people": p.area.members.filter(level_id=p.level_id).count(),
         "own_weights": hasattr(p, "pillar_weight")}
        for p in Position.objects.select_related("area", "level", "pillar_weight").order_by("area__code", "level__order")
    ]
    for r in rows:
        p = r["position"]
        r["delete_url"] = reverse("catalog:position_delete", args=[p.pk])
        r["delete_confirm_id"] = f"delete-position-{p.pk}"
        r["delete_confirm_message"] = f"Se borra la posición «{p.name}». Si hay personas o cuestionarios con esa área y nivel, no se borra: desactívala."
    missing = positions.missing_default_positions()
    return render(request, "catalog/position_admin.html", {
        "page_title": "Posiciones", "rows": rows, "missing": missing,
        "areas": Area.objects.filter(is_active=True).order_by("code"),
        "levels": SeniorityLevel.objects.order_by("order"),
    })


@login_required
@requires("catalog.positions.manage")
@require_POST
def position_delete(request, pk):
    position = get_object_or_404(Position, pk=pk)
    try:
        catalogs.delete_position(position)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, f"Borré la posición «{position.name}».")
    return redirect("catalog:position_admin")


@login_required
@requires("catalog.categories.manage")
def category_admin(request):
    """Categorías de pregunta (catálogo común). Las ponderaciones viven en cada cuestionario."""
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
                    name=data["name"], order=data["order"], is_active=data["is_active"],
                )
                messages.success(request, f"Creé la categoría «{category.name}».")
        return redirect("catalog:category_admin")

    categories = list(Category.objects.prefetch_related("questions", "template_links").order_by("order", "name"))
    for c in categories:
        c.delete_url = reverse("catalog:category_delete", args=[c.pk])
        c.delete_confirm_id = f"delete-category-{c.pk}"
        c.delete_confirm_message = f"Se borra la categoría «{c.name}». Si tiene preguntas o cuestionarios, no se borra: desactívala."
    return render(request, "catalog/category_admin.html", {"page_title": "Categorías", "categories": categories})


@login_required
@requires("catalog.categories.manage")
@require_POST
def category_delete(request, pk):
    from apps.questionnaires.models import Category

    category = get_object_or_404(Category, pk=pk)
    try:
        catalogs.delete_category(category)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, f"Borré la categoría «{category.name}».")
    return redirect("catalog:category_admin")


def _unique_code(base):
    from apps.questionnaires.models import Category

    code, n = base[:40], 2
    while Category.objects.filter(code=code).exists():
        suffix = f"-{n}"
        code, n = base[:40 - len(suffix)] + suffix, n + 1
    return code
