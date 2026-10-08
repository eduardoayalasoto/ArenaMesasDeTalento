# Matriz de permisos ACTUAL (as-is) — insumo de la spec 005

Levantado contra el código el 2026-10-07 (rama `004-arena-learn-cursos`, commit `ece1a87`).
Todas las vistas llevan `@login_required` (o `LoginRequiredMixin`). Los middlewares (`apps/core/middleware.py`) **no**
filtran por rol: solo fuerzan el cambio de contraseña y la foto obligatoria.

**Convenciones**
- **Colab** = rol COLABORADOR. **Lead** = nivel `LEAD` (derivado, `User.is_lead`). **Dir** = rol DIRECTOR. **Tal** = rol TALENTO. **SU** = superusuario.
- `is_admin` = Tal o SU. Ojo: el helper `permissions._is_admin` (`apps/core/services/permissions.py:12`) es **distinto**: incluye Tal, SU **y Dir**.
- Alcance: **propio**, **área** (Lead ve su área), **relación** (asignado por un vínculo: evaluador, responsable…), **todos**.

## 1. Dashboards (`apps/dashboards/views.py`)

| Ruta (name) | Pantalla / acción | Acción | Quién puede HOY | Alcance | Regla relacional | Dónde |
|---|---|---|---|---|---|---|
| dashboards:home | Mi tablero (mi informe de resultados) | ver | Todos | propio | — | views.py:129 (`HomeView`) |
| dashboards:help | Centro de ayuda | ver | Todos | — | — | views.py:195 |
| dashboards:my_area | Mi área (personas, avance y calificación) | ver | Todos (menú solo Lead/Dir/Tal/SU) | Colab: solo él · Lead: su área · Dir/Tal/SU: todos | `visible_users` | views.py:146, permissions.py:19 |
| dashboards:user_results | Resultados de una persona (drill-down) | ver | Todos | igual que Mi área | `visible_users` (404 si fuera de alcance) | views.py:180 |
| dashboards:talent_table | Mesa de Talento (tabla) | ver | Dir, Tal, SU | todos | — | views.py:322 |
| dashboards:talent_person | Mesa de Talento · ficha de persona | ver (Dir) / editar (Tal, SU) | Dir, Tal, SU | todos | edición vía plantilla `is_admin` | views.py:672; talent_person.html:41,51 |
| dashboards:talent_note_autosave | Guardar notas de Mesa (fortalezas, comentarios…) | editar | Tal, SU | todos | — | views.py:759 |
| dashboards:talent_scenario_toggle | Marcar escenario S+1/S+2 | editar | Tal, SU | todos | — | views.py:796 |
| dashboards:talent_mesa_project_toggle | Marcar proyecto "revisado" en Mesa | editar | Tal, SU | todos | — | views.py:842 |
| dashboards:talent_responsable_add | Asignar responsable de retroalimentación | crear/asignar | Tal, SU | todos | — | views.py:878 |
| dashboards:talent_responsable_remove | Quitar responsable de retroalimentación | borrar/asignar | Tal, SU | todos | — | views.py:909 |
| dashboards:current_scenario_board | Escenario Actual (tablero drag & drop) | ver | Dir, Tal, SU | todos | — | views.py:452 |
| dashboards:current_scenario_move | Mover persona de Escenario Actual | **editar** | **Dir**, Tal, SU | todos | — | views.py:509 |
| dashboards:feedback_session_list | Retroalimentación (doy / asisto / recibo / todas) | ver | Todos (menú condicionado) | relación; Tal/SU: todos (sección "Todas") | responsable asignado o receptor | views.py:954,1009 |
| dashboards:feedback_session_detail | Detalle de retroalimentación | ver / editar | ver: responsables, receptor, Tal, SU · editar: responsables, Tal, SU | relación | `can_view_feedback_session` / `can_edit_feedback_session`; periodo Cerrado → solo Tal/SU con motivo | views.py:1049,1059; permissions.py:79,84 |
| dashboards:period_progress | Avance del periodo | ver | Tal, SU | todos | — | views.py:655 |
| dashboards:export_scores_xlsx | Exportar calificaciones (.xlsx) | exportar | **Todos** (sin verificación de rol) | según `visible_users` | — | views.py:1163 |

