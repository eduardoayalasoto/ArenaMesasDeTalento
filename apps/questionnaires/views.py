"""Editor administrable de cuestionarios para Talento (CRUD + versionado)."""

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.services import ownership_weights
from apps.core.services import questionnaire_editor as editor

from .forms import QuestionForm, WeightsForm
from .models import Category, Question, QuestionnaireTemplate, Section, TemplateCategory
from apps.access import services as access
from apps.access.decorators import requires


@login_required
@requires("questionnaires.manage")
def admin_list(request):
    """Lista de cuestionarios agrupados, con estado, versión y conteo de preguntas."""
    if not access.has(request.user, "questionnaires.manage"):
        return render(request, "errors/403.html", {
            "titulo": "Administración reservada a Talento",
            "mensaje": "Solo Talento y Cultura administra los cuestionarios.",
        }, status=403)

    templates = (
        QuestionnaireTemplate.objects.select_related("area", "level")
        .order_by("kind", "area__code", "level__order", "-version")
    )
    return render(request, "questionnaires/admin_list.html", {
        "page_title": "Cuestionarios",
        "templates": templates,
    })


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
    editable = template.status == QuestionnaireTemplate.Status.BORRADOR

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "duplicate":
            copy = editor.duplicate_as_new_version(template)
            messages.success(request, f"Creé la versión {copy.version} en borrador para editar.")
            return redirect("questionnaires:template_edit", pk=copy.pk)

        if action == "publish" and editable:
            try:
                editor.publish_template(template)
            except ValidationError as exc:
                messages.error(request, "No se puede publicar: " + " ".join(exc.messages))
            else:
                messages.success(request, f"Publicaste la versión {template.version}.")
            return redirect("questionnaires:template_edit", pk=template.pk)

        if not editable:
            messages.error(request, "Este cuestionario está publicado: crea una nueva versión para editarlo.")
            return redirect("questionnaires:template_edit", pk=template.pk)

        # Acciones de edición (solo BORRADOR)
        if action == "save_meta":
            template.scale_note = request.POST.get("scale_note", "").strip()
            template.save(update_fields=["scale_note"])
            messages.success(request, "Guardé la nota de escala.")

        elif action == "save_question":
            q = get_object_or_404(Question, pk=request.POST.get("question"), section__template=template)
            form = QuestionForm(request.POST, instance=q, template=template)
            if form.is_valid():
                form.save()
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
                # Si la categoría ya tiene pesos propios, la pregunta nueva entra con 0 para no romper la suma.
                if q.category_id and Question.objects.filter(
                    section__template=template, category_id=q.category_id, weight_pct__isnull=False
                ).exists():
                    q.weight_pct = Decimal("0.0")
                q.save()
                messages.success(request, "Agregué la pregunta.")
            else:
                messages.error(request, _form_errors(form))

        elif action in _WEIGHT_ACTIONS:
            _WEIGHT_ACTIONS[action](request, template)

        elif action == "delete_question":
            q = get_object_or_404(Question, pk=request.POST.get("question"), section__template=template)
            q.delete()
            messages.info(request, "Eliminé la pregunta.")

        elif action == "move_question":
            _move_question(template, request.POST.get("question"), request.POST.get("dir"))

        return redirect("questionnaires:template_edit", pk=template.pk)

    sections = template.sections.prefetch_related(
        Prefetch("questions", queryset=Question.objects.select_related("category").order_by("order"))
    ).order_by("order")
    scale = template.scale_options.filter(question__isnull=True).order_by("order")

    is_ownership = template.kind == QuestionnaireTemplate.Kind.OWNERSHIP
    weight_groups = ownership_weights.editor_groups(template) if is_ownership else []
    linked_ids = [g["link"].category_id for g in weight_groups]
    return render(request, "questionnaires/template_edit.html", {
        "page_title": "Editar cuestionario",
        "template": template,
        "sections": sections,
        "scale": scale,
        "editable": editable,
        "is_ownership": is_ownership,
        "weight_groups": weight_groups,
        "category_choices": [g["link"].category for g in weight_groups],
        "available_categories": Category.objects.filter(is_active=True).exclude(pk__in=linked_ids),
        "weights_errors": ownership_weights.validate_template_weights(template) if is_ownership else [],
    })


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


# --- Pesos de categorías y preguntas (spec 008) ------------------------------

def _add_template_category(request, template):
    category = Category.objects.filter(pk=request.POST.get("category"), is_active=True).first()
    if category is None:
        messages.error(request, "Elige una categoría válida.")
    elif TemplateCategory.objects.filter(template=template, category=category).exists():
        messages.info(request, f"«{category.name}» ya está en este cuestionario.")
    else:
        TemplateCategory.objects.create(template=template, category=category, weight_pct=Decimal("0.0"))
        messages.success(request, f"Agregué «{category.name}» con peso 0%. Ajusta los pesos para llegar a 100%.")


def _remove_template_category(request, template):
    link = get_object_or_404(TemplateCategory, pk=request.POST.get("link"), template=template)
    if Question.objects.filter(section__template=template, category_id=link.category_id).exists():
        messages.error(request, "La categoría tiene preguntas; cámbialas de categoría antes de quitarla.")
        return
    link.delete()
    messages.warning(request, "Quité la categoría. Revisa que los pesos sigan sumando 100%.")


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
    messages.success(request, "Guardé los pesos de las categorías.")


def _category_questions(request, template):
    link = get_object_or_404(TemplateCategory, pk=request.POST.get("link"), template=template)
    questions = list(Question.objects.filter(
        section__template=template, category_id=link.category_id, qtype=Question.Type.SCALE,
    ))
    return link, questions


def _save_question_weights(request, template):
    link, questions = _category_questions(request, template)
    form = WeightsForm(
        request.POST, ids=[q.pk for q in questions], field_prefix="q_",
        label=f"Preguntas de {link.category.name}",
    )
    if not questions or not form.is_valid():
        messages.error(request, _form_errors(form) if questions else "La categoría no tiene preguntas.")
        return
    with transaction.atomic():
        for q in questions:
            q.weight_pct = form.weights[q.pk]
            q.save(update_fields=["weight_pct"])
    messages.success(request, f"Guardé los pesos de las preguntas de «{link.category.name}».")


def _clear_question_weights(request, template):
    link, questions = _category_questions(request, template)
    Question.objects.filter(pk__in=[q.pk for q in questions]).update(weight_pct=None)
    messages.success(request, f"Las preguntas de «{link.category.name}» vuelven a pesar lo mismo (partes iguales).")


_WEIGHT_ACTIONS = {
    "add_template_category": _add_template_category,
    "remove_template_category": _remove_template_category,
    "save_category_weights": _save_category_weights,
    "save_question_weights": _save_question_weights,
    "clear_question_weights": _clear_question_weights,
}
