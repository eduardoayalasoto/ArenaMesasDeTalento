"""Matriz de Competencias y Pesos por Puesto (Consultoría) → YAML de importación (spec 008).

Uso (con la .venv del proyecto):
    python scripts/matriz_consultoria_to_yaml.py "docs/Matrices/Matriz de Competencias y Pesos por Puesto v1.1.xlsx" \
        fixtures/questionnaires/cons/CONS.yaml

Lee la hoja «01 · Matriz por Puesto» (una fila por puesto × competencia), agrupa cada competencia en
una categoría según su «Bloque del catálogo», calcula los pesos de categoría y de pregunta con
un decimal sumando exacto 100.0 (mayor residuo) y escribe el YAML que carga
`manage.py import_questionnaire_version --target-version 1`. Imprime un reporte de desviaciones
contra los pesos originales y **falla** si alguna suma no es 100.0 o si una competencia se desvía
más de 0.15 puntos porcentuales de su peso original.
"""

import copy
import sys
from pathlib import Path

import openpyxl
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from apps.core.services import ownership_weights as ow  # noqa: E402  (no requiere Django configurado)

PUESTOS = {"Analista": "JR", "Consultor": "MID", "Consultor Sr": "SNR", "Gerente": "LEAD"}

CATEGORIES = [
    ("delivery_cliente", "Delivery al cliente"),
    ("desarrollo_producto", "Desarrollo de producto"),
    ("herramientas_gestion", "Herramientas de gestión"),
    ("actitud_persona", "Actitud y persona"),
]

# Bloque del catálogo (columna F de la matriz) → categoría (spec 008, FR-022).
BLOCK_TO_CATEGORY = {
    "Gestión de cliente y stakeholders": "delivery_cliente",
    "Dimensionamiento de alcance y complejidad": "delivery_cliente",
    "Diagnóstico y análisis de negocio": "delivery_cliente",
    "Gestión del cambio y adopción": "delivery_cliente",
    "Análisis de datos y validación": "desarrollo_producto",
    "Especificación y modelado del problema": "desarrollo_producto",
    "IA como productividad": "desarrollo_producto",
    "Disciplina de WoW y gestión": "herramientas_gestion",
    "Competencia de persona": "actitud_persona",
    "— (filtro de valores)": "actitud_persona",
}

VALUES_COMPETENCY = "Apego a los valores de Arena Analytics"
VALUES_GUIDANCE = (
    "Se califica de 1 a 4 (3 = cumple). No pondera en el score: sirve como filtro de valores; "
    "una calificación baja se ve en el informe."
)

SCALE = [
    {"value": 1, "label": "No cumple", "order": 1,
     "description": "No cumple con lo mínimo esperado para su rol en el proyecto."},
    {"value": 2, "label": "Necesita mejorar", "order": 2,
     "description": "Cumple parcialmente con lo esperado para su rol en el proyecto."},
    {"value": 3, "label": "Cumple satisfactoriamente", "order": 3,
     "description": "Cumple en su totalidad y de manera satisfactoria con lo esperado para su rol. "
                    "La descripción del nivel esperado está redactada contra esta calificación."},
    {"value": 4, "label": "Excede", "order": 4,
     "description": "Excede frecuentemente las expectativas de acuerdo a su rol y/o cumple funciones "
                    "de un rol superior al actual."},
    {"value": None, "label": "N/A", "order": 5,
     "description": "No aplica en este periodo por razones justificadas. No entra al promedio."},
]
SCALE_NOTE = (
    "Califica cada competencia del 1 al 4 contra el nivel esperado para tu puesto (3 = cumple "
    "satisfactoriamente). «Apego a los valores» se califica pero no pondera en el score."
)

MAX_DEVIATION_PP = 0.15


def read_rows(path):
    workbook = openpyxl.load_workbook(path, data_only=True)
    sheet = next((ws for ws in workbook.worksheets if ws.title.startswith("01")), None)
    if sheet is None:
        raise SystemExit("No encontré la hoja «01 · Matriz por Puesto».")
    rows = []
    for row in sheet.iter_rows(min_row=6, values_only=True):
        puesto, competency = row[1], row[4]
        if puesto in PUESTOS and competency:
            rows.append({
                "puesto": puesto, "competency": str(competency).strip(), "block": str(row[5]).strip(),
                "skills": row[6], "target": row[7], "weight": row[8], "description": row[10],
            })
    if not rows:
        raise SystemExit("La hoja no trae filas de puesto × competencia.")
    return rows


