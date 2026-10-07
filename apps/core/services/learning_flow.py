"""Arena Learn (spec 004-arena-learn-cursos).

Orquesta el ciclo de vida de una solicitud de curso:
- Solicitud (desde catálogo o nueva) → autorización secuencial Lead → Dirección → Talento,
  con omisión automática de etapas y bitácora inmutable (`ApprovalStep`).
- Registro (no gestión) de la modalidad de pago.
- Cierre con evidencia (archivos en BD, máx. 4 MB) y reseña; validación de Talento.
- Consultas de solo lectura para el perfil público, catálogo, campana y tablero.

Las vistas solo validan con un Form, llaman a estas funciones y renderizan.
"""

from __future__ import annotations

import io
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg, Count, Q, QuerySet, Sum
from django.urls import reverse
from django.utils import timezone

from apps.core.services import permissions

User = get_user_model()

MAX_EVIDENCE_BYTES = 4 * 1024 * 1024  # Vercel limita el cuerpo del request a 4.5 MB.
MAX_IMAGE_SIDE = 2000
STALE_BUSINESS_DAYS = 5
OVERDUE_DAYS = 30


def _models():
    from apps.learning import models as m

    return m


def _stage_order():
    S = _models().CourseRequest.Stage
    return [S.LEAD, S.DIRECCION, S.TALENTO]


# --- Bitácora -----------------------------------------------------------------


def _log_step(req, stage, actor, action, from_status, to_status, comment="", assigned_to=None):
    return _models().ApprovalStep.objects.create(
        request=req,
        stage=stage,
        actor=actor,
        action=action,
        from_status=from_status or "",
        to_status=to_status or "",
        comment=comment or "",
        assigned_to=assigned_to,
    )


def _active_users() -> QuerySet:
    return User.objects.filter(is_active=True, deleted_at__isnull=True)


# --- Aprobadores (research R2) ---------------------------------------------------


def eligible_approvers(req, stage) -> QuerySet:
    """Usuarios que pueden decidir `req` en `stage`. Nunca incluye al solicitante."""
    m = _models()
    S = m.CourseRequest.Stage
    requester = req.user
    active = _active_users().exclude(pk=requester.pk)

    reassigned = (
        m.ApprovalStep.objects.filter(
            request=req, stage=stage, action=m.ApprovalStep.Action.REASIGNAR,
        )
        .order_by("-created_at", "-pk")
        .first()
    )
    if reassigned and reassigned.assigned_to_id:
        explicit = active.filter(pk=reassigned.assigned_to_id)
        if explicit.exists():
            return explicit

    if stage == S.LEAD:
        if requester.direct_lead_id:
            direct = active.filter(pk=requester.direct_lead_id)
            if direct.exists():
                return direct
        if not requester.area_id:
            return active.none()
        return active.filter(area_id=requester.area_id, level__code="LEAD")

    if stage == S.DIRECCION:
        area = requester.area
        if area is not None and area.director_id:
            director = active.filter(pk=area.director_id, role=User.Role.DIRECTOR)
            if director.exists():
                return director
        return active.filter(role=User.Role.DIRECTOR)

    if stage == S.TALENTO:
        return active.filter(Q(role=User.Role.TALENTO) | Q(is_superuser=True))

    return active.none()


def _stage_skipped_by_role(req, stage) -> bool:
    """El solicitante sería su propio aprobador en esta etapa (FR-005)."""
    S = _models().CourseRequest.Stage
    u = req.user
    if stage == S.LEAD:
        return u.is_lead or u.is_director or u.is_admin
    if stage == S.DIRECCION:
        return u.is_director
    return False


def _enter_stage(req, start_stage, actor):
    """Coloca `req` en la primera etapa aplicable desde `start_stage` (con omisiones)."""
    m = _models()
    S = m.CourseRequest.Stage
    St = m.CourseRequest.Status
    A = m.ApprovalStep.Action
    order = _stage_order()
    for stage in order[order.index(start_stage):]:
        if _stage_skipped_by_role(req, stage):
            _log_step(req, stage, None, A.OMITIR, req.status, req.status,
                      "El solicitante no puede aprobar su propia solicitud.")
            continue
        if not eligible_approvers(req, stage).exists():
            if stage == S.TALENTO:
                raise ValidationError("No hay ningún usuario de Talento disponible para autorizar.")
            if stage == S.LEAD:
                req.missing_lead = True
                comment = "El colaborador no tiene Lead asignado."
            else:
                comment = "No hay Director disponible."
            _log_step(req, stage, None, A.OMITIR, req.status, req.status, comment)
            continue
        req.status = St.EN_REVISION
        req.current_stage = stage
        return stage
    raise ValidationError("No fue posible asignar la solicitud a ninguna etapa.")


# --- Reglas de solicitud ----------------------------------------------------------


def pending_closure(user):
    """Curso autorizado (solicitud) del usuario aún sin cerrar (FR-004), o None."""
    m = _models()
    return (
        m.CourseRequest.objects.filter(
            user=user, status=m.CourseRequest.Status.AUTORIZADA,
            origin=m.CourseRequest.Origin.SOLICITUD,
        )
        .order_by("authorized_at")
        .first()
    )


def assert_can_submit(user):
    pending = pending_closure(user)
    if pending is not None:
        raise ValidationError(
            f"Antes de solicitar otro curso, cierra «{pending.name}»: sube tu evidencia y reseña "
            "o márcalo como no concluido."
        )


COURSE_FIELDS = (
    "name", "provider", "url", "kind", "duration_hours", "pillar", "tags",
    "estimated_cost", "currency", "start_date_planned", "end_date_planned", "justification",
)
CATALOG_SNAPSHOT = ("name", "provider", "url", "kind", "duration_hours", "pillar", "tags", "currency")


