"""Bloques de competencia (CRUD con skills) y reordenar secciones/preguntas por arrastre."""

import json

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.core.services import catalogs, questionnaire_editor as editor
from apps.core.tests.conftest import make_learn_user
from apps.questionnaires.models import BlockSkill, CompetencyBlock, Question, Section


@pytest.fixture
def talento(db):
    return make_learn_user("t.bloques@arena-analytics.com", role="TALENTO")


@pytest.mark.django_db
def test_block_crud_syncs_skills_exactly_and_guards_delete(client, talento, ownership_template):
    client.force_login(talento)
    assert "Nuevo bloque" in client.get(reverse("questionnaires:block_admin")).content.decode()
    client.post(reverse("questionnaires:block_admin"), {
        "name": "Disciplina de WoW", "order": 3, "is_active": "on", "skills": "Daily\nPlaneación\nDaily\n"})
    block = CompetencyBlock.objects.get(name="Disciplina de WoW")
    assert [s.name for s in block.skills.order_by("order")] == ["Daily", "Planeación"]

    # Editar: quita un skill, agrega otro, cambia el orden de las líneas
    client.post(reverse("questionnaires:block_admin"), {
        "block": block.pk, "name": "Disciplina de WoW y gestión", "order": 1, "skills": "Retro\nDaily"})
    block.refresh_from_db()
    assert block.name.endswith("gestión") and not block.is_active
    assert [(s.name, s.order) for s in block.skills.order_by("order")] == [("Retro", 1), ("Daily", 2)]
    assert not BlockSkill.objects.filter(block=block, name="Planeación").exists()

    with pytest.raises(ValidationError, match="Ya existe"):
        catalogs.save_block(pk=None, name="disciplina de wow y gestión", order=1, is_active=True, skills_text="")

    q = Question.objects.filter(section__template=ownership_template).first()
    q.block = block
    q.save()
    with pytest.raises(ValidationError, match="lo usan 1 pregunta"):
        catalogs.delete_block(block)
    q.block = None
    q.save()
    client.post(reverse("questionnaires:block_delete", args=[block.pk]))
    assert not CompetencyBlock.objects.filter(pk=block.pk).exists()


@pytest.mark.django_db
def test_reorder_sections_and_questions_across_sections(client, talento, ownership_template):
    client.force_login(talento)
    url = reverse("questionnaires:template_reorder", args=[ownership_template.pk])
    s1 = ownership_template.sections.get()
    s2 = Section.objects.create(template=ownership_template, title="Otra", order=2)
    ids = list(s1.questions.order_by("order").values_list("pk", flat=True))

    r = client.post(url, {"kind": "sections", "order": json.dumps([s2.pk, s1.pk])})
    assert r.status_code == 204
    s1.refresh_from_db(); s2.refresh_from_db()
    assert (s2.order, s1.order) == (1, 2)

    layout = {str(s1.pk): ids[:-2][::-1], str(s2.pk): ids[-2:]}   # invierte las primeras y pasa 2 a la otra sección
    assert client.post(url, {"kind": "questions", "layout": json.dumps(layout)}).status_code == 204
    assert list(s1.questions.order_by("order").values_list("pk", flat=True)) == ids[:-2][::-1]
    assert list(s2.questions.order_by("order").values_list("pk", flat=True)) == ids[-2:]

    # Un orden incompleto se rechaza y no cambia nada
    bad = client.post(url, {"kind": "questions", "layout": json.dumps({str(s1.pk): ids[:3]})})
    assert bad.status_code == 400
    assert s1.questions.count() == len(ids) - 2


@pytest.mark.django_db
def test_reorder_rejects_archived_and_foreign_ids(client, talento, ownership_template):
    client.force_login(talento)
    with pytest.raises(ValidationError):
        editor.reorder_sections(ownership_template, [999])
    ownership_template.status = ownership_template.Status.ARCHIVADO
    ownership_template.save()
    r = client.post(reverse("questionnaires:template_reorder", args=[ownership_template.pk]),
                    {"kind": "sections", "order": "[]"})
    assert r.status_code == 400


@pytest.mark.django_db
def test_editor_renders_grips_and_dnd_script(client, talento, ownership_template):
    client.force_login(talento)
    html = client.get(reverse("questionnaires:template_edit", args=[ownership_template.pk])).content.decode()
    assert 'data-grip="question"' in html and 'data-grip="section"' in html and "questionnaire_dnd.js" in html
    assert "data-reorder-url" in html


