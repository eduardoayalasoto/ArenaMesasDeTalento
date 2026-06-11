"""Editor administrable de cuestionarios para Talento (CRUD + versionado)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render

from apps.core.services import questionnaire_editor as editor

from .models import Question, QuestionnaireTemplate, Section


def _require_admin(request):
    return request.user.is_admin


@login_required
def admin_list(request):
    """Lista de cuestionarios agrupados, con estado, versión y conteo de preguntas."""
    if not _require_admin(request):
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
def template_edit(request, pk):
    """Ve un cuestionario; si es BORRADOR permite editarlo; permite versionar y publicar."""
    if not _require_admin(request):
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
            editor.publish_template(template)
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
            q.title = request.POST.get("title", "").strip()
            q.text = request.POST.get("text", "").strip()
            q.save(update_fields=["title", "text"])
            messages.success(request, "Guardé la pregunta.")

        elif action == "add_question":
            section = get_object_or_404(Section, pk=request.POST.get("section"), template=template)
            order = (section.questions.count() or 0) + 1
            Question.objects.create(
                section=section, order=order,
                title=request.POST.get("title", "Nueva pregunta").strip() or "Nueva pregunta",
                text=request.POST.get("text", "").strip(),
            )
            messages.success(request, "Agregué la pregunta.")

        elif action == "delete_question":
            q = get_object_or_404(Question, pk=request.POST.get("question"), section__template=template)
            q.delete()
            messages.info(request, "Eliminé la pregunta.")

        elif action == "move_question":
            _move_question(template, request.POST.get("question"), request.POST.get("dir"))

        return redirect("questionnaires:template_edit", pk=template.pk)

    sections = template.sections.prefetch_related(
        Prefetch("questions", queryset=Question.objects.order_by("order"))
    ).order_by("order")
    scale = template.scale_options.filter(question__isnull=True).order_by("order")

    return render(request, "questionnaires/template_edit.html", {
        "page_title": "Editar cuestionario",
        "template": template,
        "sections": sections,
        "scale": scale,
        "editable": editable,
    })


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
