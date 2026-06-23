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


def get_or_create_ownership_evaluation(user, period, project=None, evaluator=None):
    """Obtiene o crea la evaluación para el usuario y periodo dados.

    Para Leads: project=None crea una evaluación transversal (sin proyecto específico).
    Para colaboradores normales: project es el proyecto concreto.
    Devuelve (evaluation, error). error es None si todo bien, o un mensaje si no se
    pudo resolver la plantilla (área/nivel sin asignar o cuestionario no publicado).
    """
    from apps.evaluations.models import OwnershipEvaluation, OwnershipEvaluator

    if project is None:
        existing = OwnershipEvaluation.objects.filter(
            user=user, project__isnull=True, period=period
        ).first()
    else:
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
        user=user, project=project, period=period, template=template,
    )
    if evaluator:
        OwnershipEvaluator.objects.create(
            evaluation=evaluation, user=evaluator, is_primary=True,
        )
    return evaluation, None


def add_evaluator(evaluation, user, is_primary=False):
    """Agrega un evaluador (primario o secundario) a la evaluación.

    Si el usuario ya está asignado, no hace nada (idempotente).
    Si is_primary=True, baja al primario actual antes de crear el nuevo.
    """
    from apps.evaluations.models import OwnershipEvaluator

    if is_primary:
        OwnershipEvaluator.objects.filter(evaluation=evaluation, is_primary=True).update(is_primary=False)

    OwnershipEvaluator.objects.get_or_create(
        evaluation=evaluation,
        user=user,
        defaults={"is_primary": is_primary},
    )


def set_primary_evaluator(evaluation, new_primary_user):
    """Cambia el evaluador principal de la evaluación.

    Si el nuevo primario ya era secundario, lo promueve.
    Si es nuevo, lo crea como primario. El primario anterior pasa a secundario.
    """
    from apps.evaluations.models import OwnershipEvaluator

    OwnershipEvaluator.objects.filter(evaluation=evaluation, is_primary=True).update(is_primary=False)
    evaluator, created = OwnershipEvaluator.objects.get_or_create(
        evaluation=evaluation,
        user=new_primary_user,
        defaults={"is_primary": True},
    )
    if not created and not evaluator.is_primary:
        evaluator.is_primary = True
        evaluator.save(update_fields=["is_primary"])


def remove_evaluator(evaluation, user):
    """Elimina un evaluador secundario de la evaluación.

    No permite eliminar al evaluador primario (debe usarse set_primary_evaluator para reemplazarlo).
    """
    from apps.evaluations.models import OwnershipEvaluator

    OwnershipEvaluator.objects.filter(evaluation=evaluation, user=user, is_primary=False).delete()


def sync_evaluation_template(evaluation) -> bool:
    """Sincroniza el template de una evaluación abierta con el área/nivel actual del colaborador.

    Si el template guardado ya no coincide (el colaborador cambió de área o nivel),
    actualiza el template y borra las respuestas previas (pertenecían al template anterior).
    Solo actúa sobre evaluaciones en estado BORRADOR.
    Devuelve True si hubo cambio.
    """
    if evaluation.is_submitted:
        return False
    current_template = resolve_ownership_template(evaluation.user)
    if current_template is None or evaluation.template_id == current_template.id:
        return False
    evaluation.answers.all().delete()
    evaluation.template = current_template
    evaluation.save(update_fields=["template", "updated_at"])
    return True


def close_ownership_evaluation(evaluation) -> list[str]:
    """Cierre por cualquier evaluador: valida, calcula score y bloquea para todos.

    Las Fortalezas y Oportunidades son obligatorias para cerrar.
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