## 2. Cuenta y usuarios (`apps/accounts/views.py`)

| Ruta | Pantalla / acción | Acción | Quién puede HOY | Alcance | Regla | Dónde |
|---|---|---|---|---|---|---|
| accounts:profile | Mi perfil (foto, nombre, contraseña, Arena Learn) | ver/editar | Todos | propio | — | views.py:82 |
| accounts:password_change | Cambiar contraseña | editar | Todos | propio | — | views.py:61 |
| accounts:user_photo | Foto de una persona | ver | **Todos** (sin filtro) | todos | — | views.py:42 |
| accounts:user_admin | Usuarios (área, nivel, rol, Lead directo) | ver/editar | Tal, SU | todos (excluye SU) | — | views.py:119 |
| accounts:user_create | Alta de usuario | crear | Tal, SU | — | — | views.py:21 |
| accounts:user_reset_password | Resetear contraseña | otra (editar) | Tal, SU | todos (no SU) | — | views.py:182 |
| accounts:user_delete | Eliminar/desactivar usuario | borrar | Tal, SU | todos (no SU) | soft delete si tiene historial | views.py:205 |

## 3. Catálogos (`apps/catalog/views.py`, `views_areas.py`, `apps/questionnaires/views.py`)

| Ruta | Pantalla / acción | Acción | Quién puede HOY | Alcance | Regla | Dónde |
|---|---|---|---|---|---|---|
| catalog:project_admin | Proyectos (lista) | ver | **Lead, Dir**, Tal, SU | todos | `can_edit_project` | catalog/views.py:39; permissions.py:95 |
| catalog:project_create | Nuevo proyecto | crear | Lead, Dir, Tal, SU | — | — | catalog/views.py:66 |
| catalog:project_edit | Editar proyecto y su equipo (owner, responsable, validador, miembros) | editar / asignar | Lead, Dir, Tal, SU | **todos los proyectos** (no solo los suyos) | — | catalog/views.py:66 |
| catalog:project_delete | Eliminar / cerrar proyecto | borrar | Tal, SU | todos | botón oculto en plantilla para no-admin | catalog/views.py:251; project_admin.html:50 |
| catalog:project_reactivate | Reabrir proyecto cerrado | editar | Tal, SU | todos | — | catalog/views.py:301 |
| catalog:period_admin | Periodos (abrir/cerrar) | ver/aprobar | Tal, SU | todos | — | catalog/views.py:184 |
| catalog:period_create / period_edit / period_delete | Alta, edición y borrado de periodo | crear/editar/borrar | Tal, SU | todos | — | catalog/views.py:116,137,160 |
| catalog:area_admin | Áreas · Director por área | ver/editar/asignar | Tal, SU | todos | solo usuarios rol Director como valor | views_areas.py:14 |
| catalog:scenario_admin / scenario_create / scenario_edit | Escenarios (activar, borrar, alta, edición) | ver/crear/editar/borrar | Tal, SU | todos | — | catalog/views.py:343,377,402 |
| questionnaires:admin_list | Cuestionarios (lista) | ver | Tal, SU | todos | — | questionnaires/views.py:20 |
| questionnaires:template_edit | Editar/versionar/publicar cuestionario | editar/aprobar(publicar) | Tal, SU | todos | — | questionnaires/views.py:39 |
| *(catalog:weight_admin)* | Ponderaciones | — | **Ruta inexistente** | — | — | context_processors.py:140 |

## 4. Evaluaciones (`apps/evaluations/views.py`)

