---

description: "Task list for 006 Arena Learn — planes anuales, etiquetas e importación"
---

# Tasks: Arena Learn — planes anuales, etiquetas e importación

**Input**: spec.md, plan.md, research.md (R1–R12), data-model.md, contracts/routes.md, contracts/planes-json.md, quickstart.md

**Tests**: compactos por escenario, contra Neon (`--reuse-db`, sin paralelo). Usuarios de prueba con `password=None`. Cada servicio nuevo cubre el camino feliz y al menos un error.

**Gate antes de implementar**: el usuario audita el resultado de `/speckit-analyze`.

**Gate antes de la corrida en producción (T030)**: el usuario revisa `apps/learning/data/planes_2026.json` y el resumen del `--dry-run`.

## Phase 1: Setup

- [x] T001 Crear la rama git `006-arena-learn-planes-anuales` desde la rama actual y confirmar que `.specify/feature.json` apunta a `specs/006-arena-learn-planes-anuales`
- [x] T002 [P] Script de apoyo `scripts/extract_plans_html.py`: lee los 4 HTML (ruta por argumento, ejecutado con `python -I`) y genera un borrador de `apps/learning/data/planes_2026.json` con el formato de `contracts/planes-json.md`: metadatos del plan, textos por tipo, niveles por liga, certificaciones con costo, notas y ligas KO con fase. El plan CD une IA v4 (DS_2026) e IA v2 (IS); el plan ID sale de la parte de Ingeniería de Datos de IS

## Phase 2: Foundational (bloquea todas las historias)

- [x] T003 Modelos en `apps/learning/models.py` según data-model.md:
  - nuevos: `Tag`, `TrainingPlan` (con `Status`, `type_notes` y `UniqueConstraint(area, year)`), `PlanCourse` (FK plan, M2M `levels`, `UniqueConstraint(plan, course)`), `PersonalPlan`, `PersonalPlanItem`;
  - en `CatalogCourse` y `CourseRequest`: `tags` pasa a M2M, `duration_hours` a `DecimalField(5,1)` y se quitan `normalize_tags`, `tag_list` y el `save()` de catálogo;
  - `CourseKind` redefinido como tipo de aprendizaje (Estructurado, Certificación, Puntual, Contextual, Soft Skills, Evento) y `Focus` (HORIZONTAL/VERTICAL) independiente, sin derivación entre ambos (R12);
  - en `CatalogCourse`: se quitan `levels`, `pillar` y `areas`; se agrega `focus`; propiedad o servicio `plan_areas` (áreas de los planes publicados);
  - en `CourseRequest`: se agrega `is_imported`.
- [x] T004 Migración `apps/learning/migrations/0004_tags_planes.py`, generada con `makemigrations` y revisada: quita los CharField `tags` (también del modelo histórico) y `CatalogCourse.levels`, `pillar` y `areas`; agrega `focus` (default HORIZONTAL), convierte `kind` con el mapeo de R12 (CURSO/CAPACITACION → ESTRUCTURADO, CONFERENCIA → EVENTO, OTRO → PUNTUAL) en catálogo, solicitudes e historial, y crea las tablas nuevas. No migra las etiquetas de texto (FR-008); sí convierte los valores de `kind`
- [x] T005 [P] `normalize_url` en `apps/core/services/learning_flow.py` (R3): conserva los parámetros identificadores y quita `t, si, ref, trk, utm_*, coupon*, referralCode, source`. Prueba en `apps/core/tests/test_learning.py`: dos videos de YouTube con distinto `v` dan ligas distintas y `&t=` se ignora
- [x] T006 Claves nuevas en `apps/access/registry.py` (R9), con rutas de `contracts/routes.md`: `learn.plans.view`, `learn.plans.manage`, `learn.myplan`, `learn.myplan.others`, `learn.plans.tracking` y `learn.tags.manage`. `learning:tag_suggest` va en `learn.public.view`. `learn.myplan`, `learn.myplan.others` y `learn.plans.tracking` se registran con `status="pending"` y se activan en T034/T036 (I1)
- [x] T007 Filas en `apps/access/seed.py` y `apps/access/legacy.py` (Colab, Lead, Dir, Tal):
  - plans.view (T, T, T, T)
  - plans.manage (N, N, N, T)
  - myplan (P, P, P, P)
  - myplan.others (N, A, T, T)
  - plans.tracking (N, A, T, T)
  - tags.manage (N, N, N, T)
