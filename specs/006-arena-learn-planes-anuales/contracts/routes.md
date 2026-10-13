# Contrato de rutas y servicios: Arena Learn 006

Todas las vistas son server-rendered y llevan `@login_required` + `@requires("<clave>")` (R9). Viven bajo `/arena-learn/` (`app_name="learning"`). Las escrituras pasan por `apps/core/services/learning_tags.py` y `apps/core/services/learning_plans.py`. Todo POST usa un Django Form. Las respuestas htmx son parciales con toast.

## Rutas nuevas

### Etiquetas (US1)

| Método | Ruta | Nombre | Clave | Respuesta |
|---|---|---|---|---|
| GET | `/arena-learn/etiquetas/sugerir/?q=` | `tag_suggest` | `learn.public.view` | Parcial `<li>` con hasta 8 etiquetas activas que contienen `q` (por `key`) |
| GET | `/arena-learn/etiquetas/` | `tag_list` | `learn.tags.manage` | Lista: nombre, activa, nº de cursos, nº de solicitudes |
| POST | `/arena-learn/etiquetas/<pk>/editar/` | `tag_edit` | `learn.tags.manage` | htmx: fila; renombra (error si choca → sugiere fusionar) |
| POST | `/arena-learn/etiquetas/<pk>/fusionar/` | `tag_merge` | `learn.tags.manage` | htmx: lista; `target=<pk>` (modal de confirmación) |
| POST | `/arena-learn/etiquetas/<pk>/estado/` | `tag_toggle` | `learn.tags.manage` | htmx: fila; activa/desactiva |

### Planes por área (US2)

| Método | Ruta | Nombre | Clave | Respuesta |
|---|---|---|---|---|
| GET | `/arena-learn/planes/` | `plan_list` | `learn.plans.view` | Redirige al plan publicado vigente del área del usuario; si no tiene área o plan, muestra la lista de planes (área × año) |
| GET | `/arena-learn/planes/<pk>/` (`?tipo=&nivel=&etiqueta=&etiqueta=`) | `plan_detail` | `learn.plans.view` (BORRADOR: `learn.plans.manage`) | Plan agrupado por tipo de aprendizaje; con `HX-Request`, solo el parcial de cursos filtrados |
| GET/POST | `/arena-learn/planes/nuevo/`, `/planes/<pk>/editar/` | `plan_create`, `plan_edit` | `learn.plans.manage` | Form de cabecera del plan (incluye textos por tipo) |
| POST | `/arena-learn/planes/<pk>/estado/` | `plan_status` | `learn.plans.manage` | `action=publish\|unpublish\|archive\|reopen`; redirect + mensaje |
| POST | `/arena-learn/planes/<pk>/cursos/` y `/cursos/<iid>/` (`action=save\|delete\|up\|down`) | `plan_item_save`, `plan_item_edit` | `learn.plans.manage` | htmx: grupo del tipo; campos curso, niveles y nota |

### Mi plan (US3)

| Método | Ruta | Nombre | Clave | Respuesta |
|---|---|---|---|---|
| GET | `/arena-learn/mi-plan/` (`?anio=`) | `my_plan` | `learn.myplan` | Cursos del año con estado derivado y resumen (pendientes, en curso, completados, descartados) |
| POST | `/arena-learn/mi-plan/agregar/` | `my_plan_add` | `learn.myplan` | `plan_course=<id>` o `course=<id>`; htmx: botón cambia a "En mi plan" + toast |
| POST | `/arena-learn/mi-plan/<iid>/iniciar/` | `my_plan_start` | `learn.myplan` | `mode=request` → redirect a `request_create?catalogo=<id>`; `mode=free` → marca `started_at`, htmx fila |
| POST | `/arena-learn/mi-plan/<iid>/completar/` | `my_plan_complete` | `learn.myplan` | redirect a `direct_create?catalogo=<id>` (si no hay solicitud) o a `request_complete` de la solicitud |
| POST | `/arena-learn/mi-plan/<iid>/descartar/` | `my_plan_discard` | `learn.myplan` | `action=discard\|restore`; htmx fila |
| GET | `/arena-learn/personas/<pk>/plan/` (`?anio=`) | `person_plan` | `learn.myplan.others` (alcance A/AR/T) | Mi plan de otra persona, solo lectura. 403 fuera de alcance |

