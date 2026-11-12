# Implementation Plan: Ownership ponderado por categorías (todas las áreas) + Consultoría

**Branch**: `main` (directorio `008-ownership-ponderado-categorias`) | **Date**: 2026-11-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-ownership-ponderado-categorias/spec.md`

## Summary

El pilar Ownership pasa de promedio simple a **promedio ponderado por categorías** para todas las áreas. Cada pregunta de escala pertenece a una `Category` (catálogo común); cada cuestionario define el peso de sus categorías (`TemplateCategory`) y, opcionalmente, el peso de cada pregunta dentro de su categoría. Todo cuestionario existente migra a la categoría «General» al 100% con preguntas en partes iguales, de forma que el cálculo da **exactamente** el mismo resultado (se verifica con un comando que recalcula todas las evaluaciones y compara). El editor de cuestionarios gana edición de pesos con **validación visible en vivo** (Alpine, aritmética en décimas enteras) y la misma validación en el servidor y la importación. Se agrega el catálogo `Position` (área × nivel → nombre visible) y se cargan 4 cuestionarios de CONS desde la matriz de Dirección de Consultoría (xlsx → YAML → importación idempotente). El motor de la calificación final (`final_score`, `PillarWeight`) no se toca.

Abordaje técnico: lógica en servicios (`scoring`, `ownership_weights`, `questionnaire_editor`, `questionnaire_import`, `positions`), migraciones **aditivas** (la columna `Question.weight` actual queda sin uso y se añade `weight_pct`), vistas delgadas con Django Forms, y desglose por categoría calculado a partir de las respuestas (no se congela en la evaluación).

## Technical Context

**Language/Version**: Python 3.12 (Vercel) / 3.14 (local), Django 6

**Primary Dependencies**: Django, django-simple-history, openpyxl (ya usado en exportes), PyYAML (ya usado en importación), Tailwind v4 + daisyUI 5, Alpine.js, htmx, Lucide (todo vendorizado)

**Storage**: SQLite en local; Postgres (Neon) en producción, esquema `"talento-app"`; migraciones se aplican a Neon con la URL unpooled antes del push

**Testing**: pytest contra Neon con `--reuse-db`, nunca en paralelo; pruebas compactas por escenario; `scripts/pytest_changed.py` local (≤ 3 min); suite completa en CI

**Target Platform**: Aplicación web interna (Vercel + Neon)

**Project Type**: Aplicación web Django monolítica (apps en `apps/`, plantillas en `templates/`)

**Performance Goals**: Calcular el desglose de una evaluación (≤ ~40 preguntas) en una sola consulta de respuestas + una de preguntas; el editor responde en la misma petición sin consultas por pregunta (prefetch)

**Constraints**: Ningún score existente cambia (SC-001); pesos con máximo 1 decimal y suma exacta 100.0; sin `fetch` en Alpine para código nuevo, sin `style=` inline, sin emojis, diálogos como modal (DESIGN_SYSTEM.md); permisos por matriz de perfiles

**Scale/Scope**: 65 usuarios (13 de CONS), 17 + 4 cuestionarios de Ownership, ~420 reactivos actuales + ~60 de CONS, 73+ evaluaciones históricas a verificar

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento | Nota |
|---|---|---|
| I. Permisos = matriz de perfiles | **Cumple** | Las pantallas nuevas (Puestos, Categorías) reciben clave en `registry.py`, fila en `seed.py` y `legacy.py`; el editor de cuestionarios reutiliza `questionnaires.manage`. `test_access_coverage.py` en verde. Ninguna decisión por rol. |
| II. Lógica en servicios | **Cumple** | Cálculo en `scoring.py`; reglas de pesos en `ownership_weights.py` (nuevo); versionado/publicación en `questionnaire_editor.py`; vistas validan con Forms y delegan. |
| III. Integridad de evaluaciones | **Cumple con salvaguarda** | Publicadas son inmutables (solo BORRADOR se edita, como hoy). La migración a «General» solo agrega categoría y pesos que no alteran el resultado y se **demuestra** con `verify_ownership_scores` antes y después. Los scores guardados de evaluaciones enviadas no se recalculan salvo reapertura (idéntico resultado). Importación rechaza versiones con respuestas. |
| IV. Diseño único con arena-crm | **Cumple** | UI con daisyUI/tema `arena`, Lucide, htmx; Alpine solo para el total en vivo. Cambios de UI pasan por `frontend-auditor`. Componentes compartidos `_nav_menu`/`_breadcrumb` no se tocan (el menú se amplía vía `navigation.py`). |
| V. Pruebas con cada cambio | **Cumple** | Pruebas compactas por escenario (ver Estructura). Prueba de no regresión del cálculo y verificación sobre datos reales. |
| VI. Datos de producción | **Cumple** | Migraciones aditivas (campos nuevos, tablas nuevas, datos «General» y Puestos); orden migrar → desplegar → cargar CONS; simulación `--dry-run` y conteos antes/después registrados en la spec. Esquema `"talento-app"`. |
| VII. Español de México, código en inglés | **Cumple** | Textos de UI en español; identificadores en inglés. |

Sin violaciones; no hay Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/008-ownership-ponderado-categorias/
├── plan.md
├── spec.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cons-yaml.md          # esquema del YAML de importación con categorías y pesos
│   └── weights-ui.md         # contrato de las pantallas de pesos y del JSON de autoguardado
├── checklists/requirements.md
└── tasks.md                  # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
apps/
├── questionnaires/
│   ├── models.py                       # Category, TemplateCategory; Question.category / weight_pct
│   ├── forms.py                        # QuestionForm (+category), CategoryWeightsForm, QuestionWeightsForm
│   ├── views.py                        # acciones de pesos en template_edit; categorías de la plantilla
│   └── migrations/0003_*.py, 0004_*.py # esquema; datos «General»
├── catalog/
│   ├── models.py                       # Position; Project.suggested_evaluator
│   ├── forms.py, views.py, urls.py     # position_admin, category_admin; campo en ProjectForm
│   └── migrations/0011_*.py, 0012_*.py # esquema; siembra de Puestos
├── evaluations/views.py                # ownership_start preselecciona; _render_ownership/autosave con desglose
├── dashboards/views.py                 # desglose por categoría del pilar en el informe
└── core/
    ├── services/
    │   ├── scoring.py                  # score ponderado y desglose (funciones puras)
    │   ├── ownership_weights.py        # validación de pesos y reparto en partes iguales (mayor residuo)
    │   ├── positions.py                # nombre de puesto con caché corta
    │   ├── questionnaire_editor.py     # duplicar con categorías; validar publicación
    │   └── questionnaire_import.py     # importar con categorías, pesos y escala propia
    ├── templatetags/                   # filtro `puesto`
    ├── management/commands/
    │   ├── import_questionnaire_version.py   # admite --target-version 1 si el YAML trae escala
    │   └── verify_ownership_scores.py        # recalcula y compara contra el score guardado
    ├── navigation.py                   # Catálogos: Puestos y Categorías
    └── tests/                          # test_scoring_weighted, test_ownership_weights, test_positions,
                                        # test_cons_import, test_questionnaire_editor (ampliado)
scripts/matriz_consultoria_to_yaml.py   # xlsx de la matriz → fixtures/questionnaires/cons/CONS.yaml
fixtures/questionnaires/cons/CONS.yaml  # resultado versionado en git
docs/Matrices/Matriz de Competencias y Pesos por Puesto v1.1.xlsx   # fuente
templates/
├── questionnaires/template_edit.html   # pesos con total en vivo
├── catalog/position_admin.html, category_admin.html
├── evaluations/ownership_fill.html, ownership_start.html, _category_scores.html
└── dashboards/_results_body.html       # desglose por categoría
```

**Structure Decision**: aplicación Django existente; no se crea app nueva. `Category`/`TemplateCategory` viven en `questionnaires` (son parte del cuestionario); `Position` y `suggested_evaluator` en `catalog` (catálogos y proyectos); la lógica en `core/services`, como manda la constitución.

## Complexity Tracking

Sin violaciones que justificar.
