"""Convierte el checklist de Desarrolladores (xlsx de Talento) a un fixture YAML revisable (Área Desarrollo).

Uso:  python scripts/checklists_dev_to_yaml.py "C:/ruta/Checklist de Actividades Desarrolladores.xlsx"
Escribe fixtures/questionnaires/2027/DEV.yaml (4 cuestionarios: Desarrollador Jr / Mid / Snr y Gerente de Desarrollo).
Reusa las reglas de `checklists_2027_to_yaml.py`: sin categorías el cuestionario queda en «General» al 100% y todas las
preguntas pesan lo mismo; el orden es el de la hoja. Falla si una Actividad se repite sin subtema curado.
"""

import sys
from pathlib import Path

import openpyxl
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import checklists_2027_to_yaml as base  # noqa: E402

# hoja -> (clave de la posición, clave del nivel o None)
SHEETS = {
    "jr": ("DEV", "JR"),
    "mid": ("DEV", "MID"),
    "sr": ("DEV", "SNR"),
    "gerente": ("GERDES", None),
}


def main(path):
    specific = base.v1_specific_titles()
    wb = openpyxl.load_workbook(path, data_only=True)
    templates, errors = [], []
    for ws in wb.worksheets:
        if not ws.title.lower().startswith("checklist"):
            continue
        area, level = SHEETS[ws.title.split()[-1].lower()]
        rows, seen = [], set()
        for row in base.read_sheet(ws):
            if row["activity"] in seen:   # copia posterior de una actividad ya listada: se conserva la primera aparición
                print(f"  (se omite la repetida «{row['activity']}» de la hoja {ws.title})")
                continue
            seen.add(row["activity"])
            rows.append(row)
        questions, missing, dupes = base.build_questions(rows, specific, f"{area}/{level}")
        errors += missing + dupes
        templates.append({"area": area, "level": level, "questions": questions})
        print(f"{area}/{level or 'sin nivel'}: {len(questions)} reactivos")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)
    order = {("DEV", "JR"): 0, ("DEV", "MID"): 1, ("DEV", "SNR"): 2, ("GERDES", None): 3}
    templates.sort(key=lambda t: order[(t["area"], t["level"])])
    out = base.OUT / "DEV.yaml"
    doc = {"source": f"Checklist de Actividades Desarrolladores ({Path(path).name})", "templates": templates}
    out.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100000), encoding="utf-8")
    print("Escribí", out)


if __name__ == "__main__":
    main(sys.argv[1])