def raw_weight(row):
    value = row["weight"]
    return float(value) if isinstance(value, (int, float)) else 0.0


def build_template(puesto, rows):
    """(plantilla YAML, reporte) de un puesto; lanza SystemExit si algo no cuadra."""
    by_category = {code: [] for code, _ in CATEGORIES}
    for row in rows:
        code = BLOCK_TO_CATEGORY.get(row["block"])
        if code is None:
            raise SystemExit(f"{puesto}: el bloque «{row['block']}» ({row['competency']}) no tiene categoría.")
        by_category[code].append(row)

    raw_total = sum(raw_weight(r) for r in rows)
    category_raw = {code: sum(raw_weight(r) for r in group) for code, group in by_category.items()}
    category_weights = dict(zip(
        [c for c, _ in CATEGORIES],
        ow.normalize_to_100([category_raw[c] for c, _ in CATEGORIES]),
    ))

    questions, report, worst = [], [], 0.0
    for code, name in CATEGORIES:
        group = by_category[code]
        if not group:
            continue
        weights = ow.normalize_to_100([raw_weight(r) for r in group])
        for r, q_weight in zip(group, weights):
            effective = float(category_weights[code]) * float(q_weight) / 100
            original = raw_weight(r) / raw_total * 100 if raw_total else 0.0
            worst = max(worst, abs(effective - original))
            skills = f"Skills: {r['skills']}" if r["skills"] else ""
            guidance = " · ".join(x for x in (
                VALUES_GUIDANCE if r["competency"] == VALUES_COMPETENCY else "", skills, f"Bloque: {r['block']}"
            ) if x)
            questions.append({
                "title": r["competency"], "category": code, "weight": float(q_weight),
                "text": str(r["description"] or "").strip(),
                "level_expectation": str(r["target"] or "").strip(),
                "guidance": guidance,
            })
        report.append((name, category_raw[code] / raw_total * 100 if raw_total else 0.0, float(category_weights[code])))

    if worst > MAX_DEVIATION_PP:
        raise SystemExit(f"{puesto}: una competencia se desvía {worst:.2f} pp de su peso original (máx. {MAX_DEVIATION_PP}).")
    for code, _ in CATEGORIES:
        group = [q for q in questions if q["category"] == code]
        if group and ow.group_error(f"{puesto} · {code}", [q["weight"] for q in group]):
            raise SystemExit(ow.group_error(f"{puesto} · {code}", [q["weight"] for q in group]))
    error = ow.group_error(f"{puesto} · categorías", list(category_weights.values()))
    if error:
        raise SystemExit(error)

    template = {
        "area": "CONS", "level": PUESTOS[puesto], "scale_note": SCALE_NOTE, "scale": copy.deepcopy(SCALE),
        "categories": [
            {"code": code, "name": name, "weight": float(category_weights[code])}
            for code, name in CATEGORIES if by_category[code]
        ],
        "questions": questions,
    }
    return template, report, worst


def main(argv):
    if len(argv) != 3:
        raise SystemExit(__doc__)
    source, target = Path(argv[1]), Path(argv[2])
    rows = read_rows(source)
    templates = []
    for puesto in PUESTOS:
        puesto_rows = [r for r in rows if r["puesto"] == puesto]
        template, report, worst = build_template(puesto, puesto_rows)
        templates.append(template)
        print(f"\n{puesto} ({PUESTOS[puesto]}): {len(puesto_rows)} competencias · desviación máx. {worst:.3f} pp")
        for name, original, final in report:
            print(f"  {name:<26} matriz {original:6.2f}%  →  cargado {final:5.1f}%")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        yaml.safe_dump({"source": source.name, "templates": templates}, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )
    print(f"\nEscribí {target} con {len(templates)} cuestionarios.")


if __name__ == "__main__":
    main(sys.argv)
