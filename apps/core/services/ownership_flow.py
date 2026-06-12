"""Reglas del ciclo de vida de la evaluación de Ownership (RN-05/06)."""

from django.utils import timezone

from apps.core.services import scoring


def resolve_ownership_template(user):
    """Plantilla de Ownership PUBLICADA para el área y nivel del usuario, o None."""
    from apps.questionnaires.models import QuestionnaireTemplate

    if not user.area_id or not user.level_id:
        return None
    return (
        QuestionnaireTemplate.objects.filter(
            kind=QuestionnaireTemplate.Kind.OWNERSHIP,
            area_id=user.area_id,
            level_id=user.level_id,
            status=QuestionnaireTemplate.Status.PUBLICADO,
        )
        .order_by("-version")
        .first()
    )


def get_or_create_ownership_evaluation(user, project, period, evaluator=None):
    """Obtiene o crea la evaluación (user × project × period) con la plantilla vigente.

    `evaluator` es la persona que validará (la elige el evaluado; cualquiera de Arena).
    Devuelve (evaluation, error). error es None si todo bien, o un mensaje si no se
    pudo resolver la plantilla (área/nivel sin asignar o cuestionario no publicado).
    """
    from apps.evaluations.models import OwnershipEvaluation

    existing = OwnershipEvaluation.objects.filter(
        user=user, project=project, period=period
    ).first()
    if existing:
        return existing, None

    template = resolve_ownership_template(user)
    if template is None:
        return None, (
            "Aún no podemos abrir tu evaluación: tu área y nivel deben estar asignados "
            "por Talento y debe existir un cuestionario publicado para tu puesto."
        )

    evaluation = OwnershipEvaluation.objects.create(
        user=user, project=project, period=period,
        template=template, validator=evaluator,
    )
    return evaluation, None


def close_ownership_evaluation(evaluation) -> list[str]:
    """Cierre por el líder (Guardar y cerrar): valida, calcula score y bloquea para todos.

    Las Fortalezas y Oportunidades (que complementa el líder) son obligatorias para cerrar.
    Devuelve una lista de mensajes de error (en español); vacía = cerrada con éxito.
    """
    from apps.core.services import final_flow
    from apps.evaluations.models import OwnershipEvaluation

    if evaluation.status == OwnershipEvaluation.Status.ENVIADA:
        return ["Esta evaluación ya está cerrada y no puede modificarse."]

    errors: list[str] = []
    if not evaluation.strengths.strip():
        errors.append("Captura las Fortalezas antes de cerrar.")
    if not evaluation.opportunities.strip():
        errors.append("Captura las Oportunidades antes de cerrar.")
    if errors:
        return errors

    evaluation.score = scoring.ownership_evaluation_score(evaluation)
    evaluation.status = OwnershipEvaluation.Status.ENVIADA
    evaluation.submitted_at = timezone.now()
    evaluation.confirmed_with_leader = True
    evaluation.save(update_fields=[
        "score", "status", "submitted_at", "confirmed_with_leader", "updated_at"
    ])
    final_flow.recompute_final_score(evaluation.user, evaluation.period)
    return []


def reopen_ownership_evaluation(evaluation):
    """Reapertura por Talento/admin: ENVIADA → BORRADOR (RN-06).

    Al reabrir, la evaluación deja de contar como enviada, así que se recalcula
    la calificación final del colaborador (el pilar de Ownership solo promedia
    las evaluaciones ENVIADAS).
    """
    from apps.core.services import final_flow
    from apps.evaluations.models import OwnershipEvaluation

    evaluation.status = OwnershipEvaluation.Status.BORRADOR
    evaluation.submitted_at = None
    evaluation.save(update_fields=["status", "submitted_at", "updated_at"])
    final_flow.recompute_final_score(evaluation.user, evaluation.period)
