# Data Model: Ownership ponderado por categorías

Cambios **aditivos**. Ninguna columna existente se elimina ni se reinterpreta.

## Entidades nuevas

### `questionnaires.Category`
Catálogo común de categorías de pregunta.

| Campo | Tipo | Notas |
|---|---|---|
| `code` | slug, único | `general`, `delivery_cliente`, `desarrollo_producto`, `herramientas_gestion`, `actitud_persona` |
| `name` | texto (≤ 80) | Se muestra en pantallas e informes |
| `order` | entero positivo | Orden de despliegue |
| `is_active` | booleano | Una categoría inactiva no se ofrece en cuestionarios nuevos |

Siembra: `General` (orden 0) y las cuatro de Consultoría.
Regla: no se elimina una categoría con preguntas o configuraciones asociadas (`PROTECT`).

### `questionnaires.TemplateCategory`
Peso de una categoría dentro de un cuestionario.

| Campo | Tipo | Notas |
|---|---|---|
| `template` | FK → `QuestionnaireTemplate` (CASCADE) | |
| `category` | FK → `Category` (PROTECT) | |
| `weight_pct` | decimal(4,1) | 0.0 a 100.0, un decimal |

Restricciones: único `(template, category)`; la suma de `weight_pct` de un cuestionario publicado de Ownership es exactamente 100.0.

### `catalog.Position`
Relación área × nivel con nombre visible.

| Campo | Tipo | Notas |
|---|---|---|
| `area` | FK → `Area` (PROTECT) | |
| `level` | FK → `SeniorityLevel` (PROTECT) | |
| `name` | texto (≤ 60) | «Analista», «Consultor Sr», «Junior»… |
| `is_active` | booleano | |

Restricción: único `(area, level)`. Con historial (`HistoricalRecords`) como los demás catálogos.

Siembra: una fila por cada combinación de las 4 áreas de Analítica × 4 niveles con el nombre actual del nivel, y para `CONS`: JR = Analista, MID = Consultor, SNR = Consultor Sr, LEAD = Gerente.

## Entidades modificadas

### `questionnaires.Question`
| Cambio | Detalle |
|---|---|
| `category` | FK → `Category` (PROTECT), **nula**; obligatoria para preguntas de escala de Ownership al publicar; nula en texto largo |
| `weight_pct` | decimal(4,1), **nulo = partes iguales**; 0.0 = «se califica, no pondera» |
| `weight` (existente) | Se conserva sin uso; se retirará en un spec posterior |

Regla de grupo: dentro de una `(template, category)` los `weight_pct` están **todos nulos** (partes iguales) **o todos definidos** y suman 100.0.

### `catalog.Project`
| Cambio | Detalle |
|---|---|
| `suggested_evaluator` | FK → usuario, nula, `SET_NULL`, `related_name="suggested_for_projects"`; con historial |

## Sin cambios
`SeniorityLevel`, `PillarWeight`, `OwnershipEvaluation`, `OwnershipAnswer` (el valor 1–4 / N/A no cambia), `FinalScore`, `ValueDeliveryEvaluation`, `ArenaImpactScore`, Arena Learn.

## Reglas de cálculo

Para una evaluación con respuestas `R` (excluyendo N/A) y su cuestionario `T`:

1. Agrupar las preguntas de escala por categoría. Si `T` no tiene `TemplateCategory`, existe una sola categoría implícita al 100%.
2. Peso efectivo de pregunta dentro de su categoría: `weight_pct/100` si el grupo está definido; `1/n` entre las preguntas del grupo si es nulo.
3. Score de categoría `S_c` = Σ(valor × peso) ÷ Σ(pesos de las preguntas respondidas) sobre las respondidas con peso > 0; si ninguna aporta, la categoría queda **sin calificar**.
4. Peso de categoría efectivo `W_c` = `weight_pct/100`, renormalizado entre las categorías calificadas (excluyendo las sin calificar y las de peso 0 sin aportación).
5. Score del cuestionario = Σ(`S_c` × `W_c`), redondeado **una vez** a 2 decimales (mitad hacia arriba).
6. Si no hay ninguna categoría calificada, el score es nulo (igual que hoy sin respuestas).

Equivalencia con hoy: una categoría, `weight_pct` nulo → `Σ valores ÷ n`, redondeado una vez.

## Validaciones (servicio `ownership_weights`)

| Regla | Dónde se aplica |
|---|---|
| Todo peso con máximo 1 decimal y entre 0.0 y 100.0 | Formularios, servicio, importación |
| Σ pesos de categorías de un cuestionario = 100.0 | Formulario de pesos de categorías, publicación, importación |
| Σ pesos de preguntas de una categoría = 100.0, o todos nulos | Formulario de pesos de preguntas, publicación, importación |
| No se permiten pesos parcialmente definidos en un grupo | Igual |
| Categoría con peso > 0 sin preguntas, o con todas las preguntas en 0 → no publicable | Publicación, importación |
| Toda pregunta de escala de Ownership tiene categoría presente en el cuestionario | Publicación, importación |
| Combinación área × nivel con `Position` activo | Publicación y alta/edición de usuario |

## Migraciones

1. **`questionnaires/0003_category_templatecategory_question_fields`** (esquema): crea las tablas, `Question.category` y `Question.weight_pct`.
2. **`questionnaires/0004_seed_general_category`** (datos, reversible): crea las categorías sembradas; para cada cuestionario **de Ownership** crea `TemplateCategory(General, 100.0)` y asigna `General` a todas sus preguntas de escala. No toca Entrega de Valor ni respuestas.
3. **`catalog/0011_position_project_suggested_evaluator`** (esquema).
4. **`catalog/0012_seed_positions`** (datos, reversible): siembra Puestos.

Orden en producción: ejecutar `verify_ownership_scores` (línea base) → aplicar migraciones con la URL unpooled → `verify_ownership_scores` (debe dar diferencia cero) → desplegar → importar CONS en borrador.
