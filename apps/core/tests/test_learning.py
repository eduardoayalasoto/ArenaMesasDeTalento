"""Arena Learn (spec 004): pruebas compactas por escenario (servicio, permisos y vistas).

Cada prueba encadena un flujo completo para minimizar viajes a la BD (Neon).
"""

import io
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone

from apps.catalog.models import Area
from apps.core.services import learning_flow as flow
from apps.core.services import permissions
from apps.core.tests.conftest import learn_request_data, learn_review_data, make_learn_user
from apps.learning.models import ApprovalStep, CourseEvidence, CourseRequest

St = CourseRequest.Status
Stage = CourseRequest.Stage
PDF = b"%PDF-1.4 certificado"


def pdf(name="cert.pdf", content=PDF):
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def submit(user, **kw):
    return flow.create_request(user, learn_request_data(**kw), submit=True)


def authorize(req, p):
    for who in ("lead", "director", "talento"):
        req = flow.decide(req, p[who], "approve")
    return req


def closed(p, **kw):
    req = authorize(submit(p["colab"], **kw), p)
    return flow.complete(req, p["colab"], learn_review_data(), [pdf()])


# --- Servicio ------------------------------------------------------------------------------


@pytest.mark.django_db
def test_happy_path_end_to_end(learn_people):
    """Solicitud → regreso/reanudación → autorización → bloqueo FR-004 → pago → cierre → validación."""
    p = learn_people
    req = submit(p["colab"])
    assert (req.status, req.current_stage) == (St.EN_REVISION, Stage.LEAD)
    assert flow.approvals_for(p["lead"]) == [req]
    assert any("por aprobar" in i["text"] for i in flow.pending_for(p["lead"]))

    req = flow.decide(req, p["lead"], "approve")
    req = flow.decide(req, p["director"], "return", "Aclara el costo")
    assert (req.status, req.returned_from_stage) == (St.REQUIERE_AJUSTES, Stage.DIRECCION)
    req = flow.submit_request(req, p["colab"])
    assert req.current_stage == Stage.DIRECCION  # reanuda donde se regresó (FR-009)
    req = flow.decide(req, p["director"], "approve")
    req = flow.decide(req, p["talento"], "approve", "Fondos ok")
    assert req.status == St.AUTORIZADA
    assert list(req.steps.values_list("action", flat=True)) == [
        "ENVIAR", "APROBAR", "REGRESAR", "REENVIAR", "APROBAR", "APROBAR"]

    with pytest.raises(ValidationError, match="Curso de dbt"):
        submit(p["colab"], name="Otro")  # FR-004

    req = flow.update_payment(req, p["colab"], "REEMBOLSO", "COMPRADO", Decimal("2800"), "CFDI")
    assert req.cost_overrun  # > 10 %

    req = flow.complete(req, p["colab"], learn_review_data(), [pdf()])
    assert req.status == St.COMPLETADA and req.review.rating == 5
    ev = req.evidences.get()
    flow.validate_evidence(ev, p["talento"], False, "Ilegible")
    flow.replace_evidence(ev, p["colab"], pdf("nuevo.pdf"))
    flow.validate_evidence(ev, p["talento"], True)
    req.refresh_from_db()
    assert req.status == St.VALIDADA
    assert submit(p["colab"], name="Otro").status == St.EN_REVISION  # ya no bloquea


@pytest.mark.django_db
def test_approver_resolution_and_stage_skipping(learn_people, learn_levels, learn_area):
    p = learn_people
    assert submit(p["lead"]).current_stage == Stage.DIRECCION
    assert submit(p["director"]).current_stage == Stage.TALENTO

    ux = Area.objects.create(code="UXUI", name="UX/UI")
    ux_colab = make_learn_user("ux@arena-analytics.com", area=ux, level=learn_levels["JR"])
    ux_req = submit(ux_colab)
    assert ux_req.current_stage == Stage.DIRECCION and ux_req.missing_lead

    lead2 = make_learn_user("lalo@arena-analytics.com", area=learn_area, level=learn_levels["LEAD"])
    p["colab"].direct_lead = lead2
    p["colab"].save()
    learn_area.director = p["director"]
    learn_area.save()
    other_dir = make_learn_user("otro.dir@arena-analytics.com", role="DIRECTOR")
    req = submit(p["colab"])
    assert list(flow.eligible_approvers(req, Stage.LEAD)) == [lead2]
    with pytest.raises(PermissionDenied):
        flow.decide(req, p["lead"], "approve")
    req = flow.decide(req, lead2, "approve")
    assert list(flow.eligible_approvers(req, Stage.DIRECCION)) == [p["director"]]
    with pytest.raises(PermissionDenied):
        flow.decide(req, other_dir, "approve")