- [x] T008 Migración de datos `apps/access/migrations/0003_learn_planes_grants.py`: agrega a los perfiles existentes los grants de T007 **solo si faltan**, sin pisar ediciones hechas desde la matriz. Es idempotente y tiene reversa que los quita
- [x] T009 Servicio `apps/core/services/learning_tags.py`: `normalize_tag_key`, `resolve`, `suggest`, `rename`, `merge`, `set_active` y `filter_by_tags` (contracts/routes.md § Servicios). Usa `transaction.atomic` en `merge` y `access.require(actor, "learn.tags.manage")` en las de administración
- [x] T010 Adaptar `apps/core/services/learning_flow.py` a las etiquetas M2M y a la ausencia de `levels`:
  - `_apply_data` recibe una lista de nombres de etiqueta;
  - `catalog_queryset` usa `prefetch_related("tags")`; filtra por etiquetas (AND) y por enfoque; "área" filtra por planes publicados; se quitan los filtros de nivel y pilar; `q` busca en `tags__name`;
  - `promote_to_catalog` copia las etiquetas y fija `focus`; no copia niveles, pilar ni áreas;
  - `CATALOG_SNAPSHOT` y la precarga desde el catálogo ya no incluyen `pillar` (la solicitud lo conserva como opinión del colaborador);
  - `requestable_courses`, `template_data_from` y `public_course_context` usan las etiquetas como lista.
- [x] T011 Ajustar `apps/learning/admin.py`, `apps/learning/forms.py` (quitar `levels`, `pillar` y `areas` del curso; agregar `focus` como campo obligatorio aparte del tipo, sin sugerencia automática; duración decimal en formularios, plantillas y `export_rows` con formato "1.5 h"); `tags` provisional como texto separado por comas hasta T014) y las plantillas que usaban `course.levels`, `tag_list` y `.tags`: `templates/learning/catalog_detail.html`, `catalog_form.html`, `catalog_list.html`, `course_public.html` y `request_detail.html`. `apps/core/tests/test_learning.py` debe quedar en verde

**Checkpoint**: migración aplicada en la BD de pruebas, `test_learning.py` y `test_access_coverage.py` en verde (las rutas nuevas aún no existen; la cobertura de claves sin ruta se valida en T028).

## Phase 3: US1 — Etiquetas gestionables y filtro (P1)

**Goal**: etiquetas con autocompletar en todos los formularios, filtro AND en el catálogo y administración por Talento.

**Independent Test**: spec US1 (crear "KO" desde un curso, asignarla a 2 más, filtrar y obtener exactamente 3; fusionar "PowerBI" en "Power BI").

- [x] T012 [P] [US1] Pruebas en `apps/core/tests/test_learning_tags.py`, una por escenario de US1 (1 a 6) más los casos borde: " KO " = "ko", fusionar en sí misma o en inactiva → error, renombrar a un nombre existente → error, etiqueta inactiva no sugerida ni re-creable pero visible en el curso
- [x] T013 [P] [US1] Componente `templates/components/_tag_input.html` (R2): fichas `badge badge-soft` con botón para quitar (Lucide `x`), input con `hx-get` a `learning:tag_suggest` (`input changed delay:200ms`, `hx-indicator`), lista de sugerencias navegable con teclado, Enter crea una ficha nueva y un `<input type="hidden" name="tags">` por ficha. Alpine solo para el estado local. Cumple `DESIGN_SYSTEM.md`
- [x] T014 [US1] `TagNamesField` en `apps/learning/forms.py` (lista de nombres limpia y sin duplicados por `key`), usado en `CatalogCourseForm`, el formulario de solicitud, el registro directo y el histórico. Las views llaman a `learning_tags.resolve` dentro del servicio. Con `?catalogo=` se precargan las etiquetas del curso (FR-004)
- [x] T015 [US1] Vista `tag_suggest` y parcial `templates/learning/_tag_suggest.html` en `apps/learning/views.py` y `urls.py`
- [x] T016 [US1] Filtros del catálogo en `catalog_list`: multi-etiqueta (`?etiqueta=<id>&etiqueta=<id>`, AND) y enfoque, en lugar de "nivel" y "pilar". Filtro y badges de tipo de aprendizaje, enfoque y etiqueta en `templates/learning/catalog_list.html` y `_course_card.html`
- [x] T017 [US1] Administración de etiquetas: vistas `tag_list`, `tag_edit`, `tag_merge` (modal `_confirm.html` con selector de destino) y `tag_toggle`; plantillas `templates/learning/tag_list.html` y `_tag_row.html` (tabla `_table.html` con nº de cursos y de solicitudes); acceso desde Catálogo con `{% can "learn.tags.manage" %}` y `also_active` en `apps/core/navigation.py`