| Ruta | Pantalla / acción | Acción | Quién puede HOY | Alcance | Regla | Dónde |
|---|---|---|---|---|---|---|
| evaluations:ownership_list | Mis evaluaciones de Ownership | ver | Todos (menú oculto a Dir/Tal salvo SU) | propio; Tal/SU pueden elegir periodo | Lead: tarjeta transversal | views.py:53,57,74 |
| evaluations:ownership_start | Iniciar evaluación por proyecto (elegir evaluadores) | crear/asignar | Todos con membresía al proyecto | propio | requiere `ProjectMembership` | views.py:108,118 |
| evaluations:ownership_lead_start | Iniciar evaluación transversal de Lead | crear/asignar | Solo Lead | propio | — | views.py:168 |
| evaluations:ownership_view / ownership_edit | Ver / editar evaluación de Ownership | ver/editar | evaluado, evaluadores, Lead de su área, Dir, Tal, SU (ver) · edición: evaluado y evaluadores mientras esté abierta | relación / área | `can_view_evaluation`; `_can_edit_answers`; `_can_complement`; periodo Cerrado → solo Tal/SU | views.py:243-262; permissions.py:28 |
| evaluations:ownership_set_evaluator / add_evaluator / remove_evaluator | Gestionar evaluadores | asignar | Solo el evaluado, antes de cerrar | propio | — | views.py:341,364,389 |
| evaluations:ownership_autosave | Guardar respuestas | editar | evaluado, evaluadores, Tal, SU | relación | `_can_edit_answers` | views.py:403 |
| evaluations:ownership_save | Complementar y cerrar (fortalezas/oportunidades) | aprobar/editar | evaluadores, Tal, SU (**no** el evaluado) | relación | `_can_complement` → `can_validate_ownership` | views.py:434; permissions.py:55 |
| evaluations:ownership_reopen | Reabrir evaluación cerrada | editar | Tal, SU | todos | — | views.py:481 |
| evaluations:ownership_reset | Reiniciar evaluación | borrar | Tal, SU | todos | no en periodo Cerrado | views.py:540 |
| evaluations:ownership_reset_user | Reiniciar Ownership de un usuario (desde Usuarios) | borrar | Tal, SU | todos | — | views.py:512 |
| evaluations:ownership_validation | Validación de Ownership (mi cola de evaluador) | ver | Todos (menú solo si es evaluador) | relación; Tal/SU en periodo histórico: todos | `OwnershipEvaluator` | views.py:570,581 |
| evaluations:value_delivery_list | Entrega de Valor (mis proyectos como responsable) | ver | Todos (menú: responsable o SU) | relación; Tal/SU histórico: todos | `projects_led_by` (responsable) | views.py:621,630 |
| evaluations:value_delivery_capture | Capturar Entrega de Valor | crear/editar | responsable del proyecto, **Dir**, Tal, SU | relación | `can_capture_value_delivery` usa `_is_admin` (incluye Dir) | views.py:657; permissions.py:60 |
| evaluations:value_delivery_review | Validar Entrega de Valor (validar / regresar / comentar) | aprobar | validador del proyecto, Tal, SU | relación | `can_validate_value_delivery` (Dir solo si es validador) | views.py:737,749,776; permissions.py:65,74 |
| evaluations:arena_impact / arena_impact_autosave | Impacto Arena (captura) | ver/editar | Tal, SU | todos | — | views.py:792,844 |

## 5. Arena Learn (`apps/learning/views.py`, servicio `apps/core/services/learning_flow.py`)