@pytest.mark.django_db
def test_talento_never_self_approves(learn_people):
    p = learn_people
    req = submit(p["talento"])
    with pytest.raises(ValidationError):  # único Talento y sin superusuario → nadie autoriza
        flow.decide(req, p["director"], "approve")
    su = get_user_model().objects.create_superuser(email="su@arena-analytics.com", password=None, full_name="SU")
    req = flow.decide(CourseRequest.objects.get(pk=req.pk), p["director"], "approve")
    assert list(flow.eligible_approvers(req, Stage.TALENTO)) == [su]
    with pytest.raises(PermissionDenied):
        flow.decide(req, p["talento"], "approve")


@pytest.mark.django_db
def test_decision_errors_cancel_and_reassign(learn_people):
    p = learn_people
    req = submit(p["colab"])
    for action in ("return", "reject"):
        with pytest.raises(ValidationError):
            flow.decide(req, p["lead"], action, " ")
    for actor in (p["other"], p["director"], p["colab"]):
        with pytest.raises(PermissionDenied):
            flow.decide(req, actor, "approve")
    with pytest.raises(PermissionDenied):
        flow.reassign(req, p["lead"], p["other"], "x")
    with pytest.raises(ValidationError):
        flow.reassign(req, p["talento"], p["colab"], "a sí mismo")
    flow.reassign(req, p["talento"], p["other"], "Lead de vacaciones")
    req = flow.decide(req, p["other"], "approve")
    assert req.current_stage == Stage.DIRECCION
    req = flow.decide(req, p["director"], "reject", "No aplica")
    assert req.status == St.RECHAZADA

    step = req.steps.first()
    step.comment = "editado"
    with pytest.raises(ValueError):
        step.save()  # bitácora inmutable

    draft = flow.create_request(p["colab"], learn_request_data(name="B"))
    assert flow.cancel(draft, p["colab"]).status == St.CANCELADA
    auth = authorize(submit(p["colab"], name="C"), p)
    with pytest.raises(PermissionDenied):
        flow.cancel(auth, p["colab"])
    with pytest.raises(ValidationError):
        flow.cancel(auth, p["talento"], "")
    assert flow.cancel(auth, p["talento"], "Presupuesto").status == St.CANCELADA


@pytest.mark.django_db
def test_request_validation_and_evidence_rules(learn_people):
    p = learn_people
    with pytest.raises(ValidationError) as exc:
        flow.create_request(p["colab"], learn_request_data(justification="", start_date_planned=None), submit=True)
    assert {"justification", "start_date_planned"} <= set(exc.value.message_dict)
    with pytest.raises(ValidationError):
        submit(p["colab"], start_date_planned=date(2026, 12, 1), end_date_planned=date(2026, 11, 1))

    req = authorize(submit(p["colab"]), p)
    fake = SimpleUploadedFile("virus.pdf", b"MZ\x90 not a pdf", content_type="application/pdf")
    big = pdf("big.pdf", b"%PDF" + b"0" * (4 * 1024 * 1024 + 1))
    for files in ([], [fake], [big]):
        with pytest.raises(ValidationError):
            flow.complete(req, p["colab"], learn_review_data(), files)
    with pytest.raises(ValidationError):
        flow.complete(req, p["colab"], learn_review_data(opinion=""), [pdf()])
    assert not req.evidences.exists()  # atómico

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (3000, 1500), "white").save(buf, format="PNG")
    req = flow.complete(req, p["colab"], learn_review_data(), [SimpleUploadedFile("c.png", buf.getvalue())])
    ev = req.evidences.get()
    assert ev.mime == "image/jpeg" and max(Image.open(io.BytesIO(bytes(ev.data))).size) <= flow.MAX_IMAGE_SIDE
    with pytest.raises(ValidationError):
        flow.replace_evidence(ev, p["colab"], pdf())  # solo si fue regresada

    req2 = flow.create_request(p["colab"], learn_request_data(name="X"))
    with pytest.raises(ValidationError):
        flow.update_payment(req2, p["colab"], "REEMBOLSO", "COMPRADO")
    with pytest.raises(PermissionDenied):
        flow.update_payment(req, p["other"], "REEMBOLSO", "COMPRADO")


