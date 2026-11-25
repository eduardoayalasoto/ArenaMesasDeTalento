"""Áreas, Posiciones y Niveles: índice con búsqueda en vivo, «Ver y editar» en drawer y bitácora.

Vocabulario de la interfaz: Área (Analítica, Consultoría) → Posición (Ingeniero de Datos, Analista…)
→ Nivel opcional (Jr, Mid, Snr, Lead…). En el código el «Área» es `Department` y la «Posición» es `Area`.
"""

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.access import services as access
from apps.access.decorators import requires
from apps.core.http import back_to_list, hx_done
from apps.core.services import audit, catalogs

from .forms import AreaDirectorForm, AreaPositionForm, DepartmentForm, LevelForm
from .models import Area, Department, PillarWeight, Position, SeniorityLevel

User = get_user_model()

STATE_OPTIONS = (("", "Todas"), ("activas", "Solo activas"), ("inactivas", "Solo inactivas"))
PEOPLE = {"is_superuser": False, "deleted_at__isnull": True}

DEPARTMENT_LABELS = {"name": "Nombre", "code": "Clave", "order": "Orden", "director": "Director", "is_active": "Activa"}
AREA_LABELS = {"name": "Nombre", "code": "Clave", "department": "Área", "director": "Director", "is_active": "Activa"}
LEVEL_LABELS = {"name": "Nombre", "code": "Clave", "order": "Orden"}


# --- Utilidades --------------------------------------------------------------------------------------

def _params(request, *names):
    return {name: request.GET.get(name, "").strip() for name in ("q", "state", *names)}


def _state(qs, state):
    if state == "activas":
        return qs.filter(is_active=True)
    if state == "inactivas":
        return qs.filter(is_active=False)
    return qs


def _tokens(qs, q, *fields):
    """Filtra por CUALQUIER palabra: cada palabra debe aparecer en algún campo (AND entre palabras)."""
    for token in (q or "").split():
        cond = Q()
        for field in fields:
            cond |= Q(**{f"{field}__icontains": token})
        qs = qs.filter(cond)
    return qs


def _render_list(request, context):
    template = "catalog/_org_results.html" if request.headers.get("HX-Request") else "catalog/org_list.html"
    return render(request, template, context)


def _confirm(row, noun, name):
    row.delete_confirm_id = f"delete-{noun}-{row.pk}"
    row.delete_message = f"¿Eliminar «{name}»? Si algo la usa, no se borra: desactívala."
    return row


def _drawer(request, *, form, obj, entity, title, post_url, aside_title="", aside_items=(), aside_link=None):
    return render(request, "catalog/_org_drawer_form.html", {
        "form": form, "obj": obj, "title": title, "post_url": post_url,
        "aside_title": aside_title, "aside_items": aside_items, "aside_link": aside_link,
        "history": audit.history(entity, obj.pk) if obj is not None else (),
    })


def _done(message, variant="success"):
    return hx_done(message, variant, refresh="org-changed", close="close-org-drawer")


def _base_context(request, params, rows, **extra):
    return {
        "rows": rows, "total": len(rows), "q": params["q"], "state": params["state"],
        "filtered": any(v for k, v in params.items()), "states": STATE_OPTIONS, **extra,
    }


# --- Áreas (Analítica, Consultoría) -----------------------------------------------------------------

@login_required
@requires("departments.manage")
def department_admin(request):
    params = _params(request)
    qs = Department.objects.select_related("director").prefetch_related("areas")
    qs = _tokens(_state(qs, params["state"]), params["q"], "name", "code", "director__full_name", "areas__name").distinct()
    rows = list(qs.order_by("order", "name"))
    for d in rows:
        d.people = User.objects.filter(area__department=d, **PEOPLE).count()
        d.positions_text = ", ".join(a.name for a in d.areas.all()) or "Sin posiciones"
        _confirm(d, "department", d.name)
    return _render_list(request, _base_context(
        request, params, rows, page_title="Áreas", kind="department", results_template="catalog/_org_department_rows.html",
        intro="Las Áreas agrupan posiciones y personas (Analítica, Consultoría). El Director del Área aprueba el nivel Dirección de Arena Learn.",
        new_label="Nueva área", create_url=reverse("catalog:department_edit"), list_url=reverse("catalog:department_admin"),
        placeholder="Buscar por área, clave, Director o posición…", selects=[]))


