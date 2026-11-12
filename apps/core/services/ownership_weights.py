"""Reglas de pesos de los cuestionarios de Ownership (spec 008).

Los pesos son porcentajes con **un decimal** y se manejan en *décimas enteras* (0–1000) para que
las sumas sean exactas: un grupo de pesos es válido solo si suma 1000 décimas (100.0%).

La pantalla del editor aplica la misma aritmética en el navegador; este módulo es la fuente de
verdad en el servidor (formularios, publicación e importación).
"""

from decimal import Decimal, InvalidOperation

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
        group = [q for q in questions if q.category_id == link.category_id]
        name = link.category.name
        if link.weight_pct > 0 and not group:
            errors.append(f"La categoría «{name}» pesa {link.weight_pct}% pero no tiene preguntas.")
            continue
        defined = [q.weight_pct for q in group if q.weight_pct is not None]
        if defined and len(defined) != len(group):
            errors.append(
                f"En «{name}» hay preguntas con peso y otras sin peso; define el peso de todas "
                "o deja todas en partes iguales."
            )
            continue
        if defined:
            error = group_error(f"Preguntas de {name}", defined)
            if error:
                errors.append(error)
            elif link.weight_pct > 0 and not any(w > 0 for w in defined):
                errors.append(
                    f"La categoría «{name}» pesa {link.weight_pct}% pero todas sus preguntas pesan 0."
                )
    return errors


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
        group = [q for q in questions if q.category_id == link.category_id]
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
