"""Carga de la «Matriz de competencias y pesos por puesto» (Excel) como cuestionarios de Ownership.

Cada fila de la hoja «01 · Matriz por Puesto» es una competencia de un puesto:
  - **Familia** → categoría de la pregunta (Persona, Proyecto, Cliente, Metodología y técnica).
  - **Competencia** → título de la pregunta; **descripción del nivel esperado** → su texto.
  - **Bloque del catálogo** y **skills** → catálogo de bloques; los skills los hereda la pregunta.
  - **Nivel objetivo** (N1–N4) → ponderación automática; lo que pesa 0 queda como «no pondera».

Por cada puesto se crea una versión nueva del cuestionario (la anterior se archiva al publicar), con
ponderaciones enteras que suman 100 (la última absorbe la diferencia).
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils.text import slugify

from apps.core.services import ownership_weights, questionnaire_editor as editor

SHEET = "01 · Matriz por Puesto"
NO_BLOCK = "— (filtro de valores)"

FAMILIES = (
    ("Persona", "persona", 10),
    ("Proyecto", "proyecto", 20),
    ("Cliente", "cliente", 30),
    ("Metodología y técnica", "metodologia-tecnica", 40),
)
# Puesto de la matriz → (clave de la posición, clave del nivel o None)
POSITIONS = {
    "Analista": ("ANAL", None),
    "Consultor": ("CONSUL", None),
    "Consultor Sr": ("CONSUL", "SNR"),
    "Gerente": ("GERENTE", None),
}
LEGACY_CATEGORY_CODES = ("delivery_cliente", "desarrollo_producto", "herramientas_gestion", "actitud_persona")


def read_matrix(path) -> list[dict]:
    """Filas de la hoja 01 (una por puesto y competencia), sin los renglones de total."""
    import openpyxl

    workbook = openpyxl.load_workbook(path, data_only=True)
    if SHEET not in workbook.sheetnames:
        raise ValidationError(f"El archivo no tiene la hoja «{SHEET}».")
    rows = []
    for raw in workbook[SHEET].iter_rows(min_row=6, values_only=True):
        cells = raw[1:]
        if not cells[0] or str(cells[0]).startswith("Total"):
            continue
        puesto, order, family, competency, block, skills, level, weight, _scale, description = cells[:10]
        level_text = str(level or "")
        rows.append({
            "puesto": str(puesto).strip(), "order": int(order or 0), "family": str(family).strip(),
            "competency": str(competency).strip(),
            "block": None if not block or str(block).strip() == NO_BLOCK else str(block).strip(),
            "skills": [s.strip() for s in str(skills or "").split("·") if s.strip()],
            "target_level": int(level_text[1]) if level_text[:1] == "N" and level_text[1:2].isdigit() else None,
            "weight": float(weight) if isinstance(weight, (int, float)) else None,
            "description": str(description or "").strip(),
        })
    return rows


@transaction.atomic
def load(rows: list[dict]) -> list[dict]:
    """Crea y publica una versión nueva del cuestionario de cada puesto de la matriz. Devuelve el reporte."""
    from apps.catalog.models import Area, SeniorityLevel
    from apps.questionnaires.models import (
        BlockSkill, Category, CompetencyBlock, Question, QuestionnaireTemplate, Section, TemplateCategory,
    )

    # 1) Catálogo de bloques y skills
    blocks, order = {}, 0
    for row in rows:
        if row["block"] and row["block"] not in blocks:
            order += 1
            block, _ = CompetencyBlock.objects.get_or_create(
                code=slugify(row["block"])[:60], defaults={"name": row["block"], "order": order})
            block.name, block.is_active = row["block"], True
            block.save(update_fields=["name", "is_active"])
            for i, skill in enumerate(row["skills"], 1):
                BlockSkill.objects.get_or_create(block=block, name=skill, defaults={"order": i})
            blocks[row["block"]] = block

    # 2) Categorías = familias de la matriz
    categories = {}
    for name, code, position in FAMILIES:
        category, _ = Category.objects.get_or_create(code=code, defaults={"name": name, "order": position})
        category.name, category.order, category.is_active = name, position, True
        category.save(update_fields=["name", "order", "is_active"])
        categories[name] = category

    report = []
    for puesto, (area_code, level_code) in POSITIONS.items():
        puesto_rows = sorted((r for r in rows if r["puesto"] == puesto), key=lambda r: r["order"])
        if not puesto_rows:
            continue
        area = Area.objects.filter(code=area_code).first()
        level = SeniorityLevel.objects.filter(code=level_code).first() if level_code else None
        if area is None or (level_code and level is None):
            raise ValidationError(f"No existe la posición «{puesto}» ({area_code}/{level_code or 'sin nivel'}) en el sistema.")

        existing = QuestionnaireTemplate.objects.filter(
            kind=QuestionnaireTemplate.Kind.OWNERSHIP, area=area, level=level).order_by("-version")
        draft = existing.filter(status=QuestionnaireTemplate.Status.BORRADOR).first()
        source = existing.filter(status=QuestionnaireTemplate.Status.PUBLICADO).first() or existing.first()
        if draft is None and source is None:
            template = editor.create_template(QuestionnaireTemplate.Kind.OWNERSHIP, area=area, level=level)
        else:
            template = draft or editor.duplicate_as_new_version(source)
        Section.objects.filter(template=template).delete()
        TemplateCategory.objects.filter(template=template).delete()

        families = [name for name, _code, _pos in FAMILIES if any(r["family"] == name for r in puesto_rows)]
        for position, family in enumerate(families, 1):
            TemplateCategory.objects.create(template=template, category=categories[family], weight_pct=Decimal(0))
            section = Section.objects.create(template=template, title=family, order=position)
            for number, row in enumerate((r for r in puesto_rows if r["family"] == family), 1):
                weighted = bool(row["weight"]) and row["weight"] > 0
                Question.objects.create(
                    section=section, order=number, title=row["competency"], text=row["description"],
                    category=categories[family], block=blocks.get(row["block"]) if row["block"] else None,
                    target_level=row["target_level"], is_weighted=weighted,
                    weight_pct=None if weighted else Decimal(0),
                )
        summary = ownership_weights.auto_distribute(template)
        editor.publish_template(template)
        report.append({
            "puesto": puesto, "template": template, "questions": len(puesto_rows), "categories": summary["categories"],
            "max_deviation": _max_deviation(template, puesto_rows),
        })

    Category.objects.filter(code__in=LEGACY_CATEGORY_CODES).update(is_active=False)
    return report


def _max_deviation(template, puesto_rows) -> float:
    """Mayor diferencia (en puntos porcentuales) entre la ponderación efectiva y la del Excel."""
    from apps.questionnaires.models import Question

    links = {link.category_id: link.weight_pct for link in template.template_categories.all()}
    by_title = {r["competency"]: (r["weight"] or 0) * 100 for r in puesto_rows}
    worst = 0.0
    for q in Question.objects.filter(section__template=template):
        effective = float(links.get(q.category_id, 0)) * float(q.weight_pct or 0) / 100 if q.is_weighted else 0.0
        worst = max(worst, abs(effective - by_title.get(q.title, 0)))
    return round(worst, 2)
