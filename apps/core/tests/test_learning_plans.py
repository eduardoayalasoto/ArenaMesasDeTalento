"""Arena Learn 006 · US2/US3/US5: planes por área, Mi plan y seguimiento. Compactas por escenario."""

from datetime import date

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Area
from apps.core.services import learning_flow as flow
from apps.core.services import learning_plans as plans
from apps.core.services import learning_tags as tags
from apps.core.tests.conftest import learn_request_data, learn_review_data, make_learn_user
from apps.learning.models import CatalogCourse, PersonalPlanItem, PlanCourse, TrainingPlan

from .test_learning import authorize, pdf

YEAR = timezone.localdate().year
S = TrainingPlan.Status


def mk_course(name, kind="PUNTUAL", focus="VERTICAL", *tag_names, cost=None):
    c = CatalogCourse.objects.create(name=name, provider="MS Learn", kind=kind, focus=focus,
                                     url=f"https://learn.microsoft.com/{name.replace(' ', '-')}", reference_cost=cost)
    c.tags.set(tags.resolve(tag_names))
    return c


@pytest.fixture
def plan_setup(learn_people, learn_area, learn_levels):
    p = learn_people
    plan = plans.save_plan(TrainingPlan(area=learn_area, year=YEAR, title="Plan CD", start_month=4, end_month=12,
                                        hours_min=5, hours_max=10, type_notes={"PUNTUAL": "Cursos cortos"}),
                           p["talento"])
    c_struct = mk_course("Fundamentos IA", "ESTRUCTURADO", "HORIZONTAL")
    c_ko = mk_course("Copilot en PBI", "PUNTUAL", "VERTICAL", "KO")
    c_cert = mk_course("AI-900", "CERTIFICACION", "VERTICAL", cost=165)
    i_struct = plans.save_item(plan, p["talento"], course=c_struct, levels=[learn_levels["JR"]])
    i_ko = plans.save_item(plan, p["talento"], course=c_ko)  # sin niveles = todos
    i_cert = plans.save_item(plan, p["talento"], course=c_cert, levels=[learn_levels["LEAD"]], note="~$165 USD")
    return {"plan": plan, "courses": (c_struct, c_ko, c_cert), "items": (i_struct, i_ko, i_cert)}


