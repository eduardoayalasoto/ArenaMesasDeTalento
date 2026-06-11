"""Pruebas del versionado de cuestionarios (publicar archiva el anterior; duplicar crea borrador)."""

import pytest

from apps.core.services import questionnaire_editor as editor
from apps.questionnaires.models import Question, QuestionnaireTemplate, Section


@pytest.fixture
def published(db, area, level_jr):
    tpl = QuestionnaireTemplate.objects.create(
        kind=QuestionnaireTemplate.Kind.OWNERSHIP, area=area, level=level_jr,
        version=1, status=QuestionnaireTemplate.Status.PUBLICADO, scale_note="Escala",
    )
    s = Section.objects.create(template=tpl, title="Checklist", order=1)
    Question.objects.create(section=s, order=1, title="P1", text="desc")
    Question.objects.create(section=s, order=2, title="P2")
    return tpl


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
