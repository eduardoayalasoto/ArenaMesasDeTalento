"""Ciclo de vida de los Periodos de Evaluación (spec 002-ciclo-vida-periodos).

Orquesta las reglas que `EvaluationPeriod` por sí solo no garantiza:
- Un único periodo Abierto a la vez (constraint de BD + validación con mensaje).
- Cierre y apertura del siguiente periodo contiguo, en una sola transacción.
- Inmutabilidad de los registros de un periodo Cerrado, con excepción auditada
  para Talento/superusuario.
- Bloqueo de creación de nuevos registros cuando no hay periodo Abierto.
"""

from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.core.services import permissions


class NoOpenPeriodError(Exception):
    """No hay ningún EvaluationPeriod en estatus Abierto."""


def open_period(period, actor=None):
    """Abre `period` (FR-001/FR-002). Falla si ya existe otro periodo Abierto."""
    from apps.catalog.models import EvaluationPeriod

    other = (
        EvaluationPeriod.objects.filter(status=EvaluationPeriod.Status.ABIERTO)
        .exclude(pk=period.pk)
        .first()
    )
    if other is not None:
        raise ValidationError(
            f"Ya existe un periodo Abierto («{other.name}»). Ciérralo antes de abrir «{period.name}»."
        )
    period.status = EvaluationPeriod.Status.ABIERTO
    period.save(update_fields=["status"])
    return period


def find_contiguous_next(period):
    """Periodo Planeado cuyo `start_date` es el día siguiente al `end_date` de `period`, o None."""
    from apps.catalog.models import EvaluationPeriod

    return EvaluationPeriod.objects.filter(
        status=EvaluationPeriod.Status.PLANEADO,
        start_date=period.end_date + timedelta(days=1),
    ).first()


def close_and_open_next(period, actor=None):
    """Cierra `period` y abre en la misma transacción el Planeado contiguo (FR-005).

    Si no hay un periodo Planeado contiguo, no cambia nada y levanta ValidationError.
    """
    from apps.catalog.models import EvaluationPeriod

    next_period = find_contiguous_next(period)
    if next_period is None:
        raise ValidationError(
            f"No puedes cerrar «{period.name}»: no existe un periodo Planeado contiguo "
            f"(que inicie el {(period.end_date + timedelta(days=1)):%d/%m/%Y}) para sucederlo. "
            "Crea primero ese periodo."
        )

    with transaction.atomic():
        period.status = EvaluationPeriod.Status.CERRADO
        period.save(update_fields=["status"])
        next_period.status = EvaluationPeriod.Status.ABIERTO
        next_period.save(update_fields=["status"])

    return next_period


def assert_record_editable(record, actor, reason=None):
    """Bloquea editar/eliminar un registro cuyo periodo ya está Cerrado (FR-006).

    Si el periodo está Cerrado:
    - `actor` sin permiso de corrección (`permissions.is_period_correction_allowed`) → PermissionDenied.
    - `actor` con permiso: exige `reason` no vacío y lo deja listo para que
      `django-simple-history` lo registre en el historial de este `save()`.
    No hace nada si el periodo sigue Abierto/Planeado.
    """
    period = record.period
    if not period.is_closed:
        return

    if actor is None or not permissions.is_period_correction_allowed(actor):
        raise PermissionDenied(
            f"El periodo «{period.name}» ya está Cerrado: este registro es de solo lectura."
        )

    if not (reason or "").strip():
        raise ValidationError(
            "Debes capturar un motivo para corregir un registro de un periodo ya Cerrado."
        )

    record._change_reason = reason.strip()


def require_open_period():
    """Periodo Abierto vigente, o levanta NoOpenPeriodError con mensaje de negocio (FR-008/FR-009)."""
    from apps.catalog.models import EvaluationPeriod

    period = EvaluationPeriod.objects.filter(status=EvaluationPeriod.Status.ABIERTO).first()
    if period is None:
        raise NoOpenPeriodError(
            "No hay un periodo de evaluación abierto en este momento. "
            "Contacta a Talento para que abra el periodo correspondiente."
        )
    return period


def resolve_requested_period(request, *, fallback=None):
    """Periodo indicado en `?periodo=<id>` (cualquier estatus), o `fallback()` si no viene o no existe.

    Centraliza el patrón de navegación histórica ya usado en 002
    (spec 003-salvaguardas-cierre-periodo, FR de US3): permite a las
    pantallas de listado/consulta operar sobre un periodo específico en vez
    de forzar siempre el periodo Abierto vigente.
    """
    from apps.catalog.models import EvaluationPeriod

    raw_pk = request.GET.get("periodo")
    if raw_pk:
        period = EvaluationPeriod.objects.filter(pk=raw_pk).first()
        if period is not None:
            return period
    return fallback() if fallback else None


def pending_activity_counts(period):
    """Conteos de actividad aún no completada en `period` (solo lectura).

    Mismos conteos que ya muestra `dashboards.period_progress`, extraídos
    aquí para que también los use la confirmación de cierre de
    `catalog.period_admin` sin duplicar las queries (spec 003, FR-005/FR-008).
    """
    from apps.evaluations.models import FinalScore, OwnershipEvaluation, ValueDeliveryEvaluation

    own = OwnershipEvaluation.objects.filter(period=period)
    vd = ValueDeliveryEvaluation.objects.filter(period=period)
    finals = FinalScore.objects.filter(period=period)
    return {
        "own_total": own.count(),
        "own_submitted": own.filter(status=OwnershipEvaluation.Status.ENVIADA).count(),
        "vd_total": vd.count(),
        "vd_validated": vd.filter(status=ValueDeliveryEvaluation.Status.VALIDADA).count(),
        "finals_total": finals.count(),
        "finals_complete": finals.filter(is_complete=True).count(),
    }
