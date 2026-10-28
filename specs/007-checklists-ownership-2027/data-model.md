# Data Model: Checklists de Ownership versión 2027

## Question (cambio aditivo)

| Campo | Tipo | Etiqueta (UI) | Origen en Excel |
|---|---|---|---|
| `acceptance_criteria` | TextField, blank | Criterio de aceptación | Criterio de aceptación |
| `deliverable` | TextField, blank | Entregable | Entregable |
| `deliverable_format` | TextField, blank | Formato | Formato |
| `frequency` | TextField, blank | Frecuencia | Frecuencia |
| `level_expectation` | TextField, blank | Expectativa por nivel | Expectativas por nivel de seniority |
| `guidance` | TextField, blank | Comentarios y guía | Comentarios |

Propiedad `has_checklist_details` → True si alguno tiene contenido. Valores "n/a" se guardan vacíos.
Sin cambios en `title` (máx. 200), `text`, `qtype` (SCALE), `weight` (1), `allow_na` (True), `is_required` (True).

## QuestionnaireTemplate (sin cambios de esquema)

Estados: BORRADOR → PUBLICADO → ARCHIVADO. Un solo PUBLICADO por (kind, area, level).
Reglas nuevas de publicación: ≥ 1 reactivo SCALE, títulos únicos dentro del cuestionario, escala presente; el archivado del anterior queda en historial.

Estado objetivo en producción tras la feature:

| Puesto | v1 | v2 |
|---|---|---|
| 16 Ownership | ARCHIVADO | PUBLICADO |
| CD/JR | ARCHIVADO (v3 borrador sobrante → ARCHIVADO) | PUBLICADO |
| Entrega de Valor | PUBLICADO | — |

## OwnershipEvaluation (sin cambios de esquema)

Queda ligada a su versión. Transición de cuestionario solo por cambio de puesto (área/nivel) con periodo ABIERTO, en borrador y nunca enviada.

## Fixture YAML `fixtures/questionnaires/2027/<AREA>.yaml`

```yaml
source: docs/Checklists/Versión 2027/<libro>.xlsx
templates:
  - area: CD
    level: JR
    questions:
      - title: "..."
        text: "..."
        acceptance_criteria: "..."     # campos opcionales, se omiten si vacíos
        deliverable: "..."
        deliverable_format: "..."
        frequency: "..."
        level_expectation: "..."
        guidance: "..."
```