**Checkpoint**: US1 funcional e independiente.

## Phase 4: US2 — Planes anuales por área (P1)

**Goal**: ver y administrar planes por área y año, agrupados por tipo de aprendizaje, con niveles por plan y filtros.

**Independent Test**: spec US2 (Talento crea el plan PM 2026 con 5 cursos de 3 tipos y con niveles; un PM Jr lo ve preseleccionado y filtra por Jr + KO).

- [x] T018 [P] [US2] Pruebas en `apps/core/tests/test_learning_plans.py` (sección planes) para los escenarios 1 a 6 de US2:
  - unicidad área-año;
  - un borrador es invisible sin `learn.plans.manage`;
  - no se publica un plan vacío;
  - niveles distintos del mismo curso en dos planes;
  - filtro de nivel que incluye "Todos los niveles";
  - curso archivado como "No disponible";
  - usuario sin área recibe la lista de planes;
  - usuario que cambia de área recibe preseleccionado el plan de su nueva área (C1);
  - un curso no se repite en un plan, la vista agrupa por tipo en el orden fijo y las áreas de un curso se derivan de sus planes publicados.
- [x] T019 [US2] Servicio `apps/core/services/learning_plans.py` (parte de planes): `current_plan_for`, `plan_groups(plan, filters)` con prefetch (≤ 6 consultas), agrupación por tipo y filtros por tipo, nivel (N o vacío) y etiquetas (AND), `save_plan` (incluye `type_notes`), `set_status` (FR-013/014), `save_item`, `move_item` y `delete_item`
- [x] T020 [US2] Forms `PlanForm` (cabecera + un texto por tipo de aprendizaje) y `PlanItemForm` (curso con buscador del catálogo, niveles con checkboxes y nota) en `apps/learning/forms.py`
- [x] T021 [US2] Vistas `plan_list` y `plan_detail` (página completa o, con `HX-Request`, el parcial de cursos) más plantillas `templates/learning/plan_list.html`, `plan_detail.html` y `_plan_courses.html`. Cada curso muestra plataforma, liga, tipo, enfoque, niveles ("Todos los niveles"), etiquetas, costo, duración y rating promedio (FR-016). Grupos por tipo de aprendizaje con su texto; filtros por tipo, nivel y etiqueta con htmx
- [x] T022 [US2] Vistas de administración `plan_create`, `plan_edit`, `plan_status` y `plan_item_save`/`plan_item_edit`, con plantillas `plan_form.html` y `_plan_items_admin.html` (edición en línea con htmx y toast; confirmación de archivado o despublicación con `_confirm.html`)
- [x] T023 [US2] Menú: ítem "Planes" (`learn.plans.view`, icono Lucide `map`) en la categoría Arena Learn de `apps/core/navigation.py`, con `also_active` para las rutas de plan; actualizar `templates/learning/_subnav.html` si aplica. Ajustar `apps/core/tests/test_navigation.py`
- [x] T024 [US2] En `catalog_detail`, bloque "En los planes" (área, año y niveles de cada `PlanCourse` del curso) en `templates/learning/catalog_detail.html`

**Checkpoint**: US2 funcional; se puede crear un plan a mano.

## Phase 5: US4 — Limpieza e importación del catálogo y los planes (P1) 🎯 MVP

**Goal**: dejar en producción el catálogo real y los 4 planes 2026 publicados, sin datos de prueba.

**Independent Test**: spec US4 (en BD de prueba: importar fixture → N cursos, 4 planes publicados, sin agrupación KO, "KO" solo en las ligas KO; segunda corrida → 0 creados).

- [x] T025 [US4] Generar con T002 y **curar a mano** `apps/learning/data/planes_2026.json`:
  - revisar periodo, horas, textos por tipo y niveles de PM (67) y UX/UI (12);
  - certificaciones con costo (PMP, PL-300, DP-900, AI-900/901, AI-103, AI-300, CCA, Google UX, DP-700, DP-203, Databricks DE Associate, AZ-400);
  - ligas KO con fase;
  - los 20 cursos solo-KO del plan PM;
  - `courses`: tipo y/o enfoque **propuestos** para los huecos (58 sin tipo, 206 sin enfoque, 5 con dos tipos), cada uno con su motivo, según el criterio de los supuestos de la spec.
  Validar contra el Excel que toda liga del JSON exista en el Excel o sea una certificación
