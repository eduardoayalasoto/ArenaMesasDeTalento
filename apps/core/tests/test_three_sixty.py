"""Spec 010: evaluación 360 al owner del proyecto (informativa; la interfaz no muestra quién respondió qué)."""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.core.services import questionnaire_editor as editor, three_sixty
from apps.core.tests.conftest import make_learn_user, make_membership
from apps.evaluations.models import FinalScore, ThreeSixtyAnswer, ThreeSixtyResponse
from apps.questionnaires.models import Question, QuestionnaireTemplate as T

User = get_user_model()


@pytest.fixture
def setup(db, period, project_finite, lead, learn_area):
    """Cuestionario 360 publicado (2 dimensiones: 60/40), proyecto con 360 activa, owner y 2 miembros."""
    t = editor.create_template(T.Kind.THREE_SIXTY)
    s1 = t.sections.get()
    s1.title = "Liderazgo"
    s1.save()
    s2 = editor.add_section(t, "Cliente")
    editor.save_dimension_weights(t, {s1.pk: "60", s2.pk: "40"})
    q1 = Question.objects.create(section=s1, order=1, title="¿Lo identifican como líder?", qtype="SCALE", allow_na=False)
    q2 = Question.objects.create(section=s1, order=2, title="¿Retroalimenta a tiempo?", qtype="SCALE", allow_na=False)
    q3 = Question.objects.create(section=s2, order=1, title="¿El cliente confía?", qtype="SCALE", allow_na=False)
    editor.publish_template(t)
    lead.photo_data, lead.photo_mime = b"x", "image/jpeg"   # evita el redirect a «Mi perfil»
    lead.save()
    project_finite.three_sixty_enabled = True
    project_finite.save()
    ana = make_learn_user("ana.360@arena-analytics.com", area=learn_area)
    beto = make_learn_user("beto.360@arena-analytics.com", area=learn_area)
    for u in (ana, beto):
        make_membership(project_finite, u, period)
    talento = make_learn_user("talento.360@arena-analytics.com", role="TALENTO")
    return {"t": t, "qs": [q1, q2, q3], "ana": ana, "beto": beto, "owner": lead, "talento": talento,
            "project": project_finite, "period": period}


def _answer(client, user, project, values, action="submit", comment=""):
    client.force_login(user)
    data = {f"q_{q.pk}": v for q, v in values}
    return client.post(reverse("evaluations:three_sixty_respond", args=[project.pk]),
                       {**data, "comment": comment, "action": action})


@pytest.mark.django_db
def test_respondents_exclude_owner_and_pending_list(setup):
    s = setup
    assert set(three_sixty.respondents(s["project"], s["period"])) == {s["ana"], s["beto"]}
    assert [r["project"] for r in three_sixty.to_answer(s["ana"], s["period"])] == [s["project"]]
    assert three_sixty.to_answer(s["owner"], s["period"]) == []     # el evaluado no se califica a sí mismo
    s["project"].three_sixty_enabled = False
    s["project"].save()
    assert three_sixty.to_answer(s["ana"], s["period"]) == []


@pytest.mark.django_db
def test_draft_autosave_then_submit_needs_everything(client, setup):
    s = setup
    q1, q2, q3 = s["qs"]
    client.force_login(s["ana"])
    url = reverse("evaluations:three_sixty_respond", args=[s["project"].pk])
    assert client.get(url).status_code == 200
    r = client.post(url, {f"q_{q1.pk}": "4", "action": "autosave"}, HTTP_HX_REQUEST="true")
    assert r.status_code == 204
    resp = ThreeSixtyResponse.objects.get(respondent=s["ana"])
    assert resp.status == "BORRADOR" and resp.answers.count() == 1 and resp.evaluee == s["owner"]
    r = client.post(url, {f"q_{q1.pk}": "4", f"q_{q2.pk}": "3", "action": "submit"})
    assert r.status_code == 200 and "Faltan 1 pregunta" in r.content.decode()      # incompleta: no se envía
    r = client.post(url, {f"q_{q1.pk}": "4", f"q_{q2.pk}": "3", f"q_{q3.pk}": "2", "comment": "Va muy bien", "action": "submit"})
    assert r.status_code == 302
    resp.refresh_from_db()
    assert resp.is_submitted and resp.submitted_at and resp.duration_seconds is not None and resp.comment == "Va muy bien"
    # lo enviado no se edita
    with pytest.raises(ValidationError):
        three_sixty.save_answers(resp, {q1.pk: 1})
    assert client.get(url).status_code == 302
    with pytest.raises(ValidationError):
        three_sixty.get_or_start(s["project"], s["period"], s["owner"])               # el owner no responde
    with pytest.raises(ValidationError):
        three_sixty.save_answers(ThreeSixtyResponse(template=s["t"], status="BORRADOR"), {q1.pk: 9})


