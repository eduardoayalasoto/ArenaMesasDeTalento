# Research — 006 Arena Learn: planes anuales, etiquetas e importación

Fecha: 2026-10-12. Cada decisión: **Decisión / Razón / Alternativas**.

## R1. Etiquetas: modelo propio + M2M

- **Decisión**: nuevo modelo `learning.Tag` (`name`, `key` normalizada única, `is_active`) con M2M desde `CatalogCourse.tags` y `CourseRequest.tags`. Se eliminan los `CharField tags` y `normalize_tags`. No se migra su contenido, porque solo hay datos de prueba que se borran (FR-008, FR-039).
- **Normalización de `key`**: minúsculas, sin acentos (NFKD) y espacios colapsados. "KO", " ko " y "Kó" dan `ko`. El `name` visible conserva la primera captura.
- **Razón**: el filtro "todas las etiquetas" (FR-007) y la fusión (FR-005) piden filas, no texto. El M2M permite `filter(tags=a).filter(tags=b)` y `Count`.
- **Alternativas**: (a) `django-taggit`: dependencia extra y modelo genérico de más para dos modelos; (b) `ArrayField`: no deja renombrar ni fusionar sin reescribir filas.

## R2. Componente de captura de etiquetas

- **Decisión**: nuevo componente `templates/components/_tag_input.html`, un campo dentro de un `<form>`. Las fichas elegidas se guardan en `<input type="hidden" name="tags">`; Alpine solo maneja la lista local (agregar o quitar ficha). Las sugerencias llegan por htmx GET a `learning:tag_suggest?q=` (`hx-trigger="input changed delay:200ms"`), que devuelve un parcial `<li>`. Escribir un nombre que no existe y presionar Enter crea una ficha "nueva"; la etiqueta se crea al guardar el formulario, en el servicio `tags.resolve(names, actor)`.
- **Razón**: `_tag_picker.html` (arena-crm) aplica o quita al instante por entidad y maneja colores. Aquí la etiqueta es parte de un formulario (catálogo, solicitud, registro) y sin color (decisión de sencillez). Se reutiliza su estructura visual (`badge badge-soft`) y no su flujo.
- **Alternativas**: un `<select multiple>` con datalist, que no permite crear en el mismo campo (FR-003).

## R3. Identidad de curso por liga (FR-024)

- **Decisión**: `normalize_url` deja de descartar todo el query string. Conserva los parámetros que identifican el recurso y quita los de rastreo o posición: `t`, `si`, `ref`, `trk`, `utm_*`, `coupon*`, `referralCode`, `source`. También quita esquema, `www.` y la diagonal final. Ejemplo: `youtube.com/watch?v=gNQ9-kgyHfo&t=285s` → `youtube.com/watch?v=gNQ9-kgyHfo`.
- **Razón**: el Excel tiene 4 videos de YouTube distintos que hoy colapsarían en `youtube.com/watch`.
- **Alternativas**: una regla especial solo para YouTube, más frágil ante otras plataformas.
- **Impacto**: `catalog_for_url`, `open_request_for` y `requestable_courses` usan la misma función. Con la limpieza de datos no hay ligas previas que re-normalizar.

## R4. Nivel recomendado solo en el plan

- **Decisión**: se elimina `CatalogCourse.levels`. El nivel vive en `PlanCourse.levels` (M2M a `catalog.SeniorityLevel`). `promote_to_catalog` deja de copiar `audience_levels` y la reseña conserva sus `audience_levels`, que son la opinión del colaborador. El filtro "nivel" del catálogo se reemplaza por "etiqueta"; filtrar por nivel ocurre en la vista del plan.
- **Razón**: decisión del usuario. El curso describe la plataforma y el nivel es criterio de Talento, por plan.

## R5. Duración con decimales

- **Decisión**: `duration_hours` pasa de `PositiveSmallIntegerField` a `DecimalField(max_digits=5, decimal_places=1)` en `CatalogCourse` y `CourseRequest`.
- **Razón**: el material trae duraciones de 0.5 h, 1.5 h, 2.5 h y 9.5 h, que hoy se truncarían.

## R6. Fuente de la importación: Excel + archivo de datos curado