- [x] T026 [P] [US4] Pruebas en `apps/core/tests/test_learning_import.py` con un xlsx y un JSON mínimos generados en la prueba (`tmp_path`), uno por escenario de US4 (1 a 9):
  - misma liga en CD e ID;
  - ruta "Ingeniería de IA" → CD;
  - "Mid-Snr" → {Mid, Snr};
  - curso solo-KO → tipo Puntual + nivel por fase + etiqueta KO, sin agrupación KO;
  - "Aprendizaje Horizontal/Vertical" solo fija el enfoque y nunca el tipo; "Habilidades Blandas" → Soft Skills; se quita el prefijo de ruta de la hoja ID;
  - hueco de tipo o enfoque, o dos tipos → valor de `courses[url]` marcado propuesto; sin valor → fila reportada;
  - certificación con costo USD;
  - no sobrescribe datos editados;
  - fila sin liga reportada;
  - la limpieza respeta `LearningSettings` y no toca otros modelos;
  - los planes quedan PUBLICADO.
  Más la idempotencia (segunda corrida = 0 creados) y que un plan ARCHIVADO no se republica
- [x] T027 [US4] Servicio `apps/core/services/learning_import.py`:
  - `import_catalog_and_plans(xlsx_path, plans_json_path, year, dry_run)` con las reglas R7, en una sola `transaction.atomic`, que hace rollback si `dry_run`;
  - devuelve `ImportSummary` (creados, actualizados, sin cambio, planes, etiquetas asignadas, alias, datos propuestos y filas no procesadas con motivo);
  - completa solo campos vacíos de cursos existentes (FR-029);
  - infiere la plataforma desde el dominio si viene vacía;
  - `reset_learning_data(before, confirm)` según R10.
- [x] T028 [US4] Comandos `apps/learning/management/commands/reset_learning_data.py` (`--before`, `--confirm`; sin confirm solo imprime conteos) e `import_learning_plans.py` (`--xlsx`, `--plans`, `--year`, `--dry-run`; imprime el resumen legible). Verificar `test_access_coverage.py` en verde con todas las rutas de las fases 3 y 4
- [x] T029 [US4] `--dry-run` local contra la BD de desarrollo con los archivos reales; guardar el resumen en `specs/006-arena-learn-planes-anuales/reporte-importacion.md`, con la tabla de datos **propuestos** (curso, tipo, enfoque, motivo). **Gate: el usuario lo revisa junto con el JSON**
- [x] T030 [US4] Corrida en producción (quickstart § 3), solo con autorización explícita del usuario:
  1. migraciones con la URL directa;
  2. `reset_learning_data` en seco y luego confirmar conteos;
  3. rama de respaldo `backup-pre-006` en Neon;
  4. `--confirm`;
  5. `import_learning_plans`;
  6. segunda corrida = 0 creados;
  7. push a `main`;
  8. anexar los resultados a `reporte-importacion.md`.

**Checkpoint (MVP)**: producción muestra los 4 planes reales con etiquetas y filtros.

## Phase 6: US3 — Mi plan (P2)

**Goal**: el colaborador arma su plan del año y ve su avance derivado de Arena Learn.

**Independent Test**: spec US3 (agregar 4 cursos, Empezar 1, Solicitar 1, completar el primero, descartar otro; el Lead ve lo mismo y otro colaborador recibe 403).

- [x] T031 [P] [US3] Pruebas en `apps/core/tests/test_learning_plans.py` (sección Mi plan) para los escenarios 1 a 7 de US3:
  - estado derivado de cada estado de `CourseRequest` (R8): BORRADOR → Pendiente con nota; RECHAZADA, CANCELADA y NO_CONCLUIDA → Pendiente;
  - curso agregado desde el catálogo cae en el plan del año en curso;
  - un curso ya completado se agrega como Completado;
  - no se agrega desde un plan archivado ni un curso inactivo;
  - bloqueo por curso autorizado sin cerrar (FR-038);
  - visibilidad propio / Lead (A = reportes directos, `Q(direct_lead=viewer)`) / Director / Talento / otro (403);
  - Mi plan se resuelve en ≤ 3 consultas.
- [x] T032 [US3] Servicio (parte Mi plan) en `apps/core/services/learning_plans.py`: `add_to_my_plan`, `start_item`, `discard_item`, `item_states` y `can_view_personal_plan`
- [x] T033 [US3] Forms y vistas `my_plan`, `my_plan_add`, `my_plan_start` (`mode=request|free`), `my_plan_complete`, `my_plan_discard` y `person_plan`, con plantillas `templates/learning/my_plan.html`, `_my_plan_row.html` y `person_plan.html`. Botón "Agregar a Mi plan" en `_plan_courses.html` y `catalog_detail.html` (htmx: cambia a "En mi plan"). "Iniciar" abre un modal con las dos opciones y sugiere la opción según el costo de referencia (FR-019)
- [x] T034 [US3] Activar `learn.myplan` y `learn.myplan.others` (quitar `status="pending"`). Menú "Mi plan" (`learn.myplan`, icono Lucide `list-checks`) en `apps/core/navigation.py`. Enlace "Plan" en `person_profile.html` solo con `{% can "learn.myplan.others" %}` y alcance válido

