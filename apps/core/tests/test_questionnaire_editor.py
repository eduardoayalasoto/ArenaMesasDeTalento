"""Pruebas del versionado de cuestionarios (publicar archiva el anterior; duplicar crea borrador)."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.urls import reverse

from apps.core.services import questionnaire_editor as editor
from apps.core.tests.conftest import make_general
from apps.questionnaires.models import (
    Category, Question, QuestionnaireTemplate, ScaleOption, Section, TemplateCategory,
)


@pytest.fixture
def published(db, area, level_jr):
    tpl = QuestionnaireTemplate.objects.create(
        kind=QuestionnaireTemplate.Kind.OWNERSHIP, area=area, level=level_jr,
        version=1, status=QuestionnaireTemplate.Status.PUBLICADO, scale_note="Escala",
    )
    s = Section.objects.create(template=tpl, title="Checklist", order=1)
    Question.objects.create(section=s, order=1, title="P1", text="desc")
    Question.objects.create(section=s, order=2, title="P2")
    ScaleOption.objects.create(template=tpl, value=3, label="Cumple", order=1)
    return make_general(tpl)


@pytest.mark.django_db
def test_duplicate_creates_draft_next_version_with_content(published):
    copy = editor.duplicate_as_new_version(published)
    assert copy.pk != published.pk
    assert copy.version == 2
    assert copy.status == QuestionnaireTemplate.Status.BORRADOR
    assert copy.question_count == published.question_count == 2
    # No comparte secciones con el original.
    assert not copy.sections.filter(pk__in=published.sections.values("pk")).exists()


@pytest.mark.django_db
def test_publish_archives_previous(published):
    draft = editor.duplicate_as_new_version(published)
    editor.publish_template(draft)

    published.refresh_from_db()
    draft.refresh_from_db()
    assert draft.status == QuestionnaireTemplate.Status.PUBLICADO
    assert published.status == QuestionnaireTemplate.Status.ARCHIVADO
    # Solo una publicada por (kind, area, level).
    assert QuestionnaireTemplate.objects.filter(
        kind=draft.kind, area=draft.area, level=draft.level,
        status=QuestionnaireTemplate.Status.PUBLICADO,
    ).count() == 1


@pytest.mark.django_db
def test_editor_weights_must_sum_100_before_saving_or_publishing(client, published):
    """Spec 008 (US2): categorías y pesos con validación en servidor; nada inválido se guarda ni publica."""
    User = get_user_model()
    talento = User.objects.create_user(
        email="talento.pesos@arena-analytics.com", password=None, full_name="Talento",
        role=User.Role.TALENTO, photo_data=b"x", photo_mime="image/jpeg",
    )
    client.force_login(talento)
    draft = editor.duplicate_as_new_version(published)
    url = reverse("questionnaires:template_edit", args=[draft.pk])
    uno = Category.objects.create(code="uno", name="Uno", order=1)
    dos = Category.objects.create(code="dos", name="Dos", order=2)

    page = client.get(url).content.decode()
    assert "Categorías y pesos" in page and "Repartir en partes iguales" in page

    for category in (uno, dos):
        client.post(url, {"action": "add_template_category", "category": category.pk})
    links = {l.category.code: l for l in draft.template_categories.select_related("category")}
    assert {k: l.weight_pct for k, l in links.items()} == {"general": 100, "uno": 0, "dos": 0}

    def say(data):
        """Mensajes que dejó la petición (los toasts viajan escapados en el HTML)."""
        response = client.post(url, data)
        return " ".join(str(m) for m in get_messages(response.wsgi_request))

    def post_weights(general, one, two):
        return say({
            "action": "save_category_weights", f"w_{links['general'].pk}": general,
            f"w_{links['uno'].pk}": one, f"w_{links['dos'].pk}": two,
        })

    def weights():
        return {l.category.code: l.weight_pct for l in draft.template_categories.select_related("category")}

    # 99.9%, dos decimales o texto: se rechaza y no se guarda nada.
    assert "suman 99.9%; deben sumar 100%" in post_weights("60.0", "30.0", "9.9")
    assert "un solo decimal" in post_weights("60.0", "30.0", "10.05")
    assert "no son válidos" in post_weights("60.0", "abc", "10.0")
    assert weights() == {"general": 100, "uno": 0, "dos": 0}

    # 100.0%: se guarda.
    assert "Guardé los pesos de las categorías" in post_weights("60.0", "30.0", "10.0")
    assert weights() == {"general": Decimal("60.0"), "uno": Decimal("30.0"), "dos": Decimal("10.0")}

    # No se publica: «Dos» pesa 10% y no tiene preguntas; «Uno» pesa 30% y tampoco.
    client.post(url, {"action": "publish"})
    draft.refresh_from_db()
    assert draft.status == QuestionnaireTemplate.Status.BORRADOR
    q1, q2 = Question.objects.filter(section__template=draft).order_by("order")
    client.post(url, {"action": "save_question", "question": q2.pk, "title": q2.title, "category": uno.pk})
    q2.refresh_from_db()
    assert q2.category == uno
    client.post(url, {"action": "remove_template_category", "link": links["dos"].pk})
    assert "dos" not in weights()
    assert "Guardé los pesos" in say({
        "action": "save_category_weights", f"w_{links['general'].pk}": "60.0", f"w_{links['uno'].pk}": "40.0",
    })

    # Pesos de preguntas dentro de la categoría: 99.9 no se guarda; 100.0 sí; volver a partes iguales.
    assert "suman 99.9%" in say({
        "action": "save_question_weights", "link": links["general"].pk, f"q_{q1.pk}": "99.9",
    })
    q1.refresh_from_db()
    assert q1.weight_pct is None
    client.post(url, {"action": "save_question_weights", "link": links["general"].pk, f"q_{q1.pk}": "100.0"})
    q1.refresh_from_db()
    assert q1.weight_pct == Decimal("100.0")
    client.post(url, {"action": "clear_question_weights", "link": links["general"].pk})
    q1.refresh_from_db()
    assert q1.weight_pct is None

    # Todo cuadra: se publica y el publicado queda inmutable.
    client.post(url, {"action": "publish"})
    draft.refresh_from_db()
    assert draft.status == QuestionnaireTemplate.Status.PUBLICADO
    client.post(url, {"action": "save_category_weights", f"w_{links['general'].pk}": "50.0", f"w_{links['uno'].pk}": "50.0"})
    assert weights()["general"] == Decimal("60.0")


@pytest.mark.django_db
def test_publish_requires_position_and_categories(published):
    from apps.catalog.models import Position

    draft = editor.duplicate_as_new_version(published)
    Position.objects.filter(area=draft.area, level=draft.level).delete()
    from apps.core.services import positions
    positions.invalidate()
    assert any("puesto activo" in e for e in editor.validate_for_publish(draft))

    draft.template_categories.all().delete()
    assert any("no tiene categorías con peso" in e for e in editor.validate_for_publish(draft))