@pytest.mark.django_db
def test_plans_service_rules(learn_people, learn_area, learn_levels, plan_setup):
    p, plan = learn_people, plan_setup["plan"]
    c_struct, c_ko, c_cert = plan_setup["courses"]

    # Escenario 4: un plan por área y año; solo quien gestiona planes.
    with pytest.raises(ValidationError):
        plans.save_plan(TrainingPlan(area=learn_area, year=YEAR, title="Otro"), p["talento"])
    with pytest.raises(PermissionDenied):
        plans.save_plan(TrainingPlan(area=learn_area, year=YEAR + 1, title="X"), p["colab"])
    with pytest.raises(ValidationError):
        plans.save_plan(TrainingPlan(area=learn_area, year=YEAR + 1, title="X", start_month=9, end_month=3), p["talento"])
    with pytest.raises(ValidationError, match="ya está en el plan"):
        plans.save_item(plan, p["talento"], course=c_ko)

    # FR-013/014: borrador invisible; no se publica vacío.
    assert plan.status == S.BORRADOR and plans.current_plan_for(p["colab"]) is None
    assert not plans.can_view_plan(p["colab"], plan) and plans.can_view_plan(p["talento"], plan)
    empty = plans.save_plan(TrainingPlan(area=learn_area, year=YEAR + 1, title="Vacío"), p["talento"])
    with pytest.raises(ValidationError, match="al menos un curso"):
        plans.set_status(empty, "publish", p["talento"])
    plans.set_status(plan, "publish", p["talento"])
    assert plans.current_plan_for(p["colab"]).pk == plan.pk

    # Agrupación por tipo en orden fijo, con texto del tipo; filtros por nivel (incluye "Todos") y etiqueta.
    groups = plans.plan_groups(plan)
    assert [g["kind"] for g in groups] == ["ESTRUCTURADO", "CERTIFICACION", "PUNTUAL"]
    assert groups[2]["note"] == "Cursos cortos"
    jr = plans.plan_groups(plan, {"level": learn_levels["JR"].pk})
    assert {i.course.name for g in jr for i in g["items"]} == {"Fundamentos IA", "Copilot en PBI"}
    ko = tags.resolve(["KO"])[0]
    assert [i.course for g in plans.plan_groups(plan, {"tags": [ko.pk]}) for i in g["items"]] == [c_ko]
    assert [g["kind"] for g in plans.plan_groups(plan, {"kind": "CERTIFICACION"})] == ["CERTIFICACION"]

    # Escenario 3: niveles propios por plan; áreas del curso derivadas de planes publicados.
    ux = Area.objects.create(code="UXUI", name="UX/UI")
    plan_ux = plans.save_plan(TrainingPlan(area=ux, year=YEAR, title="Plan UX"), p["talento"])
    plans.save_item(plan_ux, p["talento"], course=c_ko, levels=[learn_levels["LEAD"]])
    assert flow.course_plan_areas([c_ko])[c_ko.pk] == [learn_area]  # el plan UX sigue en borrador
    plans.set_status(plan_ux, "publish", p["talento"])
    assert set(flow.course_plan_areas([c_ko])[c_ko.pk]) == {learn_area, ux}
    assert {c.pk for c in flow.catalog_queryset({"area": ux.pk})} == {c_ko.pk}
    assert list(PlanCourse.objects.get(plan=plan, course=c_ko).levels.all()) == []

    # Orden dentro del grupo y quitar del plan.
    c_p2 = mk_course("Fabric RTI", "PUNTUAL")
    i_p2 = plans.save_item(plan, p["talento"], course=c_p2)
    plans.move_item(i_p2, "up", p["talento"])
    assert [i.course.name for i in plans.plan_groups(plan)[2]["items"]] == ["Fabric RTI", "Copilot en PBI"]
    plans.delete_item(i_p2, p["talento"])
    plan = plans.set_status(plan, "archive", p["talento"])
    assert plans.current_plan_for(p["colab"]) is None and plans.can_view_plan(p["colab"], plan)