@pytest.mark.django_db
def test_direct_historic_catalog_and_promotion(learn_people, catalog_course, learn_area):
    p = learn_people
    direct = flow.create_direct(p["colab"], p["colab"], learn_request_data(justification=""),
                                learn_review_data(audience_areas=[learn_area]), [pdf()])
    assert direct.status == St.COMPLETADA and direct.origin == CourseRequest.Origin.REGISTRO_DIRECTO
    with pytest.raises(PermissionDenied):
        flow.create_direct(p["other"], p["colab"], learn_request_data(), learn_review_data(), [pdf()],
                           origin=CourseRequest.Origin.HISTORICO)
    with pytest.raises(ValidationError):
        flow.create_direct(p["colab"], p["colab"], learn_request_data(name="Sin evidencia"), learn_review_data(), [])
    hist = flow.create_direct(p["other"], p["talento"], {}, learn_review_data(rating=2), [pdf()],
                              origin=CourseRequest.Origin.HISTORICO, catalog_course=catalog_course)
    assert hist.name == catalog_course.name

    catalog_course.areas.add(learn_area)
    flow.create_direct(p["colab"], p["colab"], {}, learn_review_data(rating=4), [pdf()], catalog_course=catalog_course)
    c = flow.catalog_queryset({"area": learn_area.pk}).get()
    assert c.completed_count == 2 and float(c.avg_rating) == 3.0

    with pytest.raises(PermissionDenied):
        flow.promote_to_catalog(direct, p["colab"])
    course = flow.promote_to_catalog(direct, p["talento"])
    assert list(course.areas.all()) == [learn_area] and list(flow.catalog_reviews(course)) == [direct.review]

    catalog_course.is_active = False
    catalog_course.save()
    assert list(flow.catalog_queryset()) == [course]
    with pytest.raises(ValidationError):
        flow.create_request(p["colab"], learn_request_data(), catalog_course=catalog_course)


@pytest.mark.django_db
def test_dashboard_alerts_and_export(learn_people):
    p = learn_people
    monday = date(2026, 10, 5)
    assert flow.business_days_between(monday, monday + timedelta(days=7)) == 5
    stale = submit(p["colab"])
    ApprovalStep.objects.filter(request=stale).update(created_at=timezone.now() - timedelta(days=12))
    overdue = authorize(submit(p["other"], start_date_planned=date(2025, 1, 1), end_date_planned=date(2025, 2, 1)), p)
    data = flow.dashboard_rows({})
    rows = {r["req"].pk: r for r in data["rows"]}
    assert rows[stale.pk]["stale"] and rows[overdue.pk]["overdue"]
    assert (data["stale_count"], data["overdue_count"]) == (1, 1)
    assert [c["total"] for c in data["cost_by_area"]] == [Decimal("2500.00")]
    assert len(flow.export_rows({})) == 2


@pytest.mark.django_db
def test_visibility_public_vs_private(learn_people):
    p = learn_people
    assert list(permissions.visible_users(p["colab"])) == [p["colab"]]  # RN-14 intacta
    in_review = submit(p["colab"], name="En revisión")
    assert not permissions.can_view_course_public(p["other"], in_review)
    assert permissions.can_view_course_private(p["lead"], in_review)  # aprobador elegible

    flow.mark_not_completed(authorize(in_review, p), p["colab"], "Cambio de prioridades")
    req = closed(p)
    assert permissions.can_view_course_public(p["other"], req)
    assert not permissions.can_view_course_private(p["other"], req)
    assert all(permissions.can_view_course_private(p[w], req) for w in ("colab", "lead", "director", "talento"))

    flow.add_evidence(req, p["colab"], pdf("cfdi.pdf"), CourseEvidence.Kind.COMPROBANTE_FISCAL)
    ctx = flow.public_course_context(req)
    assert {"estimated_cost", "final_cost", "justification", "payment_mode", "steps"}.isdisjoint(ctx)
    assert len(ctx["certificates"]) == 1  # el comprobante fiscal nunca es público
    assert [r.pk for r in flow.learning_public_requests(p["colab"])] == [req.pk]


