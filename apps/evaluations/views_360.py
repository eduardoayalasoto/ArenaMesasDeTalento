"""Evaluación 360 al owner del proyecto (spec 010): pendientes, responder y resultados. Informativa."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from apps.access.decorators import requires
from apps.catalog.models import EvaluationPeriod, Project
from apps.core.services import three_sixty


def _period(request):
    """Periodo a mostrar: `?periodo=<id>` (histórico) o el Abierto; si no hay, el más reciente."""
    pk = request.GET.get("periodo")
    if pk and pk.isdigit():
        found = EvaluationPeriod.objects.filter(pk=pk).first()
        if found:
            return found
    return three_sixty.open_period() or EvaluationPeriod.objects.order_by("-end_date").first()


@login_required
@requires("three_sixty.respond")
def three_sixty_list(request):
    """Arriba lo que me toca responder; debajo lo que mi equipo dijo de mí; y, para Talento/Dirección, el seguimiento."""
    period = _period(request)
    user = request.user
    to_answer = three_sixty.to_answer(user, period) if period and period.is_open else []
    mine = [{"project": p, "summary": three_sixty.owner_summary(p, period)}
            for p in three_sixty.owned_projects(user)] if period else []
    followup = []
    if period and three_sixty.sees_followup(user):
        for p in three_sixty.all_projects_for(user):
            r = three_sixty.result(p, period)
            followup.append({"project": p, "result": r})
    return render(request, "evaluations/three_sixty_list.html", {
        "page_title": "Evaluaciones 360", "period": period, "periods": EvaluationPeriod.objects.all(),
        "to_answer": to_answer, "mine": mine, "followup": followup,
        "has_template": three_sixty.active_template() is not None,
    })


def _values_from_post(post):
    return {int(k[2:]): v for k, v in post.items() if k.startswith("q_") and k[2:].isdigit()}


@login_required
@requires("three_sixty.respond")
def three_sixty_respond(request, project_id):
    """Responder la 360 del owner de un proyecto: autoguardado como borrador y envío con confirmación."""
    project = get_object_or_404(Project.objects.select_related("owner"), pk=project_id)
    period = three_sixty.open_period()
    try:
        response = three_sixty.get_or_start(project, period, request.user)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("evaluations:three_sixty_list")
    if response.is_submitted:
        messages.info(request, "Ya enviaste esta evaluación. Gracias.")
        return redirect("evaluations:three_sixty_list")

    errors = []
    if request.method == "POST":
        action = request.POST.get("action", "save")
        try:
            three_sixty.save_answers(response, _values_from_post(request.POST), request.POST.get("comment", ""))
        except ValidationError as exc:
            errors = exc.messages
            action = "error"
        if action == "autosave":
            return HttpResponse(status=204)
        if action == "submit" and not errors:
            errors = three_sixty.submit(response)
            if not errors:
                messages.success(request, f"Enviaste tu evaluación de {project.owner.full_name} en «{project.name}». Gracias.")
                return redirect("evaluations:three_sixty_list")
        elif action == "save" and not errors:
            messages.success(request, "Guardé tu borrador. Puedes continuar cuando quieras.")
            return redirect("evaluations:three_sixty_list")

    answers = {a.question_id: a.value for a in response.answers.all()}
    template = response.template
    sections = []
    for section in template.sections.order_by("order"):
        qs = [{"q": q, "value": answers.get(q.pk)} for q in section.questions.order_by("order")]
        if qs:
            sections.append({"section": section, "questions": qs})
    total = sum(len(s["questions"]) for s in sections)
    return render(request, "evaluations/three_sixty_respond.html", {
        "page_title": f"360 · {project.name}", "project": project, "response": response, "sections": sections,
        "scale": list(template.scale_options.filter(question__isnull=True, value__isnull=False).order_by("-value")),
        "answered": len(answers), "total": total, "errors": errors, "template": template,
    })


@login_required
@requires("three_sixty.results.own")
def three_sixty_result(request, project_id):
    """Resultado de un proyecto: el owner ve su score; Talento/Dirección además avance y quién falta."""
    project = get_object_or_404(Project.objects.select_related("owner"), pk=project_id)
    if not three_sixty.can_view_results(request.user, project):
        return render(request, "errors/403.html", {
            "titulo": "No puedes ver este resultado",
            "mensaje": "La 360 solo la ve su owner, Dirección y Talento.",
        }, status=403)
    period = _period(request)
    data = three_sixty.result(project, period) if period else None
    followup = three_sixty.sees_followup(request.user)
    return render(request, "evaluations/three_sixty_result.html", {
        "page_title": f"360 · {project.name}", "project": project, "period": period, "r": data,
        "followup": followup, "is_owner": project.owner_id == request.user.pk,
        "periods": EvaluationPeriod.objects.all() if followup else None,
    })