@pytest.mark.django_db
def test_my_plan_states_and_visibility(learn_people, learn_area, plan_setup):
    p, plan = learn_people, plan_setup["plan"]
    c_struct, c_ko, c_cert = plan_setup["courses"]
    i_struct, i_ko, i_cert = plan_setup["items"]
    colab = p["colab"]
    colab.direct_lead = p["lead"]
    colab.save(update_fields=["direct_lead"])

    with pytest.raises(ValidationError, match="publicado"):  # borrador: no se agrega
        plans.add_to_my_plan(colab, plan_course=i_ko)
    plans.set_status(plan, "publish", p["talento"])

    # Escenario 1/2: agregar (Pendiente) y "Empezar" sin costo (En curso).
    it_ko = plans.add_to_my_plan(colab, plan_course=i_ko)
    it_cert = plans.add_to_my_plan(colab, plan_course=i_cert)
    it_struct = plans.add_to_my_plan(colab, plan_course=i_struct)
    assert it_ko.personal_plan.year == plan.year and plans.add_to_my_plan(colab, plan_course=i_ko) == it_ko
    st = plans.item_states([it_ko, it_cert, it_struct], colab)
    assert {s.code for s in st.values()} == {plans.PENDIENTE}
    plans.start_item(it_ko, colab)
    assert plans.item_states([it_ko], colab)[it_ko.pk].code == plans.EN_CURSO

    # Escenario 3: solicitud con autorización → En curso con la etapa; borrador → Pendiente con nota.
    draft = flow.create_request(colab, learn_request_data(), catalog_course=c_cert)
    s = plans.item_states([it_cert], colab)[it_cert.pk]
    assert (s.code, s.detail) == (plans.PENDIENTE, "Borrador de solicitud")
    flow.submit_request(draft, colab)
    s = plans.item_states([it_cert], colab)[it_cert.pk]
    assert (s.code, s.detail) == (plans.EN_CURSO, "En revisión del Lead")

    # Escenario 4/5: completar con el registro existente → Completado (también si ya lo había tomado).
    flow.create_direct(colab, colab, {}, learn_review_data(), [pdf()], catalog_course=c_struct)
    assert plans.item_states([it_struct], colab)[it_struct.pk].code == plans.COMPLETADO
    other_course = mk_course("Ya tomado", "PUNTUAL")
    flow.create_direct(colab, colab, {}, learn_review_data(), [pdf()], catalog_course=other_course)
    done = plans.add_to_my_plan(colab, course=other_course)
    assert done.personal_plan.year == YEAR and plans.item_states([done], colab)[done.pk].code == plans.COMPLETADO

    # Escenario 6: descartar y reactivar; no se agrega un curso inactivo.
    plans.discard_item(it_ko, colab)
    view = plans.my_plan(colab, plan.year)
    assert view.counts == {"PENDIENTE": 0, "EN_CURSO": 1, "COMPLETADO": 2, "DESCARTADO": 1}
    plans.discard_item(it_ko, colab, discard=False)
    c_ko.is_active = False
    c_ko.save()
    with pytest.raises(ValidationError):
        plans.add_to_my_plan(p["other"], course=c_ko)
    with pytest.raises(PermissionDenied):
        plans.start_item(it_cert, p["other"])

    # Escenario 7 (FR-022): dueño, su Lead (A = reporte directo), Director y Talento sí; otro no.
    assert plans.can_view_personal_plan(colab, colab)
    assert plans.can_view_personal_plan(p["lead"], colab)
    assert plans.can_view_personal_plan(p["director"], colab) and plans.can_view_personal_plan(p["talento"], colab)
    assert not plans.can_view_personal_plan(p["other"], colab)
    assert not plans.can_view_personal_plan(p["lead"], p["other"])  # no es su reporte directo

    # Mi plan en pocas consultas (sin N+1).
    with CaptureQueriesContext(connection) as ctx:
        plans.my_plan(colab, plan.year)
    assert len(ctx.captured_queries) <= 4

    # US5: seguimiento con alcance (Lead = sus reportes directos; Talento = todos).
    t = plans.tracking_rows(p["talento"], {"year": plan.year})
    assert t["people_with_plan"] == 1 and t["totals"]["COMPLETADO"] == 2
    row = t["rows"][0]
    assert (row["active"], row["counts"]["COMPLETADO"], row["progress"]) == (4, 2, 50)
    assert plans.tracking_rows(p["lead"], {"year": plan.year})["people_with_plan"] == 1
    assert plans.tracking_rows(p["colab"], {"year": plan.year})["people_with_plan"] == 0
    rows = plans.tracking_export_rows(p["talento"], {"year": plan.year})
    assert len(rows) == 4 and {r[8] for r in rows} == {"Completado", "En curso"}


