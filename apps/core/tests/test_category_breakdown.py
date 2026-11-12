"""Score por categoría visible en la evaluación y en el informe (spec 008, US5)."""

import json
from decimal import Decimal

import pytest
from django.urls import reverse

from apps.core.services import scoring
from apps.core.tests.test_scoring_weighted import build_template, evaluation_with
from apps.dashboards.views import build_results
from apps.evaluations.models import OwnershipEvaluation


def _json_rows(html):
    start = html.index('<script id="category-rows" type="application/json">') + len('<script id="category-rows" type="application/json">')
    return json.loads(html[start:html.index("</script>", start)])


@pytest.mark.django_db
def test_category_scores_in_evaluation_report_and_autosave(client, collaborator, project_finite, period, area, level_jr):
    type(collaborator).objects.filter(pk=collaborator.pk).update(photo_data=b"x", photo_mime="image/jpeg")
    template, questions = build_template(area, level_jr, [
        ("a", "Delivery", "60.0", [None, None]), ("b", "Producto", "40.0", [None, None]),
    ])
    evaluation = evaluation_with(collaborator, project_finite, period, template, questions, [4, 4, 2, None])
    client.force_login(collaborator)

    # La evaluación lleva el desglose en la página; «sin calificar» cuando no hay respuestas en la categoría.
    html = client.get(reverse("evaluations:ownership_edit", args=[evaluation.pk])).content.decode()
    rows = _json_rows(html)
    assert [(r["name"], r["weight"], r["score"], r["answered"], r["total"]) for r in rows] == [
        ("Delivery", "60.0", "4.00", 2, 2), ("Producto", "40.0", "2.00", 2, 2)]
    assert "Score por categoría" in html

    # El autoguardado devuelve el desglose actualizado (todo N/A en una categoría → «sin calificar»).
    answer_url = reverse("evaluations:ownership_autosave", args=[evaluation.pk])
    response = client.post(answer_url, json.dumps({"question": questions[2].pk, "is_na": True}), content_type="application/json")
    data = response.json()
    assert data["ok"] and data["average"] == "4.00"
    assert [(c["name"], c["score"]) for c in data["categories"]] == [("Delivery", "4.00"), ("Producto", None)]

    # Informe: promedio por categoría de las evaluaciones enviadas; oculto si solo hay una categoría.
    evaluation.refresh_from_db()
    evaluation.score = scoring.ownership_evaluation_score(evaluation)
    evaluation.status = OwnershipEvaluation.Status.ENVIADA
    evaluation.save()
    results = build_results(collaborator, period)
    assert [(c["name"], c["score"]) for c in results["ownership_categories"]] == [
        ("Delivery", Decimal("4.00")), ("Producto", None)]

    OwnershipEvaluation.objects.filter(pk=evaluation.pk).delete()
    general, gq = build_template(area, level_jr, [("general", "General", "100.0", [None, None])], version=2)
    legacy = evaluation_with(collaborator, project_finite, period, general, gq, [3, 3])
    legacy.status = OwnershipEvaluation.Status.ENVIADA
    legacy.score = scoring.ownership_evaluation_score(legacy)
    legacy.save()
    assert build_results(collaborator, period)["ownership_categories"] == []
    assert _json_rows(client.get(reverse("evaluations:ownership_view", args=[legacy.pk])).content.decode()) == []
