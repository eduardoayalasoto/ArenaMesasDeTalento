# Data Model — 006 Arena Learn: planes anuales, etiquetas e importación

Todo vive en la app `apps/learning` (esquema `"talento-app"`). Referencias externas: `catalog.Area`, `catalog.SeniorityLevel` y `accounts.User`.

## Cambios a modelos existentes

### `CatalogCourse` (modificado)

| Campo | Cambio |
|---|---|
| `tags` | `CharField` → **`ManyToManyField(Tag, blank=True, related_name="courses")`** |
| `levels` | **se elimina** (R4); el nivel vive en `PlanCourse.levels` |
| `pillar` | **se elimina** (R12) |
| `areas` | **se elimina** (R12); se derivan de los planes publicados en que aparece |
| `focus` | **nuevo** `CharField` choices `HORIZONTAL / VERTICAL` (R12), independiente de `kind` |
| `duration_hours` | `PositiveSmallIntegerField` → **`DecimalField(5,1)`** (R5) |
| `normalize_tags`, `tag_list`, override de `save()` | se eliminan |
| `kind` | **valores nuevos** de `CourseKind` = tipo de aprendizaje (R12), con migración de los valores anteriores |
| resto (`name`, `provider`, `url`, `reference_cost`, `currency`, `description`, `is_active`, …) | sin cambio |

La regla de identidad (liga normalizada, R3) se aplica en el servicio y no en la BD, porque la normalización no es indexable de forma simple. La importación la garantiza y el alta manual avisa si la liga ya existe (`catalog_for_url`).

### `CourseRequest` (modificado)

| Campo | Cambio |
|---|---|
| `tags` | `CharField` → **`ManyToManyField(Tag, blank=True, related_name="requests")`**. Snapshot: al elegir un curso del catálogo se copian sus etiquetas y el colaborador puede editarlas. |
| `duration_hours` | → `DecimalField(5,1)` |
| `is_imported` | **nuevo** `BooleanField(default=False)`, solo para US6: registro histórico cargado sin evidencia ni reseña |
| `pillar` | se conserva ("pilar que fortalece", opinión del colaborador); ya no se precarga desde el catálogo |

`HistoricalCourseRequest` (simple_history) no registra M2M, así que el historial no guarda cambios de etiquetas. Es aceptable: las etiquetas no son dato de autorización.

## Modelos nuevos

### `Tag`

| Campo | Tipo | Reglas |
|---|---|---|
| `name` | `CharField(60)` | visible; `strip` y espacios colapsados |
| `key` | `CharField(60, unique=True)` | `normalize_tag_key(name)`: minúsculas, sin acentos, espacios colapsados (R1) |
| `is_active` | `BooleanField(default=True)` | inactiva = no se sugiere y no se puede volver a crear (FR-006) |
| `created_by` | FK User, `SET_NULL`, null | |
| `created_at` | `DateTimeField(auto_now_add)` | |

- `ordering = ["name"]`.
- **Fusionar** `src → dst`: en una transacción, `dst.courses.add(*src.courses.all())` y `dst.requests.add(*src.requests.all())` (el M2M evita duplicados) y luego `src.delete()`. Prohibido si `src == dst` o si `dst` está inactiva.
- **Renombrar**: recalcula `key`. Si choca con otra etiqueta, se rechaza y se sugiere fusionar.

### `TrainingPlan`

| Campo | Tipo | Reglas |
|---|---|---|
| `area` | FK `catalog.Area`, `PROTECT` | |
| `year` | `PositiveSmallIntegerField` | |
| `title` | `CharField(160)` | p. ej. "Plan de Capacitación PM 2026" |
| `start_month`, `end_month` | `PositiveSmallIntegerField` 1–12 | `start_month <= end_month` |
| `hours_min`, `hours_max` | `PositiveSmallIntegerField`, null | horas/semana sugeridas; `min <= max` |
| `intro` | `TextField(blank)` | |
| `type_notes` | `JSONField(default=dict)` | `{kind: texto de la guía}`; se muestra como introducción de cada grupo |
| `status` | `CharField` choices `BORRADOR / PUBLICADO / ARCHIVADO` | default `BORRADOR` (alta manual) |
| `published_at` | `DateTimeField`, null | |
| `created_by` | FK User, `SET_NULL`, null | |
| `created_at`, `updated_at` | auto | |