@pytest.mark.django_db
def test_plan_and_my_plan_views(client, learn_people, learn_area, plan_setup):
    p, plan = learn_people, plan_setup["plan"]
    i_struct, i_ko, i_cert = plan_setup["items"]
    colab = p["colab"]
    colab.direct_lead = p["lead"]
    colab.save(update_fields=["direct_lead"])

    client.force_login(colab)
    assert client.get(reverse("learning:plan_detail", args=[plan.pk])).status_code == 404  # borrador
    assert client.get(reverse("learning:plan_list")).status_code == 200  # sin plan publicado: lista
    plans.set_status(plan, "publish", p["talento"])
    resp = client.get(reverse("learning:plan_list"))
    assert resp.status_code == 302 and resp["Location"] == reverse("learning:plan_detail", args=[plan.pk])

    html = client.get(reverse("learning:plan_detail", args=[plan.pk])).content.decode()
    assert "Plan CD" in html and "Todos los niveles" in html and "Cursos cortos" in html and "Agregar a Mi plan" in html
    assert "Agregar curso del catálogo" not in html  # no gestiona planes
    ko = tags.resolve(["KO"])[0]
    part = client.get(reverse("learning:plan_detail", args=[plan.pk]),
                      {"partial": "courses", "etiqueta": ko.pk}, HTTP_HX_REQUEST="true").content.decode()
    assert "Copilot en PBI" in part and "Fundamentos IA" not in part and "<html" not in part

    resp = client.post(reverse("learning:my_plan_add"), {"plan_course": i_ko.pk}, HTTP_HX_REQUEST="true")
    assert resp.status_code == 200 and "En mi plan" in resp.content.decode() and "toast" in resp["HX-Trigger"]
    item = PersonalPlanItem.objects.get()
    resp = client.post(reverse("learning:my_plan_start", args=[item.pk]), {"mode": "free"}, HTTP_HX_REQUEST="true")
    assert "En curso" in resp.content.decode()
    resp = client.post(reverse("learning:my_plan_start", args=[item.pk]), {"mode": "request"})
    assert resp["Location"].endswith(f"?catalogo={item.course_id}")
    resp = client.post(reverse("learning:my_plan_complete", args=[item.pk]))
    assert reverse("learning:direct_create") in resp["Location"]
    html = client.get(reverse("learning:my_plan")).content.decode()
    assert "Copilot en PBI" in html and "Mi plan" in html
    assert client.get(reverse("learning:person_plan", args=[p["other"].pk])).status_code == 403
    assert client.get(reverse("learning:plan_tracking")).status_code == 403
    client.force_login(p["other"])
    assert client.post(reverse("learning:my_plan_discard", args=[item.pk])).status_code == 403

    # Lead: ve el plan de su reporte directo y el seguimiento; no administra planes.
    client.force_login(p["lead"])
    assert "Copilot en PBI" in client.get(reverse("learning:person_plan", args=[colab.pk])).content.decode()
    assert colab.full_name in client.get(reverse("learning:plan_tracking")).content.decode()
    assert client.get(reverse("learning:plan_create")).status_code == 403

    # Talento: crea plan, agrega/edita/quita cursos por htmx, exporta.
    client.force_login(p["talento"])
    ux = Area.objects.create(code="UXUI", name="UX/UI")
    resp = client.post(reverse("learning:plan_create"), {
        "area": ux.pk, "year": YEAR, "title": "Plan UX", "start_month": 5, "end_month": 12,
        "hours_min": 3, "hours_max": 10, "intro": "", "note_ESTRUCTURADO": "Amplitud UX",
    })
    new = TrainingPlan.objects.get(area=ux)
    assert resp.status_code == 302 and new.type_notes == {"ESTRUCTURADO": "Amplitud UX"}
    c = plan_setup["courses"][0]
    resp = client.post(reverse("learning:plan_item_save", args=[new.pk]), {"course": c.pk, "levels": [], "note": ""},
                       HTTP_HX_REQUEST="true")
    assert resp.status_code == 200 and "Fundamentos IA" in resp.content.decode()
    pc = PlanCourse.objects.get(plan=new)
    lv = p["colab"].level
    client.post(reverse("learning:plan_item_edit", args=[new.pk, pc.pk]), {"action": "save", "levels": [lv.pk], "note": "Jr"})
    assert list(pc.levels.all()) == [lv]
    client.post(reverse("learning:plan_status", args=[new.pk]), {"action": "publish"})
    client.post(reverse("learning:plan_status", args=[new.pk]) + "?action=archive")
    assert TrainingPlan.objects.get(pk=new.pk).status == S.ARCHIVADO
    client.post(reverse("learning:plan_item_edit", args=[new.pk, pc.pk]), {"action": "delete"})
    assert not PlanCourse.objects.filter(plan=new).exists()
    resp = client.get(reverse("learning:plan_tracking_export"), {"anio": plan.year})
    assert resp.status_code == 200 and resp["Content-Type"].startswith("application/vnd.openxmlformats")
    html = client.get(reverse("learning:catalog_detail", args=[i_ko.course_id])).content.decode()
    assert "En los planes de capacitación" in html and learn_area.name in html