**Checkpoint**: US3 funcional.

## Phase 7: US5 — Seguimiento de planes (P3)

**Goal**: tablero y exporte del avance de planes personales por área, año y persona.

**Independent Test**: spec US5 (3 personas PM con avances distintos: totales correctos en pantalla y en Excel; un Lead solo ve a sus reportes).

- [x] T035 [P] [US5] Pruebas en `apps/core/tests/test_learning_plans.py` (sección seguimiento) para los escenarios 1 a 3 de US5, con el alcance del Lead (A)
- [x] T036 [US5] Activar `learn.plans.tracking`. `tracking_rows` y `tracking_export_rows` en `apps/core/services/learning_plans.py` (2 consultas más resolución en memoria), más las vistas `plan_tracking` y `plan_tracking_export` (openpyxl, mismo estilo que `tracking_export`) y la plantilla `templates/learning/plan_tracking.html` (pestaña junto a Seguimiento)

## Phase 8: US6 — Cursos ya tomados (P3) ⏸ bloqueada

**Bloqueo**: necesita el export (.xlsx/.csv) de la lista de SharePoint "Cursos actuales por colaborador".

- [ ] T037 [US6] Al recibir el archivo: documentar sus columnas en `specs/006-arena-learn-planes-anuales/contracts/cursos-tomados.md` y la regla de cruce (persona por correo y luego por nombre; curso por liga y luego por nombre)
- [ ] T038 [US6] Pruebas en `apps/core/tests/test_learning_import.py` (escenarios 1 a 5 de US6)
- [ ] T039 [US6] Decidir con el archivo en mano si un importado "En curso" se exenta del bloqueo por curso autorizado sin cerrar (U2). En `learning_flow.create_direct` o en una función hermana `create_imported`: permitir `origin=HISTORICO` + `is_imported=True` sin evidencia ni reseña, con estado COMPLETADA o AUTORIZADA (En curso), sin relajar el registro histórico manual
- [ ] T040 [US6] Comando `import_taken_courses` idempotente (persona + curso) con su resumen; badge "Importado" en `request_detail.html` y en el perfil

## Phase 9: Polish

- [x] T041 [P] Auditoría de UI con el agente `frontend-auditor` sobre las plantillas nuevas (CUMPLE / NO CUMPLE contra `DESIGN_SYSTEM.md`) y corrección de hallazgos
- [x] T042 [P] Actualizar `docs/CONTEXTO_Sistema.md` (modelos, rutas y comandos de 006)
- [ ] T043 Suite completa `python -m pytest --reuse-db` en verde y recorrido manual de quickstart § 4

## Dependencies & Execution Order

- **Setup (T001–T002)** → **Foundational (T003–T011)** → historias.
- **US1 (T012–T017)** y **US2 (T018–T024)** pueden ir en paralelo después de Foundational; T016 y T021 comparten el filtro de etiquetas (`filter_by_tags`, T009).
- **US4 (T025–T030)** depende de Foundational y usa los modelos de US2. Su corrida en producción (T030) requiere que US1 y US2 estén listas para el deploy, porque las pantallas del catálogo y de planes deben funcionar.
- **US3 (T031–T034)** depende de US2 (plan_detail) y de que haya planes (US4 en dev).
- **US5 (T035–T036)** depende de US3.
- **US6 (T037–T040)** depende del archivo externo y de T003 (`is_imported`).
- **Polish** al final de cada deploy.

### Deploys

1. **Deploy 1 (MVP)**: fases 1 a 5 + T041 y T043 parciales, con la corrida en producción T030.
2. **Deploy 2**: fases 6 y 7.
3. **Deploy 3**: fase 8 (cuando llegue el archivo).

## Parallel Example

```text
Después de T011:
  T012 (pruebas de etiquetas) ‖ T013 (componente _tag_input) ‖ T018 (pruebas de planes) ‖ T026 (pruebas de import) ‖ T025 (curar el JSON)
```

## Implementation Strategy

MVP = US1 + US2 + US4: el catálogo real con etiquetas y los 4 planes publicados en producción. Mi plan y Seguimiento llegan en un segundo deploy sin migraciones destructivas (sus tablas ya se crean en T004). US6 queda pendiente del archivo de SharePoint.