@pytest.mark.django_db
def test_score_direct_with_one_answer_average_with_many_and_never_touches_final(client, setup):
    s = setup
    q1, q2, q3 = s["qs"]
    FinalScore.objects.create(user=s["owner"], period=s["period"], final_score=Decimal("3.20"))
    assert three_sixty.result(s["project"], s["period"])["index"] is None
    _answer(client, s["ana"], s["project"], [(q1, 4), (q2, 4), (q3, 2)])
    r = three_sixty.result(s["project"], s["period"])
    # Liderazgo 4.0 (60 %) + Cliente 2.0 (40 %) = 3.2  → calificación directa de la única respuesta
    assert r["index"] == Decimal("3.20") and r["n_sent"] == 1 and r["band"] == "Cumple"
    _answer(client, s["beto"], s["project"], [(q1, 2), (q2, 2), (q3, 4)], comment="Más foco en los plazos")
    r = three_sixty.result(s["project"], s["period"])
    # Liderazgo (4+4+2+2)/4 = 3.0 ; Cliente (2+4)/2 = 3.0 → 3.00
    assert r["index"] == Decimal("3.00") and r["n_sent"] == 2 and r["missing"] == []
    assert FinalScore.objects.get(user=s["owner"]).final_score == Decimal("3.20")      # intacta
    assert r["comments"] == ["Más foco en los plazos"]


@pytest.mark.django_db
def test_authorship_is_stored_but_no_screen_shows_it(client, setup):
    s = setup
    q1, q2, q3 = s["qs"]
    _answer(client, s["ana"], s["project"], [(q1, 4), (q2, 3), (q3, 2)], comment="Comentario anónimo")
    assert ThreeSixtyResponse.objects.get().respondent == s["ana"]          # la base sí lo guarda (POC)
    assert ThreeSixtyAnswer.objects.count() == 3
    name = s["ana"].full_name
    # El owner: score y comentario, pero ni nombre, ni conteos, ni quién falta
    client.force_login(s["owner"])
    html = client.get(reverse("evaluations:three_sixty_result", args=[s["project"].pk])).content.decode()
    assert "Comentario anónimo" in html and name not in html and s["beto"].full_name not in html
    assert "Respondieron" not in html and "Falta por responder" not in html
    # Talento: avance y quién falta (nunca de quién es cada respuesta)
    client.force_login(s["talento"])
    html = client.get(reverse("evaluations:three_sixty_result", args=[s["project"].pk])).content.decode()
    assert "Respondieron" in html and s["beto"].full_name in html and "Comentario anónimo" in html
    assert name not in html.split("Falta por responder")[1].split("</p>")[0] if "Falta por responder" in html else True


@pytest.mark.django_db
def test_permissions_only_owner_talento_and_nobody_else(client, setup):
    s = setup
    url = reverse("evaluations:three_sixty_result", args=[s["project"].pk])
    client.force_login(s["ana"])
    assert client.get(url).status_code == 403            # un miembro no ve el resultado
    client.force_login(s["owner"])
    assert client.get(url).status_code == 200
    client.force_login(s["talento"])
    assert client.get(url).status_code == 200
    client.force_login(s["ana"])
    assert client.get(reverse("evaluations:three_sixty_list")).status_code == 200


@pytest.mark.django_db
def test_list_screen_blocks_and_closed_period(client, setup):
    s = setup
    client.force_login(s["ana"])
    html = client.get(reverse("evaluations:three_sixty_list")).content.decode()
    assert "Por responder" in html and s["project"].name in html and "Lo que mi equipo dijo de mí" not in html
    client.force_login(s["owner"])
    html = client.get(reverse("evaluations:three_sixty_list")).content.decode()
    assert "Lo que mi equipo dijo de mí" in html and "Aún sin respuestas" in html
    client.force_login(s["talento"])
    assert "Seguimiento de proyectos con 360" in client.get(reverse("evaluations:three_sixty_list")).content.decode()
    # periodo cerrado: ya no se puede iniciar
    s["period"].status = "CERRADO"
    s["period"].save()
    with pytest.raises(ValidationError):
        three_sixty.get_or_start(s["project"], s["period"], s["ana"])


@pytest.mark.django_db
def test_nav_item_badge_project_check_and_mesa_block(client, setup):
    from apps.core.navigation import build_nav
    from django.test import RequestFactory

    s = setup
    req = RequestFactory().get(reverse("evaluations:three_sixty_list"))
    req.user = s["ana"]
    from django.urls import resolve
    req.resolver_match = resolve(req.path)
    items = [i for c in build_nav(req)["nav_categories"] for i in c["items"]]
    assert "Evaluaciones 360" in [i["label"] for i in items]
    assert three_sixty.pending_count(s["ana"]) == 1
    # El check vive en la pantalla del proyecto (permiso projects.edit)
    client.force_login(s["talento"])
    assert "Activar evaluación 360 al owner" in client.get(reverse("catalog:project_edit", args=[s["project"].pk])).content.decode()
    # Mesa de Talento: el bloque del owner muestra el mini score
    q1, q2, q3 = s["qs"]
    _answer(client, s["ana"], s["project"], [(q1, 4), (q2, 4), (q3, 4)])
    client.force_login(s["talento"])
    html = client.get(reverse("dashboards:talent_person", args=[s["owner"].pk])).content.decode()
    assert "Tu equipo lo calificó con" in html and "4.0 / 4" in html and "Ver detalle 360" in html