@login_required
@requires("departments.manage")
def department_edit(request, pk=None):
    if not request.headers.get("HX-Request"):
        return redirect("catalog:department_admin")
    obj = get_object_or_404(Department, pk=pk) if pk else None
    form = DepartmentForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        saved, created, changed = audit.save_form(form, request.user, "Área", DEPARTMENT_LABELS)
        return _done(f"Creaste el área «{saved.name}»." if created else
                     (f"Actualizaste el área «{saved.name}»." if changed else "No hubo cambios que guardar."),
                     "success" if changed else "info")
    items = [f"{a.name} · {a.members.filter(**PEOPLE).count()} persona(s)" for a in obj.areas.all()] if obj else []
    return _drawer(request, form=form, obj=obj, entity="Área", title="Editar área" if obj else "Nueva área",
                   post_url=reverse("catalog:department_edit", args=[obj.pk]) if obj else reverse("catalog:department_edit"),
                   aside_title="Posiciones del área", aside_items=items, aside_link=(reverse("catalog:area_admin"), "Administrar posiciones"))


@login_required
@requires("departments.manage")
@require_POST
def department_delete(request, pk):
    obj = get_object_or_404(Department, pk=pk)
    try:
        audit.delete_with_audit(obj, request.user, "Área", DEPARTMENT_LABELS, f"el área «{obj.name}»")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, f"Eliminaste el área «{obj.name}».")
    return back_to_list(request, "catalog:department_admin")


# --- Posiciones (Ingeniero de Datos, Analista, Gerente…) --------------------------------------------

@login_required
@requires("areas.manage")
def area_admin(request):
    if request.method == "POST":  # cambio rápido de Director (flujo de Arena Learn, spec 004)
        return _quick_director(request)
    params = _params(request, "department")
    qs = Area.objects.select_related("department", "director").prefetch_related("positions__level")
    qs = _tokens(_state(qs, params["state"]), params["q"], "name", "code", "department__name", "positions__level__name").distinct()
    if params["department"].isdigit():
        qs = qs.filter(department_id=int(params["department"]))
    rows = list(qs.order_by("department__order", "name"))
    for a in rows:
        a.people = a.members.filter(**PEOPLE).count()
        levels = [p.level.name if p.level_id else "Sin nivel" for p in a.positions.all()]
        a.levels_text = " · ".join(levels) if levels else "Sin niveles definidos"
        _confirm(a, "position", a.name)
    selects = [{"name": "department", "label": "Todas las áreas", "current": params["department"],
                "options": [(str(d.pk), d.name) for d in Department.objects.order_by("order")]}]
    return _render_list(request, _base_context(
        request, params, rows, page_title="Posiciones", kind="area", results_template="catalog/_org_area_rows.html",
        intro="Cada posición pertenece a un Área. Una posición puede usar niveles (Jr, Mid, Snr, Lead…) o ninguno; el cuestionario se asigna por Área, posición y nivel.",
        new_label="Nueva posición", create_url=reverse("catalog:area_edit"), list_url=reverse("catalog:area_admin"),
        placeholder="Buscar por posición, clave, área o nivel…", selects=selects))


def _quick_director(request):
    form = AreaDirectorForm(request.POST)
    directors = access.assignable_users("assign.area_director")
    if form.is_valid():
        area = get_object_or_404(Area, pk=form.cleaned_data["area"])
        director_id = form.cleaned_data.get("director")
        if director_id and not directors.filter(pk=director_id).exists():
            messages.error(request, "Esa persona no puede ser Director según su perfil.")
        else:
            before = audit.describe(area, AREA_LABELS)
            area.director_id = director_id or None
            area.save(update_fields=["director"])
            changes = audit.diff(before, audit.describe(area, AREA_LABELS))
            if changes:
                audit.log(request.user, "Posición", area, "UPDATED", changes)
            messages.success(request, f"Actualicé el Director de {area.name}.")
    return redirect("catalog:area_admin")


