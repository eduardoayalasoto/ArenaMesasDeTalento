"""Capa de cálculo del modelo de desempeño. Funciones puras y testeadas (RN-03/04/05/08/09/12/19/20).

Regla transversal: la escala es 1–4, los N/A se excluyen de todo promedio (RN-03),
y los promedios se redondean a 2 decimales con ROUND_HALF_UP.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

TWO_DP = Decimal("0.01")


def _avg(values) -> Decimal | None:
    """Promedio de una lista de números (Decimal a 2 dp), o None si está vacía."""
    nums = [Decimal(str(v)) for v in values if v is not None]
    if not nums:
        return None
    return (sum(nums) / Decimal(len(nums))).quantize(TWO_DP, rounding=ROUND_HALF_UP)


# --- Pilar 1: Ownership ----------------------------------------------------

@dataclass
class CategoryScore:
    """Renglón del desglose de una evaluación de Ownership (spec 008)."""

    code: str
    name: str
    weight: Decimal          # peso configurado de la categoría, en %
    score: Decimal | None    # promedio ponderado de la categoría; None = sin calificar
    answered: int
    total: int


def _round2(value: Fraction) -> Decimal:
    """Redondeo mitad hacia arriba a 2 decimales, exacto (sin error de coma flotante)."""
    cents = (value * 100 + Fraction(1, 2)).__floor__()
    return (Decimal(cents) / 100).quantize(TWO_DP, rounding=ROUND_HALF_UP)


def _exact(value) -> Fraction:
    return Fraction(Decimal(str(value)))


def _ownership_categories(evaluation):
    """(categorías configuradas, preguntas de escala) o (None, preguntas) si no hay configuración.

    Sin `TemplateCategory`, o con preguntas fuera de las categorías del cuestionario, se usa una
    sola categoría al 100% (comportamiento anterior al spec 008: promedio simple).
    """
    from apps.questionnaires.models import Question

    template = evaluation.template
    questions = list(
        Question.objects.filter(section__template=template, qtype=Question.Type.SCALE)
        .select_related("category").order_by("section__order", "order")
    )
    links = list(template.template_categories.select_related("category").order_by("category__order"))
    linked_ids = {link.category_id for link in links}
    if not links or any(q.category_id not in linked_ids for q in questions):
        return None, questions
    return links, questions


def _graded_values(evaluation):
    """{question_id: valor} de las respuestas calificadas (N/A y vacías fuera)."""
    return {
        a.question_id: a.value
        for a in evaluation.answers.all()
        if not a.is_na and a.value is not None
    }


def ownership_category_breakdown(evaluation) -> list[CategoryScore]:
    """Desglose por categoría de una evaluación (vacío si el cuestionario no tiene categorías
    configuradas). Se calcula siempre de las respuestas; no se congela. La interfaz lo oculta
    cuando solo existe una categoría."""
    links, questions = _ownership_categories(evaluation)
    if links is None:
        return []
    graded = _graded_values(evaluation)
    answered_ids = {a.question_id for a in evaluation.answers.all() if a.is_na or a.value is not None}
    rows = []
    for link in links:
        group = [q for q in questions if q.category_id == link.category_id]
        score = _category_score(group, graded)
        rows.append(CategoryScore(
            code=link.category.code, name=link.category.name, weight=link.weight_pct,
            score=None if score is None else _round2(score),
            answered=sum(1 for q in group if q.pk in answered_ids), total=len(group),
        ))
    return rows


def _question_weights(group):
    """Pesos exactos de las preguntas de una categoría: partes iguales si ninguna define peso."""
    if all(q.weight_pct is None for q in group):
        return {q.pk: Fraction(1) for q in group}
    return {q.pk: _exact(q.weight_pct if q.weight_pct is not None else 0) for q in group}


def _category_score(group, graded) -> Fraction | None:
    weights = _question_weights(group)
    numerator = sum(Fraction(graded[q.pk]) * weights[q.pk] for q in group if q.pk in graded)
    denominator = sum(weights[q.pk] for q in group if q.pk in graded)
    if denominator == 0:
        return None
    return numerator / denominator


def ownership_evaluation_score(evaluation) -> Decimal | None:
    """Calificación de una evaluación de Ownership: promedio ponderado por categorías (spec 008).

    Score de categoría = promedio ponderado de sus preguntas calificadas (N/A fuera, RN-03/04);
    score del cuestionario = Σ score × peso de categoría, redistribuyendo el peso de las
    categorías sin calificar. Con una sola categoría y pesos nulos es el promedio simple de
    siempre. Un único redondeo final (mitad hacia arriba).
    """
    links, questions = _ownership_categories(evaluation)
    if links is None:
        return _avg(list(_graded_values(evaluation).values()))
    graded = _graded_values(evaluation)
    weighted_sum = Fraction(0)
    weight_total = Fraction(0)
    for link in links:
        score = _category_score([q for q in questions if q.category_id == link.category_id], graded)
        if score is None:
            continue
        weight = _exact(link.weight_pct)
        weighted_sum += score * weight
        weight_total += weight
    if weight_total == 0:
        return None
    return _round2(weighted_sum / weight_total)


def ownership_pillar_breakdown(user, period) -> list[dict]:
    """Desglose por categoría del pilar: promedio de cada categoría entre las evaluaciones
    ENVIADAS del periodo (mismo criterio que el total). Vacío si solo hay una categoría."""
    from apps.evaluations.models import OwnershipEvaluation

    evaluations = OwnershipEvaluation.objects.filter(
        user=user, period=period, status=OwnershipEvaluation.Status.ENVIADA,
    ).select_related("template")
    acc: dict[str, dict] = {}
    for evaluation in evaluations:
        for row in ownership_category_breakdown(evaluation):
            entry = acc.setdefault(row.code, {
                "code": row.code, "name": row.name, "weight": row.weight, "scores": [], "order": len(acc),
            })
            entry["scores"].append(row.score)
    return [
        {"code": e["code"], "name": e["name"], "weight": e["weight"], "score": _avg(e["scores"])}
        for e in sorted(acc.values(), key=lambda e: e["order"])
    ]


def ownership_pillar_score(user, period) -> Decimal | None:
    """Promedio simple de las evaluaciones ENVIADAS del usuario en el periodo (RN-05)."""
    from apps.evaluations.models import OwnershipEvaluation

    scores = OwnershipEvaluation.objects.filter(
        user=user, period=period, status=OwnershipEvaluation.Status.ENVIADA,
        score__isnull=False,
    ).values_list("score", flat=True)
    return _avg(list(scores))


# --- Pilar 2: Entrega de Valor --------------------------------------------

def value_delivery_project_score(vd_eval) -> Decimal | None:
    """Promedio de satisfacción, entregables y el criterio de tiempo aplicable (RN-08)."""
    applicable_time = vd_eval.time_finite if vd_eval.project.is_finite else vd_eval.time_indefinite
    return _avg([vd_eval.client_satisfaction, vd_eval.deliverables, applicable_time])


def value_delivery_pillar_score(user, period) -> Decimal | None:
    """Promedio de los scores VALIDADOS de los proyectos donde el usuario fue miembro (RN-09)."""
    from apps.evaluations.models import ValueDeliveryEvaluation

    scores = ValueDeliveryEvaluation.objects.filter(
        period=period,
        status=ValueDeliveryEvaluation.Status.VALIDADA,
        score__isnull=False,
        project__memberships__user=user,
    ).values_list("score", flat=True)
    return _avg(list(scores))


# --- Bandas de interpretación (RN-20) -------------------------------------

def interpretation_band(score) -> str:
    """≥3.50 Excede · 3.00–3.49 Cumple · 2.00–2.99 Cumple parcial · <2.00 No cumple."""
    s = Decimal(str(score))
    if s >= Decimal("3.50"):
        return "Excede"
    if s >= Decimal("3.00"):
        return "Cumple"
    if s >= Decimal("2.00"):
        return "Cumple parcial"
    return "No cumple"


# --- Calificación final (RN-12/19) ----------------------------------------

@dataclass
class FinalScoreResult:
    ownership: Decimal | None
    value_delivery: Decimal | None
    arena_impact: Decimal | None
    final_score: Decimal | None
    band: str
    is_complete: bool


def final_score(user, period, ownership, value_delivery, arena) -> FinalScoreResult:
    """Promedio ponderado de los 3 pilares según la ponderación del nivel del usuario (RN-12/19)."""
    is_complete = None not in (ownership, value_delivery, arena)

    final = None
    band = ""
    if is_complete:
        weight = user.level.weight  # PillarWeight (OneToOne)
        final = (
            Decimal(str(ownership)) * weight.w_ownership
            + Decimal(str(value_delivery)) * weight.w_value_delivery
            + Decimal(str(arena)) * weight.w_arena_impact
        ).quantize(TWO_DP, rounding=ROUND_HALF_UP)
        band = interpretation_band(final)

    return FinalScoreResult(
        ownership=ownership, value_delivery=value_delivery, arena_impact=arena,
        final_score=final, band=band, is_complete=is_complete,
    )
