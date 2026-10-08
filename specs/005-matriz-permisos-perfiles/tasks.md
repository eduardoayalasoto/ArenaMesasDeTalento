---

description: "Task list for 005 Matriz de permisos por perfiles"
---

# Tasks: Matriz de permisos por perfiles

**Input**: spec.md, plan.md, research.md, data-model.md, seed-matrix.md, research-permisos-actuales.md

**Tests**: compactos por escenario (preferencia del usuario). La cobertura y la paridad corren sin HTTP. Usar `--reuse-db` y nunca correr en paralelo.

**Gate antes de implementar**: el usuario revisa y aprueba `seed-matrix.md`.

## Phase 1: Setup

- [x] T001 Crear `apps/access/` (`__init__`, `apps.py`, `models.py`, `admin.py`, `migrations/`) y registrarla en `config/settings.py`
- [x] T002 [P] `apps/access/registry.py`: `Scope` IntEnum, `PermissionDef`, `PERMISSIONS` con todas las claves de `seed-matrix.md` (módulo, pantalla, acción, alcances admitidos, rutas, kind, status) y `EXEMPT_ROUTES`

## Phase 2: Foundational (bloquea todo)

- [x] T003 Modelos `Profile`, `ProfileGrant` y `AccessAuditLog` (inmutable) en `apps/access/models.py`, más la migración `0001`
- [x] T004 `User.profile` FK PROTECT null en `apps/accounts/models.py`, más su migración
- [x] T005 `apps/access/seed.py`: `SEED_MATRIX` (= `seed-matrix.md`) y `suggested_profile(user)` (R8); migración de datos `0002_seed_profiles` idempotente
- [x] T006 `apps/access/services.py`:
  - `effective_profile`, `grants_for(user)` con caché en el usuario del request;
  - `scope`, `has`, `require` (lanza PermissionDenied);
  - `scope_qs(user, key, qs, *, owner, area, assigned_q)`;
  - `assignable_users(key)`.
  - El superusuario siempre tiene TODOS.
- [x] T007 `apps/access/decorators.py`: `@requires(key, at_least=Scope.PROPIO)`. Marca `view._access_key`, responde 403 con `errors/403.html` y fija `request.access_scope`
- [x] T008 [P] Templatetag `{% can "clave" as x %}` / filtro `user|can:"clave"` en `apps/access/templatetags/access_tags.py`
- [x] T009 [P] `apps/core/tests/test_access_coverage.py`. Recorre el URLconf completo: cada ruta no exenta tiene `_access_key` registrada; cada permiso activo `kind=screen` protege al menos una ruta; las claves de la semilla existen en el registro; los alcances de la semilla están entre los admitidos

## Phase 3: US6 + US3 — Aplicación en todas las pantallas con paridad (P1) 🎯

- [x] T010 [US3] Fachada `apps/core/services/permissions.py`: `visible_users`, `can_view_evaluation`, `can_capture_value_delivery`, `can_validate_*`, `can_edit_project`, `can_*feedback*` y las de Arena Learn consultan `access` más la relación. Se elimina `_is_admin` con Director (una sola definición de admin)
- [x] T011 [US3] `@requires` en `apps/dashboards/views.py` (17 rutas), usando `people.results.*`, `talent_table.*`, `current_scenario.*`, `feedback.*`, `period_progress.view` y `dashboard.home.view`
- [x] T012 [US3] `@requires` en `apps/accounts/views.py` (`users.*`) y `apps/catalog/views.py` / `views_areas.py` (`projects.*`, `periods.manage`, `areas.manage`, `scenarios.manage`). **Coordinar con los cambios sin commitear del usuario en `apps/catalog/views.py`**
- [x] T013 [US3] `@requires` en `apps/questionnaires/views.py` (`questionnaires.manage`)
- [x] T014 [US3] `@requires` en `apps/evaluations/views.py` (`ownership.*`, `value_delivery.*`, `arena_impact.edit`, `period.closed.correct` inline)
- [x] T015 [US3] `@requires` en `apps/learning/views.py` (`learn.*`). En `learning_flow`, `eligible_approvers` e `is_course_approver` pasan a usar `learn.approve.lead/direction/talento` con alcance (Lead directo = A, Leads del área = Ár, se conserva la preferencia por el Director del área) y `all_in_review` usa `learn.all_requests.view`
- [x] T016 [US3] Menú (`context_processors.navigation`) y campana (`notifications`) derivados de `has()`. Se quita el enlace roto `catalog:weight_admin`
- [x] T017 [US3] Plantillas: los botones y secciones condicionados por rol pasan a `{% can %}` (project_admin, talent_person, `_responsables_widget`, user_admin, approvals, request_detail, tracking…)
- [x] T018 [US3] `apps/access/legacy.py`: reglas anteriores congeladas por clave, tomadas de `research-permisos-actuales.md`
- [x] T019 [US3] `apps/core/tests/test_access_parity.py`: perfil semilla × clave, legacy contra nuevo. Toda diferencia debe estar en `EXPECTED_CHANGES` (FR-011a)
- [x] T020 [US3] `manage.py access_report`: por usuario, permisos ganados y perdidos, más el uso histórico (Entregas de Valor capturadas por un Director que no era responsable)

