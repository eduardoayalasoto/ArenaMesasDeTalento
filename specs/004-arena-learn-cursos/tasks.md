---

description: "Task list for 004 Arena Learn"
---

# Tasks: Arena Learn — solicitud, autorización y registro de cursos con costo

**Input**: Design documents from `/specs/004-arena-learn-cursos/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/routes.md, quickstart.md

**Tests**: Incluidos. La convención del repo es que todo servicio nuevo tenga camino feliz y al menos 1 caso de error. Se corren con `--reuse-db` contra `test_neondb`, nunca en paralelo.

**Organization**: Por historia de usuario, en orden de prioridad: US1, US2 y US4 (P1); US3, US5 y US6 (P2); US7 (P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: US1–US7 del spec

---

## Phase 1: Setup

- [x] T001 Crear la app `apps/learning/` (`__init__.py`, `apps.py` con `name="apps.learning"` y `verbose_name="Arena Learn"`, `admin.py`, `forms.py`, `views.py`, `urls.py` con `app_name="learning"`, `migrations/__init__.py`)
- [x] T002 Registrar `"apps.learning"` en `INSTALLED_APPS` de `config/settings.py` y `path("arena-learn/", include("apps.learning.urls"))` en `config/urls.py`
- [x] T003 [P] Crear el directorio `templates/learning/` con la plantilla base de sección `templates/learning/_subnav.html`: tabs Mis cursos · Catálogo · Personas · Por aprobar (si aplica) · Seguimiento (Talento/Director)

---

## Phase 2: Foundational (bloquea todas las historias)

- [x] T004 Agregar `User.direct_lead` (FK self, null, `SET_NULL`, `related_name="direct_reports"`) en `apps/accounts/models.py` y generar la migración en `apps/accounts/migrations/`
- [x] T005 [P] Agregar `Area.director` (FK User, null, `SET_NULL`, `related_name="directed_areas"`, `limit_choices_to={"role": "DIRECTOR"}`) en `apps/catalog/models.py` y generar la migración en `apps/catalog/migrations/`
- [x] T006 Crear en `apps/learning/models.py` los modelos `CatalogCourse`, `CourseRequest` (con `HistoricalRecords`, choices de `status`/`current_stage`/`origin`/pago y la propiedad `cost_overrun`), `ApprovalStep` (con `save()` inmutable), `CourseEvidence`, `CourseReview` y `LearningSettings`, exactamente como en `data-model.md`
- [x] T007 Generar `apps/learning/migrations/0001_initial.py` y la migración de datos `0002_seed_settings.py`. Esta siembra `LearningSettings(pk=1)` con el texto fiscal del proceso actual: CFDI a nombre de Arena Analytics; si no es posible, nota o recibo con razón social Arena Analytics y dirección fiscal completa
- [x] T008 [P] Registrar los modelos en `apps/learning/admin.py` (solo DEBUG, igual que las demás apps), con `ApprovalStep` en solo lectura
- [x] T009 Crear `apps/core/services/learning_flow.py` con el esqueleto, las constantes de etapas (`STAGE_ORDER = [LEAD, DIRECCION, TALENTO]`) y el helper `_log_step(req, stage, actor, action, from_status, to_status, comment, assigned_to=None)`
- [x] T010 Implementar `eligible_approvers(req, stage)` en `apps/core/services/learning_flow.py` según research R2. Considera: REASIGNAR explícito vigente, `direct_lead`, Leads del área, `area.director`, Directores e `is_admin`. Siempre excluye al solicitante y a los usuarios con `deleted_at`
- [x] T011 Agregar a `apps/core/services/permissions.py`: `can_view_learning_profile`, `can_view_course_public`, `can_view_course_private`, `can_decide`, `can_manage_learning` y `can_view_tracking` (contracts/routes.md). **No** modificar `visible_users`
- [x] T012 [P] Fixtures de Arena Learn en `apps/core/tests/conftest.py`: `director_user`, `talento_user`, `lead_user` (nivel LEAD, misma área), `level_lead`, `catalog_course` y la factoría `make_request(user, **kw)`
- [x] T013 [P] Tests de `eligible_approvers` y de permisos en `apps/core/tests/test_learning_permissions.py`. Cubrir: direct_lead, respaldo a los Leads del área, área sin Leads, `area.director` vs. cualquier Director, exclusión del solicitante y que `visible_users` no cambia para un colaborador
- [x] T014 Ítem "Arena Learn" (icono `graduation-cap`, visible para todos) en `navigation()` de `apps/core/context_processors.py`

**Checkpoint**: modelos migrados, resolución de aprobadores probada.

---

## Phase 3: User Story 1 — Solicitar un curso (P1) 🎯 MVP

**Goal**: el colaborador crea una solicitud (desde el catálogo o nueva), la guarda en borrador o la envía.
**Independent Test**: tras crear y enviar, la solicitud aparece en "Mis cursos" como "En revisión del Lead" y queda registrado un `ApprovalStep` ENVIAR.

- [x] T015 [P] [US1] Tests en `apps/core/tests/test_learning_flow.py` para `create_request`/`submit_request`:
  - snapshot de datos desde el catálogo
  - campos obligatorios
  - borrador vs. envío
  - primera etapa aplicable: un solicitante LEAD empieza en DIRECCION; UX/UI sin Lead queda con `missing_lead=True`; un Director empieza en TALENTO
  - bloqueo FR-004 con un curso AUTORIZADO pendiente
- [x] T016 [US1] Implementar en `apps/core/services/learning_flow.py`: `create_request`, `assert_can_submit` (R7), `submit_request`, y `_enter_stage(req, stage)` con omisión automática y registro OMITIR. Todo en `transaction.atomic` + `select_for_update`
- [x] T017 [P] [US1] `RequestForm` en `apps/learning/forms.py`:
  - campos de FR-002 (pilar opcional, etiquetas)
  - valida `end >= start` y `cost >= 0`
  - si viene `catalog_course`, solo exige justificación y fechas
- [x] T018 [US1] Vistas `my_courses`, `request_create` (con `?catalogo=<id>` y `action=draft|submit`), `request_edit` y `request_detail` (vista privada con bitácora) en `apps/learning/views.py`, más sus rutas en `apps/learning/urls.py`
- [x] T019 [P] [US1] Plantillas `templates/learning/my_courses.html`, `templates/learning/request_form.html` y `templates/learning/request_detail.html`:
  - badge de estado + etapa, usando `partials/status_badge.html`
  - mensaje de bloqueo FR-004 con enlace al curso pendiente
- [x] T020 [US1] Tests de vista en `apps/core/tests/test_learning_views.py`: GET/POST de creación, que un tercero no pueda editar la solicitud ajena (403) y que el detalle privado esté prohibido para un colaborador ajeno

---

## Phase 4: User Story 2 — Autorización Lead → Director → Talento (P1) 🎯 MVP

**Goal**: los aprobadores deciden desde una bandeja; queda una bitácora inmutable y se notifica.
**Independent Test**: se recorren las 3 etapas hasta AUTORIZADA; un regreso desde Dirección se reanuda en Dirección; un rechazo sin comentario se impide.

- [x] T021 [P] [US2] Tests en `apps/core/tests/test_learning_flow.py` para `decide`, `cancel` y `reassign`:
  - aprobar avanza de etapa
  - regresar y reenviar reanuda en `returned_from_stage`
  - rechazar o regresar sin comentario lanza ValidationError
  - un actor no elegible lanza PermissionDenied
  - un Talento que es el solicitante no puede aprobarse
  - la cancelación del dueño vs. la de Talento
  - REASIGNAR prevalece sobre la resolución automática
  - `ApprovalStep` no se puede modificar
- [x] T022 [US2] Implementar `decide`, `cancel`, `reassign` y `_notify(req, event)` en `apps/core/services/learning_flow.py`. `_notify` usa `send_mail` con `fail_silently=True` dentro de `transaction.on_commit`: al siguiente aprobador cuando la solicitud entra a su etapa, y al dueño al aprobar, regresar o rechazar. Plantillas de correo de texto en `templates/learning/email/`
- [x] T023 [P] [US2] `DecisionForm` (`action` y `comment`, obligatorio para regresar y rechazar) y `ReassignForm` en `apps/learning/forms.py`
- [x] T024 [US2] Vistas `approvals_inbox` (solicitudes donde `can_decide`, con `select_related`), `request_decide` (htmx: devuelve `_decision_row.html` y un toast `HX-Trigger`), `request_cancel` y `request_reassign` en `apps/learning/views.py`, con sus rutas
- [x] T025 [P] [US2] Plantillas `templates/learning/approvals_inbox.html` y `templates/learning/_decision_row.html`:
  - modal de comentario para regresar o rechazar, reutilizando el patrón de modal de `templates/evaluations/ownership_fill.html`
  - panel de contexto (FR-011): historial de Arena Learn del colaborador y costo autorizado en el año
- [x] T026 [US2] Línea de tiempo de la bitácora en `templates/learning/request_detail.html`, con los botones Cancelar y Reasignar según permisos
- [x] T027 [US2] Pendientes de Learn en `notifications()` de `apps/core/context_processors.py` vía `learning_flow.pending_for(user)`, con 3 consultas como máximo: por aprobar, regresadas a mí, cursos por cerrar y evidencias por validar (Talento). Agregar el ítem "Por aprobar" con contador en `_subnav.html`
- [x] T028 [US2] Tests de vista en `apps/core/tests/test_learning_views.py`: la bandeja muestra solo lo elegible, `request_decide` con htmx devuelve el parcial, un no elegible recibe 403 y la campana incluye el pendiente

---

## Phase 5: User Story 4 — Cierre: evidencia y reseña (P1) 🎯 MVP

**Goal**: el colaborador cierra su curso con un certificado y una reseña; Talento valida.
**Independent Test**: se cierra un curso AUTORIZADO con un PDF de 3 MB y una reseña, pasa a COMPLETADA y se libera el bloqueo FR-004.

- [x] T029 [P] [US4] Tests en `apps/core/tests/test_learning_flow.py`:
  - `add_evidence`: tipo por magic bytes (rechaza un `.pdf` falso), límite de 4 MB, re-encode de imagen
  - `complete`: atómico; sin certificado o con reseña incompleta lanza error
  - `mark_not_completed` libera FR-004
  - `validate_evidence`: validar o regresar; con todas validadas pasa a VALIDADA
- [x] T030 [US4] Implementar `add_evidence`, `replace_evidence` (solo si `validation=REGRESADA`, registra el paso en la bitácora) (Pillow: lado mayor ≤2000 px, JPEG/WEBP de calidad 85; PDF tal cual), `complete`, `mark_not_completed` y `validate_evidence` en `apps/core/services/learning_flow.py`
- [x] T031 [P] [US4] `ReviewForm` (FR-019) y `EvidenceUploadForm` (validación de tamaño en el cliente con el atributo `accept` y en el servidor) en `apps/learning/forms.py`
- [x] T032 [US4] Vistas `request_complete` (multipart; también accesible en COMPLETADA con evidencia REGRESADA para reemplazarla), `request_not_completed`, `evidence_validate` (htmx) y `evidence_file` en `apps/learning/views.py`. `evidence_file` sirve los bytes con permisos: el CERTIFICADO es público si el curso es visible; el COMPROBANTE_FISCAL solo lo ven el dueño y Talento
- [x] T033 [P] [US4] Plantilla `templates/learning/complete_form.html`: vista previa del archivo con Alpine, estrellas 1–5, audiencia sugerida (áreas y niveles) y modal "No concluido" con motivo
- [x] T034 [US4] Tests de vista: subida de un archivo de 5 MB rechazada con mensaje, `evidence_file` responde 403 para el comprobante fiscal ajeno y 200 para el certificado público

**Checkpoint MVP**: US1 + US2 + US4 permiten dar de baja el Forms y el seguimiento de SharePoint.

---

## Phase 6: User Story 3 — Registro de pago (P2)

**Goal**: registrar la modalidad y el estado de pago sin gestionarlo.
**Independent Test**: en un curso AUTORIZADO se elige Reembolso y se marca Comprado; Talento lo ve.

- [x] T035 [P] [US3] Tests en `apps/core/tests/test_learning_flow.py` para `update_payment`: estados permitidos, `cost_overrun` > 10% y que un colaborador ajeno reciba PermissionDenied
- [x] T036 [US3] Implementar `update_payment` en `apps/core/services/learning_flow.py` y `PaymentForm` en `apps/learning/forms.py`
- [x] T037 [US3] Vista `request_payment` (htmx, devuelve `templates/learning/_payment_block.html`), vista `settings_edit` (Talento, `SettingsForm`) y plantilla `templates/learning/settings_form.html`
- [x] T038 [US3] Mostrar las instrucciones fiscales de `LearningSettings` y el bloque de pago en `templates/learning/request_detail.html` cuando el estado es AUTORIZADA o posterior. Permitir subir el COMPROBANTE_FISCAL privado

---

## Phase 7: User Story 5 — Arena Learn en el perfil, consultable por todos (P2)

**Goal**: cualquiera ve los cursos de otra persona; los datos privados nunca se exponen.
**Independent Test**: el colaborador A abre el perfil de B y ve el curso, la reseña y el certificado, pero no el costo ni la justificación.

- [x] T039 [P] [US5] Tests en `apps/core/tests/test_learning_permissions.py` y `test_learning_views.py`:
  - `person_profile` lista solo los estados públicos
  - el HTML de `course_public` **no contiene** costo, justificación ni comentarios de autorización (assert sobre el contenido)
  - no aparecen borradores, rechazadas ni canceladas
- [x] T040 [US5] Implementar `learning_public_requests(person)` y `public_course_context(req)` en `apps/core/services/learning_flow.py`. Este último arma un dict solo con campos públicos
- [x] T041 [US5] Vistas `people_list` (buscador por nombre y área, con fotos `?mini=1`; excluye usuarios con `deleted_at`), `person_profile` (sigue accesible para usuarios dados de baja, como historial) y `course_public` en `apps/learning/views.py`
- [x] T042 [P] [US5] Plantillas `templates/learning/people_list.html`, `templates/learning/person_profile.html` y `templates/learning/course_public.html`
- [x] T043 [US5] Agregar la tab "Arena Learn" en `templates/accounts/profile.html`, con resumen y enlace a su `person_profile`

---

## Phase 8: User Story 6 — Catálogo sugerido y explorador (P2)

**Goal**: Talento administra el catálogo; todos exploran con su rating y reseñas.
**Independent Test**: Talento da de alta un curso, el colaborador lo filtra por área y crea una solicitud precargada.

- [x] T044 [P] [US6] Tests: filtros del catálogo, agregados `completed_count`/`avg_rating` (sin N+1, anotados en el queryset), archivado oculto en la solicitud pero conservado en el historial, y `promote_to_catalog` conserva las reseñas
- [x] T045 [US6] Implementar `catalog_queryset(filters)` (con `annotate`) y `promote_to_catalog` en `apps/core/services/learning_flow.py`, y `CatalogCourseForm` en `apps/learning/forms.py`
- [x] T046 [US6] Vistas `catalog_list`, `catalog_detail`, `catalog_create`, `catalog_edit`, `catalog_archive` (htmx) y `catalog_promote` en `apps/learning/views.py`
- [x] T047 [P] [US6] Plantillas `templates/learning/catalog_list.html`, `templates/learning/catalog_detail.html` y `templates/learning/catalog_form.html`, con el botón "Solicitar este curso" que lleva a `request_create?catalogo=<id>`
- [x] T048 [US4] Registro directo (FR-022; se agenda en esta fase porque comparte el form de catálogo): `create_direct` en `apps/core/services/learning_flow.py`, vista `direct_create` y plantilla `templates/learning/direct_form.html` (curso + evidencia + reseña), con su test de camino feliz y error

---

## Phase 9: User Story 7 — Seguimiento para Talento (P3)

**Goal**: tablero de estados, costos por área y año, atascadas, vencidos y exporte.
**Independent Test**: los conteos del tablero coinciden con las filas exportadas.

- [x] T049 [P] [US7] Tests de `dashboard_rows`: atascada (> 5 días hábiles desde el último paso), vencido (AUTORIZADA y fin + 30 días) y costo autorizado por área y año
- [x] T050 [US7] Implementar `business_days_between`, `dashboard_rows(filters)` y `export_rows(filters)` en `apps/core/services/learning_flow.py`
- [x] T051 [US7] Vistas `tracking` y `tracking_export` (openpyxl, mismo patrón que `apps/dashboards/views.py::export_scores_xlsx`) y plantilla `templates/learning/tracking.html`
- [x] T052 [US7] Carga histórica (FR-032): vista `historic_create` (solo Talento, elige persona, reutiliza `direct_form.html` con `origin=HISTORICO`)

---

## Phase 10: Polish & Cross-Cutting

- [x] T053 [P] Columna "Lead directo" editable en `/cuenta/usuarios/` (`apps/accounts/views.py::user_admin`, `templates/accounts/user_admin.html`). Respetar el fix de 2026-06-17: solo se actualizan los usuarios cuyo campo llegó en el POST. Validar que la persona no se asigne a sí misma
- [x] T054 [P] Crear la pantalla `area_admin` (no existe hoy): ruta `catalogo/areas/` en `apps/catalog/urls.py`, vista en `apps/catalog/views.py`, `templates/catalog/area_admin.html`, edición del campo "Director" por área (solo `is_admin`) e ítem dentro del folder "Catálogos" del sidebar en `apps/core/context_processors.py`
- [x] T055 [P] Mostrar Arena Learn (lista resumida) en `templates/dashboards/talent_person.html` como insumo cualitativo de Mesa de Talento, sin afectar las calificaciones
- [x] T056 [P] Sección de Arena Learn en la ayuda `/ayuda/` y actualización de `docs/CONTEXTO_Sistema.md` (app, modelos, rutas, excepción a RN-14)
- [x] T057 Recompilar CSS con `.\build_css.ps1` y versionar `static/css/app.css`
- [ ] T058 Correr la regresión completa `.\.venv\Scripts\python.exe -m pytest apps/core/tests/ --reuse-db` y los escenarios de `quickstart.md`
- [ ] T059 Aplicar las migraciones a Neon (URL unpooled de `docs/neon.md`) junto con el push a `main`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)**: no tiene dependencias.
- **Foundational (Fase 2)**: depende de Setup y **bloquea todas las historias**.
- **US1 (Fase 3)**: depende de Foundational.
- **US2 (Fase 4)**: depende de US1 (necesita solicitudes enviadas).
- **US4 (Fase 5)**: depende de US2 (necesita cursos AUTORIZADOS). En los tests se puede crear AUTORIZADA directo con la factoría.
- **US3 (Fase 6)**: depende de US2.
- **US5 (Fase 7)**: depende de US4 (necesita cursos cerrados).
- **US6 (Fase 8)**: el catálogo solo depende de Foundational y de US1 (precarga). La promoción depende de US4.
- **US7 (Fase 9)**: depende de US2 y US4.
- **Polish (Fase 10)**: T053 y T054 se pueden adelantar después de Fase 2, porque desbloquean la prueba manual de US2.

### Parallel Opportunities

- Fase 2: T005 ∥ T004, y T008, T012 y T013 en paralelo una vez que existen los modelos.
- Dentro de cada historia, el test, el form y la plantilla [P] van en paralelo; servicio → vista es secuencial.
- US3, US5 y US6 son paralelas entre sí una vez cerrado el MVP.

### Parallel Example: US2

```text
T021 tests de decide/cancel/reassign   ∥  T023 DecisionForm  ∥  T025 plantillas bandeja
→ T022 servicio → T024 vistas → T026/T027 → T028
```

## Implementation Strategy

### MVP First (US1 + US2 + US4)

1. Fases 1–2, más T053 y T054 (Lead directo y Director de área) para poder probar con datos reales.
2. US1, US2 y US4: con esto se da de baja el Forms. **Validar** con quickstart 1–6.
3. Desplegar con las migraciones a Neon.

### Incremental Delivery

4. US5 y US6: visibilidad colectiva (el mayor valor después del MVP).
5. US3: pago e instrucciones fiscales.
6. US7: tablero y carga histórica, con la migración de SharePoint.

## Notes

- **Desviaciones de implementación (2026-10-06)**:
  - Las decisiones (aprobar/regresar/rechazar), cancelar, reasignar y validar evidencia usan POST de formulario + redirect con toast (patrón de `ownership_fill.html`) en vez de htmx parcial. Solo el bloque de pago usa htmx. Así funciona sin JS y es más simple de probar.
  - La vista de Áreas vive en `apps/catalog/views_areas.py` para no mezclarse con cambios ajenos en curso en `apps/catalog/views.py`.
  - El resumen de Arena Learn en Mi perfil y en Mesa de Talento se inserta con el templatetag `{% arena_learn_summary %}` (`apps/learning/templatetags/learning_tags.py`).
  - T059 (migrar Neon y push) queda **pendiente a propósito**: el usuario pidió solo commit local.

- Toda escritura pasa por `learning_flow.py`. Las vistas solo validan con un Form, llaman al servicio y renderizan.
- Nunca pasar campos privados al contexto de las plantillas públicas (R6).
- Correr pytest **una sola vez a la vez** contra Neon, con `--reuse-db`.