@pytest.mark.django_db
def test_editing_questions_keeps_weights_in_sync(client, talento, ownership_template):
    """En modo automático, quitar «pondera» o agregar una pregunta recalcula todo; en manual avisa qué falta."""
    from apps.core.services import ownership_weights
    from apps.questionnaires.models import Category, TemplateCategory

    general = Category.objects.get(code="general")
    TemplateCategory.objects.get_or_create(template=ownership_template, category=general)
    qs = list(Question.objects.filter(section__template=ownership_template).order_by("order"))
    for q in qs:
        q.category, q.target_level, q.is_weighted = general, 2, True
        q.save()
    ownership_weights.auto_distribute(ownership_template)
    assert ownership_weights.is_automatic(ownership_template)
    client.force_login(talento)
    url = reverse("questionnaires:template_edit", args=[ownership_template.pk])

    # Quitar «pondera» de una pregunta: el resto se reparte solo y la suma sigue en 100
    client.post(url, {"action": "save_question", "question": qs[0].pk, "title": qs[0].title, "weighting_fields": "1",
                      "category": general.pk, "target_level": 2})  # sin is_weighted = desmarcada
    qs[0].refresh_from_db()
    assert not qs[0].is_weighted
    assert not ownership_weights.validate_template_weights(ownership_template)
    assert ownership_weights.is_automatic(ownership_template)

    # Agregar una pregunta con nivel: entra al reparto automáticamente
    section = ownership_template.sections.get()
    client.post(url, {"action": "add_question", "section": section.pk, "title": "Nueva", "weighting_fields": "1",
                      "category": general.pk, "target_level": 3, "is_weighted": "on"})
    new = Question.objects.get(title="Nueva")
    assert new.weight_pct and new.weight_pct > 0
    assert not ownership_weights.validate_template_weights(ownership_template)

    # Modo manual: se ajusta a mano y el panel lo dice
    link = ownership_template.template_categories.get()
    link.weight_pct = 90
    link.save()
    assert not ownership_weights.is_automatic(ownership_template)
    html = client.get(url).content.decode()
    assert "Ponderación manual" in html and "Falta para que las ponderaciones sean válidas" in html


@pytest.mark.django_db
def test_scale_is_dragged_and_autosaved_by_htmx_without_redirects(client, talento, ownership_template):
    """Paso 1: reordenar, editar, agregar y quitar opciones por htmx (sin POST + redirect a la página)."""
    from apps.questionnaires.models import ScaleOption

    client.force_login(talento)
    hx = {"HTTP_HX_REQUEST": "true"}
    t = ownership_template
    for i, (v, label) in enumerate(((1, "No cumple"), (2, "Parcial"), (3, "Cumple"), (4, "Excede")), 1):
        ScaleOption.objects.create(template=t, value=v, label=label, order=i)
    ids = list(t.scale_options.order_by("order").values_list("pk", flat=True))
    html = client.get(reverse("questionnaires:template_edit", args=[t.pk])).content.decode()
    assert 'id="scale-list"' in html and 'data-grip="scale"' in html and 'hx-post' in html
    assert 'value="move_scale_option"' not in html and 'value="move_section"' not in html and 'value="move_question"' not in html

    reorder = reverse("questionnaires:template_reorder", args=[t.pk])
    r = client.post(reorder, {"kind": "scale", "order": json.dumps(ids[::-1])}, **hx)
    assert r.status_code == 204
    assert list(t.scale_options.order_by("order").values_list("pk", flat=True)) == ids[::-1]
    assert client.post(reorder, {"kind": "scale", "order": json.dumps(ids[:2])}, **hx).status_code == 400

    # Autoguardado: sin redirección, 204 (valor, etiqueta y descriptor)
    opt = t.scale_options.get(value=3)
    r = client.post(reverse("questionnaires:scale_option_save", args=[opt.pk]), {"value": "3", "label": "Cumple bien", "description": "Estándar"}, **hx)
    assert r.status_code == 204
    opt.refresh_from_db()
    assert opt.label == "Cumple bien" and opt.description == "Estándar"
    # Valor repetido: no se guarda y la fila vuelve con lo guardado + toast de error
    r = client.post(reverse("questionnaires:scale_option_save", args=[opt.pk]), {"value": "4", "label": "X"}, **hx)
    assert r.status_code == 200 and r["HX-Retarget"] == f"#scale-row-{opt.pk}"
    assert "Ya hay una opción con valor 4" in json.loads(r["HX-Trigger"])["toast"]["message"]
    opt.refresh_from_db()
    assert opt.value == 3

    # Alta: devuelve la fila; baja: 200 vacío con toast; ninguna redirige
    n = t.scale_options.count()
    r = client.post(reverse("questionnaires:scale_option_add", args=[t.pk]), {"value": "", "label": "N/A", "description": ""}, **hx)
    assert r.status_code == 200 and b"scale-row-" in r.content and t.scale_options.count() == n + 1
    new = t.scale_options.get(label="N/A")
    r = client.post(reverse("questionnaires:scale_option_delete", args=[new.pk]), **hx)
    assert r.status_code == 200 and not t.scale_options.filter(pk=new.pk).exists()
    # Nota de escala
    assert client.post(reverse("questionnaires:scale_note_save", args=[t.pk]), {"scale_note": "Nota nueva"}, **hx).status_code == 204
    t.refresh_from_db()
    assert t.scale_note == "Nota nueva"
