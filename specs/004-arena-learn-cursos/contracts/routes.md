# Contrato de rutas y servicios: Arena Learn (004)

Todas las vistas son server-rendered y llevan `@login_required`. Las rutas viven bajo `/arena-learn/` (`app_name="learning"`). Toda escritura pasa por `apps/core/services/learning_flow.py`.

## Rutas

| Método | Ruta | Nombre | Quién | Respuesta |
|---|---|---|---|---|
| GET | `/arena-learn/` | `my_courses` | todos | Mis solicitudes y cursos, agrupados por estado |
| GET/POST | `/arena-learn/solicitar/` (`?catalogo=<id>`) | `request_create` | todos | Form; POST guarda en borrador o envía (`action=draft\|submit`) |
| GET/POST | `/arena-learn/solicitudes/<pk>/editar/` | `request_edit` | dueño (BORRADOR/REQUIERE_AJUSTES) | Form |
| GET | `/arena-learn/solicitudes/<pk>/` | `request_detail` | dueño, aprobadores, Talento, Director (vista privada completa) | Detalle con bitácora |
| POST | `/arena-learn/solicitudes/<pk>/decision/` | `request_decide` | aprobador elegible de la etapa actual | htmx: fila parcial y toast (`action=approve\|return\|reject`, `comment`) |
| POST | `/arena-learn/solicitudes/<pk>/cancelar/` | `request_cancel` | dueño (antes de AUTORIZADA) / Talento (AUTORIZADA) | Redirect + mensaje |
| POST | `/arena-learn/solicitudes/<pk>/reasignar/` | `request_reassign` | Talento | Redirect + mensaje |
| POST | `/arena-learn/solicitudes/<pk>/pago/` | `request_payment` | dueño, Talento | htmx: bloque de pago parcial |
| GET/POST | `/arena-learn/solicitudes/<pk>/cerrar/` | `request_complete` | dueño (AUTORIZADA, o COMPLETADA con evidencia regresada) | Form multipart: evidencia + reseña |
| POST | `/arena-learn/solicitudes/<pk>/no-concluido/` | `request_not_completed` | dueño | Redirect |
| POST | `/arena-learn/evidencias/<pk>/validar/` | `evidence_validate` | Talento | htmx (`action=validate\|return`) |
| GET | `/arena-learn/evidencias/<pk>/` | `evidence_file` | público si es CERTIFICADO de un curso visible; privado si es COMPROBANTE_FISCAL | Bytes (`Content-Disposition: inline`) |
| GET/POST | `/arena-learn/registrar/` | `direct_create` | todos | Registro directo: curso + evidencia + reseña |
| GET | `/arena-learn/por-aprobar/` | `approvals_inbox` | quien tenga solicitudes en su etapa | Bandeja |
| GET | `/arena-learn/catalogo/` | `catalog_list` | todos | Filtros `area, nivel, tipo, pilar, q` |
| GET | `/arena-learn/catalogo/<pk>/` | `catalog_detail` | todos | Curso, rating y reseñas públicas |
| GET/POST | `/arena-learn/catalogo/nuevo/`, `/<pk>/editar/` | `catalog_create`, `catalog_edit` | Talento | Form |
| POST | `/arena-learn/catalogo/<pk>/archivar/` | `catalog_archive` | Talento | htmx |
| POST | `/arena-learn/solicitudes/<pk>/promover/` | `catalog_promote` | Talento | Redirect al curso del catálogo |
| GET | `/arena-learn/personas/` | `people_list` | todos | Directorio con buscador (nombre, área) |
| GET | `/arena-learn/personas/<pk>/` | `person_profile` | todos | Ficha pública + Arena Learn (solo campos públicos) |
| GET | `/arena-learn/cursos/<pk>/` | `course_public` | todos (si el estado es público) | Detalle público: reseña + certificado |
| GET | `/arena-learn/seguimiento/` | `tracking` | Talento, Director | Tablero (filtros `area, persona, anio, estado`) |
| GET | `/arena-learn/seguimiento/exportar/` | `tracking_export` | Talento, Director | `.xlsx` |
| GET/POST | `/arena-learn/historico/nuevo/` | `historic_create` | Talento | Carga de curso histórico para una persona |
| GET/POST | `/arena-learn/configuracion/` | `settings_edit` | Talento | Instrucciones fiscales |

Además se tocan rutas existentes:
- `/cuenta/perfil/`: se agrega la tab "Arena Learn", que enlaza a `person_profile` propio.
- `/cuenta/usuarios/`: se agrega la columna "Lead directo".
- Catálogo de áreas o admin de áreas: se agrega el campo "Director".

## Servicios (`apps/core/services/learning_flow.py`)

| Función | Efecto | Errores (`ValidationError` / `PermissionDenied`) |
|---|---|---|
| `create_request(user, data, catalog_course=None, submit=False)` | Crea en BORRADOR; si `submit`, llama a `submit_request` | datos inválidos |
| `submit_request(req, actor)` | BORRADOR o REQUIERE_AJUSTES → EN_REVISION en la primera etapa aplicable (o en `returned_from_stage`); registra ENVIAR/REENVIAR y OMITIR | `assert_can_submit` (FR-004), no es dueño |
| `eligible_approvers(req, stage) -> QuerySet[User]` | Pura | — |
| `decide(req, actor, action, comment)` | approve: avanza o AUTORIZADA; return: REQUIERE_AJUSTES; reject: RECHAZADA | actor no elegible, comentario faltante, estado inválido |
| `cancel(req, actor, comment)` | → CANCELADA | estado o rol inválido |
| `reassign(req, actor, new_approver, comment)` | ApprovalStep REASIGNAR | actor sin `is_admin`, aprobador inválido |
| `update_payment(req, actor, mode, status, final_cost, receipt_type)` | actualiza los campos de pago | estado inválido |
| `add_evidence(req, actor, uploaded_file, kind)` | valida y comprime, crea CourseEvidence | tipo o tamaño inválido |
| `complete(req, actor, review_data, files)` | → COMPLETADA (atómico: evidencia + reseña) | sin certificado, reseña incompleta |
| `mark_not_completed(req, actor, reason)` | → NO_CONCLUIDA | — |
| `validate_evidence(evidence, actor, approve, comment)` | VALIDADA, o REGRESADA; si todas están validadas, la solicitud pasa a VALIDADA | — |
| `create_direct(user, data, review_data, files, origin)` | REGISTRO_DIRECTO / HISTORICO → COMPLETADA | HISTORICO solo `is_admin` |
| `promote_to_catalog(req, actor)` | crea CatalogCourse con `promoted_from` y enlaza la solicitud | — |
| `pending_for(user) -> list[dict]` | elementos para la campana | — |
| `dashboard_rows(filters) / export_rows(filters)` | tablero y exporte | — |

## Permisos (`apps/core/services/permissions.py`)

`can_view_learning_profile`, `can_view_course_private`, `can_view_course_public`, `can_decide(viewer, req)`, `can_manage_learning(viewer)` (es `is_admin`), `can_view_tracking(viewer)` (es `is_admin` o `is_director`).
