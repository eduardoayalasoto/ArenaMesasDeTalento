---

description: "Task list template for feature implementation"
---

# Tasks: Reapertura de retroalimentación y vista de superusuario para Talento

**Input**: Design documents from `/specs/001-retroalimentacion-superusuario-talento/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, quickstart.md

**Tests**: Se incluyen tareas de test — este dominio ya tiene suite `pytest-django`
establecida (`apps/core/tests/test_feedback_session.py`) que cubre exactamente
este comportamiento, incluido un test (`test_solo_talento_puede_reabrir`) cuya
aserción esta feature invierte a propósito; omitir los tests dejaría ese cambio
de comportamiento sin cobertura y arriesgaría una regresión silenciosa. **No es
TDD estricto**: la fase Foundational implementa el mecanismo compartido (permiso
+ botón + redirect) y luego se prueba, tanto en Foundational como en cada
historia — no se espera que los tests de historia fallen antes de esas
implementaciones, porque el mecanismo que prueban ya existe desde Foundational
por diseño (ver `plan.md`/`research.md`).

**Organization**: Tareas agrupadas por historia de usuario (spec.md) para poder
implementar y probar cada una de forma independiente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencias)
- **[Story]**: A qué historia de usuario pertenece (US1, US2)
- Cada tarea incluye la ruta exacta del archivo

## Path Conventions

Proyecto Django único (sin frontend separado): `apps/`, `templates/` en la raíz
del repo — no aplican las convenciones de `src/`/`backend/`/`frontend/` del
template genérico.

---

## Phase 1: Setup

**Purpose**: Confirmar línea base antes de tocar código

- [X] T001 Confirmar que la suite actual pasa en verde antes de empezar: `./.venv/Scripts/python.exe -m pytest apps/core/tests/test_feedback_session.py -v` (línea base para detectar regresiones propias más adelante)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Cambios y verificaciones compartidos por ambas historias — el
permiso de reabrir y el campo `can_reopen` de la tarjeta los usan tanto US1
(botón en la tarjeta) como US2 (mismo botón, en la nueva sección "Todas"); las
tareas de prueba T005-T006 cubren garantías transversales (auditoría, FR-011)
que no pertenecen a una sola historia.

**⚠️ CRITICAL**: Ninguna historia puede darse por terminada sin esta fase.

- [X] T002 En `apps/dashboards/views.py`, función `_feedback_card()` (línea ~921): agregar parámetro `can_reopen: bool` al dict que retorna; en sus dos llamadores dentro de `feedback_session_list()` (líneas ~971 y ~977) pasar `permissions.can_edit_feedback_session(request.user, note)` (ya importado como `permissions` en el módulo)
- [X] T003 En `apps/dashboards/views.py`, función `feedback_session_detail()`: (a) en la rama `action == "reopen"` (línea ~1017-1026) cambiar el chequeo `if not request.user.is_admin` por `if not permissions.can_edit_feedback_session(request.user, note)`, y mensaje de error acorde (ya no es exclusivo de "Talento y Cultura"); (b) tras reabrir, redirigir a `request.POST.get("next")` si es una ruta interna válida (usar `django.utils.http.url_has_allowed_host_and_scheme` contra `request.get_host()`), si no, mantener el `redirect("dashboards:feedback_session_detail", pk=target.pk)` actual; (c) en el contexto GET (línea ~1066), cambiar `"can_reopen": note.feedback_agreed and request.user.is_admin` por `"can_reopen": note.feedback_agreed and permissions.can_edit_feedback_session(request.user, note)`
- [X] T004 En `templates/dashboards/_feedback_session_card.html`, dentro del bloque de estado (línea ~70-77): cuando `card.note.feedback_agreed` sea verdadero y `card.can_reopen` también, agregar un `<form method="post">` con `{% csrf_token %}`, `action` apuntando a `{% url 'dashboards:feedback_session_detail' pk=card.target.pk %}`, un input oculto `name="action" value="reopen"`, un input oculto `name="next" value="{% url 'dashboards:feedback_session_list' %}"`, y un botón "Reabrir" junto al badge — sin agregar ningún botón de "Cerrar" en la tarjeta (FR-011)
- [X] T005 [P] En `apps/core/tests/test_feedback_session.py`, agregar test de auditoría (FR-004/SC-004): tras un `agree` y un `reopen` consecutivos sobre la misma nota, verificar que `note.history.all()` tiene una fila por cada cambio de estado y que `history_user` en la fila del `agree` es quien cerró y en la del `reopen` es quien reabrió (confirma que el mecanismo de `simple_history`/`HistoryRequestMiddleware` ya activo en `config/settings.py` efectivamente deja el rastro que pide FR-004, aunque `feedback_agreed_by` se limpie a `None` — ver `data-model.md`, nota de auditoría)
- [X] T006 [P] En `apps/core/tests/test_feedback_session.py`, agregar test que renderice `feedback_session_list` con una nota cerrada asignada a un responsable y confirme que el HTML de la tarjeta **no** contiene ningún form/botón con `action=agree` ni `value="agree"` (FR-011: cerrar sigue siendo exclusivo del detalle, nunca un botón directo en la tarjeta)

**Checkpoint**: El mecanismo de reabrir (permiso + botón + redirect) ya funciona y está probado (incluida su auditoría) en cualquier tarjeta que lo reciba; las historias de abajo solo agregan/ajustan *quién ve qué tarjetas* y afirman ese comportamiento desde la perspectiva de cada historia.

---

## Phase 3: User Story 1 - Reabrir una retroalimentación cerrada por error, desde su tarjeta (Priority: P1) 🎯 MVP

**Goal**: Responsable asignado (principal/secundario) o superusuario de Talento reabren, con un clic desde la tarjeta del listado, una retroalimentación que cerraron por error.

**Independent Test**: Cerrar una retroalimentación como su responsable asignado, volver al listado, confirmar que aparece "Reabrir" en su tarjeta, presionarlo, confirmar que sigue en el listado y la tarjeta ya no dice "Acordada · cerrada".

### Tests for User Story 1

> El mecanismo que estos tests verifican ya quedó implementado en Foundational (T002-T004); no se espera que fallen antes de esa implementación (ver nota de la sección "Tests" arriba).

- [X] T007 [P] [US1] En `apps/core/tests/test_feedback_session.py`, actualizar `test_solo_talento_puede_reabrir` (línea ~178-195): renombrar a algo como `test_responsable_y_talento_pueden_reabrir_tercero_no` y ajustar sus aserciones — el responsable primario/secundario que cerró su propia sesión **ahora sí** logra reabrirla (`feedback_agreed` vuelve a `False`), Talento sigue pudiendo reabrir cualquiera, y un usuario sin asignación ni `is_admin` sigue recibiendo el rechazo (mensaje de error, `feedback_agreed` sin cambios)
- [X] T008 [P] [US1] En `apps/core/tests/test_feedback_session.py`, agregar test que haga POST `action=reopen` con `next` apuntando a la URL de `feedback_session_list` y verifique que la respuesta redirige ahí (no al detalle); en el mismo test (o uno adicional junto a él), verificar el caso límite de idempotencia: reabrir una nota que ya está abierta (`feedback_agreed=False`) no cambia nada y no produce error
- [X] T009 [P] [US1] En `apps/core/tests/test_feedback_session.py`, agregar test que renderice `feedback_session_list` para un responsable con una nota cerrada asignada y verifique que el HTML de su tarjeta contiene el formulario/botón "Reabrir"; y otro test que confirme que esa misma tarjeta, vista por un usuario sin `can_edit_feedback_session` sobre esa nota, no contiene el botón

**Checkpoint**: User Story 1 completamente funcional y probada de forma independiente — ya se puede entregar como incremento (MVP).

---

## Phase 4: User Story 2 - Ver y operar sobre todas las retroalimentaciones como superusuario (Priority: P2)

**Goal**: El superusuario de Talento ve, en `/retroalimentacion/`, una sección adicional con todas las retroalimentaciones del periodo activo donde no es responsable ni receptor, con las mismas acciones que ya tiene en el detalle.

**Independent Test**: Crear una `TalentSessionNote` del periodo activo sin ningún `FeedbackResponsible`; entrar como Talento y confirmar que aparece en una sección nueva del listado, con su estado real y (si está cerrada) su botón "Reabrir".

### Tests for User Story 2

- [X] T010 [P] [US2] En `apps/core/tests/test_feedback_session.py` (o un archivo nuevo `test_feedback_session_superuser_view.py` si se prefiere no sobrecargar el existente), agregar test: una nota del periodo activo sin `FeedbackResponsible` no aparece para un Lead cualquiera, pero sí aparece para un usuario Talento en `feedback_session_list` (contexto `all_cards`, o presente en el HTML), con su badge de estado real y, si está cerrada, su botón "Reabrir" (cierra el hueco de cobertura de FR-006/FR-007 detectado en `/speckit-analyze`)
- [X] T011 [P] [US2] Agregar test de deduplicación: una nota donde Talento **sí** es responsable principal aparece en `primary_cards` pero no se repite en `all_cards`
- [X] T012 [P] [US2] Agregar test: un usuario Director (no `is_admin`) no recibe `all_cards` ni ve la sección ampliada, sin cambio de alcance respecto al comportamiento actual

### Implementation for User Story 2

- [X] T013 [US2] En `apps/dashboards/views.py`, función `feedback_session_list()` (línea ~936-983): cuando `request.user.is_admin`, agregar al contexto `all_cards` con todas las `TalentSessionNote.objects.filter(period=period)` cuyo `pk` no esté ya en las notas usadas para `primary_cards`/`secondary_cards`/`own_cards` (dedupe por `note.pk`, ver `research.md` Decisión 3), construidas con `_feedback_card(note, list(note.responsables.all()), finals.get(note.user_id), "Talento")`
- [X] T014 [US2] En `templates/dashboards/feedback_session_list.html`: agregar una cuarta sección "Todas" (mismo patrón `{% if all_cards %}` + grid de tarjetas que las otras tres, línea ~30-37) y actualizar la condición de estado vacío (línea 8, `{% if not primary_cards and not secondary_cards and not own_cards %}`) para incluir también `and not all_cards`

**Checkpoint**: Ambas historias funcionan de forma independiente y en conjunto — Talento ve todo (US2) y puede reabrir cualquier cosa cerrada por error, sea suya o ajena (US1).

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T015 [P] Ejecutar `./.venv/Scripts/python.exe manage.py makemigrations --check --dry-run` para confirmar que ningún cambio de esta feature requiere migración (coherente con `data-model.md`: no hay cambios de esquema)
- [X] T016 Ejecutar la suite completa relevante: `./.venv/Scripts/python.exe -m pytest apps/core/tests/test_feedback_session.py apps/core/tests/test_period_progress_pending_people.py -v`
- [X] T017 Recorrer manualmente los pasos de `quickstart.md` (Historia 1 e Historia 2) contra el entorno local

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias, arranca de inmediato
- **Foundational (Phase 2)**: depende de Setup; **bloquea** ambas historias
- **User Story 1 (Phase 3)**: depende de Foundational; sin dependencia de US2
- **User Story 2 (Phase 4)**: depende de Foundational; sin dependencia de US1 (usa el mismo `can_reopen`/botón ya construidos en Foundational, pero no necesita que US1 esté "terminada" para funcionar)
- **Polish (Phase 5)**: depende de que ambas historias que se vayan a entregar estén completas

### Parallel Opportunities

- T005 y T006 (tests de Foundational) pueden escribirse en paralelo — archivos/aserciones independientes dentro del mismo archivo de test
- T007, T008, T009 (tests de US1) pueden escribirse en paralelo
- T010, T011, T012 (tests de US2) ídem
- T013 y T014 (implementación de US2) tocan archivos distintos (`views.py` vs template) y pueden avanzar en paralelo una vez escritos sus tests
- T015 es independiente de T016/T017

---

## Implementation Strategy

### MVP First (User Story 1 solamente)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1) → validar con `quickstart.md` Historia 1 → esto ya resuelve el dolor principal reportado ("un cierre no se puede deshacer jamás")

### Incremental Delivery

1. Setup + Foundational → base lista (incluye auditoría y no-regresión de FR-011 ya probadas)
2. US1 → probar independientemente → esto ya es entregable
3. US2 → probar independientemente → entregable adicional (visión completa para Talento)
4. Polish → confirma que nada se rompió y que `quickstart.md` pasa de punta a punta

---

## Notes

- No hay tarea de migración porque no hay cambio de esquema (ver `data-model.md`)
- No hay `contracts/` ni tareas de contrato: no existe API pública en esta feature (ver `plan.md`)
- FR-011 (no agregar botón de "cerrar" en la tarjeta) es una restricción a **no** implementar; T006 la verifica con una prueba negativa
- FR-004/SC-004 (auditoría) se apoya en `simple_history`, ya activo en el proyecto; T005 lo confirma explícitamente en vez de darlo por hecho (hallazgo de `/speckit-analyze`)
