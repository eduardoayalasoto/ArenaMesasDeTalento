"""Alta, edición completa y descarte de cuestionarios desde la interfaz (secciones, escala, borrado)."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.catalog.models import Area, Position, SeniorityLevel
from apps.core.services import questionnaire_editor as editor
from apps.core.tests.conftest import make_general
from apps.questionnaires.forms import ScaleOptionForm, TemplateCreateForm
from apps.questionnaires.models import (
    Category, Question, QuestionnaireTemplate as T, ScaleOption, Section,
)

User = get_user_model()


@pytest.fixture
def published(db, area, level_jr):
    """Un cuestionario publicado con escala (la fuente de la que nacen los nuevos)."""
    tpl = T.objects.create(kind=T.Kind.OWNERSHIP, area=area, level=level_jr, version=1,
                           status=T.Status.PUBLICADO, scale_note="Nota vigente")
    section = Section.objects.create(template=tpl, title="Checklist", order=1)
    Question.objects.create(section=section, order=1, title="P1")
    ScaleOption.objects.create(template=tpl, value=1, label="No cumple", order=1)
    ScaleOption.objects.create(template=tpl, value=None, label="N/A", order=2)
    return make_general(tpl)


@pytest.fixture
def new_position(db):
    area = Area.objects.create(code="CONS", name="Consultoría")
    level = SeniorityLevel.objects.create(code="ANA", name="Analista", order=5)
    return Position.objects.create(area=area, level=level, name="Analista")


@pytest.fixture
def talento(db):
    return User.objects.create_user(
        email="talento.crud@arena-analytics.com", password=None, full_name="Talento",
        role=User.Role.TALENTO, photo_data=b"x", photo_mime="image/jpeg",
    )


@pytest.fixture
def draft(published):
    return editor.duplicate_as_new_version(published)


# --- Alta ---------------------------------------------------------------------

@pytest.mark.django_db
def test_create_template_is_a_complete_draft(published, new_position):
    tpl = editor.create_template(T.Kind.OWNERSHIP, new_position.area, new_position.level)

    assert (tpl.status, tpl.version) == (T.Status.BORRADOR, 1)
    assert tpl.scale_note == "Nota vigente"
    assert list(tpl.scale_options.order_by("order").values_list("label", flat=True)) == ["No cumple", "N/A"]
    assert [(l.category.code, l.weight_pct) for l in tpl.template_categories.all()] == [("general", 100)]
    assert tpl.sections.count() == 1


@pytest.mark.django_db
def test_create_template_rejects_a_puesto_that_already_has_one(published, area, level_jr):
    with pytest.raises(ValidationError, match="nueva versión"):
        editor.create_template(T.Kind.OWNERSHIP, area, level_jr)
    assert T.objects.filter(area=area, level=level_jr).count() == 1


@pytest.mark.django_db
def test_create_ownership_requires_area_and_level(published):
    with pytest.raises(ValidationError, match="área y el nivel"):
        editor.create_template(T.Kind.OWNERSHIP)


@pytest.mark.django_db
def test_create_value_delivery_only_once():
    tpl = editor.create_template(T.Kind.VALUE_DELIVERY)
    assert (tpl.area, tpl.level, tpl.status) == (None, None, T.Status.BORRADOR)
    with pytest.raises(ValidationError):
        editor.create_template(T.Kind.VALUE_DELIVERY)


@pytest.mark.django_db
def test_create_form_lists_all_positions_and_rejects_taken(published, new_position, area, level_jr):
    taken, _ = Position.objects.get_or_create(area=area, level=level_jr, defaults={"name": "Junior"})
    form = TemplateCreateForm()
    assert {new_position, taken} <= set(form.fields["position"].queryset)
    assert "ya tiene cuestionario" in form.fields["position"].label_from_instance(taken)
    assert not TemplateCreateForm({"kind": "OWNERSHIP", "position": taken.pk}).is_valid()

    assert not TemplateCreateForm({"kind": "OWNERSHIP"}).is_valid()
    assert TemplateCreateForm({"kind": "OWNERSHIP", "position": new_position.pk}).is_valid()
    assert TemplateCreateForm({"kind": "VALUE_DELIVERY"}).is_valid()


# --- Secciones ----------------------------------------------------------------

@pytest.mark.django_db
def test_sections_add_rename_move_delete(draft):
    first = draft.sections.get()
    second = editor.add_section(draft, "Segunda")
    assert (first.order, second.order) == (1, 2)

    editor.rename_section(second, "Renombrada")
    second.refresh_from_db()
    assert second.title == "Renombrada"

    editor.move_section(draft, second.pk, "up")
    assert list(draft.sections.order_by("order").values_list("title", flat=True)) == ["Renombrada", "Checklist"]

    with pytest.raises(ValidationError, match="tiene preguntas"):
        editor.delete_section(first)
    editor.delete_section(second)
    assert draft.sections.count() == 1


# --- Escala -------------------------------------------------------------------

@pytest.mark.django_db
def test_scale_option_form_rejects_duplicates_and_bad_values(draft):
    taken = draft.scale_options.get(value=1)
    na = draft.scale_options.get(value=None)

    def form(**data):
        return ScaleOptionForm({"label": "X", **data}, template=draft)

    assert not form(value="1").is_valid()                       # valor repetido
    assert not form(value="").is_valid()                        # segundo N/A
    assert not form(value="5").is_valid()                       # fuera de 1–4
    assert not ScaleOptionForm({"value": "2", "label": " "}, template=draft).is_valid()
    assert ScaleOptionForm({"value": "2", "label": "Cumple parcial"}, template=draft).is_valid()
    # Editar la propia opción no cuenta como duplicado.
    assert ScaleOptionForm({"value": "1", "label": "Nuevo"}, template=draft, option=taken).is_valid()
    assert ScaleOptionForm({"value": "", "label": "No aplica"}, template=draft, option=na).is_valid()


@pytest.mark.django_db
def test_scale_option_save_move_delete(draft):
    option = editor.save_scale_option(draft, value=3, label="Cumple", description="Estándar")
    assert option.order == 3
    editor.save_scale_option(draft, option=option, value=3, label="Cumple bien", description="")
    option.refresh_from_db()
    assert option.label == "Cumple bien"

    editor.move_scale_option(draft, option.pk, "up")
    assert list(draft.scale_options.order_by("order").values_list("label", flat=True)) == [
        "No cumple", "Cumple bien", "N/A",
    ]
    editor.delete_scale_option(option)
    assert draft.scale_options.count() == 2


# --- Descarte -----------------------------------------------------------------

@pytest.mark.django_db
def test_delete_draft_never_touches_published(published, draft):
    editor.delete_draft(draft)
    assert not T.objects.filter(pk=draft.pk).exists()
    with pytest.raises(ValidationError, match="Solo se puede descartar un borrador"):
        editor.delete_draft(published)
    assert T.objects.filter(pk=published.pk).exists()


# --- Vistas -------------------------------------------------------------------

@pytest.mark.django_db
def test_view_create_redirects_to_the_new_draft(client, talento, published, new_position):
    client.force_login(talento)
    assert "Nuevo cuestionario" in client.get(reverse("questionnaires:admin_list")).content.decode()

    response = client.post(reverse("questionnaires:template_create"),
                           {"kind": "OWNERSHIP", "position": new_position.pk})
    tpl = T.objects.get(area=new_position.area, level=new_position.level)
    assert response.status_code == 302 and response.url == reverse("questionnaires:template_edit", args=[tpl.pk])


@pytest.mark.django_db
def test_view_create_shows_errors_without_creating(client, talento, published):
    client.force_login(talento)
    before = T.objects.count()
    response = client.post(reverse("questionnaires:template_create"), {"kind": "OWNERSHIP"})
    assert response.status_code == 400 and "Elige el Área" in response.content.decode()
    assert T.objects.count() == before


@pytest.mark.django_db
def test_view_create_is_forbidden_without_permission(client, collaborator, published, new_position):
    client.force_login(collaborator)
    before = T.objects.count()
    client.post(reverse("questionnaires:template_create"), {"kind": "OWNERSHIP", "position": new_position.pk})
    assert T.objects.count() == before


@pytest.mark.django_db
def test_view_edit_structure_actions_on_draft(client, talento, draft):
    client.force_login(talento)
    url = reverse("questionnaires:template_edit", args=[draft.pk])

    client.post(url, {"action": "add_section", "title": "Nueva sección"})
    new_section = draft.sections.get(title="Nueva sección")
    client.post(url, {"action": "rename_section", "section": new_section.pk, "title": "Otra"})
    client.post(url, {"action": "save_scale_option", "value": "4", "label": "Excede", "description": "Más"})
    assert draft.sections.filter(title="Otra").exists()
    assert draft.scale_options.filter(value=4, label="Excede").exists()

    # Una pregunta cambia de sección y entra al final de la nueva.
    question = Question.objects.get(section__template=draft, title="P1")
    category = Category.objects.get(code="general")
    client.post(url, {"action": "save_question", "question": question.pk, "title": "P1",
                      "category": category.pk, "section": new_section.pk})
    question.refresh_from_db()
    assert (question.section_id, question.order) == (new_section.pk, 1)

    client.post(reverse("questionnaires:section_delete", args=[new_section.pk]))
    assert draft.sections.filter(pk=new_section.pk).exists()     # tiene preguntas: se conserva

    client.post(reverse("questionnaires:question_delete", args=[question.pk]))
    client.post(reverse("questionnaires:section_delete", args=[new_section.pk]))
    assert not draft.sections.filter(pk=new_section.pk).exists()


@pytest.mark.django_db
def test_view_deletes_are_refused_on_archived(client, talento, published):
    published.status = T.Status.ARCHIVADO   # publicado sin respuestas sí se edita (spec 009); archivado no
    published.save()
    client.force_login(talento)
    question = Question.objects.get(section__template=published)
    option = published.scale_options.first()
    section = published.sections.get()

    client.post(reverse("questionnaires:question_delete", args=[question.pk]))
    client.post(reverse("questionnaires:scale_option_delete", args=[option.pk]))
    client.post(reverse("questionnaires:section_delete", args=[section.pk]))
    client.post(reverse("questionnaires:template_delete", args=[published.pk]))

    assert Question.objects.filter(pk=question.pk).exists()
    assert ScaleOption.objects.filter(pk=option.pk).exists()
    assert Section.objects.filter(pk=section.pk).exists()
    assert T.objects.filter(pk=published.pk).exists()


@pytest.mark.django_db
def test_view_discards_a_draft(client, talento, draft):
    client.force_login(talento)
    response = client.post(reverse("questionnaires:template_delete", args=[draft.pk]))
    assert response.url == reverse("questionnaires:admin_list")
    assert not T.objects.filter(pk=draft.pk).exists()


@pytest.mark.django_db
def test_view_rejects_a_question_weighing_zero(client, talento, draft):
    """Una pregunta en 0% no participa en el score: no se guarda y el error nombra la pregunta."""
    client.force_login(talento)
    url = reverse("questionnaires:template_edit", args=[draft.pk])
    section = draft.sections.get()
    q1 = Question.objects.get(section=section, title="P1")
    q2 = Question.objects.create(section=section, order=2, title="P2", category=q1.category)
    link = draft.template_categories.get()

    def save(first, second):
        response = client.post(url, {"action": "save_question_weights", "link": link.pk,
                                     f"q_{q1.pk}": first, f"q_{q2.pk}": second})
        return " ".join(str(m) for m in get_messages(response.wsgi_request))

    message = save("100.0", "0.0")
    assert "«P2»" in message and "peso 0%" in message
    q2.refresh_from_db()
    assert q2.weight_pct is None

    assert "Guardé los pesos" in save("60.0", "40.0")
    q2.refresh_from_db()
    assert q2.weight_pct == Decimal("40.0")


@pytest.mark.django_db
def test_adding_a_question_to_a_weighted_category_warns_about_zero(client, talento, draft):
    client.force_login(talento)
    url = reverse("questionnaires:template_edit", args=[draft.pk])
    section = draft.sections.get()
    q1 = Question.objects.get(section=section, title="P1")
    q1.weight_pct = Decimal("100.0")
    q1.save()

    response = client.post(url, {"action": "add_question", "section": section.pk, "title": "P2",
                                 "category": q1.category_id})
    message = " ".join(str(m) for m in get_messages(response.wsgi_request))
    assert "peso 0%" in message and "no se puede publicar" in message
    assert any("peso 0%" in e for e in editor.validate_for_publish(draft))


@pytest.mark.django_db
def test_delete_routes_require_post(client, talento, draft):
    client.force_login(talento)
    assert client.get(reverse("questionnaires:template_delete", args=[draft.pk])).status_code == 405
    assert T.objects.filter(pk=draft.pk).exists()


# --- Editar es editar: en sitio, también con respuestas ------------------------------------------

@pytest.mark.django_db
def test_edit_in_place_even_with_responses(client, talento, published, monkeypatch):
    monkeypatch.setattr(editor, "has_responses", lambda template: True)   # ya contestado
    client.force_login(talento)
    html = client.get(reverse("questionnaires:admin_list")).content.decode()
    assert reverse("questionnaires:template_edit", args=[published.pk]) in html
    assert 'name="action" value="duplicate"' not in html                  # «Editar» ya no pide versión nueva
    # Cambiar un texto/peso se guarda directamente sobre la publicada.
    q = Question.objects.get(section__template=published)
    resp = client.post(reverse("questionnaires:template_edit", args=[published.pk]), {
        "action": "save_question", "question": q.pk, "title": "P1 ajustada", "text": "", "category": q.category_id or "",
    })
    assert resp.status_code == 302
    q.refresh_from_db()
    assert q.title == "P1 ajustada"
    page = client.get(reverse("questionnaires:template_edit", args=[published.pk])).content.decode()
    assert "Esta versión ya tiene respuestas" in page


@pytest.mark.django_db
def test_answered_questions_and_scale_values_are_protected(client, talento, published, monkeypatch):
    from apps.evaluations.models import OwnershipAnswer, OwnershipEvaluation

    monkeypatch.setattr(editor, "has_responses", lambda template: True)
    client.force_login(talento)
    q = Question.objects.get(section__template=published)
    ev = OwnershipEvaluation.objects.create(user=talento, period=_open_period(), template=published)
    OwnershipAnswer.objects.create(evaluation=ev, question=q, value=3)
    client.post(reverse("questionnaires:question_delete", args=[q.pk]))
    assert Question.objects.filter(pk=q.pk).exists()                       # contestada: no se borra
    option = ScaleOption.objects.get(template=published, value=1)
    client.post(reverse("questionnaires:scale_option_delete", args=[option.pk]))
    assert ScaleOption.objects.filter(pk=option.pk).exists()               # con respuestas: no se quita
    client.post(reverse("questionnaires:template_edit", args=[published.pk]), {
        "action": "save_scale_option", "option": option.pk, "value": "2", "label": "Nuevo", "description": "",
    })
    option.refresh_from_db()
    assert option.value == 1                                               # el valor numérico no cambia


@pytest.mark.django_db
def test_archived_version_is_read_only_and_screen_is_a_guided_sequence(client, talento, draft, published):
    client.force_login(talento)
    html = client.get(reverse("questionnaires:template_edit", args=[draft.pk])).content.decode()
    for marker in ("Paso 1 · Escala de respuestas", "Paso 2 · Categorías y pesos",
                   "Paso 3 · Secciones y preguntas", "Paso 4 · Publicar", "Estás editando un borrador"):
        assert marker in html
    published.status = T.Status.ARCHIVADO
    published.save(update_fields=["status"])
    page = client.get(reverse("questionnaires:template_edit", args=[published.pk])).content.decode()
    assert "Versión anterior (solo lectura)" in page
    client.post(reverse("questionnaires:template_edit", args=[published.pk]), {"action": "save_meta", "scale_note": "x"})
    published.refresh_from_db()
    assert published.scale_note != "x"


def _open_period():
    from datetime import date

    from apps.catalog.models import EvaluationPeriod

    return EvaluationPeriod.objects.get_or_create(
        name="2026-S2", defaults=dict(start_date=date(2026, 7, 1), end_date=date(2026, 12, 31),
                                      status=EvaluationPeriod.Status.ABIERTO))[0]


@pytest.mark.django_db
def test_list_summary_cards_and_missing_positions(client, talento, published, new_position):
    client.force_login(talento)
    resp = client.get(reverse("questionnaires:admin_list"))
    html = resp.content.decode()
    assert resp.status_code == 200
    assert [p.pk for p in resp.context["missing_positions"]] == [new_position.pk]   # Consultoría aún sin cuestionario
    assert "Posiciones sin cuestionario" in html and "Consultoría · Analista" in html
    assert "Vigente · sin respuestas aún" in html and "1 pregunta" in html