# --- Vistas --------------------------------------------------------------------------------


@pytest.mark.django_db
def test_views_render_and_request_via_form(client, learn_people, catalog_course):
    p = learn_people
    client.force_login(p["colab"])
    for name, kw in [("my_courses", {}), ("request_create", {}), ("direct_create", {}), ("catalog_list", {}),
                     ("catalog_detail", {"pk": catalog_course.pk}), ("people_list", {}),
                     ("person_profile", {"pk": p["other"].pk}), ("approvals_inbox", {})]:
        assert client.get(reverse(f"learning:{name}", kwargs=kw)).status_code == 200, name

    url = reverse("learning:request_create") + f"?catalogo={catalog_course.pk}"
    resp = client.post(url, {
        "catalogo": catalog_course.pk, "estimated_cost": "3500", "currency": "MXN", "kind": "CURSO",
        "start_date_planned": "2026-10-10", "end_date_planned": "2026-11-10",
        "justification": "Spark para el proyecto Y", "payment_mode": "REEMBOLSO", "action": "submit",
    })
    req = CourseRequest.objects.get()
    assert resp.status_code == 302 and req.catalog_course == catalog_course
    assert (req.name, req.status, req.payment_mode) == (catalog_course.name, St.EN_REVISION, "REEMBOLSO")

    client.force_login(p["lead"])
    assert "solicitud de curso por aprobar" in client.get(reverse("learning:approvals_inbox")).content.decode()
    client.post(reverse("learning:request_decide", args=[req.pk]), {"action": "return", "comment": ""})
    req.refresh_from_db()
    assert req.current_stage == Stage.LEAD  # sin comentario no se regresa
    client.post(reverse("learning:request_decide", args=[req.pk]), {"action": "approve"})
    req.refresh_from_db()
    assert req.current_stage == Stage.DIRECCION


@pytest.mark.django_db
def test_views_access_control(client, learn_people, catalog_course):
    p = learn_people
    review = submit(p["colab"])
    req = closed(p, name="Cerrado")
    receipt = flow.add_evidence(req, p["colab"], pdf("cfdi.pdf"), CourseEvidence.Kind.COMPROBANTE_FISCAL)
    cert = req.evidences.get(kind=CourseEvidence.Kind.CERTIFICADO)

    client.force_login(p["other"])
    assert client.get(reverse("learning:request_detail", args=[review.pk])).status_code == 403
    assert client.get(reverse("learning:request_edit", args=[review.pk])).status_code == 403
    assert client.get(reverse("learning:course_public", args=[review.pk])).status_code == 404
    assert client.post(reverse("learning:request_decide", args=[review.pk]), {"action": "approve"}).status_code == 403
    ok = client.get(reverse("learning:evidence_file", args=[cert.pk]))
    assert ok.status_code == 200 and ok.content == PDF
    assert client.get(reverse("learning:evidence_file", args=[receipt.pk])).status_code == 403
    for name in ("tracking", "tracking_export", "catalog_create", "historic_create", "settings_edit"):
        assert client.get(reverse(f"learning:{name}")).status_code == 403, name

    for who in ("talento", "director"):
        client.force_login(p[who])
        assert client.get(reverse("learning:tracking")).status_code == 200
        assert client.get(reverse("learning:tracking_export"))["Content-Type"].startswith(
            "application/vnd.openxmlformats")
    assert client.get(reverse("learning:evidence_file", args=[receipt.pk])).status_code == 403  # Director
    client.force_login(p["talento"])
    assert client.get(reverse("learning:evidence_file", args=[receipt.pk])).status_code == 200


