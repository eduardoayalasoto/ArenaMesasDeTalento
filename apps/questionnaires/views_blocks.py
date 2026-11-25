"""Catálogo de bloques de competencias (y sus skills): CRUD con drawer. Los bloques solo describen qué skills
componen una competencia; no entran al cálculo de la calificación."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.access.decorators import requires
from apps.core.services import catalogs

from .forms import BlockForm
from .models import CompetencyBlock


@login_required
@requires("questionnaires.manage")
def block_admin(request):
    if request.method == "POST":
        form = BlockForm(request.POST)
        if not form.is_valid():
            messages.error(request, " ".join(e for errs in form.errors.values() for e in errs))
        else:
            d = form.cleaned_data
            try:
                block = catalogs.save_block(pk=d.get("block"), name=d["name"], order=d["order"],
                                            is_active=d["is_active"], skills_text=d["skills"])
            except ValidationError as exc:
                messages.error(request, " ".join(exc.messages))
            else:
                messages.success(request, f"Guardé el bloque «{block.name}» con {block.skills.count()} skill(s).")
        return redirect("questionnaires:block_admin")

    blocks = list(CompetencyBlock.objects.prefetch_related("skills", "questions").order_by("order", "name"))
    for b in blocks:
        b.skills_text = "\n".join(s.name for s in b.skills.all())
        b.n_questions = len(b.questions.all())
        b.delete_url = reverse("questionnaires:block_delete", args=[b.pk])
        b.delete_confirm_id = f"delete-block-{b.pk}"
        b.delete_message = f"Se borra el bloque «{b.name}» y sus skills. Si alguna pregunta lo usa, no se borra: desactívalo."
    return render(request, "questionnaires/block_admin.html", {"page_title": "Bloques de competencia", "blocks": blocks})


@login_required
@requires("questionnaires.manage")
@require_POST
def block_delete(request, pk):
    block = get_object_or_404(CompetencyBlock, pk=pk)
    try:
        catalogs.delete_block(block)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
    else:
        messages.success(request, f"Borré el bloque «{block.name}».")
    return redirect("questionnaires:block_admin")
