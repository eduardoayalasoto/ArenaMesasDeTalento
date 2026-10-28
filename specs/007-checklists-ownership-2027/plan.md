# Implementation Plan: Checklists de Ownership versión 2027

**Branch**: `main` (dir `007-checklists-ownership-2027`) | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-checklists-ownership-2027/spec.md`

## Summary

Publicar hoy en producción los 16 cuestionarios de Ownership v2 (checklists 2027) con criterio de aceptación,
entregable, formato, frecuencia, expectativa por nivel y guía por reactivo. Antes de publicar se corrige la
resincronización que borraba respuestas. Enfoque: 6 campos de texto opcionales en `Question` (1 migración aditiva),
conversión xlsx → YAML revisable (`scripts/checklists_2027_to_yaml.py` → `fixtures/questionnaires/2027/*.yaml`),
comando idempotente `import_questionnaire_version` que carga la v2 y opcionalmente la publica vía
`questionnaire_editor.publish_template` (ahora con validación e historial), desplegable "Ver criterio" en
`ownership_fill.html` y edición de los campos en el editor con un Django Form.

## Technical Context

**Language/Version**: Python 3.14, Django 6.0

**Primary Dependencies**: django-simple-history, PyYAML, openpyxl (solo en el script de conversión), daisyUI 5 + Tailwind v4 (CSS compilado), Alpine.js para el desplegable (estado local de UI)

**Storage**: Neon Postgres, esquema `"talento-app"`

**Testing**: pytest + pytest-django contra Neon (`--reuse-db`, nunca en paralelo), pruebas compactas por escenario, `password=None`

**Target Platform**: Vercel (push a `main` = deploy); migraciones aplicadas a mano a Neon (URL unpooled de `docs/neon.md`)

**Project Type**: web app Django monolítica (plantillas en `templates/`)

**Performance Goals**: el formulario de evaluación no agrega consultas (los campos viven en la misma fila de `Question`)

**Constraints**: sin Node; corrida de pruebas ≤ 3 min; no tocar el esquema `crm-app`; no romper evaluaciones de 2026-S1

**Scale/Scope**: 16 cuestionarios, 427 reactivos nuevos; 73+2 evaluaciones de 2026-S1 y 2.116 respuestas que deben quedar intactas

## Constitution Check

`.specify/memory/constitution.md` es la plantilla vacía; las reglas vigentes son las de `CLAUDE.md` del proyecto:

| Regla | Cumplimiento |
|---|---|
| Lógica en `apps/core/services/<dominio>.py` | Importación en `apps/core/services/questionnaire_import.py`; sync en `ownership_flow.py`; validación de publicación en `questionnaire_editor.py`. El comando solo orquesta. |
| `@login_required` + `@requires("clave")`; matriz de permisos | Sin vistas ni rutas nuevas; el editor sigue con `questionnaires.manage`. `test_access_coverage` debe seguir en verde. |
| Menú = datos | Sin cambios de menú. |
| Django Forms para todo POST | `save_question`/`add_question` pasan a `QuestionForm` (ModelForm) con validación de título único. |
| `transaction.atomic` al escribir 2+ modelos | Importación por puesto, sync y publicación son atómicos. |
| `select_related`/`prefetch_related` | Sin listados nuevos; el prefetch actual de preguntas ya trae los campos. |
| DESIGN_SYSTEM.md (daisyUI, Lucide, sin emojis, sin `style=`) | Desplegable con `collapse` de daisyUI/Alpine y `partials/icon.html`; badge Publicado con tokens existentes. |
| Pruebas compactas | 1 archivo nuevo `apps/core/tests/test_checklists_2027.py` con 3–4 escenarios encadenados. |

Gates: PASS (sin violaciones). Re-evaluado tras el diseño: PASS.

## Project Structure

### Documentation (this feature)

```text
specs/007-checklists-ownership-2027/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/import-command.md
├── reporte-revision.md      # revisión por cuestionario y estado resultante (FR-011)
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/questionnaires/models.py            # +6 campos en Question
apps/questionnaires/migrations/000X_*    # migración aditiva
apps/questionnaires/forms.py             # nuevo: QuestionForm
apps/questionnaires/views.py             # save_question/add_question con QuestionForm
apps/core/services/questionnaire_editor.py  # duplicar copia campos; publish valida + historial
apps/core/services/questionnaire_import.py  # nuevo: carga YAML → versión N
apps/core/services/ownership_flow.py     # sync seguro (FR-001)
apps/evaluations/views.py                # sync solo en edición
apps/core/management/commands/import_questionnaire_version.py  # nuevo
apps/core/management/commands/seed_questionnaires.py  # no revive v1
apps/core/management/commands/seed_all.py  # + v2 en entornos nuevos
scripts/checklists_2027_to_yaml.py       # conversión xlsx → YAML (ya generado)
fixtures/questionnaires/2027/{CD,ID,PM,UXUI}.yaml
templates/evaluations/ownership_fill.html   # "Ver criterio" + saltos de línea
templates/questionnaires/template_edit.html # campos nuevos (edición y solo lectura)
templates/partials/_checklist_details.html  # nuevo parcial compartido
templates/partials/status_badge.html     # PUBLICADO = success
docs/Checklists/Versión 2027/Metodologia_PM_referencia.md
apps/core/tests/test_checklists_2027.py
```

**Structure Decision**: se respeta la estructura existente (apps + `apps/core/services` + plantillas centralizadas).

## Complexity Tracking

Sin violaciones que justificar.
