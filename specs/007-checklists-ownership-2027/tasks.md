# Tasks: Checklists de Ownership versión 2027

**Input**: `specs/007-checklists-ownership-2027/` (spec, plan, research, data-model, contracts, quickstart)
**Tests**: sí (CLAUDE.md: pruebas con el cambio, compactas por escenario).

## Phase 1: Setup

- [x] T001 Generar los fixtures revisables con `scripts/checklists_2027_to_yaml.py` → `fixtures/questionnaires/2027/{CD,ID,PM,UXUI}.yaml` (16 puestos, títulos únicos; research D2/D3)
- [x] T002 [P] Documentar la metodología de PM en `docs/Checklists/Versión 2027/Metodologia_PM_referencia.md` (US5)

## Phase 2: Foundational

- [x] T003 Agregar `acceptance_criteria`, `deliverable`, `deliverable_format`, `frequency`, `level_expectation`, `guidance` (TextField blank) y la propiedad `has_checklist_details` a `Question` en `apps/questionnaires/models.py`
- [x] T004 Crear la migración aditiva en `apps/questionnaires/migrations/` con `makemigrations questionnaires`

## Phase 3: User Story 1 — Sin pérdida de respuestas (P1)

**Independent test**: borrador v1 con respuestas + v2 publicada → conserva v1; cambio de nivel en periodo ABIERTO → cambia; periodo CERRADO o evaluación reabierta → no cambia.

- [x] T005 [US1] Reescribir `sync_evaluation_template` en `apps/core/services/ownership_flow.py`: atómica; solo si no está enviada, nunca fue enviada (historial), `period.status == ABIERTO` y área/nivel del template ≠ área/nivel del usuario (research D5)
- [x] T006 [US1] En `apps/evaluations/views.py::_render_ownership`, llamar al sync solo con `editing=True` y si `_can_edit_answers(request.user, evaluation)`
- [x] T007 [US1] Escenario de prueba US1 (los 4 casos) en `apps/core/tests/test_checklists_2027.py`

## Phase 4: User Story 2 — "Ver criterio" en la evaluación (P1)

**Independent test**: evaluación sobre v2 muestra el desplegable con solo los campos con contenido; v1 se ve igual que antes.

- [x] T008 [P] [US2] Crear `templates/partials/_checklist_details.html` (desplegable daisyUI `collapse` + Alpine, etiquetas de data-model.md, `whitespace-pre-line`, icono Lucide vía `partials/icon.html`)
- [x] T009 [US2] Incluir el parcial en `templates/evaluations/ownership_fill.html` y aplicar `whitespace-pre-line` a `question.text`
- [x] T010 [US2] Prueba de render (GET de la evaluación contiene "Ver criterio" y el criterio; v1 sin desplegable) en `apps/core/tests/test_checklists_2027.py`

## Phase 5: User Story 3 — Editor con campos del checklist (P2)

**Independent test**: editar el criterio en un borrador persiste; duplicar copia los campos; título duplicado se rechaza.

- [x] T011 [P] [US3] Crear `QuestionForm` (ModelForm: title, text + 6 campos; título no vacío, ≤ 200, único en el cuestionario) en `apps/questionnaires/forms.py`
- [x] T012 [US3] Usar `QuestionForm` en `save_question` y `add_question` de `apps/questionnaires/views.py`; errores con `messages.error`
- [x] T013 [US3] En `apps/core/services/questionnaire_editor.py::duplicate_as_new_version`, copiar los 6 campos
- [x] T014 [US3] En `apps/core/services/questionnaire_editor.py::publish_template`, validar (≥ 1 SCALE, títulos únicos, escala) con `ValidationError` y archivar con `save()` por instancia; manejar el error en `apps/questionnaires/views.py` (research D8)
- [x] T015 [US3] En `templates/questionnaires/template_edit.html`: campos nuevos en el formulario de edición y en "agregar", `_checklist_details` en solo lectura, `whitespace-pre-line`
- [x] T016 [P] [US3] `templates/partials/status_badge.html`: PUBLICADO → success (FR-016)
- [x] T017 [US3] Escenario de prueba editor (guardar campos, duplicar, título duplicado, publicar inválido) en `apps/core/tests/test_checklists_2027.py`

## Phase 6: User Story 4 — 16 v2 publicados en producción (P1)

**Independent test**: tras importar con `--publish`: 16 v2 PUBLICADO, v1 ARCHIVADO, respuestas intactas; re-ejecutar no crea registros.

- [x] T018 [US4] Implementar `apps/core/services/questionnaire_import.py` (`import_version(data, version, publish)` por puesto, atómico; reglas del contrato `contracts/import-command.md`; escala/nota copiadas de la v1; archiva borradores mayores sin respuestas)
- [x] T019 [US4] Crear `apps/core/management/commands/import_questionnaire_version.py` (`--dir`, `--target-version`, `--publish`, `--dry-run`)
- [x] T020 [US4] `apps/core/management/commands/seed_questionnaires.py`: omitir puestos con versión > 1; `apps/core/management/commands/seed_all.py`: invocar la importación 2027 publicada (research D9)
- [x] T021 [US4] Escenario de prueba importación (crea, idempotente, rechaza con respuestas, publica y archiva v1, evaluación existente conserva v1) en `apps/core/tests/test_checklists_2027.py`

## Phase 7: Polish & entrega

- [x] T022 Correr `test_checklists_2027.py`, `test_questionnaire_editor.py`, `test_ownership_flow.py`, `test_access_coverage.py` (≤ 3 min)
- [x] T023 Compilar CSS con `.\build_css.ps1` (clases nuevas) y versionar `static/css/`
- [x] T024 Aplicar la migración a Neon producción (URL unpooled de `docs/neon.md`)
- [x] T025 Actualizar `docs/CONTEXTO_Sistema.md` (campos del reactivo, comando de importación, v2 vigente)
- [x] T026 Commit + push a `main` (deploy Vercel) y **esperar a que el deploy con el sync corregido esté activo** (analyze F1)
- [x] T027 Importación en producción: registrar conteo de respuestas, `--dry-run`, luego `--publish`; volver a contar (SC-002) y verificar quickstart paso 4
- [x] T028 Escribir `specs/007-checklists-ownership-2027/reporte-revision.md` (por cuestionario: reactivos, títulos ajustados, criterios de revisión, estado final, conteos antes/después), commit + push

## Dependencies

- T003–T004 bloquean US2, US3 y US4. US1 (T005–T007) es independiente y **debe estar en producción antes de T025**.
- T018 depende de T013/T014 (publicación validada). Orden de producción: T024 (migrar) → T026 (push + deploy activo) → T027 (importar/publicar). Publicar antes del deploy dejaría activo el sync viejo y podría borrar respuestas de S1.
- Paralelo: T008 ∥ T011 ∥ T016; T005 ∥ T003.

## Implementation Strategy

Todo el alcance hoy (el usuario lo pidió). Orden: Foundational → US1 → US2/US3 → US4 → producción (migrar → importar → push). MVP técnico mínimo seguro = T003–T007 + T018–T019.