def _validate_request_data(req):
    errors = {}
    if req.origin == req.Origin.SOLICITUD:
        for field, label in (
            ("name", "el nombre del curso"), ("provider", "el proveedor"),
            ("start_date_planned", "la fecha tentativa de inicio"),
            ("end_date_planned", "la fecha tentativa de fin"),
            ("justification", "la justificación"),
        ):
            value = getattr(req, field)
            if value in (None, "") or (isinstance(value, str) and not value.strip()):
                errors[field] = f"Falta {label}."
    if req.start_date_planned and req.end_date_planned and req.end_date_planned < req.start_date_planned:
        errors["end_date_planned"] = "La fecha de fin no puede ser anterior a la de inicio."
    if req.estimated_cost is not None and req.estimated_cost < 0:
        errors["estimated_cost"] = "El costo no puede ser negativo."
    if errors:
        raise ValidationError(errors)


def _apply_data(req, data, catalog_course=None):
    from apps.learning.models import normalize_tags

    for field in COURSE_FIELDS:
        if field in data:
            setattr(req, field, data[field] if data[field] is not None else _blank_for(field))
    if catalog_course is not None:
        req.catalog_course = catalog_course
        for field in CATALOG_SNAPSHOT:
            setattr(req, field, getattr(catalog_course, field))
        if data.get("estimated_cost") is None and catalog_course.reference_cost is not None:
            req.estimated_cost = catalog_course.reference_cost
    req.tags = normalize_tags(req.tags)
    req.name = " ".join((req.name or "").split())
    req.provider = " ".join((req.provider or "").split())


def _blank_for(field):
    return None if field in (
        "duration_hours", "estimated_cost", "start_date_planned", "end_date_planned",
    ) else ""


@transaction.atomic
def create_request(user, data: dict, catalog_course=None, submit=False):
    """Crea una solicitud en BORRADOR; con `submit=True` la envía de inmediato."""
    m = _models()
    if catalog_course is not None and not catalog_course.is_active:
        raise ValidationError("Ese curso del catálogo ya no está disponible.")
    req = m.CourseRequest(user=user, origin=m.CourseRequest.Origin.SOLICITUD)
    _apply_data(req, data, catalog_course)
    if submit:
        _validate_request_data(req)
    req.save()
    if submit:
        req = submit_request(req, user)
    return req


@transaction.atomic
def update_request(req, actor, data: dict, submit=False):
    """El dueño edita su solicitud en BORRADOR o REQUIERE_AJUSTES."""
    req = _locked(req)
    if req.user_id != actor.pk:
        raise PermissionDenied("Solo quien hizo la solicitud puede editarla.")
    if not req.is_editable:
        raise ValidationError("Esta solicitud ya no se puede editar.")
    _apply_data(req, data, req.catalog_course if req.catalog_course_id else None)
    if submit:
        _validate_request_data(req)
    req.save()
    if submit:
        req = submit_request(req, actor)
    return req


def _locked(req):
    """Recarga `req` con bloqueo de fila. `of=("self",)`: Postgres no permite FOR UPDATE
    sobre el lado nullable de un outer join (área/nivel del usuario)."""
    return _models().CourseRequest.objects.select_for_update(of=("self",)).select_related(
        "user", "user__area", "user__level",
    ).get(pk=req.pk)


@transaction.atomic
def submit_request(req, actor):
    """BORRADOR/REQUIERE_AJUSTES → EN_REVISION (en la etapa que corresponda)."""
    m = _models()
    St = m.CourseRequest.Status
    A = m.ApprovalStep.Action
    req = _locked(req)
    if req.user_id != actor.pk:
        raise PermissionDenied("Solo quien hizo la solicitud puede enviarla.")
    if req.status not in (St.BORRADOR, St.REQUIERE_AJUSTES):
        raise ValidationError("Esta solicitud ya fue enviada.")
    _validate_request_data(req)
    assert_can_submit(req.user)
    dup = open_request_for(req.user, req.catalog_course if req.catalog_course_id else None,
                           req.name, req.provider, exclude_pk=req.pk)
    if dup is not None:
        raise ValidationError(f"Ya tienes este curso pedido («{dup.name}», {dup.status_display.lower()}).")

    from_status = req.status
    resuming = from_status == St.REQUIERE_AJUSTES and req.returned_from_stage
    start = req.returned_from_stage if resuming else m.CourseRequest.Stage.LEAD
    _log_step(req, m.ApprovalStep.Stage.COLABORADOR, actor,
              A.REENVIAR if resuming else A.ENVIAR, from_status, St.EN_REVISION)
    if not resuming:
        req.missing_lead = False
    _enter_stage(req, start, actor)
    req.returned_from_stage = ""
    req.submitted_at = req.submitted_at or timezone.now()
    req.save()
    _notify_stage(req)
    return req


# --- Decisiones -------------------------------------------------------------------


def can_decide(user, req) -> bool:
    St = _models().CourseRequest.Status
    if req.status != St.EN_REVISION or not req.current_stage:
        return False
    return eligible_approvers(req, req.current_stage).filter(pk=user.pk).exists()


@transaction.atomic
def decide(req, actor, action: str, comment: str = ""):
    """`action` ∈ {approve, return, reject}. Regresar/rechazar exige comentario."""
    m = _models()
    St = m.CourseRequest.Status
    A = m.ApprovalStep.Action
    req = _locked(req)
    if not can_decide(actor, req):
        raise PermissionDenied("No te corresponde decidir esta solicitud en su etapa actual.")
    comment = (comment or "").strip()
    stage = req.current_stage
    from_status = req.status

    if action == "approve":
        order = _stage_order()
        idx = order.index(stage)
        if idx == len(order) - 1:
            req.status = St.AUTORIZADA
            req.current_stage = ""
            req.authorized_at = timezone.now()
            _log_step(req, stage, actor, A.APROBAR, from_status, St.AUTORIZADA, comment)
            req.save()
            _notify_owner(req, "autorizada", comment)
            return req
        _log_step(req, stage, actor, A.APROBAR, from_status, St.EN_REVISION, comment)
        _enter_stage(req, order[idx + 1], actor)
        req.save()
        _notify_stage(req)
        return req

    if action in ("return", "reject"):
        if not comment:
            raise ValidationError(
                "Escribe un comentario para regresar la solicitud."
                if action == "return" else "Escribe el motivo del rechazo."
            )
        if action == "return":
            req.status = St.REQUIERE_AJUSTES
            req.returned_from_stage = stage
            req.current_stage = ""
            _log_step(req, stage, actor, A.REGRESAR, from_status, St.REQUIERE_AJUSTES, comment)
            req.save()
            _notify_owner(req, "regresada con comentarios", comment)
        else:
            req.status = St.RECHAZADA
            req.current_stage = ""
            req.closed_at = timezone.now()
            _log_step(req, stage, actor, A.RECHAZAR, from_status, St.RECHAZADA, comment)
            req.save()
            _notify_owner(req, "rechazada", comment)
        return req

    raise ValidationError("Acción no reconocida.")


