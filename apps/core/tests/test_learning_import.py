"""Arena Learn 006 · US4: importación del catálogo/planes y limpieza de datos de prueba."""

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from apps.catalog.models import Area, SeniorityLevel
from apps.core.services import learning_flow as flow
from apps.core.services import learning_import as imp
from apps.core.tests.conftest import learn_request_data
from apps.learning.models import (
    CatalogCourse,
    CourseKind,
    CourseRequest,
    Focus,
    LearningSettings,
    PlanCourse,
    Tag,
    TrainingPlan,
)

YT1 = "https://www.youtube.com/watch?v=AAA&t=285s"
YT2 = "https://www.youtube.com/watch?v=BBB"


def course(key, name, kind="PUNTUAL", focus="VERTICAL", url=None, **kw):
    return {"key": key, "url": url if url is not None else f"https://learn.microsoft.com/{key}", "name": name,
            "provider": kw.pop("provider", "Microsoft Learn"), "kind": kind, "focus": focus,
            "duration_hours": kw.pop("hours", None), "reference_cost": kw.pop("cost", None),
            "currency": kw.pop("currency", "USD"), "ko": kw.pop("ko", False), "proposed": kw.pop("proposed", []),
            "why": "", "aliases": kw.pop("aliases", [])}


def plans_json(tmp_path, courses, plans):
    p = tmp_path / "planes.json"
    p.write_text(json.dumps({"year": 2026, "plans": plans, "courses": courses}), encoding="utf-8")
    return p


def plan(area, items, **kw):
    return {"area": area, "year": 2026, "title": f"Plan {area} 2026", "start_month": 5, "end_month": 12,
            "hours_min": 3, "hours_max": 10, "intro": "Sugerido", "type_notes": kw.get("notes", {}), "items": items}


@pytest.fixture
def import_refs(db):
    areas = {c: Area.objects.get_or_create(code=c, defaults={"name": c})[0] for c in ("PM", "CD", "ID")}
    levels = {}
    for i, c in enumerate(("JR", "MID", "SNR", "LEAD"), start=1):
        levels[c] = SeniorityLevel.objects.get_or_create(code=c, defaults={"name": c.title(), "order": i})[0]
    return areas, levels


@pytest.mark.django_db
def test_import_rules_idempotency_and_no_overwrite(tmp_path, import_refs):
    areas, levels = import_refs
    courses = [
        course("shared", "Fabric RTI", "ESTRUCTURADO", "HORIZONTAL", hours=6),
        course("ko-only", "Introduction to AI", ko=True, proposed=["focus"], hours=2.5),
        course("cert:AI-901", "AI-901 · Azure AI Fundamentals", "CERTIFICACION", url="", cost=165,
               provider="Microsoft"),
        course("yt1", "Video 1", url=YT1, provider="YouTube", cost=0),
        course("yt2", "Video 2", url=YT2, provider="YouTube"),
        course("alias", "Supply Chain Analytics", "CONTEXTUAL", "HORIZONTAL", aliases=["Unilever Data Analyst"]),
    ]
    data = plans_json(tmp_path, courses, [
        plan("PM", [{"course": "ko-only", "levels": ["JR"], "note": ""},
                    {"course": "yt1", "levels": ["MID", "SNR"], "note": ""},
                    {"course": "yt2", "levels": [], "note": ""}], notes={"PUNTUAL": "Cursos cortos"}),
        plan("CD", [{"course": "shared", "levels": [], "note": ""},
                    {"course": "cert:AI-901", "levels": [], "note": "Beta abr 2026"}]),
        plan("ID", [{"course": "shared", "levels": [], "note": ""}, {"course": "alias", "levels": [], "note": ""}]),
    ])

    # Simulación: no guarda nada.
    s = imp.import_plans(data, dry_run=True)
    assert s.courses_created == 6 and s.plans_created == 3
    assert not CatalogCourse.objects.exists() and not TrainingPlan.objects.exists()

    s = imp.import_plans(data)
    assert (s.courses_created, s.plans_created, s.items_created, s.ko_assigned) == (6, 3, 7, 1)
    assert any("Unilever" in a for a in s.aliases)
    # Escenario 1/2: una sola vez en el catálogo, en ambos planes; áreas derivadas de los planes.
    shared = CatalogCourse.objects.get(name="Fabric RTI")
    assert set(flow.course_plan_areas([shared])[shared.pk]) == {areas["CD"], areas["ID"]}
    # Escenario 3/4: niveles por plan; KO solo como etiqueta; YouTube con `v` distinto = 2 cursos.
    pm = TrainingPlan.objects.get(area=areas["PM"])
    assert pm.status == TrainingPlan.Status.PUBLICADO and pm.type_notes == {"PUNTUAL": "Cursos cortos"}  # escenario 9
    assert set(PlanCourse.objects.get(plan=pm, course__name="Video 1").levels.values_list("code", flat=True)) == {"MID", "SNR"}
    assert [t.name for t in CatalogCourse.objects.get(name="Introduction to AI").tags.all()] == ["KO"]
    assert Tag.objects.count() == 1
    assert CatalogCourse.objects.filter(provider="YouTube").count() == 2
    assert CatalogCourse.objects.get(name="Video 1").url == YT1  # liga tal cual (la normalización solo identifica)
    # Escenario 5: certificación con costo de examen; tipo y enfoque independientes.
    cert = CatalogCourse.objects.get(name__startswith="AI-901")
    assert (cert.kind, cert.focus, cert.reference_cost, cert.currency) == (
        CourseKind.CERTIFICACION, Focus.VERTICAL, Decimal("165"), "USD")
    assert str(CatalogCourse.objects.get(name="Introduction to AI").duration_hours) == "2.5"

    # Escenario 6: Talento edita; la reimportación no pisa nada ni duplica (SC-003).
    shared.kind, shared.focus, shared.reference_cost = "PUNTUAL", "VERTICAL", Decimal("999")
    shared.save()
    pc = PlanCourse.objects.get(plan=pm, course__name="Video 2")
    pc.levels.set([levels["LEAD"]])
    TrainingPlan.objects.filter(area=areas["ID"]).update(status=TrainingPlan.Status.ARCHIVADO)
    s = imp.import_plans(data)
    assert (s.courses_created, s.plans_created, s.items_created, s.ko_assigned) == (0, 0, 0, 0)
    shared.refresh_from_db()
    assert (shared.kind, shared.focus, shared.reference_cost) == ("PUNTUAL", "VERTICAL", Decimal("999"))
    assert list(pc.levels.values_list("code", flat=True)) == ["LEAD"]
    assert TrainingPlan.objects.get(area=areas["ID"]).status == TrainingPlan.Status.ARCHIVADO
    assert CatalogCourse.objects.count() == 6

    # Escenario 7: archivo inválido -> se rechaza completo con su motivo.
    bad = plans_json(tmp_path, [course("x", "X", kind="CURSO")], [plan("ZZ", [{"course": "nope", "levels": ["XX"]}])])
    with pytest.raises(ValidationError) as exc:
        imp.import_plans(bad)
    msgs = " ".join(exc.value.messages)
    assert "tipo inválido" in msgs and "área inexistente" in msgs and "curso inexistente" in msgs