- **Decisión**: hay dos entradas. (1) El Excel, tal cual, se lee con `openpyxl` (ya es dependencia del exporte). (2) `apps/learning/data/planes_2026.json` es un archivo versionado que se extrae **una vez** de los 4 HTML con un script de apoyo (`scripts/extract_plans_html.py`, fuera de la app), se revisa a mano y se commitea. Trae metadatos de cada plan (título, periodo, horas, intro), el orden de secciones, los niveles por liga, las certificaciones con costo de referencia y la lista de ligas KO con su fase. El comando `import_learning_plans` cruza ambos.
- **Razón**: los HTML son documentos ad hoc (con emojis, badges concatenados y dos versiones del plan de IA). Parsearlos en cada corrida es frágil; un JSON revisado es auditable y repetible (FR-029, SC-003).
- **Alternativas**: (a) una pantalla de carga de archivos para Talento. Se descartó: es una carga inicial única y el usuario la pidió ejecutada por nosotros. (b) Parsear el HTML en el comando, frágil.

## R7. Reglas de clasificación de la importación

| Origen en el material | Resultado |
|---|---|
| Hoja PM / UX-UI | área PM / UXUI |
| Hoja ID, ruta "Ingeniería de Datos" | área ID, plan ID 2026 |
| Hoja ID, ruta "Ingeniería de IA" | área CD, plan CD 2026 |
| Hoja CD | área CD, plan CD 2026 |
| Columna D "Aprendizaje Estructurado / Certificado / Puntual / Contextual", "Habilidades Blandas" | `kind` (tipo de aprendizaje); Habilidades Blandas → Soft Skills |
| Columna D "Aprendizaje Horizontal" / "Aprendizaje Vertical" | `focus` (enfoque). **No** define el tipo |
| Prefijo "Ingeniería de IA — " / "Ingeniería de Datos — " | se quita antes de interpretar |
| Sin tipo, sin enfoque o con dos tipos | valor del JSON curado, marcado `propuesto` (FR-026a); sin valor en el JSON → fila reportada |
| Solo "Cursos del programa KO Upskilling" (20, PM) | tipo **Puntual** (enfoque del JSON curado); nivel por fase: Foundations → Jr, Intermediate → Mid, Advanced → Snr |
| Marca KO (bloque KO, badge KO o 🅺🅾 en el HTML) | etiqueta "KO" en el curso del catálogo |
| Nivel "Jr", "Mid", "Snr", "Jr-Mid", "Mid-Snr", "Snr-Lead" | niveles del curso **en ese plan** |
| "Todos" o sin marca | sin niveles ("Todos los niveles") |
| Certificaciones del HTML (no están en el Excel) | `CatalogCourse(kind=CERTIFICACION, reference_cost, currency=USD)` en el plan de su área |
| Misma liga con nombres distintos | un curso; se conserva el primer nombre visto; el alias va al resumen |
| Plataforma vacía | se infiere del dominio (`learn.microsoft.com` → "Microsoft Learn"); si no se puede, "Sin especificar" |

Los planes se crean en estado **PUBLICADO** (FR-031). Una nueva corrida no cambia el estado de un plan ya archivado.

## R8. Avance de Mi plan derivado (FR-018)

- **Decisión**: `PersonalPlanItem` no guarda estado. Guarda `discarded` y `started_at`; este último marca "Empezar" sin costo. El estado se calcula en `learning_plans.item_status(items, user)` con **una** consulta a las `CourseRequest` del usuario, indexadas por `catalog_course_id` y por liga normalizada:
  - descartado → Descartado
  - solicitud COMPLETADA/VALIDADA → Completado
  - solicitud EN_REVISION/REQUIERE_AJUSTES/AUTORIZADA → En curso (con `status_display`, p. ej. "En revisión del Lead")
  - solicitud BORRADOR → Pendiente con nota "Borrador de solicitud" (cubre el bloqueo por curso autorizado sin cerrar)
  - `started_at` sin solicitud → En curso
  - si no → Pendiente
  - Las solicitudes RECHAZADA, CANCELADA o NO_CONCLUIDA no cuentan; el curso vuelve a Pendiente y se muestra la última como nota.
- **Razón**: una sola fuente de verdad (FR-038). Evita estados duplicados que diverjan.

## R9. Permisos (spec 005)

Claves nuevas en `apps/access/registry.py` con su fila en `seed.py` y `legacy.py`:

| Clave | Acción | Alcances | Rutas |
|---|---|---|---|
| `learn.plans.view` | ver | ON_OFF (todos los perfiles en T) | `plan_list`, `plan_detail` |
| `learn.plans.manage` | editar | ON_OFF (Talento, Admin) | crear/editar plan, estado, textos por tipo y cursos del plan |
| `learn.myplan` | editar | (N, P) | `my_plan`, `my_plan_add`, `my_plan_item_*` |
| `learn.myplan.others` | ver | (N, A, AR, T) | `person_plan` (A = reportes directos; AR = su área; T = todos) |
| `learn.plans.tracking` | ver | (N, A, AR, T) | `plan_tracking`, `plan_tracking_export` |
| `learn.tags.manage` | administrar | ON_OFF (Talento, Admin) | `tag_list`, `tag_edit`, `tag_merge`, `tag_toggle` |

