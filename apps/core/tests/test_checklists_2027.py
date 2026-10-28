"""Checklists de Ownership 2027 (spec 007): sync seguro, importación de la v2, "Ver criterio" y editor."""

import pytest
import yaml
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse

from apps.catalog.models import EvaluationPeriod
from apps.core.services import ownership_flow, questionnaire_editor, questionnaire_import
from apps.evaluations.models import OwnershipAnswer, OwnershipEvaluation
from apps.questionnaires.models import Question, QuestionnaireTemplate as T, ScaleOption

User = get_user_model()

V2_QUESTIONS = [
    {"title": "Backlog de tareas", "text": "Mantener el backlog.",
     "acceptance_criteria": "El backlog está al día\ncada sprint.", "deliverable": "Backlog actualizado"},
    {"title": "Rutinas de gestión — Daily", "text": "Asistir al daily preparado."},
]


@pytest.fixture
def v1(ownership_template):
    ScaleOption.objects.create(template=ownership_template, value=3, label="Cumple", order=1)
    ScaleOption.objects.create(template=ownership_template, value=None, label="N/A", order=2)
    ownership_template.scale_note = "Nota v1"
    ownership_template.save()
    return ownership_template


@pytest.fixture
def talento(db):
    return User.objects.create_user(
        email="talento@arena-analytics.com", password=None, full_name="Talento",
        role=User.Role.TALENTO, photo_data=b"x", photo_mime="image/jpeg",
    )


def _import(publish=True):
    return questionnaire_import.import_version("ID", "JR", V2_QUESTIONS, 2, publish=publish)


def _answered_eval(collaborator, period, project, template):
    ev = OwnershipEvaluation.objects.create(user=collaborator, project=project, period=period, template=template)
    q = Question.objects.filter(section__template=template).first()
    OwnershipAnswer.objects.create(evaluation=ev, question=q, value=3)
    return ev


@pytest.mark.django_db
def test_import_publishes_v2_and_sync_never_moves_by_version(
    v1, collaborator, period, project_finite, project_indefinite, level_lead, ownership_template_lead,
):
    ev = _answered_eval(collaborator, period, project_finite, v1)
    stale = questionnaire_editor.duplicate_as_new_version(v1)   # v2 borrador sin respuestas
    extra = questionnaire_editor.duplicate_as_new_version(v1)   # v3 borrador sobrante

    result = _import()
    v1.refresh_from_db(); stale.refresh_from_db(); extra.refresh_from_db()
    assert result.questions == 2 and result.archived == ["v3"]
    assert stale.status == T.Status.PUBLICADO and v1.status == T.Status.ARCHIVADO
    assert extra.status == T.Status.ARCHIVADO
    assert list(stale.scale_options.values_list("label", flat=True)) == ["Cumple", "N/A"]
    assert stale.scale_note == "Nota v1"
    q = Question.objects.get(section__template=stale, order=1)
    assert q.acceptance_criteria.startswith("El backlog") and q.has_checklist_details
    assert v1.history.filter(status=T.Status.ARCHIVADO).exists()

    # Versión nueva del mismo puesto: la evaluación conserva v1 y sus respuestas.
    assert ownership_flow.sync_evaluation_template(ev) is False
    assert ev.answers.count() == 1

    # Cambio de nivel con periodo cerrado: no cambia. Con periodo abierto: sí.
    collaborator.level = level_lead
    collaborator.save()
    EvaluationPeriod.objects.filter(pk=period.pk).update(status=EvaluationPeriod.Status.CERRADO)
    ev = OwnershipEvaluation.objects.get(pk=ev.pk)
    assert ownership_flow.sync_evaluation_template(ev) is False
    EvaluationPeriod.objects.filter(pk=period.pk).update(status=EvaluationPeriod.Status.ABIERTO)
    ev = OwnershipEvaluation.objects.get(pk=ev.pk)
    assert ownership_flow.sync_evaluation_template(ev) is True
    assert ev.template_id == ownership_template_lead.pk and ev.answers.count() == 0

    # Evaluación reabierta (alguna vez enviada): conserva su cuestionario.
    reopened = _answered_eval(collaborator, period, project_indefinite, v1)
    reopened.status = OwnershipEvaluation.Status.ENVIADA
    reopened.save()
    reopened.status = OwnershipEvaluation.Status.BORRADOR
    reopened.save()
    assert ownership_flow.sync_evaluation_template(reopened) is False
    assert reopened.answers.count() == 1


