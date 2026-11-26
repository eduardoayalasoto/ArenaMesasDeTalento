"""Spec 010, fase 1: cuestionario tipo 360 en el editor (dimensiones con ponderación, publicar, versionar)."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.core.services import questionnaire_editor as editor
from apps.core.tests.conftest import make_learn_user
from apps.questionnaires.models import Question, QuestionnaireTemplate as T, Section

K = T.Kind


@pytest.fixture
def talento(db):
    return make_learn_user("t.360@arena-analytics.com", role="TALENTO")


@pytest.mark.django_db
def test_create_360_needs_no_position_and_starts_with_scale_and_one_dimension(client, talento):
    client.force_login(talento)
    r = client.post(reverse("questionnaires:template_create"), {"kind": "THREE_SIXTY"})
    assert r.status_code == 302
    t = T.objects.get(kind=K.THREE_SIXTY)
    assert t.area is None and t.level is None and t.status == T.Status.BORRADOR
    assert [o.value for o in t.scale_options.order_by("order")] == [4, 3, 2, 1]
    s = t.sections.get()
    assert s.weight_pct == 100
    with pytest.raises(ValidationError, match="Ya existe"):
        editor.create_template(K.THREE_SIXTY)


@pytest.mark.django_db
def test_dimension_weights_must_sum_100_and_publish_archives_previous(client, talento):
    t = editor.create_template(K.THREE_SIXTY)
    s1 = t.sections.get()
    s2 = editor.add_section(t, "Liderazgo")
    assert s2.weight_pct == 0
    for s in (s1, s2):
        Question.objects.create(section=s, order=1, title=f"P {s.title}", qtype="SCALE")
    errors = editor.validate_for_publish(t)
    assert any("suman 100.0" in e or "suman" in e for e in errors) is False  # 100 + 0 sí suma 100
    with pytest.raises(ValidationError):
        editor.save_dimension_weights(t, {s1.pk: "60", s2.pk: "30"})
    editor.save_dimension_weights(t, {s1.pk: "87.5", s2.pk: "12.5"})
    editor.equalize_dimension_weights(t)
    s1.refresh_from_db(); s2.refresh_from_db()
    assert (s1.weight_pct, s2.weight_pct) == (50, 50)
    editor.publish_template(t)
    t.refresh_from_db()
    assert t.status == T.Status.PUBLICADO

    new = editor.duplicate_as_new_version(t)
    assert [float(s.weight_pct) for s in new.sections.order_by("order")] == [50.0, 50.0]
    editor.publish_template(new)
    t.refresh_from_db()
    assert t.status == T.Status.ARCHIVADO


@pytest.mark.django_db
def test_360_editor_screen_shows_dimension_weights_and_saves_them(client, talento):
    client.force_login(talento)
    t = editor.create_template(K.THREE_SIXTY)
    s2 = editor.add_section(t, "Liderazgo")
    s1 = t.sections.order_by("order").first()
    url = reverse("questionnaires:template_edit", args=[t.pk])
    html = client.get(url).content.decode()
    assert "Ponderación de las dimensiones" in html and "informativa" in html
    client.post(url, {"action": "save_dimension_weights", f"w_{s1.pk}": "40", f"w_{s2.pk}": "60"})
    s1.refresh_from_db(); s2.refresh_from_db()
    assert (float(s1.weight_pct), float(s2.weight_pct)) == (40.0, 60.0)
    client.post(url, {"action": "equalize_dimensions"})
    s1.refresh_from_db()
    assert float(s1.weight_pct) == 50.0