## Phase 4: US1 — Matriz editable (P1)

- [x] T021 [US1] Servicios `set_grant`, `create/rename/duplicate/delete_profile` con bitácora y guardia FR-007 (nunca quedar sin `access.manage`)
- [x] T022 [US1] Vistas, URLs y formularios `/catalogo/perfiles/` (lista con conteo de usuarios) y `/catalogo/perfiles/<slug>/` (matriz por módulo, `<select>` por celda limitado a los alcances admitidos, guardado por módulo con htmx y toast). Protegidas por `access.manage`
- [x] T023 [P] [US1] Plantillas `templates/access/profiles_list.html` y `matrix.html`, más el ítem "Perfiles y permisos" en Catálogos

## Phase 5: US2 — Asignación de perfiles (P1)

- [x] T024 [US2] Columna y selector "Perfil" en `/cuenta/usuarios/` (respetando el fix de filtro: solo usuarios presentes en el POST) y en el alta de usuario (sugerido por rol y nivel). Con bitácora
- [x] T025 [US2] Usuario sin perfil: se aplica `colaborador` (falla cerrado). Cubierto en `test_access.py`

## Phase 6: US4 + US5 — Lead flexible y asignables (P2)

- [x] T026 [US4] Alcance "Su área" en Mesa de Talento, Escenario Actual, Seguimiento de Arena Learn y exportes (`scope_qs` por área)
- [x] T027 [US5] Los selectores usan `assignable_users`: evaluadores de Ownership, roles de proyecto, responsables de retroalimentación, Lead directo, Director de área y reasignación de Arena Learn
- [x] T028 [US5] Resumen "fuera de perfil" (FR-021) en la lista de perfiles: asignaciones vigentes que ya no cumplen el asignable

## Phase 7: US7 — Acceso efectivo (P3)

- [x] T029 [US7] `/catalogo/perfiles/acceso/<user_pk>/`: perfil, permisos con alcance por módulo y relaciones vigentes. Enlace desde Usuarios

## Phase 8: Polish y entrega

- [x] T030 [P] `apps/core/tests/test_access.py` compacto: matriz (cambiar celda → menú y 403), auto-bloqueo, asignación, Lead flexible por área, asignables, superusuario y caché por request
- [x] T031 Ajustar las pruebas existentes que asumían roles fijos (fixtures con perfil semilla)
- [x] T032 Ayuda (pestaña Talento: Perfiles y permisos) y `docs/CONTEXTO_Sistema.md`
- [x] T033 Correr `access_report` contra producción (solo lectura) y entregarlo al usuario **antes** de activar
- [ ] T034 Regresión dirigida y pruebas nuevas, compilar CSS, migraciones a Neon y push (con aprobación del usuario)

## Dependencies

- Gate: el usuario aprueba `seed-matrix.md` → Fase 1 → Fase 2 → Fase 3. La prueba de cobertura queda verde al terminar T011–T015.
- Las Fases 4 y 5 dependen de la 2 y pueden ir en paralelo con la 3.
- La Fase 6 depende de la 3. T033 precede a T034.

## Notes

- **Implementación (2026-10-07)**: rama `005-matriz-permisos-perfiles`. Cobertura 100% de rutas; regresión completa en verde tras ajustar pruebas que codificaban el comportamiento anterior (FR-011a).
- **Desviaciones**:
  - Sin perfil explícito, se aplica el **sugerido por rol/nivel** (no "Colaborador" a secas) para no degradar altas por CSV/comandos ni las pruebas existentes. Nunca da más que el rol.
  - La matriz muestra una fila por permiso con un selector de alcance (los permisos ya están separados por acción), agrupada por módulo y plegable.
  - `dashboard.home.view` cubre también ver **mis propios** resultados históricos (`user_results` sobre uno mismo).
  - Las vistas basadas en clase se envuelven en `views.home = requires(...)(HomeView.as_view())`.
- T034 (migrar Neon + push) **espera aprobación del usuario**; el reporte previo está en `reporte-activacion.md`.

- Deuda que esta spec cierra: dos definiciones de admin, accesos solo por URL, `weight_admin` roto y Lead acoplado al nivel.
- Fuera de alcance: el agente auditor (spec siguiente, que usa `test_access_coverage` como base) y la pantalla de Ponderaciones (registrada como pendiente).