@pytest.mark.django_db
def test_import_is_idempotent_and_rejects_when_answered(v1, collaborator, period, project_finite, tmp_path):
    (tmp_path / "ID.yaml").write_text(
        yaml.safe_dump({"templates": [{"area": "ID", "level": "JR", "questions": V2_QUESTIONS}]}, allow_unicode=True),
        encoding="utf-8",
    )
    call_command("import_questionnaire_version", dir=str(tmp_path), target_version=2, publish=True, dry_run=True)
    assert not T.objects.filter(version=2).exists()
    call_command("import_questionnaire_version", dir=str(tmp_path), target_version=2, publish=True)
    before = (T.objects.count(), Question.objects.count())
    _import()
    assert (T.objects.count(), Question.objects.count()) == before

    v2 = T.objects.get(version=2)
    _answered_eval(collaborator, period, project_finite, v2)
    with pytest.raises(questionnaire_import.ImportRejected):
        _import()
    assert Question.objects.filter(section__template=v2).count() == 2

    # Con una versión posterior publicada, la carga de una menor se omite (no la desplaza).
    v3 = questionnaire_editor.duplicate_as_new_version(v2)
    questionnaire_editor.publish_template(v3)
    assert "omitido" in questionnaire_import.import_version("ID", "JR", V2_QUESTIONS, 2, publish=True).status
    v3.refresh_from_db()
    assert v3.status == T.Status.PUBLICADO


@pytest.mark.django_db
def test_view_shows_criteria_and_editor_handles_checklist_fields(
    client, v1, talento, collaborator, period, project_finite,
):
    _import()
    v2 = T.objects.get(version=2)
    ev = _answered_eval(collaborator, period, project_finite, v2)
    client.force_login(talento)

    html = client.get(reverse("evaluations:ownership_view", args=[ev.pk])).content.decode()
    assert "Ver criterio" in html and "El backlog está al día" in html
    v1_ev = OwnershipEvaluation.objects.create(user=collaborator, project=None, period=period, template=v1)
    assert "Ver criterio" not in client.get(reverse("evaluations:ownership_view", args=[v1_ev.pk])).content.decode()

    # Duplicar copia los campos; el editor guarda y rechaza títulos repetidos.
    draft = questionnaire_editor.duplicate_as_new_version(v2)
    q1, q2 = Question.objects.filter(section__template=draft).order_by("order")
    assert q1.deliverable == "Backlog actualizado"
    url = reverse("questionnaires:template_edit", args=[draft.pk])
    client.post(url, {"action": "save_question", "question": q2.pk, "title": q1.title})
    q2.refresh_from_db()
    assert q2.title == "Rutinas de gestión — Daily"
    client.post(url, {"action": "save_question", "question": q2.pk, "title": "Daily",
                      "text": "x", "frequency": "Diaria", "guidance": "Llegar preparado"})
    q2.refresh_from_db()
    assert (q2.title, q2.frequency, q2.guidance) == ("Daily", "Diaria", "Llegar preparado")

    # Publicar valida: con un título repetido no se publica.
    Question.objects.filter(pk=q2.pk).update(title=q1.title)
    client.post(url, {"action": "publish"})
    draft.refresh_from_db()
    assert draft.status == T.Status.BORRADOR


@pytest.mark.django_db
def test_mis_evaluaciones_keeps_history_and_only_offers_active_projects(
    client, v1, collaborator, period, project_finite, project_indefinite,
):
    """Proyecto cerrado: su evaluación del periodo pasado sigue visible; no se ofrece para iniciar."""
    from datetime import date

    from apps.catalog.models import ProjectMembership

    ProjectMembership.objects.create(project=project_finite, user=collaborator)
    ProjectMembership.objects.create(project=project_indefinite, user=collaborator)
    old = _answered_eval(collaborator, period, project_finite, v1)
    EvaluationPeriod.objects.filter(pk=period.pk).update(status=EvaluationPeriod.Status.CERRADO)
    s2 = EvaluationPeriod.objects.create(
        name="2026-S2", start_date=date(2026, 7, 1), end_date=date(2026, 12, 31),
        status=EvaluationPeriod.Status.ABIERTO,
    )
    project_finite.is_active = False
    project_finite.save()

    past = ownership_flow.ownership_cards(collaborator, EvaluationPeriod.objects.get(pk=period.pk))
    assert [(c["project"], c["evaluation"], c["historical"]) for c in past] == [(project_finite, old, True)]
    current = ownership_flow.ownership_cards(collaborator, s2)
    assert [(c["project"], c["evaluation"]) for c in current] == [(project_indefinite, None)]

    collaborator.photo_data, collaborator.photo_mime = b"x", "image/jpeg"
    collaborator.save()
    client.force_login(collaborator)
    html = client.get(reverse("evaluations:ownership_list") + f"?periodo={period.pk}").content.decode()
    assert project_finite.name in html and "Proyecto cerrado" in html
    assert client.get(reverse("evaluations:ownership_start", args=[project_finite.pk])).status_code == 404