@transaction.atomic
def cancel(req, actor, comment: str = ""):
    """Dueño: antes de autorizarse. Talento: también autorizada (con motivo)."""
    m = _models()
    St = m.CourseRequest.Status
    req = _locked(req)
    comment = (comment or "").strip()
    owner_cancellable = (St.BORRADOR, St.EN_REVISION, St.REQUIERE_AJUSTES)
    if req.user_id == actor.pk and req.status in owner_cancellable:
        stage = m.ApprovalStep.Stage.COLABORADOR
    elif actor.is_admin and req.status in (*owner_cancellable, St.AUTORIZADA):
        if not comment:
            raise ValidationError("Escribe el motivo de la cancelación.")
        stage = m.ApprovalStep.Stage.TALENTO
    else:
        raise PermissionDenied("No puedes cancelar esta solicitud.")
    from_status = req.status
    req.status = St.CANCELADA
    req.current_stage = ""
    req.closed_at = timezone.now()
    _log_step(req, stage, actor, m.ApprovalStep.Action.CANCELAR, from_status, St.CANCELADA, comment)
    req.save()
    if req.user_id != actor.pk:
        _notify_owner(req, "cancelada", comment)
    return req


@transaction.atomic
def reassign(req, actor, new_approver, comment: str = ""):
    """Talento asigna explícitamente al aprobador de la etapa actual (FR-013)."""
    m = _models()
    req = _locked(req)
    if not actor.is_admin:
        raise PermissionDenied("Solo Talento puede reasignar aprobadores.")
    if req.status != m.CourseRequest.Status.EN_REVISION or not req.current_stage:
        raise ValidationError("Solo se reasignan solicitudes en revisión.")
    comment = (comment or "").strip()
    if not comment:
        raise ValidationError("Escribe el motivo de la reasignación.")
    if new_approver.pk == req.user_id:
        raise ValidationError("El solicitante no puede aprobar su propia solicitud.")
    if not _active_users().filter(pk=new_approver.pk).exists():
        raise ValidationError("El aprobador elegido no está activo.")
    _log_step(req, req.current_stage, actor, m.ApprovalStep.Action.REASIGNAR,
              req.status, req.status, comment, assigned_to=new_approver)
    _notify_stage(req)
    return req


# --- Pago (registro, no gestión) ----------------------------------------------------


@transaction.atomic
def update_payment(req, actor, payment_mode, payment_status, final_cost=None, receipt_type=""):
    m = _models()
    St = m.CourseRequest.Status
    req = _locked(req)
    if not (req.user_id == actor.pk or actor.is_admin):
        raise PermissionDenied("No puedes registrar el pago de esta solicitud.")
    if req.status not in (St.AUTORIZADA, St.COMPLETADA, St.VALIDADA):
        raise ValidationError("El pago se registra una vez autorizado el curso.")
    if final_cost is not None and final_cost < 0:
        raise ValidationError("El costo final no puede ser negativo.")
    req.payment_mode = payment_mode or ""
    req.payment_status = payment_status or ""
    req.final_cost = final_cost
    req.receipt_type = receipt_type or ""
    req.save(update_fields=["payment_mode", "payment_status", "final_cost", "receipt_type", "updated_at"])
    return req


# --- Evidencia ---------------------------------------------------------------------


