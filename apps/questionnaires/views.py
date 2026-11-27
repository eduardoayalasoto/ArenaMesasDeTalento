"""Editor administrable de cuestionarios para Talento (CRUD + versionado)."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.core.services import ownership_weights
from apps.core.services import questionnaire_editor as editor

from .forms import QuestionForm, ScaleOptionForm, SectionForm, TemplateCreateForm, WeightsForm
from .models import (
    Category, CompetencyBlock, Question, QuestionnaireTemplate, ScaleOption, Section, TemplateCategory,
)
from apps.access import services as access
from apps.access.decorators import requires


def _template_key(template):
    return (template.kind, template.area_id, template.level_id)


def _draft_index(templates):
    """Borrador vigente por cuestionario (mismo tipo, área y nivel), para continuarlo en vez de duplicar."""
    drafts = {}
    for t in templates:
        if t.status == QuestionnaireTemplate.Status.BORRADOR:
            drafts.setdefault(_template_key(t), t)
    return drafts


def _missing_positions(templates):
    """Posiciones activas que todavía no tienen ningún cuestionario de Ownership (ni borrador)."""
    from apps.catalog.models import Position

    taken = {(t.area_id, t.level_id) for t in templates if t.kind == QuestionnaireTemplate.Kind.OWNERSHIP}
    return [
        p for p in Position.objects.filter(is_active=True).select_related("area", "level")
        if (p.area_id, p.level_id) not in taken
    ]


def _list_context(request, create_form=None):
    templates = list(
        QuestionnaireTemplate.objects.select_related("area__department", "level")
        .annotate(n_questions=Count("sections__questions", distinct=True), n_sections=Count("sections", distinct=True))
        .order_by("kind", "area__code", "level__order", "-version")
    )
    Kind = QuestionnaireTemplate.Kind
    Status = QuestionnaireTemplate.Status
    drafts = _draft_index(templates)
    for t in templates:
        t.editable_now = editor.is_editable(t)
        t.has_answers = t.status == Status.PUBLICADO and editor.has_responses(t)
        draft = drafts.get(_template_key(t)) if t.status == Status.PUBLICADO else None
        t.draft_version = draft.version if draft else None
    missing = _missing_positions(templates)
    return {
        "page_title": "Cuestionarios",
        "templates": templates,
        "ownership_count": sum(1 for t in templates if t.kind == Kind.OWNERSHIP and t.is_published),
        "value_delivery_count": sum(1 for t in templates if t.kind == Kind.VALUE_DELIVERY and t.is_published),
        "three_sixty_count": sum(1 for t in templates if t.kind == Kind.THREE_SIXTY and t.is_published),
        "draft_count": sum(1 for t in templates if t.status == Status.BORRADOR),
        "archived_count": sum(1 for t in templates if t.status == Status.ARCHIVADO),
        "answered_count": sum(1 for t in templates if t.has_answers),
        "missing_positions": missing,
        "areas": sorted({t.area for t in templates if t.area_id}, key=lambda a: a.name),
        "departments": sorted({t.area.department for t in templates if t.area_id and t.area.department_id},
                              key=lambda d: d.order),
        "create_form": create_form or TemplateCreateForm(),
    }


@login_required
@requires("questionnaires.manage")
def admin_list(request):
    """Lista de cuestionarios agrupados, con estado, versión y conteo de preguntas."""
    if not access.has(request.user, "questionnaires.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento y Cultura administra los cuestionarios.",
        }, status=403)

    return render(request, "questionnaires/admin_list.html", _list_context(request))


@login_required
@requires("questionnaires.manage")
@require_POST
def template_create(request):
    """Crea un cuestionario nuevo en BORRADOR para un puesto que todavía no tiene ninguno."""
    form = TemplateCreateForm(request.POST)
    if form.is_valid():
        position = form.cleaned_data["position"]
        try:
            template = editor.create_template(
                form.cleaned_data["kind"],
                area=position.area if position else None,
                level=position.level if position else None,
            )
        except ValidationError as exc:
            form.add_error(None, " ".join(exc.messages))
        else:
            messages.success(request, "Creé el cuestionario en borrador. Agrega sus preguntas y publícalo cuando esté listo.")
            return redirect("questionnaires:template_edit", pk=template.pk)
    return render(request, "questionnaires/admin_list.html", _list_context(request, create_form=form), status=400)


@login_required
@requires("questionnaires.manage")
def template_edit(request, pk):
    """Ve un cuestionario; si es BORRADOR permite editarlo; permite versionar y publicar."""
    if not access.has(request.user, "questionnaires.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento administra los cuestionarios.",
        }, status=403)

    template = get_object_or_404(QuestionnaireTemplate, pk=pk)
    is_draft = template.status == QuestionnaireTemplate.Status.BORRADOR
    editable = editor.is_editable(template)

    if request.method == "POST":
        action = request.POST.get("action")
        # ¿El reparto sigue al nivel de dominio de las preguntas? (se mide ANTES de editar)
        was_auto = (editable and template.kind == QuestionnaireTemplate.Kind.OWNERSHIP
                    and action in ("save_question", "add_question") and ownership_weights.is_automatic(template))

        if action == "duplicate":
            copy = editor.duplicate_as_new_version(template)
            messages.success(request, f"Creé la versión {copy.version} en borrador para editar.")
            return redirect("questionnaires:template_edit", pk=copy.pk)

        if action == "publish" and is_draft:
            try:
                editor.publish_template(template)
            except ValidationError as exc:
                messages.error(request, "No se puede publicar: " + " ".join(exc.messages))
            else:
                messages.success(request, f"Publicaste la versión {template.version}.")
            return redirect("questionnaires:template_edit", pk=template.pk)

        if not editable:
            messages.error(request, "Esta es una versión anterior (archivada) y es de solo lectura: edita la versión vigente.")
            return redirect("questionnaires:template_edit", pk=template.pk)

        # Acciones de edición (borrador o publicado)
        if action == "save_meta":
            template.scale_note = request.POST.get("scale_note", "").strip()
            template.save(update_fields=["scale_note"])
            messages.success(request, "Guardé la nota de escala.")

        elif action == "save_question":
            q = get_object_or_404(Question, pk=request.POST.get("question"), section__template=template)
            previous_section = q.section_id
            form = QuestionForm(request.POST, instance=q, template=template)
            if form.is_valid():
                question = form.save(commit=False)
                if question.section_id != previous_section:
                    # Al cambiar de sección entra al final de la nueva.
                    question.order = question.section.questions.count() + 1
                question.save()
                messages.success(request, "Guardé la pregunta.")
            else:
                messages.error(request, _form_errors(form))

        elif action == "add_question":
            section = get_object_or_404(Section, pk=request.POST.get("section"), template=template)
            form = QuestionForm(request.POST, template=template)
            if form.is_valid():
                q = form.save(commit=False)
                q.section = section
                q.order = (section.questions.count() or 0) + 1
                # Si la categoría ya tiene ponderaciones propias, la pregunta nueva entra con 0 para no romper la suma.
                if q.category_id and Question.objects.filter(
                    section__template=template, category_id=q.category_id, weight_pct__isnull=False
                ).exists():
                    q.weight_pct = Decimal("0.0")
                q.save()
                if q.weight_pct == 0:
                    messages.warning(
                        request,
                        "Agregué la pregunta con ponderación 0%. Reparte las ponderaciones de su categoría: "
                        "no se puede publicar con preguntas en 0%.",
                    )
                else:
                    messages.success(request, "Agregué la pregunta.")
            else:
                messages.error(request, _form_errors(form))

        elif action in _WEIGHT_ACTIONS:
            _WEIGHT_ACTIONS[action](request, template)

        elif action in _STRUCTURE_ACTIONS:
            _STRUCTURE_ACTIONS[action](request, template)

        elif action == "move_question":
            _move_question(template, request.POST.get("question"), request.POST.get("dir"))

        if action in ("save_question", "add_question") and template.kind == QuestionnaireTemplate.Kind.OWNERSHIP:
            _sync_weights(request, template, was_auto)

        return redirect("questionnaires:template_edit", pk=template.pk)

    sections = template.sections.prefetch_related(
        Prefetch("questions", queryset=Question.objects.select_related("category", "block")
                 .prefetch_related("block__skills").order_by("order"))
    ).order_by("order")
    scale = template.scale_options.filter(question__isnull=True).order_by("order")

    is_ownership = template.kind == QuestionnaireTemplate.Kind.OWNERSHIP
    weight_groups = ownership_weights.editor_groups(template) if is_ownership else []
    linked_ids = [g["link"].category_id for g in weight_groups]
    current = None
    if not editable:
        current = QuestionnaireTemplate.objects.filter(
            kind=template.kind, area=template.area, level=template.level,
            status__in=(QuestionnaireTemplate.Status.PUBLICADO, QuestionnaireTemplate.Status.BORRADOR),
        ).order_by("-version").first()
    publish_errors = editor.validate_for_publish(template) if is_draft else []
    question_count = Question.objects.filter(section__template=template).count()
    return render(request, "questionnaires/template_edit.html", {
        "page_title": "Editar cuestionario",
        "current_version": current,
        "has_answers": template.status == QuestionnaireTemplate.Status.PUBLICADO and editor.has_responses(template),
        "block_choices": CompetencyBlock.objects.filter(is_active=True),
        "mastery_choices": Question.Mastery.choices,
        "step_questions": 3 if is_ownership else 2,
        "step_publish": 4 if is_ownership else 3,
        "not_draft_flag": not is_draft,
        "publish_errors": publish_errors,
        "question_count": question_count,
        "scale_done": scale.exists(),
        "weights_done": is_ownership and bool(weight_groups) and not ownership_weights.validate_template_weights(template),
        "template": template,
        "sections": sections,
        "section_choices": list(template.sections.order_by("order")),
        "scale": scale,
        "scale_form": ScaleOptionForm(template=template),
        "editable": editable,
        "is_draft": is_draft,
        "is_ownership": is_ownership,
        "is_360": template.kind == QuestionnaireTemplate.Kind.THREE_SIXTY,
        "dimension_errors": editor.three_sixty_dimension_errors(template) if template.kind == QuestionnaireTemplate.Kind.THREE_SIXTY else [],
        "weight_groups": weight_groups,
        "category_choices": [g["link"].category for g in weight_groups],
        "available_categories": Category.objects.filter(is_active=True).exclude(pk__in=linked_ids),
        "weights_errors": ownership_weights.validate_template_weights(template) if is_ownership else [],
        "weights_auto": is_ownership and ownership_weights.is_automatic(template),
        "unweighted_questions": [q for s in sections for q in s.questions.all() if is_ownership and not q.is_weighted],
    })


def _sync_weights(request, template, was_auto):
    """Mantiene coherente el reparto tras editar una pregunta (toast: recalculado o qué falta)."""
    outcome = ownership_weights.sync_after_edit(template, was_auto)
    if outcome:
        level, text = outcome
        getattr(messages, level)(request, text)


def _form_errors(form):
    return " ".join(e for errors in form.errors.values() for e in errors)


def _move_question(template, question_id, direction):
    """Intercambia el orden de una pregunta con su vecina (arriba/abajo)."""
    q = get_object_or_404(Question, pk=question_id, section__template=template)
    siblings = list(q.section.questions.order_by("order"))
    idx = siblings.index(q)
    swap = idx - 1 if direction == "up" else idx + 1
    if 0 <= swap < len(siblings):
        other = siblings[swap]
        q.order, other.order = other.order, q.order
        Question.objects.bulk_update([q, other], ["order"])


# --- Ponderaciones de categorías y preguntas (spec 008) ------------------------------

def _add_template_category(request, template):
    category = Category.objects.filter(pk=request.POST.get("category"), is_active=True).first()
    if category is None:
        messages.error(request, "Elige una categoría válida.")
    elif TemplateCategory.objects.filter(template=template, category=category).exists():
        messages.info(request, f"«{category.name}» ya está en este cuestionario.")
    else:
        TemplateCategory.objects.create(template=template, category=category, weight_pct=Decimal("0.0"))
        messages.success(request, f"Agregué «{category.name}» con ponderación 0%. Ajusta las ponderaciones para llegar a 100%.")


def _remove_template_category(request, template):
    link = get_object_or_404(TemplateCategory, pk=request.POST.get("link"), template=template)
    if Question.objects.filter(section__template=template, category_id=link.category_id).exists():
        messages.error(request, "La categoría tiene preguntas; cámbialas de categoría antes de quitarla.")
        return
    link.delete()
    messages.warning(request, "Quité la categoría. Revisa que las ponderaciones sigan sumando 100%.")


def _save_category_weights(request, template):
    links = list(template.template_categories.all())
    form = WeightsForm(
        request.POST, ids=[link.pk for link in links], field_prefix="w_", label="Categorías del cuestionario",
    )
    if not form.is_valid():
        messages.error(request, _form_errors(form))
        return
    with transaction.atomic():
        for link in links:
            link.weight_pct = form.weights[link.pk]
            link.save(update_fields=["weight_pct"])
    messages.success(request, "Guardé las ponderaciones de las categorías.")


def _category_questions(request, template):
    link = get_object_or_404(TemplateCategory, pk=request.POST.get("link"), template=template)
    questions = list(Question.objects.filter(
        section__template=template, category_id=link.category_id, qtype=Question.Type.SCALE, is_weighted=True,
    ))
    return link, questions


def _save_question_weights(request, template):
    link, questions = _category_questions(request, template)
    form = WeightsForm(
        request.POST, ids=[q.pk for q in questions], field_prefix="q_",
        label=f"Preguntas de {link.category.name}", positive_for=link.category.name,
        titles={q.pk: q.title for q in questions},
    )
    if not questions or not form.is_valid():
        messages.error(request, _form_errors(form) if questions else "La categoría no tiene preguntas.")
        return
    with transaction.atomic():
        for q in questions:
            q.weight_pct = form.weights[q.pk]
            q.save(update_fields=["weight_pct"])
    messages.success(request, f"Guardé las ponderaciones de las preguntas de «{link.category.name}».")


def _clear_question_weights(request, template):
    link, questions = _category_questions(request, template)
    Question.objects.filter(pk__in=[q.pk for q in questions]).update(weight_pct=None)
    messages.success(request, f"Las preguntas de «{link.category.name}» vuelven a ponderar lo mismo (partes iguales).")


def _auto_weights(request, template):
    try:
        result = ownership_weights.auto_distribute(template)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return
    parts = ", ".join(f"{name} {pct}%" for name, pct in result["categories"].items())
    messages.success(
        request,
        f"Calculé las ponderaciones de {result['questions']} pregunta(s) con su nivel de dominio objetivo "
        f"({parts}). Revisa y ajusta si hace falta.",
    )


_WEIGHT_ACTIONS = {
    "auto_weights": _auto_weights,
    "add_template_category": _add_template_category,
    "remove_template_category": _remove_template_category,
    "save_category_weights": _save_category_weights,
    "save_question_weights": _save_question_weights,
    "clear_question_weights": _clear_question_weights,
}


# --- Secciones y escala de respuestas ----------------------------------------

def _add_section(request, template):
    form = SectionForm(request.POST)
    if not form.is_valid():
        messages.error(request, _form_errors(form))
        return
    editor.add_section(template, form.cleaned_data["title"])
    messages.success(request, "Agregué la sección.")


def _rename_section(request, template):
    section = get_object_or_404(Section, pk=request.POST.get("section"), template=template)
    form = SectionForm(request.POST)
    if not form.is_valid():
        messages.error(request, _form_errors(form))
        return
    editor.rename_section(section, form.cleaned_data["title"])
    messages.success(request, "Guardé el título de la sección.")


def _move_section(request, template):
    try:
        editor.move_section(template, request.POST.get("section") or 0, request.POST.get("dir"))
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))


def _scale_option_from_post(request, template):
    pk = request.POST.get("option")
    if not pk:
        return None
    return get_object_or_404(ScaleOption, pk=pk, template=template, question__isnull=True)


def _save_scale_option(request, template):
    option = _scale_option_from_post(request, template)
    form = ScaleOptionForm(request.POST, template=template, option=option)
    if not form.is_valid():
        messages.error(request, _form_errors(form))
        return
    if option is not None and form.cleaned_data.get("value") != option.value and editor.has_responses(template):
        messages.error(request, "No se puede cambiar el valor de una opción: ya hay respuestas con esta escala. Puedes editar su etiqueta y descriptor.")
        return
    editor.save_scale_option(template, option=option, **form.cleaned_data)
    messages.success(request, "Guardé la opción de la escala." if option else "Agregué la opción a la escala.")


def _move_scale_option(request, template):
    try:
        editor.move_scale_option(template, request.POST.get("option") or 0, request.POST.get("dir"))
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))


def _save_dimension_weights(request, template):
    if template.kind != QuestionnaireTemplate.Kind.THREE_SIXTY:
        return
    weights = {int(k[2:]): v for k, v in request.POST.items() if k.startswith("w_") and k[2:].isdigit()}
    try:
        editor.save_dimension_weights(template, weights)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return
    messages.success(request, "Guardé las ponderaciones de las dimensiones.")


def _equalize_dimensions(request, template):
    if template.kind == QuestionnaireTemplate.Kind.THREE_SIXTY:
        editor.equalize_dimension_weights(template)
        messages.success(request, "Repartí la ponderación en partes iguales entre las dimensiones.")


_STRUCTURE_ACTIONS = {
    "save_dimension_weights": _save_dimension_weights,
    "equalize_dimensions": _equalize_dimensions,
    "add_section": _add_section,
    "rename_section": _rename_section,
    "move_section": _move_section,
    "save_scale_option": _save_scale_option,
    "move_scale_option": _move_scale_option,
}


# --- Borrados con confirmación en modal (POST simple, solo sobre BORRADOR) ----

def _is_draft(request, template):
    if not editor.is_editable(template):
        messages.error(request, "Esta es una versión anterior (archivada) y es de solo lectura: edita la versión vigente.")
        return False
    return True


@login_required
@requires("questionnaires.manage")
@require_POST
def question_delete(request, pk):
    question = get_object_or_404(Question.objects.select_related("section__template"), pk=pk)
    template = question.section.template
    if _is_draft(request, template):
        if question.ownership_answers.exists():
            messages.error(request, "No se puede eliminar: la pregunta ya tiene respuestas. Edita su texto o su ponderación en su lugar.")
        else:
            was_auto = template.kind == QuestionnaireTemplate.Kind.OWNERSHIP and ownership_weights.is_automatic(template)
            question.delete()
            messages.info(request, "Eliminé la pregunta.")
            if template.kind == QuestionnaireTemplate.Kind.OWNERSHIP:
                _sync_weights(request, template, was_auto)
    return redirect("questionnaires:template_edit", pk=template.pk)


@login_required
@requires("questionnaires.manage")
@require_POST
def section_delete(request, pk):
    section = get_object_or_404(Section.objects.select_related("template"), pk=pk)
    template = section.template
    if _is_draft(request, template):
        try:
            editor.delete_section(section)
        except ValidationError as exc:
            messages.error(request, " ".join(exc.messages))
        else:
            messages.info(request, "Eliminé la sección.")
    return redirect("questionnaires:template_edit", pk=template.pk)


@login_required
@requires("questionnaires.manage")
@require_POST
def scale_option_delete(request, pk):
    option = get_object_or_404(
        ScaleOption.objects.select_related("template"), pk=pk, template__isnull=False, question__isnull=True,
    )
    template = option.template
    if request.headers.get("HX-Request"):   # baja sin recargar: la fila se quita del DOM
        if not editor.is_editable(template):
            return _hx_toast("Esta versión es de solo lectura.", "error", HX_Reswap="none")
        if editor.has_responses(template):
            return _hx_toast("No se puede quitar una opción de la escala: ya hay respuestas con esta escala.", "error", HX_Reswap="none")
        editor.delete_scale_option(option)
        return _hx_toast("Eliminé la opción de la escala.", "info")
    if _is_draft(request, template):
        if editor.has_responses(template):
            messages.error(request, "No se puede quitar una opción de la escala: ya hay respuestas con esta escala. Puedes editar su etiqueta y descriptor.")
        else:
            editor.delete_scale_option(option)
            messages.info(request, "Eliminé la opción de la escala.")
    return redirect("questionnaires:template_edit", pk=template.pk)


@login_required
@requires("questionnaires.manage")
@require_POST
def template_delete(request, pk):
    template = get_object_or_404(QuestionnaireTemplate, pk=pk)
    try:
        editor.delete_draft(template)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("questionnaires:template_edit", pk=template.pk)
    messages.info(request, "Descarté el borrador.")
    return redirect("questionnaires:admin_list")


@login_required
@requires("questionnaires.manage")
@require_POST
def template_reorder(request, pk):
    """Reordena por arrastre (htmx): secciones, o preguntas (también entre secciones). Responde 204 o 400 con el motivo."""
    import json

    from django.http import HttpResponse

    template = get_object_or_404(QuestionnaireTemplate, pk=pk)
    if not editor.is_editable(template):
        return HttpResponse("Esta versión es de solo lectura.", status=400)
    try:
        if request.POST.get("kind") == "sections":
            editor.reorder_sections(template, json.loads(request.POST.get("order", "[]")))
        elif request.POST.get("kind") == "scale":
            editor.reorder_scale(template, json.loads(request.POST.get("order", "[]")))
        else:
            editor.reorder_questions(template, json.loads(request.POST.get("layout", "{}")))
    except (ValidationError, ValueError, TypeError) as exc:
        return HttpResponse(" ".join(getattr(exc, "messages", [str(exc)])), status=400)
    return HttpResponse(status=204)


# --- Escala de respuestas por htmx: autoguardado, alta y baja sin recargar la página -------------------

def _hx_toast(message, variant="success", **headers):
    import json

    from django.http import HttpResponse

    response = HttpResponse("")
    response["HX-Trigger"] = json.dumps({"toast": {"message": message, "variant": variant}})
    for k, v in headers.items():
        response[k.replace("_", "-")] = v
    return response


def _scale_row_response(request, option, message=None, variant="error"):
    """Devuelve la fila con lo que SÍ está guardado (revierte lo que el servidor rechazó) y avisa por toast."""
    import json

    option.refresh_from_db()
    response = render(request, "questionnaires/_scale_row.html", {"opt": option, "editable": True})
    response["HX-Retarget"] = f"#scale-row-{option.pk}"
    response["HX-Reswap"] = "outerHTML"
    if message:
        response["HX-Trigger"] = json.dumps({"toast": {"message": message, "variant": variant}})
    return response


@login_required
@requires("questionnaires.manage")
@require_POST
def scale_option_save(request, pk):
    """Autoguardado de una opción de la escala (valor, etiqueta, descriptor)."""
    from django.http import HttpResponse

    option = get_object_or_404(ScaleOption.objects.select_related("template"), pk=pk, template__isnull=False, question__isnull=True)
    template = option.template
    if not editor.is_editable(template):
        return _hx_toast("Esta versión es de solo lectura.", "error", HX_Reswap="none")
    form = ScaleOptionForm(request.POST, template=template, option=option)
    if not form.is_valid():
        return _scale_row_response(request, option, _form_errors(form))
    if form.cleaned_data.get("value") != option.value and editor.has_responses(template):
        return _scale_row_response(request, option, "No se puede cambiar el valor de una opción: ya hay respuestas con esta escala. Puedes editar su etiqueta y descriptor.")
    editor.save_scale_option(template, option=option, **form.cleaned_data)
    return HttpResponse(status=204)


@login_required
@requires("questionnaires.manage")
@require_POST
def scale_option_add(request, pk):
    """Agrega una opción a la escala y devuelve su fila para anexarla a la lista."""
    template = get_object_or_404(QuestionnaireTemplate, pk=pk)
    if not editor.is_editable(template):
        return _hx_toast("Esta versión es de solo lectura.", "error", HX_Reswap="none")
    form = ScaleOptionForm(request.POST, template=template)
    if not form.is_valid():
        return _hx_toast(_form_errors(form), "error", HX_Reswap="none")
    option = editor.save_scale_option(template, **form.cleaned_data)
    response = render(request, "questionnaires/_scale_row.html", {"opt": option, "editable": True})
    import json

    response["HX-Trigger"] = json.dumps({"toast": {"message": "Agregué la opción a la escala.", "variant": "success"}})
    return response


@login_required
@requires("questionnaires.manage")
@require_POST
def scale_note_save(request, pk):
    """Autoguardado de la nota de escala."""
    from django.http import HttpResponse

    template = get_object_or_404(QuestionnaireTemplate, pk=pk)
    if not editor.is_editable(template):
        return _hx_toast("Esta versión es de solo lectura.", "error", HX_Reswap="none")
    template.scale_note = request.POST.get("scale_note", "").strip()
    template.save(update_fields=["scale_note"])
    return HttpResponse(status=204)
