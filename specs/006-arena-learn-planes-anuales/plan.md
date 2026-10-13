# Implementation Plan: Arena Learn — planes anuales, etiquetas e importación

**Branch**: `006-arena-learn-planes-anuales` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-arena-learn-planes-anuales/spec.md`

## Summary

Arena Learn pasa de "solicitudes curso por curso" a **planes anuales por área**:

- Talento publica un plan por área y año. El plan agrupa sus cursos por **tipo de aprendizaje** (dato del curso). Cada curso del plan lleva **sus propios niveles recomendados**, que salen del curso del catálogo.
- El colaborador arma **Mi plan**. Su avance se deriva de las solicitudes y registros que ya existen.
- Las etiquetas pasan de texto libre a un **catálogo gestionable** (M2M) con un campo autocompletable. "KO" es la única etiqueta que asigna la importación y **no existe agrupación KO**.
- Se borran los datos de prueba de Learn y se importan el Excel (≈249 cursos) y los 4 planes 2026, ya **publicados**. Los datos que solo vienen en los HTML se fijan en un JSON versionado.
- La carga de cursos ya tomados (US6) queda al final, bloqueada hasta tener el export de SharePoint.

## Technical Context

**Language/Version**: Python 3.14, Django 5.x (existente)

**Primary Dependencies**: Django, django-simple-history, openpyxl (ya en uso para exportes), htmx, Alpine (solo estado local), daisyUI 5 (tema `arena`) y Lucide. Sin dependencias nuevas.

**Storage**: Neon Postgres, esquema `"talento-app"`. 7 modelos nuevos o cambiados en `apps/learning` (ver [data-model.md](data-model.md)).

**Testing**: pytest + pytest-django contra Neon (`--reuse-db`, sin paralelo). Pruebas compactas por escenario. Usuarios de prueba con `password=None`.

**Target Platform**: Vercel (Python, Fluid Compute). Las migraciones se aplican a mano antes del push.

**Project Type**: aplicación web Django server-rendered (monolito)

**Performance Goals**: la vista de plan (~100 cursos) se resuelve en ≤ 6 consultas sin N+1. Mi plan en ≤ 3 consultas. La importación completa tarda < 60 s.

**Constraints**:
- La UI sigue `DESIGN_SYSTEM.md` (sin estilos inline ni emojis; Lucide).
- htmx devuelve parciales y nunca JSON. Diálogos con `_modal.html`.
- No tocar el esquema `"crm-app"`.
- Las reglas de autorización de 004 no cambian (FR-038).

**Scale/Scope**: ~63 usuarios, 4 áreas, ~260 cursos, 4 planes por año y ~100 cursos por plan.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No hay constitución ratificada (`.specify/memory/constitution.md` es plantilla). Rigen `CLAUDE.md` y `DESIGN_SYSTEM.md`:

| Regla | Cumplimiento |
|---|---|
| Lógica en `apps/core/services/<dominio>.py` | `learning_tags.py`, `learning_plans.py` y `learning_import.py`; las views solo validan, llaman y renderizan |
| `@login_required` + `@requires("clave")` en cada view; clave en registry, seed y legacy; `test_access_coverage` en verde | 6 claves nuevas (R9) y `tag_suggest` en `learn.public.view` |
| Nada de decidir por rol (`is_lead`…) | La visibilidad de Mi plan usa `access.scope(viewer, "learn.myplan.others")` |
| Menú = datos en `navigation.py` | Ítems "Planes" y "Mi plan"; "Etiquetas" dentro de Catálogo (`also_active`) |
| Django Forms en todo POST; `transaction.atomic` con 2+ modelos | Forms por acción; fusión, importación, limpieza y estado de plan van en `atomic` |
| `select_related`/`prefetch_related` | Ver data-model § Índices |
| Pruebas con el cambio, contra Neon | 3 archivos de prueba nuevos y ajuste de `test_learning.py` |
| htmx + parciales; Alpine solo local; modal para diálogos | `_tag_input` (htmx sugiere y Alpine maneja las fichas); confirmar fusión y archivado con `_confirm.html` |

✅ Sin violaciones. La única tensión es de despliegue y se documenta abajo.

**Re-check post-diseño**: ✅ El diseño no agrega apps, dependencias ni patrones nuevos.

## Project Structure

### Documentation (this feature)

```text
specs/006-arena-learn-planes-anuales/
├── spec.md
├── plan.md              # este archivo
├── research.md          # R1–R11
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── routes.md        # rutas, claves y servicios
│   └── planes-json.md   # formato del archivo de datos de los planes
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
apps/learning/
├── models.py                    # Tag, TrainingPlan, PlanCourse, PersonalPlan, PersonalPlanItem; CourseKind = tipo de aprendizaje;
│                                # CatalogCourse/CourseRequest: tags M2M, sin levels, duration decimal, is_imported
├── migrations/0004_tags_planes.py        # esquema nuevo + quitar tags CharField/levels + duración decimal
├── forms.py                     # TagNamesField; PlanForm, PlanItemForm, MyPlanAddForm, TagRenameForm, TagMergeForm
├── views.py                     # (o views_plans.py / views_tags.py si views.py pasa de ~1000 líneas)
├── urls.py                      # rutas de contracts/routes.md
├── data/planes_2026.json        # datos curados de los HTML (R6)
└── management/commands/
    ├── reset_learning_data.py
    ├── import_learning_plans.py
    └── import_taken_courses.py  # US6 (al final)