| Ruta | Pantalla / acción | Acción | Quién puede HOY | Alcance | Regla | Dónde |
|---|---|---|---|---|---|---|
| learning:my_courses | Mis cursos | ver | Todos | propio | — | views.py `my_courses` |
| learning:request_start / request_create | Solicitar curso (selector / formulario) | crear | Todos | propio | FR-004 (cerrar antes de pedir otro), duplicado por liga | views.py; learning_flow `submit_request` |
| learning:request_edit | Editar solicitud | editar | dueño (BORRADOR / REQUIERE_AJUSTES) | propio | — | views.py `request_edit` |
| learning:request_detail | Detalle privado (costo, justificación, bitácora) | ver | dueño, aprobadores (actuaron o elegibles), Dir, Tal, SU | relación | `can_view_course_private` (usa `_is_admin` → incluye Dir) | permissions.py ~116 |
| learning:request_decide | Aprobar / regresar / rechazar | aprobar | aprobador elegible de la etapa | relación | `eligible_approvers`: Lead directo → Leads del área; Director del área → cualquier Dir; Tal/SU; reasignación explícita | learning_flow.py:72 |
| learning:request_cancel | Cancelar solicitud | borrar | dueño (antes de autorizar); Tal/SU (también autorizada, con motivo) | propio / todos | — | learning_flow `cancel` |
| learning:request_reassign | Reasignar aprobador | asignar | Tal, SU | todos | — | views.py `request_reassign` |
| learning:request_payment / request_receipt | Registrar pago / subir comprobante | editar/crear | dueño, Tal, SU | propio / todos | — | learning_flow `update_payment`, `add_evidence` |
| learning:request_complete / request_not_completed / review_edit | Cerrar curso / no concluido / editar reseña | editar | dueño | propio | — | views.py |
| learning:evidence_file | Ver archivo de evidencia | ver | certificado: todos si el curso es público · comprobante: dueño, Tal, SU | todos / propio | — | views.py `evidence_file` |
| learning:evidence_validate | Validar / regresar evidencia | aprobar | Tal, SU | todos | — | learning_flow `validate_evidence` |
| learning:evidence_replace | Reemplazar evidencia regresada | editar | dueño | propio | — | learning_flow `replace_evidence` |
| learning:direct_create | Registrar curso ya tomado | crear | Todos | propio | — | learning_flow `create_direct` |
| learning:historic_create | Carga histórica | crear | Tal, SU | todos | — | views.py |
| learning:approvals_inbox | Aprobar cursos (bandeja) | ver/aprobar | Todos (menú: Lead, Lead directo de alguien, Dir, Tal, SU) | relación; Tal/SU: además "todas" | `approvals_for`, `all_in_review_for_talento` | learning_flow.py:1010,1017 |
| learning:catalog_list / catalog_detail | Catálogo sugerido | ver | Todos | todos | archivados solo Tal/SU | views.py |
| learning:catalog_create / catalog_edit / catalog_archive / catalog_promote | Administrar catálogo | crear/editar/borrar | Tal, SU | todos | `can_manage_learning` | views.py |
| learning:people_list / person_profile / course_public | Personas y perfil público Arena Learn | ver | Todos | todos (excepción RN-14) | solo campos públicos | permissions `can_view_learning_profile` |
| learning:tracking / tracking_export | Seguimiento y exporte | ver/exportar | Dir, Tal, SU | todos | `can_view_learning_tracking` | views.py |
| learning:settings_edit | Instrucciones fiscales | editar | Tal, SU | todos | — | views.py |

## 6. Menú lateral (`apps/core/context_processors.py::navigation`)

| Ítem | Condición de visibilidad | Línea |
|---|---|---|
| Mi tablero | todos | 54 |
| Mis evaluaciones | `not is_talento and not is_director or is_superuser` | 58 |
| Mi área | Lead, Tal/SU, Dir | 74 |
| Validación de Ownership | tiene registros `OwnershipEvaluator` | 79 |
| Retroalimentación | Tal/SU o responsable o receptor de una nota | 89 |
| Entrega de Valor | `leads_projects` (responsable de proyecto activo) o SU | 93 |
| Arena Learn | todos | 98 |
| Aprobar cursos (+contador) | `is_course_approver`: Lead, Lead directo de alguien, Dir, Tal/SU | 110 |
| Mesa de Talento, Escenario Actual | Tal/SU, Dir | 116-117 |
| Validar Entrega de Valor | Tal/SU o `validates_projects` | 121 |
| Proyectos | `can_edit_project` (Lead, Dir, Tal, SU) | 126 |
| Impacto Arena, Avance del periodo | Tal/SU | 130-131 |
| Catálogos → Cuestionarios, Usuarios, Escenarios, Periodos, Áreas | Tal/SU | 135-139 |
| Catálogos → **Ponderaciones** | Tal/SU, pero **`catalog:weight_admin` no existe** → `_safe_url` devuelve None y el ítem nunca se pinta | 140 |

## 7. Inconsistencias detectadas

