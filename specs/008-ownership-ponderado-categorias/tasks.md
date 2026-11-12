---

description: "Tareas de la spec 008 — Ownership ponderado por categorías"
---

# Tasks: Ownership ponderado por categorías (todas las áreas) + Consultoría

**Input**: Documentos de diseño en `specs/008-ownership-ponderado-categorias/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Se incluyen. La spec los exige (SC-008) y la constitución (principio V) pide pruebas con cada cambio, compactas por escenario, contra Neon con `--reuse-db`, nunca en paralelo.

**Organization**: Por historia de usuario. Las fases 1 y 2 bloquean a todas las historias.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias abiertas)
- **[Story]**: US1–US6 de la spec; Setup, Foundational y Polish no llevan etiqueta
- Rutas relativas a `arena-talento/`
- Comando de pruebas local: `.\.venv\Scripts\python.exe scripts/pytest_changed.py [archivos]` (con `PYTHONIOENCODING=utf-8`)

## Phase 1: Setup

- [x] T001 Copiar la matriz fuente a `docs/Matrices/Matriz de Competencias y Pesos por Puesto v1.1.xlsx` (desde `Downloads`) para que el generador y la trazabilidad queden en el repo
- [x] T002 Correr `scripts/pytest_changed.py apps/core/tests/test_scoring.py apps/core/tests/test_questionnaire_editor.py apps/core/tests/test_ownership_flow.py` y anotar que la línea base está en verde antes de cambiar nada

---

## Phase 2: Foundational (bloquea todas las historias)

**⚠️ CRITICAL**: ninguna historia puede empezar hasta terminar esta fase.

- [x] T003 Agregar los modelos `Category` y `TemplateCategory`, y los campos `Question.category` (FK nula, PROTECT) y `Question.weight_pct` (decimal 4,1, nulo) en `apps/questionnaires/models.py` según `data-model.md`; `Question.weight` se conserva sin uso
- [x] T004 Generar la migración de esquema `apps/questionnaires/migrations/0003_*.py` con `makemigrations questionnaires` y revisar que sea aditiva
- [x] T005 Crear la migración de datos reversible `apps/questionnaires/migrations/0004_seed_general_category.py`: crea las 5 categorías sembradas (General, Delivery al cliente, Desarrollo de producto, Herramientas de gestión, Actitud y persona); para cada cuestionario de Ownership crea `TemplateCategory(General, 100.0)` y asigna `General` a todas sus preguntas de escala; no toca Entrega de Valor
- [x] T006 [P] Crear `apps/core/services/ownership_weights.py` con: conversión a décimas enteras, `validate_group(values)`, `validate_template_weights(template)`, `split_equal(n)` y `normalize_to_100(weights)` (mayor residuo, un decimal, suma exacta 100.0) y mensajes en español `Los pesos de «{grupo}» suman {X}%; deben sumar 100%.`
- [x] T007 [P] Crear `apps/core/tests/test_ownership_weights.py` (compacta): partes iguales 3 → 33.4/33.3/33.3; suma 99.9 inválida; dos decimales rechazados; grupo parcial rechazado; normalización de la matriz suma 100.0
- [x] T008 Reescribir en `apps/core/services/scoring.py` `ownership_evaluation_score` con el modelo ponderado y agregar `ownership_category_breakdown(evaluation)` (funciones puras, un solo redondeo final, categoría sin calificar excluida y redistribuida, fallback a una categoría al 100% si el cuestionario no tiene `TemplateCategory`) según `data-model.md`
- [x] T009 [P] Crear `apps/core/tests/test_scoring_weighted.py`: «General» = promedio simple; 60/40 con 4.00 y 2.00 → 3.20; peso 0 no pondera; categoría toda N/A redistribuye; todo N/A → `None`; **equivalencia** con el promedio simple de antes sobre muchas combinaciones aleatorias de valores y N/A; y confirmar que `test_scoring.py` sigue en verde
- [x] T010 [P] Crear `apps/core/management/commands/verify_ownership_scores.py`: recalcula con el modelo nuevo el score de toda evaluación con respuestas, lo compara con `OwnershipEvaluation.score` (solo enviadas) y con el promedio simple, imprime conteos y diferencias, y sale con error si hay alguna
- [x] T011 Actualizar `apps/core/management/commands/seed_questionnaires.py` para crear `General` y `TemplateCategory(General, 100.0)` por cuestionario de Ownership y asignar la categoría a sus preguntas (idempotente)
- [x] T012 Actualizar `apps/core/services/questionnaire_editor.py::duplicate_as_new_version` para copiar `TemplateCategory`, `Question.category` y `Question.weight_pct`
- [x] T013 [P] Registrar `Category` y `TemplateCategory` en `apps/questionnaires/admin.py`

**Checkpoint**: modelos, migraciones, cálculo y verificación listos; las historias pueden empezar.

---

## Phase 3: User Story 1 — La calificación pondera por categoría sin alterar lo existente (Priority: P1) 🎯 MVP

**Goal**: Toda evaluación se calcula con el modelo ponderado y ningún score existente cambia.

**Independent Test**: `verify_ownership_scores` da 0 diferencias sobre los datos sembrados; cerrar y reabrir una evaluación «General» conserva el score; un cuestionario de prueba 60/40 da 3.20.

- [x] T014 [US1] Verificar que `ownership_close`/`ownership_autosave` y `_progress` en `apps/evaluations/views.py` y `close_ownership_evaluation`/`reopen_ownership_evaluation` en `apps/core/services/ownership_flow.py` usan la función ponderada sin cambios de firma (ajustar solo si hace falta)
- [x] T015 [US1] Ampliar `apps/core/tests/test_ownership_flow.py` con un escenario que encadena: cuestionario con 2 categorías → respuestas → cierre → score ponderado → reapertura → recálculo; y un cuestionario «General» que conserva el score de siempre
- [x] T016 [US1] Crear `apps/core/tests/test_ownership_general_migration.py`: tras sembrar (`seed_questionnaires`), cada cuestionario de Ownership tiene `General` al 100.0, todas sus preguntas de escala tienen categoría, y `verify_ownership_scores` (llamado como comando) no reporta diferencias
- [x] T017 [US1] Ejecutar `python manage.py verify_ownership_scores` en la BD local con datos y documentar el resultado en `specs/008-ownership-ponderado-categorias/research.md` (sección de verificación)

**Checkpoint**: el nuevo cálculo es la única fuente y es equivalente al anterior (MVP técnico).

---

## Phase 4: User Story 2 — Talento edita pesos con validación visible de 100% (Priority: P1)

**Goal**: Editor con categorías y pesos, total en vivo, guardado/publicación bloqueados si no suma 100%.

**Independent Test**: en un borrador, 60.0 + 39.9 muestra «Suma actual 99.9% — debe llegar a 100%» y bloquea guardar y publicar; 40.0 lo habilita; «Repartir en partes iguales» con 3 da 33.4/33.3/33.3; un POST directo inválido es rechazado.

- [x] T018 [P] [US2] Crear el catálogo de categorías: vista `category_admin` (lista, alta y edición) en `apps/catalog/views.py`, formulario en `apps/catalog/forms.py`, ruta en `apps/catalog/urls.py` y plantilla `templates/catalog/category_admin.html` (daisyUI, Lucide, modal para alta/edición, htmx)
- [x] T019 [P] [US2] Registrar la clave `catalog.categories.manage` en `apps/access/registry.py` (con la ruta `catalog:category_admin`), su fila en `apps/access/seed.py` y `apps/access/legacy.py`
- [x] T020 [US2] Agregar las entradas de menú «Categorías» (y la de Puestos, ver US4) al folder Catálogos en `apps/core/navigation.py`
- [x] T021 [US2] Crear en `apps/questionnaires/forms.py` `CategoryWeightsForm` y `QuestionWeightsForm` (todos o ninguno, un decimal, Σ = 100.0, mensaje del servicio) y agregar `category` a `QuestionForm`
- [x] T022 [US2] Extender `apps/core/services/questionnaire_editor.py::validate_for_publish` (solo OWNERSHIP): categoría obligatoria en preguntas de escala y presente en el cuestionario, Σ de categorías = 100.0, Σ por categoría = 100.0 o todas nulas, categoría con peso > 0 sin preguntas o con todas en 0 → error, combinación área × nivel con puesto activo (se completa en US4)
- [x] T023 [US2] Agregar a `template_edit` en `apps/questionnaires/views.py` las acciones `add_template_category`, `remove_template_category`, `save_category_weights`, `save_question_weights`, `clear_question_weights` (el reparto en partes iguales es del lado del cliente con el mismo algoritmo; el servidor valida la suma al guardar) según `contracts/weights-ui.md`, con `transaction.atomic` y prefetch de categorías/preguntas
- [x] T024 [US2] Rediseñar `templates/questionnaires/template_edit.html`: sección «Categorías y pesos» con componente Alpine (décimas enteras) que muestra el total en vivo, el aviso «Suma actual X% — debe llegar a 100%», deshabilita «Guardar pesos» y «Publicar» mientras no cuadre, botón «Repartir en partes iguales» y selector de categoría por pregunta; sin `fetch`, sin `style=`, sin emojis
- [x] T025 [US2] Ampliar `apps/core/tests/test_questionnaire_editor.py` con un escenario compacto: agregar categorías, guardar 60.0/39.9 (rechazado), 60.0/40.0 (aceptado), repartir en partes iguales, pesos de preguntas, intento de publicar con grupo inválido (rechazado) y publicación válida; verificar que un POST directo con dos decimales se rechaza
- [x] T026 [US2] Ejecutar `.\build_css.ps1` y revisar que el CSS compilado se versione (clases nuevas de la plantilla)

**Checkpoint**: Talento puede armar y publicar cuestionarios ponderados con la validación visible.

---

## Phase 5: User Story 4 — Catálogo de Puestos (Priority: P2)

**Goal**: Cada área nombra sus puestos desde un catálogo; la UI muestra el nombre del puesto.

**Independent Test**: en Catálogos → Puestos, CONS muestra Analista/Consultor/Consultor Sr/Gerente; el perfil de un usuario CONS-JR dice «Analista»; renombrar el puesto no cambia ningún cálculo.

- [x] T027 [US4] Agregar el modelo `Position` (área, nivel, nombre, activo; único por área × nivel; con historial) en `apps/catalog/models.py` y generar la migración de esquema `apps/catalog/migrations/0011_*.py`
- [x] T028 [US4] Crear la migración de datos reversible `apps/catalog/migrations/0012_seed_positions.py`: una fila por área × nivel existente con el nombre del nivel; para `CONS`: JR = Analista, MID = Consultor, SNR = Consultor Sr, LEAD = Gerente
- [x] T029 [P] [US4] Crear `apps/core/services/positions.py` con `position_name(area_id, level_id)` (mapa en caché de 60 s, invalidado al guardar/eliminar `Position`; si no existe, nombre del nivel) y `position_defined(area, level)`
- [x] T030 [P] [US4] Crear el filtro de plantilla `puesto` en `apps/core/templatetags/` que recibe un usuario y devuelve el nombre del puesto
- [x] T031 [US4] Crear la vista `position_admin` (lista y edición de nombre y estado) en `apps/catalog/views.py`, formulario, ruta, plantilla `templates/catalog/position_admin.html`, y la clave `catalog.positions.manage` en `apps/access/registry.py`, `apps/access/seed.py` y `apps/access/legacy.py`
- [x] T032 [US4] Reemplazar la presentación de `user.level.name` por el filtro `puesto` en las plantillas donde se muestra el puesto de una persona: `templates/accounts/profile.html`, `templates/accounts/user_admin.html`, `templates/accounts/user_create.html`, `templates/dashboards/my_area.html` (filas), `templates/dashboards/_talent_table_main.html`, `templates/dashboards/_pending_people_table.html`, `templates/dashboards/_results_body.html`, `templates/dashboards/feedback_session_detail.html`, `templates/dashboards/_feedback_session_card.html`, `templates/dashboards/_scenario_card.html`, `templates/dashboards/current_scenario_board.html`, `templates/evaluations/ownership_fill.html`, `templates/learning/person_profile.html`, `templates/learning/people_list.html`; **los selectores/filtros por nivel (`level.code`) se dejan con niveles globales**
- [x] T033 [US4] Validar combinación área × nivel: en el alta/edición de usuario (`apps/accounts/forms.py`) y en `validate_for_publish` (T022) si no existe un `Position` activo, mostrar el error claro de FR-020
- [x] T034 [US4] Crear `apps/core/tests/test_positions.py` (compacta): siembra de CONS y Analítica, nombre visible, caché invalidada al renombrar, fallback al nivel, error por combinación no definida, y que renombrar no altera `PillarWeight` ni scores
- [x] T035 [US4] Ejecutar `scripts/pytest_changed.py apps/core/tests/test_positions.py apps/core/tests/test_access_coverage.py apps/core/tests/test_templates_compile.py apps/core/tests/test_navigation.py`

**Checkpoint**: cada área muestra sus puestos; la ponderación de pilares por nivel global sigue igual.

---

## Phase 6: User Story 3 — Consultoría contesta su Ownership por puesto (Priority: P2)

**Goal**: 4 cuestionarios de CONS (versión 1) cargados desde la matriz con categorías y pesos.

**Independent Test**: el generador produce el YAML con pesos de categoría iguales a la tabla de FR-023; la importación en seco y real crea 4 cuestionarios en borrador; un Analista de CONS ve 17 competencias agrupadas y el score coincide con la matriz (± 0.01).

**Depende de**: US2 (validación de pesos y editor) y US4 (puestos para publicar).

- [x] T036 [US3] Extender `apps/core/services/questionnaire_import.py` según `contracts/cons-yaml.md`: `categories` con pesos, `scale` y `scale_note` propios cuando no hay v1, `category`/`weight` por pregunta, una sección por categoría si hay más de una, validaciones con `ownership_weights`, versión 1 permitida sin v1, idempotente y con rechazo si hay respuestas
- [x] T037 [US3] Actualizar `apps/core/management/commands/import_questionnaire_version.py` para aceptar `--target-version 1` solo cuando el puesto no tiene v1 y el YAML trae `scale`, manteniendo `--dry-run` y `--publish`
- [x] T038 [P] [US3] Crear `scripts/matriz_consultoria_to_yaml.py` (usa `openpyxl`): lee «01 · Matriz por Puesto», aplica el mapeo bloque → categoría (FR-022), calcula pesos de categoría y de pregunta con mayor residuo a un decimal, excluye competencias que no aplican al puesto, redacta «Apego a los valores» como pregunta de escala con peso 0.0, imprime reporte de desviaciones contra los pesos originales y falla si alguna suma no es 100.0
- [x] T039 [US3] Generar `fixtures/questionnaires/cons/CONS.yaml` con el script, revisar el reporte (categorías = tabla de FR-023) y versionar el resultado
- [x] T040 [US3] Definir en el YAML la escala de CONS (No cumple, Necesita mejorar, Cumple satisfactoriamente, Excede, N/A con los descriptores de la hoja «00 · Instrucciones») y la nota de escala
- [x] T041 [US3] Crear `apps/core/tests/test_cons_import.py` (compacta): importa CONS en una BD de pruebas, verifica 4 cuestionarios con las categorías y pesos de FR-023, competencias que no aplican ausentes (Administración de recursos en Consultor; las 3 que no aplican al Analista), las 2 nuevas con peso 0.0, idempotencia, rechazo con respuestas, y que el score de respuestas conocidas coincide con el cálculo de la matriz original (pesos sin redondear) con diferencia ≤ 0.01
- [x] T042 [US3] Probar en local `import_questionnaire_version --dir fixtures/questionnaires/cons --target-version 1 --dry-run` y luego real, y verificar con un usuario CONS nivel JR que se le resuelve el cuestionario «Analista» (`resolve_ownership_template`)
- [x] T043 [US3] Agregar a `apps/core/tests/test_ownership_flow.py` un caso de Lead (nivel LEAD de CONS) que confirme que conserva la evaluación transversal sin proyecto (FR-027)

**Checkpoint**: CONS puede evaluar su Ownership con la matriz.

---

## Phase 7: User Story 5 — El informe muestra el score por categoría (Priority: P3)

**Goal**: Ver de dónde viene la calificación en la evaluación y en el informe.

**Independent Test**: una evaluación de CONS cerrada muestra cuatro categorías con score y peso; una de Analítica no muestra desglose; categoría toda N/A aparece «sin calificar».

- [x] T044 [US5] Agregar `ownership_pillar_breakdown(user, period)` a `apps/core/services/scoring.py` (promedio por categoría de las evaluaciones enviadas, emparejando por código de categoría)
- [x] T045 [US5] En `_render_ownership` y `ownership_autosave` de `apps/evaluations/views.py` agregar `category_rows` y la clave `categories` en el JSON (vacía si hay una sola categoría), según `contracts/weights-ui.md`
- [x] T046 [P] [US5] Crear el parcial `templates/evaluations/_category_scores.html` (nombre, peso, score, calificadas/total, «sin calificar») y mostrarlo en `templates/evaluations/ownership_fill.html` con actualización en vivo vía el JSON de autoguardado
- [x] T047 [US5] Mostrar el desglose del pilar en `templates/dashboards/_results_body.html` y pasar el dato desde `apps/dashboards/views.py` (oculto cuando solo existe «General»)
- [x] T048 [US5] Crear `apps/core/tests/test_category_breakdown.py`: filas por categoría, «sin calificar», desglose oculto con una categoría, promedio por categoría entre dos evaluaciones, y que la suma ponderada coincide con el total
- [x] T049 [US5] Ejecutar `.\build_css.ps1` si hubo clases nuevas

**Checkpoint**: el desglose es visible donde importa.

---

## Phase 8: User Story 6 — Evaluador sugerido por proyecto (Priority: P3)

**Goal**: El proyecto sugiere quién evalúa y se preselecciona al iniciar.

**Independent Test**: proyecto con evaluador sugerido → el integrante lo ve preseleccionado y puede cambiarlo; sin sugerido se preselecciona owner/responsable; nunca el propio colaborador.

- [x] T050 [US6] Agregar `Project.suggested_evaluator` (FK usuario, nula, `SET_NULL`, con historial) en `apps/catalog/models.py` y generar la migración `apps/catalog/migrations/0013_*.py`
- [x] T051 [US6] Incluir el campo en `ProjectForm` (`apps/catalog/forms.py`) con usuarios activos y etiqueta «Evaluador sugerido de Ownership»; mostrarlo en `templates/catalog/project_form.html`
- [x] T052 [US6] Crear en `apps/core/services/ownership_flow.py` `suggested_evaluator_for(project, user)` (sugerido → owner → responsable, excluyendo al colaborador y a inactivos) y usarlo en `ownership_start` de `apps/evaluations/views.py`; preseleccionar en `templates/evaluations/ownership_start.html`
- [x] T053 [US6] Ampliar `apps/core/tests/test_ownership_evaluators.py` con el escenario de preselección (sugerido, fallback owner, exclusión del propio colaborador, cambio por el colaborador)

**Checkpoint**: la elección de evaluador queda guiada por el proyecto.

---

## Phase 9: Polish y cross-cutting

- [x] T054 Actualizar `docs/KB_Modelo_Desempeno_2026.md` (nueva regla de ponderación por categoría y pesos, equivalencia con el promedio simple) y `docs/CONTEXTO_Sistema.md` (modelos nuevos, flujo, comandos `verify_ownership_scores` e importación de CONS, área CONS con Ownership)
- [x] T055 Actualizar `CLAUDE.md` del proyecto solo si cambia alguna regla de código (p. ej. mención de categorías) y revisar `docs/` de ayuda (`/ayuda/`) para el texto de Ownership
- [x] T056 Revisar con el agente `frontend-auditor` las pantallas nuevas/cambiadas (editor, catálogos, evaluación, informe) y corregir hasta CUMPLE
- [x] T057 Correr `scripts/pytest_changed.py` con todas las pruebas modificadas y las guardas (`test_access_coverage.py`, `test_templates_compile.py`, `test_shared_components.py`); confirmar verde
- [x] T058 Revisar `git status`: los archivos eliminados bajo `docs/Checklists/cuestionarios md/` no son de esta spec; no incluirlos en el commit
- [ ] T059 **Con confirmación del solicitante** (producción): correr `verify_ownership_scores` en Neon como línea base; aplicar migraciones con la URL unpooled de `docs/neon.md`; volver a correr `verify_ownership_scores` (debe dar cero diferencias); registrar conteos antes/después en `research.md`
- [ ] T060 **Con confirmación del solicitante**: commit + push a `main` (deploy en Vercel) y verificar `gh run list`
- [ ] T061 **Con confirmación del solicitante**: importar CONS en Neon en borrador (`--dry-run` y luego real), sembrar los puestos ya aplicados, y publicar cuando Dirección de Consultoría dé el VOBO de la matriz v1.1
- [ ] T062 Recorrer `quickstart.md` de punta a punta y marcar los resultados en el spec

---

## Dependencies & Execution Order

### Orden de fases
- **Setup (1)** → **Foundational (2)** → historias.
- **US1 (3)** depende solo de Foundational y es el MVP técnico.
- **US2 (4)** depende de Foundational; independiente de US1.
- **US4 (5)** depende de Foundational; independiente de US1/US2 (solo comparte `validate_for_publish` con T022/T033).
- **US3 (6)** depende de US2 (editor y validación) y US4 (puestos).
- **US5 (7)** depende de Foundational (cálculo); conviene después de US3 para verlo con datos reales de CONS.
- **US6 (8)** independiente; puede ir en paralelo con cualquier otra después de Foundational.
- **Polish (9)** al final; T059–T061 requieren confirmación explícita del solicitante.

### Orden recomendado de entrega
1. Foundational → US1 (equivalencia demostrada) → US2 → US4 → US3 → US5 → US6 → Polish.

### Dentro de cada historia
Modelos/migraciones → servicios → vistas/formularios → plantillas → pruebas → `build_css.ps1` si hubo UI.

### Oportunidades de paralelismo
- Foundational: T006/T007, T009, T010 y T013 en paralelo una vez hechos T003–T005.
- US2: T018 y T019 en paralelo con T021.
- US4: T029 y T030 en paralelo tras T027–T028.
- US3: T038 en paralelo con T036.
- US5: T046 en paralelo con T044–T045.
- US6 completo en paralelo con US5.

## Implementation Strategy

- **MVP técnico**: Foundational + US1 (cálculo ponderado equivalente, verificado con datos reales). Entregable sin cambios visibles.
- **MVP de negocio**: + US2 + US4 + US3 (Consultoría puede evaluar con pesos validados).
- **Incremental**: US5 (desglose) y US6 (evaluador sugerido) como mejoras.
- **Riesgo principal**: no regresión de scores (SC-001): se verifica en T009, T016, T017 y T059; si `verify_ownership_scores` reporta una sola diferencia, no se despliega.
- **Fuera de este spec** (backlog en `spec.md`): 360 al Gerente (009), seguimiento semestral (010), compuerta de Fundamentals (011), atributo vertical, C1–C10, Odoo.
