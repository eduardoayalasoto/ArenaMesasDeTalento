"""Reglas de pesos de los cuestionarios de Ownership (spec 008).

Los pesos son porcentajes con **un decimal** y se manejan en *décimas enteras* (0–1000) para que
las sumas sean exactas: un grupo de pesos es válido solo si suma 1000 décimas (100.0%).

La pantalla del editor aplica la misma aritmética en el navegador; este módulo es la fuente de
verdad en el servidor (formularios, publicación e importación).
"""

from decimal import Decimal, InvalidOperation
from fractions import Fraction

from django.core.exceptions import ValidationError
from django.db import transaction

TENTHS_TOTAL = 1000
_ONE_DP = Decimal("0.1")


class WeightError(ValueError):
    """Peso mal formado (más de un decimal, fuera de 0–100 o no numérico)."""


def to_tenths(value) -> int:
    """Convierte un peso en % a décimas enteras. Rechaza más de un decimal y fuera de 0–100."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise WeightError("Captura un peso entre 0 y 100.")
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation:
        raise WeightError("El peso debe ser un número.") from None
    if not number.is_finite():
        raise WeightError("El peso debe ser un número.")
    if number < 0 or number > 100:
        raise WeightError("El peso debe estar entre 0 y 100.")
    tenths = number * 10
    if tenths != tenths.to_integral_value():
        raise WeightError("Usa un solo decimal en los pesos (por ejemplo 33.3).")
    return int(tenths)


def from_tenths(tenths: int) -> Decimal:
    """Décimas enteras → Decimal con un decimal (p. ej. 335 → Decimal('33.5'))."""
    return (Decimal(tenths) / 10).quantize(_ONE_DP)


def format_pct(value) -> str:
    """'33.5' / '100.0' para mostrar; nunca más de un decimal."""
    return str(from_tenths(to_tenths(value)))


def group_total_tenths(values) -> int:
    return sum(to_tenths(v) for v in values)


def group_error(label: str, values) -> str | None:
    """Mensaje de error si el grupo no suma exactamente 100.0%; None si cuadra."""
    try:
        total = group_total_tenths(values)
    except WeightError as exc:
        return f"Los pesos de «{label}» no son válidos: {exc}"
    if total != TENTHS_TOTAL:
        return f"Los pesos de «{label}» suman {from_tenths(total)}%; deben sumar 100%."
    return None


def split_equal(n: int) -> list[Decimal]:
    """Reparte 100.0% en `n` partes con un decimal, sumando exacto (mayor residuo).

    El sobrante se asigna a las primeras partes: 3 → 33.4 / 33.3 / 33.3.
    """
    if n <= 0:
        return []
    base, extra = divmod(TENTHS_TOTAL, n)
    return [from_tenths(base + (1 if i < extra else 0)) for i in range(n)]


def normalize_to_100(raw_weights) -> list[Decimal]:
    """Escala pesos positivos cualesquiera a un decimal sumando exacto 100.0 (mayor residuo).

    Un grupo con suma 0 devuelve ceros (el llamador decide si eso es válido).
    """
    raw = [Decimal(str(w)) for w in raw_weights]
    total = sum(raw)
    if not raw or total <= 0:
        return [Decimal("0.0")] * len(raw)
    exact = [w * TENTHS_TOTAL / total for w in raw]
    floors = [int(x) for x in exact]
    remaining = TENTHS_TOTAL - sum(floors)
    order = sorted(range(len(raw)), key=lambda i: (-(exact[i] - floors[i]), i))
    for i in order[:remaining]:
        floors[i] += 1
    return [from_tenths(t) for t in floors]


def validate_template_weights(template) -> list[str]:
    """Errores (en español) de categorías y pesos de un cuestionario de Ownership.

    Reglas (data-model.md): Σ categorías = 100.0; cada pregunta de escala con categoría presente
    en el cuestionario; por categoría, pesos de pregunta todos nulos o todos definidos y Σ = 100.0;
    una categoría con peso > 0 necesita preguntas ponderadas.
    """
    from apps.questionnaires.models import Question

    errors: list[str] = []
    links = list(template.template_categories.select_related("category"))
    if not links:
        return ["El cuestionario no tiene categorías con peso."]

    error = group_error("Categorías del cuestionario", [link.weight_pct for link in links])
    if error:
        errors.append(error)

    by_category = {link.category_id: link for link in links}
    questions = list(
        Question.objects.filter(section__template=template, qtype=Question.Type.SCALE)
        .select_related("category")
    )
    uncategorized = [q.title for q in questions if q.category_id is None]
    if uncategorized:
        errors.append(
            "Hay preguntas sin categoría: " + ", ".join(f"«{t}»" for t in uncategorized) + "."
        )
    foreign = [q.title for q in questions if q.category_id and q.category_id not in by_category]
    if foreign:
        errors.append(
            "Hay preguntas con una categoría que no está en el cuestionario: "
            + ", ".join(f"«{t}»" for t in foreign) + "."
        )

    for link in links:
        # Las preguntas que «no ponderan» se califican pero quedan fuera del reparto.
        group = [q for q in questions if q.category_id == link.category_id and q.is_weighted]
        name = link.category.name
        if link.weight_pct <= 0:
            errors.append(f"La categoría «{name}» pesa 0%: dale peso o quítala del cuestionario.")
        if link.weight_pct > 0 and not group:
            errors.append(f"La categoría «{name}» pesa {link.weight_pct}% pero no tiene preguntas que ponderen.")
            continue
        defined = [q.weight_pct for q in group if q.weight_pct is not None]
        if defined and len(defined) != len(group):
            errors.append(
                f"En «{name}» hay preguntas con peso y otras sin peso; define el peso de todas "
                "o deja todas en partes iguales."
            )
            continue
        if defined:
            zero_titles = [q.title for q in group if q.weight_pct == 0]
            if zero_titles:
                errors.append(zero_weight_error(name, zero_titles))
            error = group_error(f"Preguntas de {name}", defined)
            if error:
                errors.append(error)
    return errors


def zero_weight_error(category_name: str, titles) -> str:
    """Toda pregunta de una categoría debe pesar más de 0%: una en 0% no participa en el score."""
    listed = ", ".join(f"«{t}»" for t in titles)
    return (
        f"En «{category_name}» hay preguntas con peso 0%: {listed}. Toda pregunta debe pesar más de 0% "
        "para participar en el score."
    )


def editor_groups(template) -> list[dict]:
    """Datos de la pantalla de pesos: por categoría, su vínculo y sus preguntas con el valor a
    mostrar (el guardado o, si están en partes iguales, el reparto igual como punto de partida)."""
    from apps.questionnaires.models import Question

    links = list(template.template_categories.select_related("category").order_by("category__order"))
    questions = list(
        Question.objects.filter(section__template=template, qtype=Question.Type.SCALE)
        .order_by("section__order", "order")
    )
    groups = []
    for link in links:
        group = [q for q in questions if q.category_id == link.category_id and q.is_weighted]
        custom = bool(group) and all(q.weight_pct is not None for q in group)
        equal = split_equal(len(group))
        groups.append({
            "link": link,
            "weight": format_pct(link.weight_pct),
            "custom": custom,
            "questions": [
                {"question": q, "value": format_pct(q.weight_pct if custom else equal[i])}
                for i, q in enumerate(group)
            ],
        })
    return groups


# --- Ponderación automática por nivel de dominio objetivo (matriz de competencias) -----------------

def integer_shares(raw) -> list[int]:
    """Reparte 100 en enteros proporcionales a `raw`; el último absorbe la diferencia para cuadrar a 100.

    3 partes iguales → 33 / 33 / 34. Si el redondeo dejara al último en 0 o negativo, usa mayor residuo.
    """
    values = [Fraction(v) for v in raw]
    total = sum(values)
    if not values or total <= 0:
        return [0] * len(values)
    if len(values) == 1:
        return [100]
    shares = [int(Fraction(100) * v / total + Fraction(1, 2)) for v in values[:-1]]
    last = 100 - sum(shares)
    if last <= 0 and values[-1] > 0:
        exact = [Fraction(100) * v / total for v in values]
        shares = [int(x) for x in exact]
        for i in sorted(range(len(values)), key=lambda i: (-(exact[i] - shares[i]), i))[: 100 - sum(shares)]:
            shares[i] += 1
        return shares
    return shares + [last]


@transaction.atomic
def auto_distribute(template) -> dict:
    """Calcula las ponderaciones de categorías y preguntas desde el nivel de dominio objetivo.

    Regla de la matriz: la ponderación de cada pregunta es proporcional a su nivel (N1–N4) dentro del
    cuestionario. Aquí se guarda en los dos niveles del motor: ponderación de cada categoría (suma de
    los niveles de sus preguntas) y de cada pregunta dentro de su categoría; ambos con enteros que
    suman 100 (la última absorbe la diferencia). Las preguntas que no ponderan quedan en 0.
    """
    from apps.questionnaires.models import Question

    questions = list(
        Question.objects.filter(section__template=template, qtype=Question.Type.SCALE)
        .order_by("section__order", "order")
    )
    weighted = [q for q in questions if q.is_weighted]
    no_level = [q.title for q in weighted if not q.target_level]
    if no_level:
        raise ValidationError(
            "Falta el nivel de dominio objetivo en: " + ", ".join(f"«{t}»" for t in no_level)
            + ". Captúralo o márcalas como «no pondera»."
        )
    no_category = [q.title for q in weighted if q.category_id is None]
    if no_category:
        raise ValidationError("Hay preguntas sin categoría: " + ", ".join(f"«{t}»" for t in no_category) + ".")

    links = list(template.template_categories.select_related("category").order_by("category__order", "category__name"))
    totals = {link.category_id: sum(q.target_level for q in weighted if q.category_id == link.category_id)
              for link in links}
    active = [link for link in links if totals[link.category_id] > 0]
    if not active:
        raise ValidationError("El cuestionario no tiene preguntas que ponderen.")

    summary = {}
    shares = dict(zip((link.pk for link in active), integer_shares([totals[l.category_id] for l in active])))
    for link in links:
        link.weight_pct = Decimal(shares.get(link.pk, 0))
        link.save(update_fields=["weight_pct"])
        summary[link.category.name] = int(link.weight_pct)
    for link in active:
        group = [q for q in questions if q.category_id == link.category_id]
        group_weighted = [q for q in group if q.is_weighted]
        for q, share in zip(group_weighted, integer_shares([q.target_level for q in group_weighted])):
            q.weight_pct = Decimal(share)
            q.save(update_fields=["weight_pct"])
        for q in group:
            if not q.is_weighted:
                q.weight_pct = Decimal(0)
                q.save(update_fields=["weight_pct"])
    return {"categories": summary, "questions": len(weighted), "unweighted": len(questions) - len(weighted)}