@pytest.mark.django_db
def test_reset_learning_data(tmp_path, learn_people, catalog_course, import_refs):
    p = learn_people
    req = flow.create_request(p["colab"], learn_request_data(), submit=True)
    settings = LearningSettings.load()
    before = date.today() + timedelta(days=1)
    counts = imp.reset_learning_data(before)
    assert counts["Solicitudes y registros"] == 1 and counts["Cursos del catálogo"] == 1
    assert CourseRequest.objects.exists()  # sin confirmar no borra
    # Protección: datos creados desde la fecha de corte.
    with pytest.raises(ValidationError):
        imp.reset_learning_data(date.today())
    call_command("reset_learning_data", "--before", before.isoformat(), "--confirm")
    assert not CourseRequest.objects.exists() and not CatalogCourse.objects.exists() and not Tag.objects.exists()
    assert not CourseRequest.history.model.objects.exists()
    assert LearningSettings.objects.filter(pk=settings.pk).exists() and p["colab"].__class__.objects.filter(pk=p["colab"].pk).exists()
    assert req.pk is not None


def test_real_plans_json_is_consistent():
    """El JSON versionado cumple las reglas de la spec sin tocar la BD."""
    data = json.loads(imp.DEFAULT_PLANS_PATH.read_text(encoding="utf-8"))
    by_key = {c["key"]: c for c in data["courses"]}
    assert len(by_key) == len(data["courses"]) >= 250
    assert {p["area"] for p in data["plans"]} == {"PM", "UXUI", "CD", "ID"}
    assert all(c["kind"] in CourseKind.values and c["focus"] in Focus.values for c in data["courses"])
    for p in data["plans"]:
        assert all(it["course"] in by_key for it in p["items"])
        assert len({it["course"] for it in p["items"]}) == len(p["items"])
        assert "KO" not in json.dumps(p["type_notes"])  # no hay agrupación KO
    # KO solo como etiqueta; los 20 solo-KO de PM son Puntual y tienen nivel por fase.
    assert sum(c["ko"] for c in data["courses"]) >= 20
    pm = next(p for p in data["plans"] if p["area"] == "PM")
    ko_pm = [it for it in pm["items"] if by_key[it["course"]]["ko"]]
    assert all(it["levels"] for it in ko_pm)
    certs = {c["name"] for c in data["courses"] if c["kind"] == "CERTIFICACION"}
    assert {"PMP · Project Management Professional", "Claude Certified Architect"} <= certs
    # Todo dato propuesto lleva su motivo.
    assert all(c["why"] for c in data["courses"] if c["proposed"])