- `UniqueConstraint(area, year)` (FR-009).
- Transiciones: `BORRADOR → PUBLICADO` (requiere al menos un `PlanCourse`, FR-014), `PUBLICADO → ARCHIVADO`, `ARCHIVADO → PUBLICADO` (reabrir) y `PUBLICADO → BORRADOR` (despublicar). Ninguna borra datos.
- Visibilidad (FR-013): `BORRADOR` solo con `learn.plans.manage`. `PUBLICADO` y `ARCHIVADO` con `learn.plans.view`. Un plan `ARCHIVADO` no permite agregar a Mi plan.

### `PlanCourse`

| Campo | Tipo | Reglas |
|---|---|---|
| `plan` | FK `TrainingPlan`, `CASCADE`, `related_name="items"` | |
| `course` | FK `CatalogCourse`, `PROTECT`, `related_name="plan_items"` | |
| `order` | `PositiveSmallIntegerField` | orden del material dentro de su tipo |
| `levels` | M2M `catalog.SeniorityLevel`, blank | vacío = "Todos los niveles" (FR-011) |
| `note` | `CharField(200, blank)` | p. ej. "Beta abr 2026 · Live jun 2026" |

- `UniqueConstraint(plan, course)`: un curso aparece una vez por plan.
- La vista agrupa por `course.kind` (orden fijo de R12) y dentro del grupo por `order`.
- Quitar un `PlanCourse` no toca `PersonalPlanItem` (FR-017, US2-5), porque Mi plan apunta al `CatalogCourse`.
- Si `course.is_active == False`, el plan lo muestra como "No disponible" y no se puede agregar a Mi plan.

### `PersonalPlan`

| Campo | Tipo | Reglas |
|---|---|---|
| `user` | FK User, `CASCADE`, `related_name="personal_plans"` | |
| `year` | `PositiveSmallIntegerField` | |
| `created_at` | auto | |

- `UniqueConstraint(user, year)`. Se crea al agregar el primer curso del año.

### `PersonalPlanItem`

| Campo | Tipo | Reglas |
|---|---|---|
| `personal_plan` | FK `PersonalPlan`, `CASCADE`, `related_name="items"` | |
| `course` | FK `CatalogCourse`, `PROTECT` | |
| `source` | FK `PlanCourse`, `SET_NULL`, null | de qué plan se agregó |
| `discarded` | `BooleanField(default=False)` | FR-021 |
| `started_at` | `DateTimeField`, null | "Empezar" sin costo (R8) |
| `added_at` | auto | |

- `UniqueConstraint(personal_plan, course)`.
- **Estado derivado** (no se guarda; R8): `DESCARTADO | COMPLETADO | EN_CURSO | PENDIENTE`, más `detail` (`status_display` de la solicitud) y `request` (la `CourseRequest` vinculada, si existe).

## Diagrama

```text
catalog.Area ─┐
              └─< TrainingPlan (area, year) ─< PlanCourse >─ CatalogCourse (kind, focus) >─< Tag
                                                              │  >─< SeniorityLevel             │
User ─< PersonalPlan (user, year) ─< PersonalPlanItem >───────┼──────────── CatalogCourse         │
                                          └ source ───────────┘                                  │
User ─< CourseRequest >─ CatalogCourse        CourseRequest >─< Tag ────────────────────────────┘
```

## Índices y consultas

- Vista de plan: `PlanCourse.objects.filter(plan=…).select_related("course").prefetch_related("levels", "course__tags")`, agrupado en memoria por `course.kind`, más la anotación de `avg_rating` desde `catalog_queryset` en un mapa `{course_id: (avg, count)}`.
- Filtro por varias etiquetas (FR-007): se encadena `.filter(course__tags=t)` por cada etiqueta.
- Mi plan: 1 consulta de items (`select_related("course", "source__plan")`) + 1 de `CourseRequest` del usuario (R8).
- Seguimiento: items de los usuarios en alcance + sus `CourseRequest` en 2 consultas; el estado se resuelve en memoria.
