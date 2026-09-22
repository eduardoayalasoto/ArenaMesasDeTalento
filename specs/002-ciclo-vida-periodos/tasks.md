---

description: "Task list template for feature implementation"
---

# Tasks: Ciclo de vida y continuidad de Periodos de Evaluación

**Input**: Design documents from `/specs/002-ciclo-vida-periodos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: se incluyen tareas de prueba porque el proyecto ya tiene una
suite `pytest`/`pytest-django` establecida y un archivo de tests por cada
flujo de negocio equivalente (`test_ownership_flow.py`,
`test_value_delivery_flow.py`, `test_feedback_session.py`, etc.); esta
feature sigue el mismo patrón con `apps/core/tests/test_period_lifecycle.py`.

**Organization**: Tareas agrupadas por historia de usuario (US1-US5 de
`spec.md`) para permitir implementación y prueba independiente de cada una.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Story]**: Historia de usuario a la que pertenece (US1-US5)
- Cada tarea incluye la ruta de archivo exacta

## Phase 1: Setup

**Purpose**: Preparar el terreno sin tocar aún reglas de negocio

- [X] T001 Ejecutar `pytest apps/core/tests/` completo como línea base antes de cualquier cambio (confirmar que la suite actual pasa en verde) — 100% verde antes de tocar código
- [X] T002 [P] Crear el módulo `apps/core/services/period_lifecycle.py` con docstring del propósito (orquestación del ciclo de vida de `EvaluationPeriod`) y los imports base (`transaction`, `ValidationError`, `EvaluationPeriod`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestructura de la que dependen las 5 historias de usuario

**⚠️ CRITICAL**: Ninguna historia de usuario puede implementarse hasta que esta fase esté completa

- [X] T003 Agregar `models.UniqueConstraint(fields=["status"], condition=models.Q(status="ABIERTO"), name="unique_open_period")` a `EvaluationPeriod.Meta.constraints` en `apps/catalog/models.py` (FR-001/FR-002; ver research.md Decisión 1)
- [X] T004 Generar la migración del constraint de T003 con `python manage.py makemigrations catalog` (revisar el archivo resultante en `apps/catalog/migrations/`) — `0009_evaluationperiod_unique_open_period.py`, aplicada
- [X] T005 Implementar la validación de continuidad (sin huecos ni traslapes, solo prospectiva) en `EvaluationPeriod.clean()` en `apps/catalog/models.py`, comparando contra el periodo inmediato anterior y siguiente por fecha (FR-003/FR-004; ver research.md Decisión 2) — solo se re-evalúa cuando el periodo es nuevo o cambian sus fechas (no en cada guardado)
- [X] T006 Implementar en `EvaluationPeriod.clean()` (`apps/catalog/models.py`) el bloqueo de edición de `start_date`/`end_date`/`kind` cuando `status != PLANEADO` (levantar `ValidationError` si se intenta modificar cualquiera de esos campos con el periodo Abierto o Cerrado); campo `status` no está sujeto a esta restricción, ya que su transición pasa por T011/T013 (FR-013)
- [X] T007 Restringir `EvaluationPeriodAdmin` en `apps/catalog/admin.py`: volver `status`, `start_date` y `end_date` de solo lectura (`get_readonly_fields`, solo al editar — al crear siguen capturables) para que las transiciones de estatus y la edición de fechas solo puedan hacerse vía las vistas de T017/T018, nunca directo desde el admin (evita bypassear `period_lifecycle` y T006; FR-002/FR-005/FR-013). También se quitó `status` de `PeriodForm` (bypass equivalente encontrado en `apps/catalog/forms.py`)
- [X] T008 Agregar `history = HistoricalRecords()` a `FinalScore` en `apps/evaluations/models.py` (research.md Decisión 4, hallazgo de cobertura de auditoría)
- [X] T009 Generar la migración de T008 con `python manage.py makemigrations evaluations` (crea `HistoricalFinalScore` en `apps/evaluations/migrations/`) — `0015_historicalfinalscore.py`, aplicada
- [X] T010 [P] Implementar `permissions.is_period_correction_allowed(user)` (Talento/superusuario) en `apps/core/services/permissions.py` (FR-006; ver research.md Decisión 6)
- [X] T011 Implementar `period_lifecycle.open_period(period, actor)` en `apps/core/services/period_lifecycle.py`: levanta `ValidationError` si ya existe otro periodo Abierto, indicando cuál (FR-001/FR-002)
- [X] T012 Implementar `period_lifecycle.find_contiguous_next(period)` en `apps/core/services/period_lifecycle.py`: retorna el periodo Planeado cuyo `start_date == period.end_date + 1 día`, o `None`
- [X] T013 Implementar `period_lifecycle.close_and_open_next(period, actor)` en `apps/core/services/period_lifecycle.py`, usando T012 dentro de `transaction.atomic()`: si no hay contiguo, levanta `ValidationError` sin cambiar nada; si hay, cierra `period` y abre el contiguo en la misma transacción (FR-005; research.md Decisión 3)
- [X] T014 Implementar `period_lifecycle.assert_record_editable(record, actor, reason=None)` en `apps/core/services/period_lifecycle.py`: si `record.period.is_closed`, exige `permissions.is_period_correction_allowed(actor)` y un `reason` no vacío, asigna `record._change_reason = reason`; si no cumple el rol, levanta `PermissionDenied` (FR-006; research.md Decisión 4)
- [X] T015 Implementar `period_lifecycle.require_open_period()` en `apps/core/services/period_lifecycle.py`: envoltorio sobre el `_open_period()` existente (`apps/evaluations/views.py:34`) que retorna el periodo Abierto o levanta `NoOpenPeriodError` con mensaje de negocio claro (FR-008/FR-009; research.md Decisión 5)
- [X] T016 [P] Tests de `EvaluationPeriod` (constraint de unicidad T003, continuidad T005, inmutabilidad de fechas/tipo T006) y de `period_lifecycle` (T011-T015) en `apps/core/tests/test_period_lifecycle.py` — 30 tests, todos verdes. No se agregó un test dedicado a T007 (readonly del admin) vía el cliente de Django admin; se verificó solo por inspección de código.

**Checkpoint**: fundación lista — las historias de usuario pueden implementarse (en orden de prioridad o en paralelo si hay más de un desarrollador)

---

## Phase 3: User Story 1 - Un solo periodo activo a la vez (Priority: P1) 🎯 MVP

**Goal**: Talento abre y cierra periodos garantizando que exista, a lo más, uno Abierto; el cierre abre automáticamente el siguiente contiguo.

**Independent Test**: crear dos periodos, abrir el primero, intentar abrir el segundo (rechazado), cerrar el primero con un Planeado contiguo ya creado (abre el segundo automáticamente en la misma operación).

- [X] T017 [US1] ~~Agregar vista `period_open`~~ **Hallazgo de implementación**: ya existía `period_admin` (`apps/catalog/views.py`) con acciones `action=open`/`action=close` inline que mutaban `status` directo, sin ninguna validación — se reutilizó esa vista y se reescribió para llamar a `period_lifecycle.open_period`/`close_and_open_next`, en vez de crear una vista nueva
- [X] T018 [US1] (fusionado con T017: mismo `period_admin` maneja `action=close` con `period_lifecycle.close_and_open_next`)
- [X] T019 [US1] ~~Agregar rutas nuevas~~ No fue necesario: `period_admin` ya recibía `action` por POST en su única ruta existente (`catalog:period_admin`); no se crearon rutas nuevas
- [X] T020 [US1] El template `templates/catalog/period_admin.html` ya tenía los botones Abrir/Cerrar condicionales (feature preexistente); no requirió cambios — solo el backend cambió de guardar `status` directo a pasar por `period_lifecycle`
- [X] T021 [P] [US1] Tests de vista cubriendo los 3 Acceptance Scenarios de US1 en `apps/core/tests/test_period_lifecycle.py` (`test_period_admin_view_rejects_open_while_another_open`, `test_period_admin_view_close_opens_next_automatically`, `test_period_admin_view_close_without_contiguous_shows_error`)

**Checkpoint**: User Story 1 funcional y probable de forma independiente

---

## Phase 4: User Story 2 - Continuidad del calendario sin huecos (Priority: P1)

**Goal**: Talento planifica periodos futuros que, en conjunto, cubren el calendario sin huecos ni traslapes.

**Independent Test**: crear/editar un periodo con fecha de inicio que deje un hueco o traslape con el periodo adyacente (rechazado); con fecha contigua (aceptado).

- [X] T022 [US2] `templates/catalog/period_form.html` ahora renderiza `form.non_field_errors` (no existía) y muestra una nota cuando el periodo ya no está Planeado (fechas/tipo bloqueados); también se quitó el campo `status` del formulario (ver T007)
- [X] T023 [P] [US2] Tests de continuidad en `apps/core/tests/test_period_lifecycle.py`: hueco, traslape, contiguo, inmutabilidad de fechas, **no-retroactividad** (`test_continuity_not_retroactive_for_untouched_historical_periods`: renombrar un periodo histórico con hueco preexistente no dispara la validación) y su contraparte (`test_continuity_applies_to_new_period_even_with_preexisting_gap`: un periodo nuevo sí debe respetar continuidad aunque su vecino ya tuviera un hueco)

**Checkpoint**: User Stories 1 y 2 funcionan de forma independiente

---

## Phase 5: User Story 3 - Histórico de solo lectura para el colaborador (Priority: P2)

**Goal**: un colaborador consulta en cualquier momento sus acuerdos, calificaciones y estatus de periodos pasados, en modo solo lectura.

**Independent Test**: cerrar un periodo con datos de un colaborador y verificar que sigue viéndolos (sin poder editarlos) después de abrir el siguiente periodo.

- [X] T024 [US3] Nuevo helper `_resolve_period(request)` en `apps/dashboards/views.py` (lee `?periodo=<id>`, cae a `_open_period()` si no se especifica). Aplicado en `feedback_session_list`, `feedback_session_detail`, `period_progress` y `talent_person`; `_feedback_card()` ahora recibe `period` y calcula `read_only`
- [X] T025 [US3] Selector de periodo (`<select name="periodo">`) agregado en `feedback_session_list.html`, `period_progress.html` y `talent_person.html`; badge "Histórico · solo lectura" en `_feedback_session_card.html`; banner de solo lectura en `feedback_session_detail.html` y `talent_person.html`
- [X] T026 [P] [US3] `test_feedback_session_detail_readonly_for_closed_period` cubre el Acceptance Scenario 1 (consulta de periodo cerrado, solo lectura incluso para un responsable asignado). **Gap**: no se agregó un test automatizado dedicado a la diferenciación visual (Acceptance Scenario 2) ni a `period_progress`/`talent_person` con `?periodo=`; solo verificado por inspección de código, no hay browser disponible en esta sesión para confirmar el render

**Checkpoint**: User Stories 1, 2 y 3 funcionan de forma independiente

---

## Phase 6: User Story 4 - Cierre de periodo congela los datos como referencia histórica (Priority: P2)

**Goal**: al cerrar un periodo, sus registros de retroalimentación quedan inmutables, salvo la excepción auditada de Talento/superusuario.

**Independent Test**: intentar editar una calificación o un acuerdo de un periodo Cerrado (bloqueado para un usuario normal; permitido con motivo obligatorio y auditoría para Talento/superusuario).

- [X] T027 [US4] `ownership_flow.close_ownership_evaluation/reopen_ownership_evaluation/reset_ownership_evaluation` ahora aceptan `actor`/`reason` y llaman `assert_record_editable`; se actualizaron los 5 call sites en `apps/evaluations/views.py` (`ownership_save`, `ownership_reopen`, `ownership_reset`, `ownership_reset_user`, `ownership_autosave`) con manejo de `PermissionDenied`/`ValidationError`. **Gap conocido**: no se agregó un input `reason` en `templates/evaluations/ownership_fill.html`, así que Talento no tiene hoy una forma de capturar el motivo *a través de esa pantalla* para la excepción de corrección (el bloqueo en sí funciona y es seguro; falta la UI de la excepción)
- [X] T028 [US4] `value_delivery_flow.save_vd_criteria/save_vd_comment/submit_vd_for_validation/validate_vd/reject_vd` ahora aceptan `actor`/`reason` y llaman `assert_record_editable`; call sites actualizados en `value_delivery_capture` y `value_delivery_review`. Mismo gap de UI que T027 (sin input `reason` en los templates de Entrega de Valor)
- [X] T029 [US4] **Decisión de alcance, no bypass**: se investigó y `arena_impact`/`arena_impact_autosave` ya solo operan sobre `_open_period()` (nunca sobre un periodo Cerrado con el código actual), así que integrar `assert_record_editable` ahí sería código muerto sin una UI de navegación histórica para Impacto Arena (que no existe). Se deja documentado como trabajo futuro si se agrega esa UI
- [X] T030 [US4] Integrado en `feedback_session_detail` (con captura de `reason` en el propio template, ver T031) para `TalentSessionNote`. **Gap conocido**: `talent_note_autosave`, `talent_scenario_toggle` y `talent_mesa_project_toggle` (`MesaProjectReview`) siguen exigiendo `_open_period()` internamente sin aceptar `?periodo=`, por lo que hoy son inalcanzables sobre un periodo Cerrado (ni bloqueados ni permitidos: simplemente no aplican todavía a un periodo histórico)
- [X] T031 [US4] Campo `reason` agregado en `templates/dashboards/feedback_session_detail.html` (guardar, marcar acordado, reabrir), obligatorio solo cuando `can_correct_closed`; propagado a `assert_record_editable` en la vista
- [X] T032 [P] [US4] Tests en `apps/core/tests/test_period_lifecycle.py`: 5 tests directos de `assert_record_editable` (no-op abierto, bloqueo normal, bloqueo actor=None, exige motivo, permite con motivo), `test_close_ownership_evaluation_blocked_when_period_closed` (integración con `ownership_flow`), y `test_feedback_session_detail_readonly_for_closed_period` + `test_feedback_session_detail_admin_can_correct_closed_with_reason` (integración end-to-end vía HTTP, incluida la verificación de `history_change_reason`)

**Checkpoint**: User Stories 1-4 funcionan de forma independiente

---

## Phase 7: User Story 5 - Nuevo periodo con la misma operatividad, de forma aislada (Priority: P3)

**Goal**: todo registro nuevo se asocia exclusivamente al periodo Abierto vigente; sin periodo Abierto, la creación se bloquea con un mensaje claro.

**Independent Test**: abrir un periodo nuevo, crear registros y confirmar que quedan asociados solo a ese periodo; sin periodo Abierto, la creación se bloquea en vez de fallar con un error no controlado.

- [X] T033 [US5] `value_delivery_capture` usa `period_lifecycle.require_open_period()` — este era el único punto de creación con el gap real confirmado (crasheaba con `IntegrityError` sin periodo Abierto). `ownership_list`/`ownership_validation`/`ownership_start`/`ownership_lead_start`/`arena_impact`/`arena_impact_autosave` se revisaron y **ya degradaban con gracia** (mensaje o estado vacío) antes de esta feature; no se tocaron para no regresar su comportamiento actual
- [X] T034 [US5] `talent_person` ya no crea una `TalentSessionNote` nueva cuando el periodo resuelto está Cerrado (antes usaba `get_or_create` incondicional); los demás puntos de creación de `TalentSessionNote`/`MesaProjectReview` (`talent_note_autosave`, `talent_scenario_toggle`, `talent_mesa_project_toggle`, `talent_responsable_add`) ya exigían `_open_period()` de antes y no se modificaron
- [X] T035 [P] [US5] `test_value_delivery_capture_blocks_creation_without_open_period` cubre el bloqueo de creación. **Gap conocido (FR-010)**: no se escribió un test explícito de "no reasignación de periodo en un registro existente" — hoy ningún flujo ni el Django admin exponen el campo `period` como editable en los 6 modelos de retroalimentación (verificado por inspección: no están registrados en admin.py), así que el riesgo es bajo, pero queda sin cobertura de regresión automatizada

**Checkpoint**: las 5 historias de usuario funcionan de forma independiente

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Requisitos que cruzan varias historias, y validación final

- [X] T036 [P] `period_progress` y `talent_person` ahora usan `_resolve_period` + selector `?periodo=`, dando a Talento/Directores lectura de cualquier periodo (Abierto o Cerrado), no solo el propio dueño del dato
- [X] T037 [P] `test_close_and_open_next_recorded_in_history` confirma que la transición queda en `EvaluationPeriod.history` (FR-016)
- [~] T038 **No ejecutado**: no hay navegador disponible en esta sesión para recorrer la UI manualmente. Se validó equivalentemente vía `pytest` + Django test client (`test_period_admin_view_*`, `test_feedback_session_detail_*`, `test_value_delivery_capture_*`), pero el render visual de los templates (selectores de periodo, banners de solo lectura, campo `reason`) no fue confirmado con un navegador real — decirlo explícitamente en vez de asumir que "se ve bien"
- [X] T039 Ejecutada la suite completa `pytest apps/core/tests/` — ver resumen de resultados en el reporte final de la conversación

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sin dependencias — puede iniciar de inmediato
- **Foundational (Fase 2)**: depende de Setup — BLOQUEA las 5 historias de usuario
- **User Stories (Fases 3-7)**: todas dependen de que Foundational esté completa
  - US1 y US2 son ambas P1 y no dependen entre sí (pueden ir en paralelo si hay más de un desarrollador)
  - US3, US4 y US5 dependen conceptualmente de que existan periodos Cerrados/Abiertos gestionables (US1), pero no requieren que US1 esté "terminada" como tarea — solo que Foundational (T003-T016) exista
- **Polish (Fase 8)**: depende de que las historias que se quieran entregar estén completas

### User Story Dependencies

- **US1 (P1)**: solo depende de Foundational
- **US2 (P1)**: solo depende de Foundational; independiente de US1 (ambas tocan `EvaluationPeriod` pero en aspectos distintos: apertura/cierre vs. validación de fechas)
- **US3 (P2)**: depende de Foundational; se apoya en que existan periodos Cerrados (de US1) para tener algo que consultar, pero su implementación (T024-T026) no depende de las tareas de US1
- **US4 (P2)**: depende de Foundational (en particular T014); se apoya conceptualmente en US1/US3 pero es implementable de forma aislada
- **US5 (P3)**: depende de Foundational (en particular T015)

### Parallel Opportunities

- T002 (Setup) puede ir en paralelo con T001
- Dentro de Foundational: T010 es paralelo a T003-T009 y T011-T015 (archivo distinto); T016 depende de que T003-T015 estén terminadas
- Una vez completa Foundational, US1 y US2 pueden trabajarse en paralelo (equipos distintos); US3, US4 y US5 también, si hay capacidad
- Todas las tareas de test marcadas [P] dentro de una historia pueden correr en paralelo con las de otra historia, pero no con las tareas de implementación de la misma historia

---

## Parallel Example: Foundational

```bash
# En paralelo (archivos distintos):
Task: "Implementar permissions.is_period_correction_allowed(user) en apps/core/services/permissions.py"
Task: "Agregar UniqueConstraint unique_open_period en apps/catalog/models.py"
```

## Parallel Example: User Story 1

```bash
# Tests de US1 en paralelo con el resto de la implementación de otra historia ya completada:
Task: "Tests de vista de period_open/period_close en apps/core/tests/test_period_lifecycle.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Completar Fase 1: Setup
2. Completar Fase 2: Foundational (CRÍTICO — bloquea todo lo demás)
3. Completar Fase 3: User Story 1 (unicidad de periodo Abierto + apertura automática)
4. Completar Fase 4: User Story 2 (continuidad sin huecos) — sin esto, US1 no tiene periodos contiguos que abrir automáticamente
5. **DETENER y VALIDAR**: correr el Escenario 1, 2 y 3 de `quickstart.md`
6. El MVP entrega la garantía central que motivó la feature: nunca dos periodos Abiertos, nunca un hueco en el calendario

### Incremental Delivery

1. Setup + Foundational → fundación lista
2. US1 + US2 (ambas P1) → MVP: ciclo de vida de periodos gobernado correctamente
3. US3 (P2) → colaboradores consultan histórico
4. US4 (P2) → inmutabilidad con excepción auditada
5. US5 (P3) → aislamiento y mensajes de bloqueo en creación
6. Polish → reportes agregados para Talento/Leads/Directores + validación de regresión completa

---

## Notes

- [P] = archivos distintos, sin dependencias entre sí
- [Story] mapea cada tarea a su historia de usuario para trazabilidad
- Verificar que los tests fallan antes de implementar cuando se trabaje con enfoque TDD (opcional, no exigido por la spec)
- Hacer commit después de cada tarea o grupo lógico de tareas
- Detenerse en cada Checkpoint para validar la historia de forma independiente antes de continuar