### Seguimiento de planes (US5)

| Método | Ruta | Nombre | Clave | Respuesta |
|---|---|---|---|---|
| GET | `/arena-learn/seguimiento/planes/` (`?area=&anio=&persona=`) | `plan_tracking` | `learn.plans.tracking` | Totales por estado y tabla por persona (avance = completados / no descartados) |
| GET | `/arena-learn/seguimiento/planes/exportar/` | `plan_tracking_export` | `learn.plans.tracking` | `.xlsx` persona × curso × estado |

### Cursos ya tomados (US6, bloqueada hasta tener el export de SharePoint)

Sin ruta: comando `import_taken_courses <archivo>`.

## Rutas existentes que cambian

| Ruta | Cambio |
|---|---|
| `catalog_list` | Se quitan los filtros "nivel" y "pilar"; se agregan "etiqueta" (multi) y "enfoque"; "área" filtra por planes publicados. Cada tarjeta muestra tipo, enfoque y los planes en que aparece el curso |
| `catalog_create` / `catalog_edit` | Se eliminan los campos `levels`, `pillar` y `areas`; nuevo `focus`; `kind` con los tipos de aprendizaje; `tags` usa `_tag_input`; duración decimal. Aviso si la liga ya existe en otro curso |
| `catalog_detail` | Etiquetas como badges. Bloque "En los planes" (área, año, niveles) |
| `request_create` / `request_edit` / `direct_create` / `historic_create` | `tags` usa `_tag_input`; con `?catalogo=` se precargan las etiquetas del curso (FR-004) |
| `request_start` | La búsqueda por etiqueta usa `tags__name__icontains` en lugar del CharField |
| `catalog_promote` | Copia las etiquetas M2M y fija `focus` Horizontal por defecto; ya no copia niveles, pilar ni áreas |

## Servicios

`apps/core/services/learning_tags.py`
- `normalize_tag_key(name) -> str`
- `resolve(names: list[str], actor) -> list[Tag]`: busca por `key`; si no existe, crea; si existe inactiva, `ValidationError`
- `suggest(q, limit=8) -> QuerySet[Tag]`
- `rename(tag, name, actor)`, `merge(src, dst, actor)`, `set_active(tag, active, actor)`: requieren `learn.tags.manage`
- `filter_by_tags(qs, tag_ids, path="tags")`: AND de etiquetas (FR-007)

`apps/core/services/learning_plans.py`
- `current_plan_for(user, year=None) -> TrainingPlan | None`
- `plan_groups(plan, filters) -> list[(kind, label, note, items)]`: prefetch, agrupación por tipo y filtros por tipo, nivel y etiquetas
- `save_plan`, `set_status(plan, action, actor)` (FR-014: no publicar vacío), `save_item`, `move_item`, `delete_item`
- `add_to_my_plan(user, course=None, plan_course=None) -> PersonalPlanItem`: rechaza cursos inactivos y planes archivados
- `start_item(item, mode)`, `discard_item(item, discard: bool)`
- `item_states(items, user) -> dict[item_id, ItemState]` (R8)
- `can_view_personal_plan(viewer, owner) -> bool` (vía `access.scope`)
- `tracking_rows(viewer, filters) -> dict`, `tracking_export_rows(viewer, filters) -> list[list]`

`apps/core/services/learning_import.py`
- `import_catalog_and_plans(xlsx_path, plans_json_path, year=2026, dry_run=False) -> ImportSummary` (FR-023 a FR-031)
- `reset_learning_data(before: date, confirm: bool) -> dict[str, int]` (FR-039/040)

## Comandos

| Comando | Uso |
|---|---|
| `reset_learning_data --before 2026-10-13 [--confirm]` | Sin `--confirm` solo muestra conteos |
| `import_learning_plans [--plans apps/learning/data/planes_2026.json] [--year] [--dry-run]` | Imprime `ImportSummary` |
| `import_taken_courses <archivo>` | US6, cuando exista el formato |
