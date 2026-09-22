---

description: "Task list template for feature implementation"
---

# Tasks: Salvaguardas de UX y completitud de datos para el cierre/apertura de Periodos de Evaluación

**Input**: Design documents from `/specs/003-salvaguardas-cierre-periodo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: se incluyen, siguiendo el mismo patrón que 002
(`apps/core/tests/test_period_lifecycle.py`, mismo archivo, por cohesión
temática — todo es ciclo de vida de periodos).

**Organization**: Tareas agrupadas por historia de usuario (US1-US3 de
`spec.md`).

## Phase 1: Setup

- [X] T001 Ejecutar `pytest apps/core/tests/` completo como línea base (confirmar 100% verde antes de tocar código) — verde (suite de 002 ya validada)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: las 2 funciones de solo lectura de las que dependen US2 y US3 (US1 no las necesita)

- [X] T002 Implementar `period_lifecycle.resolve_requested_period(request, *, fallback=None)` en `apps/core/services/period_lifecycle.py` (lee `?periodo=<id>`, retorna ese `EvaluationPeriod` de cualquier estatus si existe, si no llama a `fallback()` o retorna `None`)
- [X] T003 Refactorizar `apps/dashboards/views.py::_resolve_period` para delegar en `resolve_requested_period(request, fallback=_open_period)`, sin cambiar su firma ni comportamiento externo
- [X] T004 Implementar `period_lifecycle.pending_activity_counts(period)` en `apps/core/services/period_lifecycle.py` (replica las queries de `own_total/own_submitted/vd_total/vd_validated/finals_total/finals_complete` que hoy están inline en `period_progress`)
- [X] T005 Refactorizar `apps/dashboards/views.py::period_progress` para llamar a `pending_activity_counts` en vez de repetir las queries inline (mismo comportamiento/contexto visible al template)
- [X] T006 [P] Tests de `resolve_requested_period` y `pending_activity_counts` en `apps/core/tests/test_period_lifecycle.py` (5 tests)

**Checkpoint**: fundación lista para US2 y US3; US1 puede implementarse en paralelo desde ahora

---

## Phase 3: User Story 1 - Confirmación antes de abrir o cerrar un periodo (Priority: P1)

**Goal**: ningún clic en Abrir/Cerrar ejecuta el cambio sin confirmación explícita.

**Independent Test**: clic en Cerrar/Abrir y cancelar → nada cambia; confirmar → ocurre igual que hoy (002).

- [X] T007 [US1] En `apps/catalog/views.py::period_admin`, calcular para la fila del periodo Abierto el nombre del periodo siguiente contiguo (`period_lifecycle.find_contiguous_next`) y pasarlo al contexto de esa fila
- [X] T008 [US1] En `templates/catalog/period_admin.html`, agregar `onclick="return confirm('...')"` a los botones "Abrir" y "Cerrar": para Abrir, nombra el periodo; para Cerrar, nombra el periodo, el periodo siguiente (si existe) y advierte que no es reversible desde la interfaz (FR-001/FR-002/FR-003/FR-004); usar `|escapejs` en los nombres interpolados
- [X] T009 [P] [US1] Tests de los 3 Acceptance Scenarios de US1 en `apps/core/tests/test_period_lifecycle.py` (verifican que el HTML renderizado de `period_admin` contiene el `onclick`/texto esperado). **Nota de implementación**: `escapejs` codifica caracteres como `-` a `-` (válido en JS, no compara igual como texto plano) — se agregó un helper `_decode_js_unicode_escapes` en el test para comparar de forma legible

**Checkpoint**: US1 funcional de forma independiente

---

## Phase 4: User Story 2 - Aviso de actividad pendiente al cerrar (Priority: P1)

**Goal**: Talento ve cuánta actividad quedaría incompleta antes de confirmar el cierre, sin que eso lo bloquee.

**Independent Test**: cerrar con pendientes → el aviso los muestra antes de confirmar; cerrar con todo completo → el aviso lo indica; confirmar en ambos casos cierra igual.

- [X] T010 [US2] En `apps/catalog/views.py::period_admin`, llamar `period_lifecycle.pending_activity_counts` para el periodo Abierto y pasar los conteos al contexto de esa fila
- [X] T011 [US2] Extender el texto del `confirm()` de "Cerrar" (T008) con los conteos de T010: "X evaluaciones de Ownership sin enviar, Y Entregas de Valor sin validar, Z calificaciones incompletas", o una indicación explícita de que no hay pendientes si los tres son 0 (FR-005/FR-006/FR-007/FR-008)
- [X] T012 [P] [US2] Tests de los 3 Acceptance Scenarios de US2 en `apps/core/tests/test_period_lifecycle.py` (conteos con pendientes, "sin pendientes" cuando todo completo, el cierre procede igual con o sin pendientes)

**Checkpoint**: US1 y US2 funcionan de forma independiente (comparten el mismo `confirm()` de "Cerrar", T011 depende de que T008 ya exista)

---

## Phase 5: User Story 3 - Campo de motivo en Ownership y Entrega de Valor (Priority: P2)

**Goal**: Talento/superusuario puede corregir con motivo auditado una evaluación de Ownership o una Entrega de Valor de un periodo Cerrado — y puede *llegar* a ella navegando por periodo.

**Independent Test**: cerrar un periodo con una evaluación incompleta, navegar a ese periodo desde el listado, abrirla, ver el campo de motivo, guardar sin motivo (rechazado) y con motivo (guardado y auditado).

- [X] T013 [US3] Extender `ownership_list` y `ownership_validation` (`apps/evaluations/views.py`) con `period_lifecycle.resolve_requested_period(request, fallback=_open_period)` en vez de forzar siempre el periodo Abierto; pasar `periods` (todos) al contexto. **Ampliación de alcance**: `ownership_validation` además muestra TODAS las evaluaciones del periodo (no solo las propias como evaluador) cuando `request.user.is_admin` y el periodo consultado no es el Abierto vigente — mismo patrón "Todas" que `feedback_session_list` en 002; sin esto, Talento no tenía ninguna forma de descubrir evaluaciones ajenas de un periodo histórico
- [X] T014 [US3] Agregar selector de periodo (`<select name="periodo">`, mismo patrón que `feedback_session_list.html` de 002) en `templates/evaluations/ownership_list.html` y `ownership_validation.html`
- [X] T015 [US3] Extender `value_delivery_list` (`apps/evaluations/views.py`) igual que T013 (mismo criterio "Todos los proyectos activos" para admin en periodo histórico, en vez de solo `projects_led_by`)
- [X] T016 [US3] Agregar selector de periodo en `templates/evaluations/value_delivery_list.html`; el link a `value_delivery_capture` ahora propaga `?periodo=`
- [X] T017 [US3] Extender `value_delivery_capture` (`apps/evaluations/views.py`) para resolver el periodo vía `resolve_requested_period(request, fallback=period_lifecycle.require_open_period)`; si el periodo resuelto NO es el Abierto vigente, obtener la Entrega de Valor con `.filter(project=project, period=period).first()` (sin crear) — si no existe, redirige con mensaje informativo, nunca crea una VD nueva sobre un periodo Cerrado
- [X] T017a [US3] **(Hallazgo de `/speckit-analyze`, bloqueante — resuelto)** `can_correct_closed` calculado en `value_delivery_capture`; el guardado ahora entra también cuando `vd.status == VALIDADA and can_correct_closed`, llamando `save_vd_criteria(..., actor=, reason=)` + `final_flow.recompute_for_project_members(...)` (para que la corrección se refleje en las calificaciones finales del equipo), **sin** llamar `submit_vd_for_validation` — el estatus se queda en `VALIDADA`
- [X] T017b [US3] **(Hallazgo de `/speckit-analyze`, bloqueante — resuelto)** `value_delivery_capture.html`/`_vd_criterion.html`: `disabled` ahora es `vd.status == 'VALIDADA' and not can_correct_closed`; botón "Guardar corrección" (reemplaza al de "Enviar a validación" cuando `can_correct_closed`, mismo `<form>` — no hizo falta un `action` nuevo, la vista ya distingue el caso por `vd.status`)
- [X] T018 [US3] En `_render_ownership` (`apps/evaluations/views.py`), agregado `can_correct_closed` al contexto; `can_reset` ahora es `request.user.is_admin and not evaluation.period.is_closed` (FR-011a)
- [X] T018a [US3] **(Hallazgo de `/speckit-analyze`, bloqueante — resuelto)** `_can_edit_answers`/`_can_complement` ahora retornan `permissions.is_period_correction_allowed(user)` cuando `evaluation.period.is_closed`, evaluado antes del chequeo de `is_submitted`
- [X] T018b [US3] **(Hallazgo de `/speckit-analyze`, bloqueante — resuelto)** `ownership_save`: si `evaluation.period.is_closed`, guarda los campos y retorna sin pasar por el bloque `action == "save_close"` (nunca reabre el flujo de cierre); el template oculta "Guardar y cerrar" y su modal de confirmación cuando `can_correct_closed`. **Hallazgo adicional durante la implementación**: `ownership_reset` tenía el mismo problema en sentido inverso — `assert_record_editable` genérico SÍ habría permitido reiniciar (eliminar) con motivo sobre un periodo Cerrado, violando FR-011a; se agregó un rechazo explícito e incondicional en la vista (reiniciar nunca es una "corrección", es un borrado)
- [X] T019 [US3] `ownership_fill.html`: input de motivo global (`x-model="reason"` en el `ownershipForm` de Alpine) visible cuando `can_correct_closed`, propagado como campo oculto al formulario de guardar y como input visible en el modal de reabrir; los radios de respuesta ya no quedan `disabled` (siguen la misma variable `answers_editable`, que ahora es `True` en este caso vía T018a)
- [X] T020 [US3] `ownership_autosave` reordenado: parsea `payload` antes de `assert_record_editable`, pasa `payload.get("reason")`; el `fetch()` de autosave en `ownership_fill.html` envía `reason: this.reason`
- [X] T021 [P] [US3] Cubierto por los tests de T024 (end-to-end vía HTTP, no fue necesario un test separado sin cambios de código)
- [X] T022 [US3] Input de motivo agregado en `templates/evaluations/value_delivery_capture.html` (ver T017b), condicional a `can_correct_closed`
- [~] T023 [US3] **Decisión de alcance (no bug)**: NO se agregó a `templates/evaluations/value_delivery_review.html`. Su cola siempre filtra `period=_open_period()` (sin cambios en esta feature): una VD de un periodo Cerrado nunca aparece ahí, así que el campo nunca se renderizaría bajo navegación normal — sería código muerto (mismo criterio que Arena Impact en 002). El guardado ya está protegido por `assert_record_editable` desde 002 para el caso residual de un POST directo con un pk obsoleto. Ver research.md, Decisión 6b
- [X] T024 [P] [US3] Tests en `apps/core/tests/test_period_lifecycle.py`: corrección real de una evaluación de Ownership ya `ENVIADA` (con y sin motivo) con auditoría verificada, bloqueo explícito de "Reiniciar" sobre periodo Cerrado, `ownership_validation` mostrando todas las evaluaciones para admin en periodo histórico, corrección real de una Entrega de Valor ya `VALIDADA` con auditoría verificada y sin reabrir validación, y que `value_delivery_capture` sobre un periodo Cerrado sin VD existente nunca crea una

**Checkpoint**: las 3 historias de usuario funcionan de forma independiente

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T025 [P] `pending_activity_counts` es exactamente las mismas 6 queries que antes vivían inline en `period_progress`, ahora extraídas sin cambio de comportamiento; cubierto indirectamente por los tests de T006 (mismos valores que antes) — no se detectó divergencia
- [~] T026 **No ejecutado manualmente**: no hay navegador disponible en esta sesión (mismo límite documentado en 002). Validado equivalentemente con `pytest` + Django test client (T009, T012, T024) cubriendo los 4 escenarios de `quickstart.md`; el render visual (selectores, banners, campo de motivo, `confirm()`) no fue confirmado con un navegador real
- [X] T027 Suite completa `pytest apps/core/tests/` ejecutada — ver resumen en la conversación

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: sin dependencias
- **Foundational (Fase 2)**: depende de Setup — bloquea US2 y US3 (no a US1)
- **US1 (Fase 3)**: puede empezar en paralelo con Foundational (no depende de T002-T006)
- **US2 (Fase 4)**: depende de Foundational (T004) y de que T008 (US1) ya exista, porque extiende el mismo `confirm()`
- **US3 (Fase 5)**: depende de Foundational (T002)
- **Polish (Fase 6)**: depende de que las historias que se quieran entregar estén completas

### Parallel Opportunities

- T006 (Foundational) es paralelo a T002-T005 en cuanto estos existan (mismo archivo de test, pero casos independientes)
- US1 (Fase 3) puede avanzar en paralelo con Foundational y con US3, ya que no comparte código con ninguna
- Dentro de US3: T013/T015 (listados de Ownership/VD) son independientes entre sí; T019/T020 (ownership_fill.html) dependen de T018; T022/T023 (VD) son independientes de la rama de Ownership

---

## Implementation Strategy

### MVP First (US1 + US2)

1. Setup + Foundational (T004/T005 para US2; US1 no necesita Foundational)
2. US1: confirmación simple — ya cierra el riesgo más alto (clic accidental)
3. US2: aviso de pendientes sobre esa misma confirmación
4. **DETENER y VALIDAR**: Escenarios 1 y 2 de `quickstart.md`

### Incremental Delivery

1. Setup + Foundational (parcial: solo lo que US2 necesita) → US1 + US2 (MVP de esta feature)
2. Foundational (resto) → US3 (motivo + navegación histórica en Ownership/Entrega de Valor)
3. Polish → validación de regresión completa

## Notes

- [P] = archivos distintos o casos de test independientes
- Hacer commit después de cada tarea o grupo lógico de tareas
- Detenerse en cada Checkpoint para validar la historia de forma independiente
