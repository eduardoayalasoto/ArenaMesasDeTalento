# Contrato: `apps/learning/data/planes_2026.json`

Es el único insumo de `manage.py import_learning_plans`. Se genera, se revisa y se versiona en git:

```text
python -I scripts/extract_plans_html.py <carpeta_html> raw_plans.json                  # volcado crudo de los 4 HTML
python -I scripts/build_plans_json.py <excel.xlsx> raw_plans.json \
          apps/learning/data/planes_2026.json specs/006-…/revision-datos-propuestos.md   # cruce + criterio técnico
```

El cruce aplica R7/R12. Los ajustes por curso del criterio técnico viven en `scripts/plans_overrides.py`, cada uno con su motivo; nunca contradicen un dato que el material da una sola vez.

```json
{
  "year": 2026,
  "plans": [
    {"area": "PM", "year": 2026, "title": "Plan de Capacitación PM 2026",
     "start_month": 5, "end_month": 12, "hours_min": 3, "hours_max": 10,
     "intro": "Catálogo sugerido, no currícula obligatoria…",
     "type_notes": {"ESTRUCTURADO": "texto de la guía", "PUNTUAL": "…"},
     "items": [{"course": "<key>", "levels": ["JR", "MID"], "note": "", "order": 1}]}
  ],
  "courses": [
    {"key": "coursera.org/learn/ai-for-everyone", "url": "https://www.coursera.org/learn/ai-for-everyone",
     "name": "AI for Everyone", "provider": "Coursera", "kind": "ESTRUCTURADO", "focus": "VERTICAL",
     "duration_hours": 6.0, "reference_cost": null, "currency": "MXN", "ko": true,
     "proposed": ["focus"], "why": "enfoque: …", "aliases": []}
  ]
}
```

## Campos

- **`key`**: la liga normalizada (R3). Para una certificación es `cert:<examen>`: el examen es un elemento propio, aparte de su curso de preparación.
- **`kind`** (tipo de aprendizaje) y **`focus`** (enfoque): dimensiones independientes. "Aprendizaje Horizontal/Vertical" del material solo fija `focus`.
- **`proposed`**: los datos que el material no da y que se asignaron con criterio técnico. **`why`** da el motivo. Todos se listan en `revision-datos-propuestos.md`.
- **`ko`**: el curso recibe la etiqueta "KO". No existe agrupación KO.
- **`levels`**: niveles del curso en ese plan (`JR | MID | SNR | LEAD`); vacío = "Todos los niveles".
- **`reference_cost`**: `0` si la guía dice "Gratis"; el costo del examen en las certificaciones; `null` si no se indica.

## Reglas del importador

- **Validación previa:** un archivo inválido se rechaza **completo** con sus motivos, sin escribir nada. Es inválido si trae tipo o enfoque fuera de catálogo, un área o nivel inexistente, o un curso referido que no existe.
- **Identidad:** un curso se reconoce por su liga normalizada; sin liga, por nombre + proveedor.
- **Cursos que ya existen:** solo se completan sus campos vacíos (duración, costo, liga). Tipo, enfoque y lo que Talento editó **no se tocan**.
- **Planes:** se crean PUBLICADOS. Si ya existe uno en borrador, se publica. Si Talento lo archivó, se respeta.
- **Cursos dentro de un plan:** los que ya están no se modifican (sus niveles y su nota se quedan como los dejó Talento); solo se agregan los que faltan.
- **`--dry-run`:** ejecuta todo y revierte al final.