_MAGIC = (
    (b"%PDF", "application/pdf"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
)


def _sniff_mime(head: bytes) -> str | None:
    for magic, mime in _MAGIC:
        if head.startswith(magic):
            return mime
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def process_upload(uploaded_file) -> tuple[bytes, str, str]:
    """Valida tipo (magic bytes) y tamaño; re-encoda imágenes. Devuelve (data, mime, filename)."""
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > MAX_EVIDENCE_BYTES:
        raise ValidationError("El archivo pesa más de 4 MB. Comprímelo o sube una captura.")
    data = uploaded_file.read()
    if len(data) > MAX_EVIDENCE_BYTES:
        raise ValidationError("El archivo pesa más de 4 MB. Comprímelo o sube una captura.")
    if not data:
        raise ValidationError("El archivo está vacío.")
    mime = _sniff_mime(data[:16])
    if mime is None:
        raise ValidationError("Formato no permitido. Sube un PDF o una imagen (PNG, JPG o WEBP).")
    filename = (getattr(uploaded_file, "name", "") or "evidencia").rsplit("/", 1)[-1][:200]
    if mime.startswith("image/"):
        data, mime, filename = _reencode_image(data, mime, filename)
    return data, mime, filename


def _reencode_image(data: bytes, mime: str, filename: str) -> tuple[bytes, str, str]:
    from PIL import Image, ImageOps

    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
    except Exception as exc:  # imagen corrupta
        raise ValidationError("No pudimos leer la imagen. Intenta con otro archivo.") from exc
    img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
    out = io.BytesIO()
    if img.mode in ("RGBA", "LA", "P"):
        img.convert("RGBA").save(out, format="WEBP", quality=85)
        new_mime, ext = "image/webp", "webp"
    else:
        img.convert("RGB").save(out, format="JPEG", quality=85, optimize=True)
        new_mime, ext = "image/jpeg", "jpg"
    base = filename.rsplit(".", 1)[0] or "evidencia"
    return out.getvalue(), new_mime, f"{base}.{ext}"


def _create_evidence(req, actor, uploaded_file, kind):
    data, mime, filename = process_upload(uploaded_file)
    return _models().CourseEvidence.objects.create(
        request=req, kind=kind, filename=filename, mime=mime, size=len(data),
        data=data, uploaded_by=actor,
    )


@transaction.atomic
def add_evidence(req, actor, uploaded_file, kind=None):
    m = _models()
    Kind = m.CourseEvidence.Kind
    kind = kind or Kind.CERTIFICADO
    req = _locked(req)
    if not (req.user_id == actor.pk or actor.is_admin):
        raise PermissionDenied("No puedes subir evidencia a esta solicitud.")
    St = m.CourseRequest.Status
    allowed = (St.AUTORIZADA, St.COMPLETADA, St.VALIDADA)
    if req.status not in allowed:
        raise ValidationError("Solo se sube evidencia a cursos autorizados.")
    return _create_evidence(req, actor, uploaded_file, kind)


@transaction.atomic
def replace_evidence(evidence, actor, uploaded_file):
    """Reemplaza un certificado regresado por Talento (US4-AS3)."""
    m = _models()
    ev = m.CourseEvidence.objects.select_for_update(of=("self",)).select_related("request").get(pk=evidence.pk)
    req = ev.request
    if req.user_id != actor.pk:
        raise PermissionDenied("Solo el dueño puede reemplazar su evidencia.")
    if ev.validation != m.CourseEvidence.Validation.REGRESADA:
        raise ValidationError("Solo se reemplaza una evidencia regresada por Talento.")
    data, mime, filename = process_upload(uploaded_file)
    ev.data, ev.mime, ev.filename, ev.size = data, mime, filename, len(data)
    ev.validation = m.CourseEvidence.Validation.PENDIENTE
    ev.validation_comment = ""
    ev.save()
    _log_step(req, m.ApprovalStep.Stage.COLABORADOR, actor,
              m.ApprovalStep.Action.REEMPLAZAR_EVIDENCIA, req.status, req.status)
    return ev


def _save_review(req, review_data: dict):
    m = _models()
    required = ("rating", "opinion", "recommends", "recommend_why", "learnings")
    missing = [f for f in required if review_data.get(f) in (None, "")]
    if missing:
        raise ValidationError("Completa tu reseña: calificación, opinión, recomendación y aprendizajes.")
    rating = int(review_data["rating"])
    if not 1 <= rating <= 5:
        raise ValidationError("La calificación debe ser de 1 a 5.")
    review, _ = m.CourseReview.objects.update_or_create(
        request=req,
        defaults={
            "rating": rating,
            "opinion": review_data["opinion"],
            "recommends": review_data["recommends"],
            "recommend_why": review_data["recommend_why"],
            "audience_notes": review_data.get("audience_notes", "") or "",
            "learnings": review_data["learnings"],
        },
    )
    review.audience_areas.set(review_data.get("audience_areas") or [])
    review.audience_levels.set(review_data.get("audience_levels") or [])
    return review


@transaction.atomic
def complete(req, actor, review_data: dict, files=()):
    """AUTORIZADA → COMPLETADA con evidencia (≥1 certificado) y reseña. Atómico."""
    m = _models()
    St = m.CourseRequest.Status
    Kind = m.CourseEvidence.Kind
    req = _locked(req)
    if req.user_id != actor.pk:
        raise PermissionDenied("Solo el dueño puede cerrar su curso.")
    if req.status != St.AUTORIZADA:
        raise ValidationError("Solo se cierra un curso en curso (autorizado).")
    for f in files or ():
        _create_evidence(req, actor, f, Kind.CERTIFICADO)
    if not req.evidences.filter(kind=Kind.CERTIFICADO).exists():
        raise ValidationError("Sube al menos un certificado, constancia o captura que avale el curso.")
    _save_review(req, review_data)
    from_status = req.status
    req.status = St.COMPLETADA
    req.closed_at = timezone.now()
    _log_step(req, m.ApprovalStep.Stage.COLABORADOR, actor, m.ApprovalStep.Action.COMPLETAR,
              from_status, St.COMPLETADA)
    req.save()
    _notify_talento(req, "tiene evidencia por validar")
    return req


@transaction.atomic
def update_review(req, actor, review_data: dict):
    """El dueño ajusta su reseña de un curso ya cerrado."""
    m = _models()
    req = _locked(req)
    if req.user_id != actor.pk:
        raise PermissionDenied("Solo el dueño puede editar su reseña.")
    if req.status not in (m.CourseRequest.Status.COMPLETADA, m.CourseRequest.Status.VALIDADA):
        raise ValidationError("Solo se edita la reseña de un curso completado.")
    return _save_review(req, review_data)


@transaction.atomic
def mark_not_completed(req, actor, reason: str):
    m = _models()
    St = m.CourseRequest.Status
    req = _locked(req)
    if req.user_id != actor.pk:
        raise PermissionDenied("Solo el dueño puede marcar su curso como no concluido.")
    if req.status != St.AUTORIZADA:
        raise ValidationError("Solo un curso en curso puede marcarse como no concluido.")
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("Escribe el motivo por el que no concluiste el curso.")
    from_status = req.status
    req.status = St.NO_CONCLUIDA
    req.not_completed_reason = reason
    req.closed_at = timezone.now()
    _log_step(req, m.ApprovalStep.Stage.COLABORADOR, actor, m.ApprovalStep.Action.NO_CONCLUIR,
              from_status, St.NO_CONCLUIDA, reason)
    req.save()
    return req


@transaction.atomic
def validate_evidence(evidence, actor, approve: bool, comment: str = ""):
    """Talento valida o regresa un certificado; si todos quedan validados → VALIDADA."""
    m = _models()
    V = m.CourseEvidence.Validation
    St = m.CourseRequest.Status
    A = m.ApprovalStep.Action
    if not actor.is_admin:
        raise PermissionDenied("Solo Talento valida evidencias.")
    ev = m.CourseEvidence.objects.select_for_update().get(pk=evidence.pk)
    req = _locked(ev.request)
    if ev.kind != m.CourseEvidence.Kind.CERTIFICADO:
        raise ValidationError("Solo se validan certificados.")
    if req.status not in (St.COMPLETADA, St.VALIDADA):
        raise ValidationError("El curso aún no se ha cerrado.")
    comment = (comment or "").strip()
    if not approve and not comment:
        raise ValidationError("Escribe qué hay que corregir en la evidencia.")
    ev.validation = V.VALIDADA if approve else V.REGRESADA
    ev.validation_comment = comment
    ev.save(update_fields=["validation", "validation_comment"])

    from_status = req.status
    certs = req.evidences.filter(kind=m.CourseEvidence.Kind.CERTIFICADO)
    if approve and not certs.exclude(validation=V.VALIDADA).exists():
        req.status = St.VALIDADA
    elif not approve:
        req.status = St.COMPLETADA
    _log_step(req, m.ApprovalStep.Stage.TALENTO, actor,
              A.VALIDAR_EVIDENCIA if approve else A.REGRESAR_EVIDENCIA, from_status, req.status, comment)
    req.save()
    if not approve:
        _notify_owner(req, "tiene la evidencia regresada", comment)
    return ev


# --- Registro directo e histórico (FR-022, FR-032) -------------------------------------


@transaction.atomic
def create_direct(user, actor, data: dict, review_data: dict, files, origin=None, catalog_course=None):
    """Curso gratuito/pagado por el colaborador (o histórico de Talento) ya completado."""
    m = _models()
    O = m.CourseRequest.Origin
    origin = origin or O.REGISTRO_DIRECTO
    if origin == O.HISTORICO:
        if not actor.is_admin:
            raise PermissionDenied("Solo Talento carga cursos históricos.")
    elif user.pk != actor.pk:
        raise PermissionDenied("Solo puedes registrar tus propios cursos.")
    if origin == O.SOLICITUD:
        raise ValidationError("Origen inválido para un registro directo.")
    req = m.CourseRequest(user=user, origin=origin)
    _apply_data(req, data, catalog_course)
    if not (req.name or "").strip() or not (req.provider or "").strip():
        raise ValidationError("Indica el nombre del curso y el proveedor.")
    _validate_request_data(req)
    req.status = m.CourseRequest.Status.COMPLETADA
    req.closed_at = timezone.now()
    req.save()
    for f in files or ():
        _create_evidence(req, actor, f, m.CourseEvidence.Kind.CERTIFICADO)
    if not req.evidences.exists():
        raise ValidationError("Sube al menos un certificado, constancia o captura que avale el curso.")
    _save_review(req, review_data)
    _log_step(req, m.ApprovalStep.Stage.TALENTO if origin == O.HISTORICO else m.ApprovalStep.Stage.COLABORADOR,
              actor, m.ApprovalStep.Action.REGISTRAR, "", req.status)
    return req


# --- Catálogo ----------------------------------------------------------------------


def catalog_queryset(filters: dict | None = None, include_archived=False) -> QuerySet:
    """Catálogo con agregados (sin N+1): personas que lo completaron y rating promedio."""
    m = _models()
    St = m.CourseRequest.Status
    done = Q(requests__status__in=(St.COMPLETADA, St.VALIDADA))
    qs = m.CatalogCourse.objects.annotate(
        completed_count=Count("requests__user", filter=done, distinct=True),
        avg_rating=Avg("requests__review__rating", filter=done),
    ).prefetch_related("areas", "levels")
    if not include_archived:
        qs = qs.filter(is_active=True)
    f = filters or {}
    if f.get("q"):
        q = f["q"].strip()
        qs = qs.filter(Q(name__icontains=q) | Q(provider__icontains=q) | Q(tags__icontains=q))
    if f.get("area"):
        qs = qs.filter(areas__pk=f["area"])
    if f.get("level"):
        qs = qs.filter(levels__pk=f["level"])
    if f.get("kind"):
        qs = qs.filter(kind=f["kind"])
    if f.get("pillar"):
        qs = qs.filter(pillar=f["pillar"])
    return qs.distinct().order_by("name")


def catalog_reviews(course) -> QuerySet:
    """Reseñas públicas asociadas a un curso del catálogo."""
    m = _models()
    return (
        m.CourseReview.objects.filter(
            request__catalog_course=course,
            request__status__in=m.CourseRequest.PUBLIC_STATUSES,
        )
        .select_related("request__user", "request__user__area")
        .order_by("-created_at")
    )


@transaction.atomic
def promote_to_catalog(req, actor):
    """Talento convierte un curso nuevo completado en curso del catálogo (FR-029)."""
    m = _models()
    if not actor.is_admin:
        raise PermissionDenied("Solo Talento administra el catálogo.")
    req = _locked(req)
    if req.catalog_course_id:
        raise ValidationError("Este curso ya pertenece al catálogo.")
    if req.status not in (m.CourseRequest.Status.COMPLETADA, m.CourseRequest.Status.VALIDADA):
        raise ValidationError("Solo se promueven cursos completados.")
    course = m.CatalogCourse.objects.create(
        name=req.name, provider=req.provider, url=req.url, kind=req.kind,
        reference_cost=req.final_cost if req.final_cost is not None else req.estimated_cost,
        currency=req.currency, duration_hours=req.duration_hours, pillar=req.pillar,
        tags=req.tags, created_by=actor, promoted_from=req,
    )
    review = getattr(req, "review", None)
    if review is not None:
        course.areas.set(review.audience_areas.all())
        course.levels.set(review.audience_levels.all())
    req.catalog_course = course
    req.save(update_fields=["catalog_course", "updated_at"])
    return course


# --- Selector "Solicitar curso": cursos ya conocidos en Arena --------------------------

OPEN_STATUSES = ("BORRADOR", "EN_REVISION", "REQUIERE_AJUSTES", "AUTORIZADA")
KNOWN_STATUSES = ("AUTORIZADA", "COMPLETADA", "VALIDADA")


def _course_key(name: str, provider: str) -> tuple[str, str]:
    return (" ".join((name or "").lower().split()), " ".join((provider or "").lower().split()))


def open_request_for(user, catalog_course=None, name="", provider="", exclude_pk=None):
    """Solicitud abierta del usuario para el mismo curso (evita pedirlo dos veces), o None."""
    m = _models()
    qs = m.CourseRequest.objects.filter(user=user, status__in=OPEN_STATUSES).exclude(pk=exclude_pk)
    if catalog_course is not None:
        return qs.filter(catalog_course=catalog_course).first()
    if not name:
        return None
    key = _course_key(name, provider)
    for r in qs.filter(catalog_course__isnull=True).only("pk", "name", "provider", "status", "current_stage"):
        if _course_key(r.name, r.provider) == key:
            return r
    return None


def requestable_courses(user, q: str = "") -> dict:
    """Cursos que el colaborador puede pedir sin capturarlos de cero (selector de US1).

    - `catalog`: catálogo sugerido activo, con veces autorizado y modalidad de pago usada.
    - `known`: cursos fuera del catálogo que alguien en Arena ya tomó con autorización
      (agrupados por nombre + proveedor; se toma el registro más reciente como plantilla).
    Cada elemento indica si el usuario ya tiene una solicitud abierta de ese curso.
    Solo expone datos de curso (costo de referencia y modalidad), nunca justificaciones.
    """
    m = _models()
    St = m.CourseRequest.Status
    q = (q or "").strip()
    mine = list(
        m.CourseRequest.objects.filter(user=user, status__in=OPEN_STATUSES)
        .only("pk", "name", "provider", "status", "current_stage", "catalog_course_id")
    )
    mine_by_catalog = {r.catalog_course_id: r for r in mine if r.catalog_course_id}
    mine_by_key = {_course_key(r.name, r.provider): r for r in mine if not r.catalog_course_id}

    known_qs = m.CourseRequest.objects.filter(status__in=KNOWN_STATUSES).select_related("review")
    if q:
        known_qs = known_qs.filter(Q(name__icontains=q) | Q(provider__icontains=q) | Q(tags__icontains=q))

    # Uso histórico de cada curso del catálogo: veces autorizado y modalidad más reciente.
    catalog_usage: dict[int, dict] = {}
    groups: dict[tuple, dict] = {}
    for r in known_qs.order_by("-authorized_at", "-created_at"):
        if r.catalog_course_id:
            u = catalog_usage.setdefault(r.catalog_course_id, {"count": 0, "payment_mode": ""})
            u["count"] += 1
            if not u["payment_mode"] and r.payment_mode:
                u["payment_mode"] = r.get_payment_mode_display()
            continue
        key = _course_key(r.name, r.provider)
        g = groups.get(key)
        if g is None:
            g = groups[key] = {
                "template": r, "count": 0, "ratings": [], "validated": False, "payment_mode": "",
            }
        g["count"] += 1
        g["validated"] = g["validated"] or r.status == St.VALIDADA
        if not g["payment_mode"] and r.payment_mode:
            g["payment_mode"] = r.get_payment_mode_display()
        review = getattr(r, "review", None)
        if review is not None:
            g["ratings"].append(review.rating)

    catalog = []
    for c in catalog_queryset({"q": q} if q else None):
        usage = catalog_usage.get(c.pk, {"count": 0, "payment_mode": ""})
        catalog.append({
            "course": c, "authorized_count": usage["count"], "payment_mode": usage["payment_mode"],
            "mine": mine_by_catalog.get(c.pk),
        })

    known = []
    for key, g in groups.items():
        t = g["template"]
        known.append({
            "template": t,
            "count": g["count"],
            "avg_rating": (sum(g["ratings"]) / len(g["ratings"])) if g["ratings"] else None,
            "validated": g["validated"],
            "payment_mode": g["payment_mode"],
            "mine": mine_by_key.get(key),
        })
    known.sort(key=lambda k: (-k["count"], k["template"].name.lower()))
    return {"catalog": catalog, "known": known}


def template_data_from(req) -> dict:
    """Datos de curso (sin justificación ni fechas) para precargar una solicitud nueva."""
    return {f: getattr(req, f) for f in (
        "name", "provider", "url", "kind", "duration_hours", "pillar", "tags", "estimated_cost", "currency",
    )}


# --- Lecturas para perfil público (R6) ---------------------------------------------


def learning_public_requests(person) -> QuerySet:
    m = _models()
    return (
        m.CourseRequest.objects.filter(user=person, status__in=m.CourseRequest.PUBLIC_STATUSES)
        .select_related("review")
        .order_by("-closed_at", "-authorized_at", "-created_at")
    )


def public_course_context(req) -> dict:
    """Solo campos públicos: nunca costo, pago, justificación ni bitácora."""
    m = _models()
    review = getattr(req, "review", None)
    certificates = [
        {"pk": e.pk, "filename": e.filename, "is_image": e.is_image}
        for e in req.evidences.filter(kind=m.CourseEvidence.Kind.CERTIFICADO).only(
            "pk", "filename", "mime", "kind",
        )
    ]
    return {
        "pk": req.pk,
        "user": req.user,
        "name": req.name,
        "provider": req.provider,
        "url": req.url,
        "kind": req.get_kind_display(),
        "pillar": req.get_pillar_display() if req.pillar else "",
        "tags": req.tag_list,
        "duration_hours": req.duration_hours,
        "start_date": req.start_date_planned,
        "end_date": req.end_date_planned,
        "closed_at": req.closed_at,
        "status": req.status,
        "status_display": req.status_display,
        "status_tone": req.status_tone,
        "catalog_course_id": req.catalog_course_id,
        "review": {
            "rating": review.rating,
            "opinion": review.opinion,
            "recommends": review.get_recommends_display(),
            "recommends_code": review.recommends,
            "recommend_why": review.recommend_why,
            "audience_areas": [a.name for a in review.audience_areas.all()],
            "audience_levels": [lv.name for lv in review.audience_levels.all()],
            "audience_notes": review.audience_notes,
            "learnings": review.learnings,
        } if review else None,
        "certificates": certificates,
    }


def authorized_cost_this_year(user, year=None) -> dict[str, Decimal]:
    """Costo autorizado del colaborador en el año, por moneda (FR-011)."""
    m = _models()
    St = m.CourseRequest.Status
    year = year or timezone.localdate().year
    rows = (
        m.CourseRequest.objects.filter(
            user=user, authorized_at__year=year,
            status__in=(St.AUTORIZADA, St.COMPLETADA, St.VALIDADA, St.NO_CONCLUIDA),
        )
        .values("currency")
        .annotate(total=Sum("estimated_cost"))
    )
    return {r["currency"]: r["total"] or Decimal("0") for r in rows}


def approver_context(req) -> dict:
    """Panel de contexto para quien decide (FR-011)."""
    m = _models()
    St = m.CourseRequest.Status
    history = (
        m.CourseRequest.objects.filter(user=req.user)
        .exclude(pk=req.pk)
        .exclude(status__in=(St.BORRADOR, St.CANCELADA))
        .order_by("-created_at")
    )
    counts = {
        "completed": history.filter(status__in=(St.COMPLETADA, St.VALIDADA)).count(),
        "in_progress": history.filter(status=St.AUTORIZADA).count(),
        "not_completed": history.filter(status=St.NO_CONCLUIDA).count(),
    }
    return {"history": history[:10], "counts": counts, "cost_year": authorized_cost_this_year(req.user)}


# --- Bandeja y campana ---------------------------------------------------------------


def is_course_approver(user) -> bool:
    """Puede llegarle una solicitud: Lead, Lead directo de alguien, Director o Talento."""
    return bool(
        user.is_lead or user.is_director or user.is_admin or user.direct_reports.exists()
    )


def approvals_for(user) -> list:
    """Solicitudes en revisión donde `user` es aprobador elegible de la etapa actual."""
    m = _models()
    candidates = m.CourseRequest.objects.filter(
        status=m.CourseRequest.Status.EN_REVISION,
    ).exclude(user=user).select_related("user", "user__area", "user__level", "catalog_course")
    # Prefiltro barato por rol antes de resolver aprobadores por solicitud.
    S = m.CourseRequest.Stage
    stages = []
    if user.is_lead or user.direct_reports.exists():
        stages.append(S.LEAD)
    if user.is_director:
        stages.append(S.DIRECCION)
    if user.is_admin:
        stages.append(S.TALENTO)
    reassigned_ids = set(
        m.ApprovalStep.objects.filter(
            action=m.ApprovalStep.Action.REASIGNAR, assigned_to=user,
        ).values_list("request_id", flat=True)
    )
    candidates = candidates.filter(Q(current_stage__in=set(stages)) | Q(pk__in=reassigned_ids))
    return [r for r in candidates.order_by("submitted_at") if can_decide(user, r)]


def pending_for(user) -> list[dict]:
    """Pendientes de Arena Learn para la campana (FR-012)."""
    m = _models()
    St = m.CourseRequest.Status
    items: list[dict] = []
    approvals = approvals_for(user)
    if approvals:
        n = len(approvals)
        items.append({
            "project": "Arena Learn",
            "text": f"{n} solicitud{'es' if n != 1 else ''} de curso por aprobar",
            "url": reverse("learning:approvals_inbox"),
            "icon": "send",
        })
    for req in m.CourseRequest.objects.filter(
        user=user, status__in=(St.REQUIERE_AJUSTES, St.AUTORIZADA),
    ).only("pk", "name", "status")[:5]:
        if req.status == St.REQUIERE_AJUSTES:
            text = "Tu solicitud requiere ajustes"
            url = reverse("learning:request_edit", args=[req.pk])
        else:
            text = "Cierra tu curso con evidencia y reseña"
            url = reverse("learning:request_complete", args=[req.pk])
        items.append({"project": req.name, "text": text, "url": url, "icon": "book"})
    if user.is_admin:
        n = m.CourseEvidence.objects.filter(
            kind=m.CourseEvidence.Kind.CERTIFICADO,
            validation=m.CourseEvidence.Validation.PENDIENTE,
            request__status=St.COMPLETADA,
        ).exclude(request__user=user).count()
        if n:
            items.append({
                "project": "Arena Learn",
                "text": f"{n} evidencia{'s' if n != 1 else ''} por validar",
                "url": reverse("learning:tracking") + "?estado=COMPLETADA",
                "icon": "check",
            })
    return items


# --- Tablero de seguimiento (US7) ------------------------------------------------------


def business_days_between(start: date, end: date) -> int:
    """Días hábiles (lun–vie) transcurridos de `start` a `end` (sin contar `start`)."""
    if end <= start:
        return 0
    days = 0
    d = start
    while d < end:
        d += timedelta(days=1)
        if d.weekday() < 5:
            days += 1
    return days


def _last_step_dates(req_ids) -> dict:
    from django.db.models import Max

    m = _models()
    return dict(
        m.ApprovalStep.objects.filter(request_id__in=req_ids)
        .values("request_id")
        .annotate(last=Max("created_at"))
        .values_list("request_id", "last")
    )


def tracking_queryset(filters: dict | None = None) -> QuerySet:
    m = _models()
    f = filters or {}
    qs = m.CourseRequest.objects.select_related("user", "user__area").exclude(
        status=m.CourseRequest.Status.BORRADOR,
    )
    if f.get("area"):
        qs = qs.filter(user__area_id=f["area"])
    if f.get("person"):
        qs = qs.filter(user_id=f["person"])
    if f.get("year"):
        qs = qs.filter(created_at__year=f["year"])
    if f.get("status"):
        qs = qs.filter(status=f["status"])
    return qs.order_by("-created_at")


def dashboard_rows(filters: dict | None = None, today: date | None = None) -> dict:
    """Filas del tablero con alertas calculadas (atascada / vencido / sobrecosto)."""
    m = _models()
    St = m.CourseRequest.Status
    today = today or timezone.localdate()
    reqs = list(tracking_queryset(filters))
    last = _last_step_dates([r.pk for r in reqs])
    rows = []
    for r in reqs:
        last_dt = last.get(r.pk) or r.created_at
        stale = (
            r.status == St.EN_REVISION
            and business_days_between(timezone.localtime(last_dt).date(), today) > STALE_BUSINESS_DAYS
        )
        overdue = (
            r.status == St.AUTORIZADA
            and r.end_date_planned is not None
            and r.end_date_planned + timedelta(days=OVERDUE_DAYS) < today
        )
        rows.append({"req": r, "stale": stale, "overdue": overdue, "cost_overrun": r.cost_overrun})

    status_counts = {s: 0 for s, _ in St.choices if s != St.BORRADOR}
    for row in rows:
        status_counts[row["req"].status] = status_counts.get(row["req"].status, 0) + 1

    year = (filters or {}).get("year") or today.year
    cost_by_area: dict[tuple[str, str], Decimal] = {}
    for r in m.CourseRequest.objects.filter(
        authorized_at__year=year,
        status__in=(St.AUTORIZADA, St.COMPLETADA, St.VALIDADA, St.NO_CONCLUIDA),
    ).select_related("user__area"):
        key = (r.user.area.name if r.user.area else "Sin área", r.currency)
        cost_by_area[key] = cost_by_area.get(key, Decimal("0")) + (r.estimated_cost or Decimal("0"))

    return {
        "rows": rows,
        "status_counts": [(St(s).label if s else s, s, n) for s, n in status_counts.items()],
        "stale_count": sum(1 for r in rows if r["stale"]),
        "overdue_count": sum(1 for r in rows if r["overdue"]),
        "cost_by_area": sorted(
            ({"area": a, "currency": c, "total": t} for (a, c), t in cost_by_area.items()),
            key=lambda x: (x["area"], x["currency"]),
        ),
        "year": year,
    }


EXPORT_HEADERS = [
    "Colaborador", "Correo", "Área", "Curso", "Proveedor", "Tipo", "Origen", "Estado",
    "Costo estimado", "Moneda", "Costo final", "Modalidad de pago", "Estado del pago",
    "Enviada", "Autorizada", "Cerrada", "Atascada", "Vencido",
]


def export_rows(filters: dict | None = None) -> list[list]:
    data = dashboard_rows(filters)
    out = []
    for row in data["rows"]:
        r = row["req"]
        out.append([
            r.user.full_name, r.user.email, r.user.area.name if r.user.area else "",
            r.name, r.provider, r.get_kind_display(), r.get_origin_display(), r.status_display,
            float(r.estimated_cost) if r.estimated_cost is not None else None, r.currency,
            float(r.final_cost) if r.final_cost is not None else None,
            r.get_payment_mode_display() if r.payment_mode else "",
            r.get_payment_status_display() if r.payment_status else "",
            timezone.localtime(r.submitted_at).replace(tzinfo=None) if r.submitted_at else None,
            timezone.localtime(r.authorized_at).replace(tzinfo=None) if r.authorized_at else None,
            timezone.localtime(r.closed_at).replace(tzinfo=None) if r.closed_at else None,
            "Sí" if row["stale"] else "", "Sí" if row["overdue"] else "",
        ])
    return out


# --- Notificaciones (R4) ---------------------------------------------------------------


def _absolute(path: str) -> str:
    base = getattr(settings, "SITE_URL", "") or ""
    return f"{base.rstrip('/')}{path}" if base else path


def _send(recipients, subject, body):
    emails = sorted({u.email for u in recipients if getattr(u, "email", "")})
    if not emails:
        return

    def _do():
        send_mail(subject, body, None, emails, fail_silently=True)

    transaction.on_commit(_do)


def _notify_stage(req):
    approvers = list(eligible_approvers(req, req.current_stage)) if req.current_stage else []
    url = _absolute(reverse("learning:request_detail", args=[req.pk]))
    _send(
        approvers,
        f"Arena Learn · Solicitud de curso por aprobar: {req.name}",
        f"{req.user.full_name} solicita el curso «{req.name}» ({req.provider}).\n"
        f"Revísalo y decide en: {url}\n",
    )


def _notify_owner(req, what: str, comment: str = ""):
    url = _absolute(reverse("learning:request_detail", args=[req.pk]))
    body = f"Tu solicitud del curso «{req.name}» fue {what}.\n"
    if comment:
        body += f"Comentario: {comment}\n"
    body += f"Detalle: {url}\n"
    _send([req.user], f"Arena Learn · Tu solicitud fue {what}", body)


def _notify_talento(req, what: str):
    talento = _active_users().filter(Q(role=User.Role.TALENTO)).exclude(pk=req.user_id)
    url = _absolute(reverse("learning:request_detail", args=[req.pk]))
    _send(list(talento), f"Arena Learn · {req.name} {what}",
          f"El curso «{req.name}» de {req.user.full_name} {what}.\nDetalle: {url}\n")


# --- Permisos de lectura específicos (delegan a permissions) -----------------------------


def can_view_private(viewer, req) -> bool:
    return permissions.can_view_course_private(viewer, req)
