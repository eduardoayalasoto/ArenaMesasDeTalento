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