1. **`catalog:weight_admin` inexistente**: el menú lo referencia; no hay pantalla para editar `PillarWeight` (solo admin de Django).
2. **Dos definiciones de "admin"**: `User.is_admin` (Tal+SU) vs `permissions._is_admin` (Tal+SU+**Dir**). Por eso Dir puede **capturar cualquier Entrega de Valor** (`can_capture_value_delivery`, permissions.py:60), **editar cualquier proyecto** y ve **todos** en `visible_users`, aunque el menú de Entrega de Valor no se le muestra.
3. **Directores no son de solo lectura**: editan Escenario Actual (`current_scenario_move`), proyectos (`project_edit`) y Entrega de Valor; en cambio NO pueden editar notas de Mesa (solo Tal/SU).
4. **Leads editan todos los proyectos**, no solo los suyos (`can_edit_project` no filtra por relación).
5. **Vistas sin verificación de rol** (dependen del filtrado de datos): `my_area`, `user_results`, `export_scores_xlsx` (cualquier Colab puede exportar su propia fila), `user_photo` (cualquier foto), `ownership_list`, `value_delivery_list`, `ownership_validation`, `feedback_session_list` (accesibles por URL aunque el menú no las muestre; devuelven listas vacías o propias).
6. **Verificaciones solo en plantilla**: botón eliminar/cerrar proyecto (`project_admin.html:50`, la vista sí lo valida); edición en ficha de Mesa (`talent_person.html:41,51`, endpoints sí validan); widget de responsables (`_responsables_widget.html`).
7. **Menú vs. vista**: "Mis evaluaciones" se oculta a Dir/Tal, pero la vista no lo impide; "Mi área" se oculta a Colab, pero la vista le muestra solo su fila.
8. **Lead depende del nivel de seniority** (`level.code == "LEAD"`): el permiso y la escala de evaluación están acoplados; no se puede dar funciones de Lead sin cambiar su nivel (que cambia ponderaciones y cuestionario).

## 8. Roles asignables / etiquetables hoy

| Rol | Quién lo asigna | A quién se puede asignar hoy | Dónde |
|---|---|---|---|
| Evaluador de Ownership (primario/secundario) | el evaluado | cualquier usuario activo excepto él mismo | evaluations/views.py:341,364 |
| Owner / Responsable / Validador de proyecto | Lead, Dir, Tal, SU (en Proyectos) | cualquier usuario activo | catalog/forms.py:68-75 |
| Miembro de proyecto | Lead, Dir, Tal, SU | cualquier usuario activo | catalog/views.py:76 |
| Responsable de retroalimentación (primario/secundario) | Tal, SU | cualquier usuario activo no SU | dashboards/views.py:878,1148 |
| Lead directo (Arena Learn) | Tal, SU (Usuarios) | cualquier usuario activo excepto él mismo | accounts/views.py `user_admin` |
| Director de área (Arena Learn) | Tal, SU (Áreas) | solo usuarios con rol DIRECTOR | views_areas.py |
| Aprobador reasignado de Arena Learn | Tal, SU | cualquier usuario activo excepto el solicitante | learning_flow `reassign` |
| Escenario Actual de una persona | Dir, Tal, SU | — (etiqueta sobre la persona) | dashboards/views.py:509 |

## 9. Funciones exclusivas de Dir/Tal candidatas a delegar en Lead

- **Mesa de Talento** (ver tabla y ficha) y **Escenario Actual** (ver y mover): hoy Dir/Tal/SU.
- **Aprobar cursos en etapa Dirección** de Arena Learn: hoy solo Dir (o reasignación de Talento).
- **Seguimiento de Arena Learn** y exporte: hoy Dir/Tal/SU.
- **Ver detalle privado de cursos** de su área: hoy Dir/Tal/SU o aprobador.
- **Avance del periodo** (acotado a su área): hoy Tal/SU.
- **Validar Entrega de Valor**: hoy por relación (validador) o Tal/SU; un Lead ya puede si se le asigna como validador.
- **Ver todas las evaluaciones**: hoy Lead ya ve las de su área (`visible_users`, `can_view_evaluation`); Dir ve todas.