@login_required
@requires("areas.manage")
def area_edit(request, pk=None):
    if not request.headers.get("HX-Request"):
        return redirect("catalog:area_admin")
    obj = get_object_or_404(Area, pk=pk) if pk else None
    form = AreaPositionForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        saved, created, changed = audit.save_form(form, request.user, "Posición", AREA_LABELS)
        return _done(f"Creaste la posición «{saved.name}»." if created else
                     (f"Actualizaste la posición «{saved.name}»." if changed else "No hubo cambios que guardar."),
                     "success" if changed else "info")
    items = []
    if obj:
        for p in obj.positions.all():
            people = obj.members.filter(level_id=p.level_id, **PEOPLE).count()
            items.append(f"{p.level.name if p.level_id else 'Sin nivel'} → «{p.name}» · {people} persona(s)")
    return _drawer(request, form=form, obj=obj, entity="Posición", title="Editar posición" if obj else "Nueva posición",
                   post_url=reverse("catalog:area_edit", args=[obj.pk]) if obj else reverse("catalog:area_edit"),
                   aside_title="Niveles de esta posición", aside_items=items,
                   aside_link=(reverse("catalog:position_admin"), "Editar nombres y ponderaciones por nivel"))


@login_required
@requires("areas.manage")
@require_POST
def area_delete(request, pk):
    obj = get_object_or_404(Area, pk=pk)
    try:
        audit.delete_with_audit(obj, request.user, "Posición", AREA_LABELS, f"la posición «{obj.name}»")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, f"Eliminaste la posición «{obj.name}».")
    return back_to_list(request, "catalog:area_admin")


# --- Niveles (Jr, Mid, Snr, Lead…) ------------------------------------------------------------------

@login_required
@requires("levels.manage")
def level_admin(request):
    params = _params(request)
    qs = _tokens(SeniorityLevel.objects.all(), params["q"], "name", "code")
    rows = list(qs.annotate(
        n_people=Count("members", filter=Q(members__is_superuser=False, members__deleted_at__isnull=True), distinct=True),
        n_templates=Count("templates", distinct=True), n_positions=Count("positions", distinct=True),
    ).order_by("order"))
    for lv in rows:
        _confirm(lv, "level", lv.name)
    return _render_list(request, _base_context(
        request, params, rows, page_title="Niveles", kind="level", results_template="catalog/_org_level_rows.html",
        intro="Los niveles son un catálogo abierto y opcional por persona: hay posiciones que los usan (Analítica) y otras que no (Analista, Gerente).",
        new_label="Nuevo nivel", create_url=reverse("catalog:level_edit"), list_url=reverse("catalog:level_admin"),
        placeholder="Buscar por nivel o clave…", selects=[], states=()))


@login_required
@requires("levels.manage")
def level_edit(request, pk=None):
    if not request.headers.get("HX-Request"):
        return redirect("catalog:level_admin")
    obj = get_object_or_404(SeniorityLevel, pk=pk) if pk else None
    form = LevelForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            saved, created, changed = audit.save_form(form, request.user, "Nivel", LEVEL_LABELS)
            if created:
                catalogs.ensure_level_pillar_weights(saved)
        return _done(f"Creaste el nivel «{saved.name}». Revisa su ponderación de pilares." if created else
                     (f"Actualizaste el nivel «{saved.name}»." if changed else "No hubo cambios que guardar."),
                     "success" if changed else "info")
    items = []
    if obj:
        items = [f"{User.objects.filter(level=obj, **PEOPLE).count()} persona(s)",
                 f"{obj.templates.count()} cuestionario(s)", f"{obj.positions.count()} posición(es) por nivel"]
    return _drawer(request, form=form, obj=obj, entity="Nivel", title="Editar nivel" if obj else "Nuevo nivel",
                   post_url=reverse("catalog:level_edit", args=[obj.pk]) if obj else reverse("catalog:level_edit"),
                   aside_title="Dónde se usa", aside_items=items,
                   aside_link=(reverse("catalog:weight_admin"), "Ponderación de pilares por nivel"))


@login_required
@requires("levels.manage")
@require_POST
def level_delete(request, pk):
    obj = get_object_or_404(SeniorityLevel, pk=pk)
    try:
        with transaction.atomic():
            others = [u for u in catalogs.usage(obj) if "ponderaciones por nivel" not in u]
            if others:
                raise ValidationError(
                    f"No se puede borrar el nivel «{obj.name}»: lo usan {', '.join(others)}. Cámbialos antes.")
            PillarWeight.objects.filter(level=obj).delete()
            audit.delete_with_audit(obj, request.user, "Nivel", LEVEL_LABELS, f"el nivel «{obj.name}»")
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, f"Eliminaste el nivel «{obj.name}».")
    return back_to_list(request, "catalog:level_admin")