`learn.myplan`, `learn.myplan.others` y `learn.plans.tracking` se registran con `status="pending"` hasta que existan sus rutas (deploy 2), para que `test_access_coverage` pase en el deploy 1. El alcance **A** de `learn.myplan.others` y `learn.plans.tracking` = "mis reportes directos" (`assigned_q = Q(direct_lead=viewer)`).

`learning:tag_suggest` se agrega a `learn.public.view`, que ya tienen todos y usa quien llena un formulario con etiquetas. La importación y la limpieza son comandos y no tienen ruta.

## R10. Limpieza de datos de prueba (FR-039/040)

- **Decisión**: comando `reset_learning_data` con `--dry-run` (default: solo cuenta) y `--confirm`. Requisito previo: una rama de respaldo en Neon (`backup-pre-006`) desde `main`. Borra en una transacción, en este orden: `ApprovalStep`, `CourseEvidence`, `CourseReview` (y sus M2M), `CourseRequest.history`, `CourseRequest`, `CatalogCourse` (y sus M2M), `Tag`. **No toca** `LearningSettings`, usuarios, áreas, niveles ni otros esquemas. Se niega a correr si encuentra datos con `created_at` posterior a la fecha de corte que se le pase (`--before`), como protección por si alguien empieza a usar Learn entre hoy y la corrida.
- **Razón**: un comando auditable y repetible en seco. Una migración de datos también correría en la BD de pruebas y en cualquier entorno nuevo.

## R11. Orden de despliegue

1. Migraciones (esquema `talento-app`, conexión directa): `Tag`, planes, Mi plan, quitar `levels` y `tags` CharField, `duration_hours` decimal.
2. `reset_learning_data --dry-run` → revisar conteos → respaldo en Neon → `--confirm`.
3. `import_learning_plans` → revisar resumen → segunda corrida para comprobar 0 creados (SC-003).
4. Push a `main` (deploy en Vercel).

Antes del paso 2, la app en producción sigue con el código anterior. Si las migraciones que quitan columnas corren antes del deploy, el código anterior falla en Catálogo. Por eso los pasos 1 a 4 se ejecutan seguidos en una ventana corta, o las columnas se quitan en un segundo deploy (ver Complexity Tracking en plan.md).

## R12. Tipo de aprendizaje, enfoque, pilar y áreas (decisiones del 2026-10-12)

- **Dos dimensiones independientes** (decisión del usuario: no se combinan ni se derivan una de otra):
  - **Tipo de aprendizaje** (`kind`): qué clase de aprendizaje es.
  - **Enfoque** (`focus`): si da amplitud (Horizontal) o profundidad (Vertical).
- `CourseKind` se redefine (aplica a `CatalogCourse.kind` y `CourseRequest.kind`):

| Valor | Etiqueta | Mapeo del valor anterior |
|---|---|---|
| ESTRUCTURADO | Estructurado | CURSO, CAPACITACION |
| CERTIFICACION | Certificación | CERTIFICACION |
| PUNTUAL | Puntual | OTRO |
| CONTEXTUAL | Contextual | — |
| SOFT_SKILLS | Soft Skills | — |
| EVENTO | Evento | CONFERENCIA |

- **`focus`**: `HORIZONTAL | VERTICAL`, obligatorio en el formulario y sin sugerencia automática. En la importación sale de "Aprendizaje Horizontal/Vertical" o del JSON curado.
- **Huecos del material** (medido el 2026-10-12 sobre 249 cursos): 58 sin tipo (38 solo "Horizontal" y 20 solo-KO), 206 sin enfoque y 5 con dos tipos. Se completan en `planes_2026.json` con el criterio de los supuestos de la spec, marcados `propuesto`. El usuario los revisa en el gate de T029.
- **Los planes no tienen secciones.** `PlanCourse` cuelga directo de `TrainingPlan` y la vista agrupa por `course.kind` en el orden de la tabla. El texto de cada tipo vive en `TrainingPlan.type_notes` (JSON `{kind: texto}`).
- **Pilar**: se quita `CatalogCourse.pillar`. Se conserva `CourseRequest.pillar` ("pilar que fortalece", opinión del colaborador), pero ya no se precarga desde el catálogo.
- **Áreas**: se quita `CatalogCourse.areas`. Las áreas de un curso son las de los planes **publicados** en que aparece (`plan_items__plan__area`). Un curso sin plan muestra "Sin plan".