apps/core/services/
├── learning_tags.py             # nuevo
├── learning_plans.py            # nuevo
├── learning_import.py           # nuevo
└── learning_flow.py             # normalize_url (R3), tags M2M en _apply_data/promote/requestable_courses/catalog_queryset

apps/access/registry.py, seed.py, legacy.py   # 6 claves nuevas + tag_suggest
apps/core/navigation.py                       # Planes, Mi plan

templates/components/_tag_input.html          # nuevo componente de formulario
templates/learning/
├── plan_list.html, plan_detail.html, _plan_courses.html, plan_form.html, _plan_items_admin.html
├── my_plan.html, _my_plan_row.html, person_plan.html
├── plan_tracking.html
├── tag_list.html, _tag_row.html, _tag_suggest.html
└── (ajustes) catalog_list/detail/form, request_form, direct_form, request_detail, course_public, _subnav

scripts/extract_plans_html.py    # apoyo único para generar planes_2026.json (no se despliega)

apps/core/tests/
├── test_learning_tags.py        # nuevo
├── test_learning_plans.py       # nuevo (planes, Mi plan, visibilidad, seguimiento)
├── test_learning_import.py      # nuevo (fixture mínimo de xlsx + json; idempotencia; KO; niveles; reset)
└── test_learning.py             # ajustes por tags M2M y quitar levels
```

**Structure Decision**: todo dentro de la app existente `apps/learning` y de los servicios en `apps/core/services`, igual que 004. No se crea app nueva: planes y Mi plan son parte del mismo contexto (Arena Learn) y comparten `CatalogCourse` y `CourseRequest`.

## Decisiones clave (detalle en research.md)

1. **Etiquetas = modelo `Tag` + M2M** (R1), con un componente de formulario propio (R2).
1b. **Tipo de aprendizaje + enfoque** (R12): el tipo del curso (Estructurado, Certificación, Puntual, Contextual, Soft Skills, Evento) es la única clasificación; los planes no tienen secciones propias y agrupan por tipo. Cada curso lleva además un enfoque Horizontal/Vertical **independiente** del tipo; no se derivan uno del otro. Se quitan del catálogo el pilar y las áreas manuales; las áreas se derivan de los planes.
2. **Identidad por liga** conservando los parámetros que identifican el recurso, como el `v` de YouTube (R3).
3. **Nivel solo en `PlanCourse`**: se elimina `CatalogCourse.levels` (R4). Filtrar por nivel N en un plan muestra los cursos con N **y** los "Todos los niveles".
4. **Duración decimal** (R5).
5. **Importación = Excel + JSON curado** ejecutada por comando (R6). Las reglas de clasificación, incluido el destino de los 20 cursos solo-KO, están en R7.
6. **Mi plan sin estado propio**: se deriva de `CourseRequest` (R8).
7. **Limpieza** con comando en seco y confirmación, más un respaldo previo en Neon (R10).

## Fases de entrega (orden sugerido para tasks)

| Fase | Contenido | Historias |
|---|---|---|
| 1. Fundación (tasks Phase 2) | Migración, modelos, claves de permiso, `normalize_url`, servicio de etiquetas | — |
| 2. Etiquetas (Phase 3) | `_tag_input`, formularios de catálogo y solicitud, filtro del catálogo, pantalla de administración | US1 |
| 3. Planes (Phase 4) | Vista de plan con filtros, administración del plan, menú | US2 |
| 4. Importación + limpieza (Phase 5) | JSON curado, `reset_learning_data`, `import_learning_plans`, corrida en producción | US4 |
| 5. Mi plan (Phase 6) | agregar, iniciar, descartar, estado derivado, vista para Lead/Talento | US3 |
| 6. Seguimiento (Phase 7) | tablero y exporte | US5 |
| 7. Cursos tomados (Phase 8) | bloqueada por el export de SharePoint | US6 |

La importación (fase 4) va antes de Mi plan para que los planes reales estén publicados en producción cuanto antes. Fases 1 a 4 forman el primer deploy (MVP); las fases 5 y 6, el segundo.

## Complexity Tracking

| Tensión | Por qué | Alternativa descartada |
|---|---|---|
| La migración quita columnas (`tags`, `levels`) que usa el código en producción | Vercel no corre migraciones y la BD se migra antes del push. Entre la migración y el deploy, el Catálogo de Learn fallaría | Hacer dos deploys (agregar y luego quitar): más trabajo para un módulo con 4 solicitudes de prueba. **Se acepta una ventana corta**: migrar → limpiar → importar → push, seguidos, en horario sin uso. |
| Archivo JSON curado además del Excel | Los HTML no son un formato estable; el JSON queda auditable en git | Parsear HTML en cada corrida, frágil |
