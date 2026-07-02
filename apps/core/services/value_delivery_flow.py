"""Ciclo de vida de la Entrega de Valor (RN-07/08/09)."""

from django.utils import timezone

from apps.core.services import final_flow, scoring


def get_or_create_vd(project, period, evaluator=None):
    from apps.evaluations.models import ValueDeliveryEvaluation

    vd, _ = ValueDeliveryEvaluation.objects.get_or_create(
        project=project, period=period,
        defaults={"evaluator": evaluator},
    )
    return vd


def save_vd_criteria(vd, *, client_satisfaction, deliverables, time_value, comments=None):
    """Guarda los criterios; el criterio de tiempo se ubica según el tipo de proyecto (RN-08)."""
    vd.client_satisfaction = client_satisfaction
    vd.deliverables = deliverables
    if vd.project.is_finite:
        vd.time_finite = time_value
        vd.time_indefinite = None
    else:
        vd.time_indefinite = time_value
        vd.time_finite = None
    if comments is not None:
        vd.comments = comments
    vd.score = scoring.value_delivery_project_score(vd)
    vd.save()
    return vd


def save_vd_comment(vd, comment):
    """Actualiza el comentario de la Entrega de Valor, sin tocar criterios ni estado.

    Lo puede usar tanto el responsable (al capturar) como el Validador (al revisar).
    """
    vd.comments = comment
    vd.save(update_fields=["comments", "updated_at"])
    return vd


def criteria_summary(vd) -> list[dict]:
    """Describe los 3 criterios evaluados (etiqueta, ayuda y valor) para mostrarlos con contexto."""
    if vd.project.is_finite:
        time_label = "Tiempo — cumplimiento de la fecha de entrega"
        time_help = "Aplica porque el proyecto tiene fecha de cierre definida."
        time_value = vd.time_finite
    else:
        time_label = "Tiempo — consistencia del servicio"
        time_help = "Aplica porque el proyecto es de tiempo indefinido."
        time_value = vd.time_indefinite
    return [
        {
            "label": "Satisfacción del cliente",
            "help": "Nivel de satisfacción del cliente con el trabajo entregado.",
            "value": vd.client_satisfaction,
        },
        {
            "label": "Entregables",
            "help": "Cumplimiento y calidad de los entregables comprometidos.",
            "value": vd.deliverables,
        },
        {"label": time_label, "help": time_help, "value": time_value},
    ]


def submit_vd_for_validation(vd) -> list[str]:
    """Envía la Entrega de Valor a validación del director."""
    from apps.evaluations.models import ValueDeliveryEvaluation

    errors = []
    if vd.client_satisfaction is None:
        errors.append("Captura la satisfacción del cliente.")
    if vd.deliverables is None:
        errors.append("Captura la calificación de entregables.")
    time_value = vd.time_finite if vd.project.is_finite else vd.time_indefinite
    if time_value is None:
        errors.append("Captura el criterio de tiempo aplicable al proyecto.")
    if errors:
        return errors

    vd.status = ValueDeliveryEvaluation.Status.EN_VALIDACION
    vd.save(update_fields=["status", "updated_at"])
    return []


def validate_vd(vd, director):
    """El director valida: persiste score, marca VALIDADA y recalcula los finales del equipo (RN-09)."""
    from apps.evaluations.models import ValueDeliveryEvaluation

    vd.score = scoring.value_delivery_project_score(vd)
    vd.status = ValueDeliveryEvaluation.Status.VALIDADA
    vd.validated_by = director
    vd.validated_at = timezone.now()
    vd.rejection_comment = ""
    vd.save()
    final_flow.recompute_for_project_members(vd.project, vd.period)
    return vd


def reject_vd(vd, comment):
    """Rechazo: regresa a BORRADOR con comentario."""
    from apps.evaluations.models import ValueDeliveryEvaluation

    vd.status = ValueDeliveryEvaluation.Status.BORRADOR
    vd.rejection_comment = comment
    vd.save(update_fields=["status", "rejection_comment", "updated_at"])
    return vd