@pytest.mark.django_db
def test_views_close_payment_and_public_profile(client, learn_people):
    p = learn_people
    req = authorize(submit(p["colab"], justification="SECRETO-JUST", estimated_cost=Decimal("98765.43")), p)
    client.force_login(p["colab"])
    resp = client.post(reverse("learning:request_payment", args=[req.pk]),
                       {"payment_mode": "PAGO_DIRECTO", "payment_status": "COMPRADO", "final_cost": "",
                        "receipt_type": "CFDI"}, HTTP_HX_REQUEST="true")
    assert 'id="payment-block"' in resp.content.decode()

    url = reverse("learning:request_complete", args=[req.pk])
    review = {"r-rating": "4", "r-opinion": "Bueno", "r-recommends": "SI", "r-recommend_why": "Práctico",
              "r-learnings": "DAGs", "r-audience_notes": ""}
    resp = client.post(url, {**review, "files": pdf("big.pdf", b"%PDF" + b"0" * (4 * 1024 * 1024 + 10))})
    assert resp.status_code == 200 and "4 MB" in resp.content.decode()
    assert client.post(url, {**review, "files": pdf()}).status_code == 302
    req.refresh_from_db()
    assert (req.status, req.payment_mode) == (St.COMPLETADA, "PAGO_DIRECTO")

    client.force_login(p["other"])
    for u in (reverse("learning:person_profile", args=[p["colab"].pk]), reverse("learning:course_public", args=[req.pk])):
        html = client.get(u).content.decode()
        assert req.name in html and "SECRETO-JUST" not in html and "98765" not in html and "98,765" not in html


@pytest.mark.django_db
def test_admin_screens_lead_and_director(client, learn_people, learn_area):
    p = learn_people
    colab = p["colab"]
    client.force_login(p["colab"])
    assert client.get(reverse("catalog:area_admin")).status_code == 403
    client.force_login(p["talento"])
    post = {f"area-{colab.id}": "CD", f"level-{colab.id}": "JR", f"role-{colab.id}": "COLABORADOR",
            f"lead-{colab.id}": str(p["lead"].id)}
    client.post(reverse("accounts:user_admin"), post)
    colab.refresh_from_db()
    assert colab.direct_lead == p["lead"]
    client.post(reverse("accounts:user_admin"), {**post, f"lead-{colab.id}": str(colab.id)})
    colab.refresh_from_db()
    assert colab.direct_lead is None  # nunca su propio Lead

    client.post(reverse("catalog:area_admin"), {"area": learn_area.pk, "director": p["director"].pk})
    client.post(reverse("catalog:area_admin"), {"area": learn_area.pk, "director": colab.pk})  # no es Director
    learn_area.refresh_from_db()
    assert learn_area.director == p["director"]
    assert client.get(reverse("catalog:area_admin")).status_code == 200


@pytest.mark.django_db
def test_request_start_lists_known_courses_and_blocks_duplicates(client, learn_people, catalog_course):
    """Solicitar curso: elegir del catálogo o de lo ya autorizado en Arena; sin pedir dos veces lo mismo."""
    p = learn_people
    taken = authorize(submit(p["other"], name="Curso de dbt"), p)
    flow.update_payment(taken, p["other"], "REEMBOLSO", "COMPRADO")

    data = flow.requestable_courses(p["colab"])
    assert [c["course"] for c in data["catalog"]] == [catalog_course]
    [known] = data["known"]
    assert known["template"] == taken and known["count"] == 1 and known["payment_mode"] == "Reembolso al colaborador"
    assert known["mine"] is None

    client.force_login(p["colab"])
    html = client.get(reverse("learning:request_start")).content.decode()
    assert "Curso de dbt" in html and catalog_course.name in html and "Es un curso nuevo" in html
    html = client.get(reverse("learning:request_create") + f"?desde={taken.pk}").content.decode()
    assert "Curso ya autorizado en Arena" in html and 'value="dbt Labs"' in html
    assert "Modelado de datos" not in html  # nunca se copia la justificación ajena

    mine = submit(p["colab"], name="curso de DBT ")  # mismo curso, otra capitalización
    assert flow.requestable_courses(p["colab"])["known"][0]["mine"] == mine
    with pytest.raises(ValidationError, match="Ya tienes este curso"):
        submit(p["colab"], name="Curso de dbt")
