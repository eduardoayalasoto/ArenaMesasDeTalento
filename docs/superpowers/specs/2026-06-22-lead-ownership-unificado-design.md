# Diseño: Evaluación de Ownership unificada para Leads

**Fecha:** 2026-06-22
**Autor:** Eduardo Ayala + Claude
**Estado:** Aprobado — listo para implementación

---

## 1. Contexto y problema

Los colaboradores con nivel LEAD participan en múltiples proyectos con un rol de oversee estratégico,
no de ejecución por proyecto. Llenar un cuestionario de Ownership por cada proyecto que integran es
desproporcionado y no refleja cómo opera un Lead. El caso concreto que lo evidenció: Marco Aristeo.

## 2. Solución aprobada

Los Leads llenan **un único cuestionario de Ownership por periodo**, no vinculado a un proyecto
específico sino a toda su participación. El cuestionario usa la plantilla PUBLICADA para su área +
nivel LEAD (ya existe en el sistema). Los proyectos en los que participan se muestran de forma
informativa al inicio del cuestionario y en las vistas relacionadas, pero el Lead no responde por
proyecto; responde por su rol transversal.

La Entrega de Valor **no cambia**: sigue siendo por proyecto.

---

## 3. Modelo de datos

### 3.1 `OwnershipEvaluation.project` → nullable

```python
project = models.ForeignKey(
    "catalog.Project", on_delete=models.PROTECT,
    related_name="ownership_evaluations", verbose_name="proyecto",
    null=True, blank=True,   # ← nuevo
)
```

NULL indica evaluación de Lead (sin proyecto específico).

### 3.2 Unique constraints — reemplazo

Se elimina el constraint actual `unique_ownership_eval` y se reemplaza por dos constraints
parciales que cubren ambos casos sin ambigüedad:

```python
constraints = [
    # Colaborador normal: un eval por (user, project, period)
    models.UniqueConstraint(
        fields=["user", "project", "period"],
        condition=models.Q(project__isnull=False),
        name="unique_ownership_eval",
    ),
    # Lead: un solo eval por (user, period) cuando project es NULL
    models.UniqueConstraint(
        fields=["user", "period"],
        condition=models.Q(project__isnull=True),
        name="unique_lead_ownership_eval",
    ),
]
```

### 3.3 Sin modelos nuevos

`OwnershipEvaluator` (evaluadores primario/secundario) funciona sin cambio: apunta a
`OwnershipEvaluation` por PK. La selección de evaluador para un Lead es idéntica a la de cualquier
colaborador — sin restricciones de rol.

### 3.4 Migración

- `AlterField` en `OwnershipEvaluation.project` (añade `null=True, blank=True`).
- `RemoveConstraint` del constraint actual.
- `AddConstraint` de los dos constraints parciales.
- No se necesita data migration: en producción no existen evaluaciones de Lead por proyecto.

---

## 4. Capa de servicios (`apps/core/services/ownership_flow.py`)

### 4.1 `get_or_create_ownership_evaluation`

`project` pasa a ser opcional (default `None`). La búsqueda del existente se bifurca:

```python
def get_or_create_ownership_evaluation(user, period, project=None, evaluator=None):
    if project is None:
        existing = OwnershipEvaluation.objects.filter(
            user=user, project__isnull=True, period=period
        ).first()
    else:
        existing = OwnershipEvaluation.objects.filter(
            user=user, project=project, period=period
        ).first()
    ...
    evaluation = OwnershipEvaluation.objects.create(
        user=user, project=project, period=period, template=template,
    )
```

### 4.2 Resto de `ownership_flow.py`

Sin cambio. `close_ownership_evaluation`, `reopen_ownership_evaluation`,
`sync_evaluation_template`, `add_evaluator`, `remove_evaluator`, `set_primary_evaluator`
son agnósticos al campo `project`.

### 4.3 `scoring.py` y `final_flow.py`

Sin cambio. `ownership_pillar_score` promedia todas las evaluaciones ENVIADAS del usuario
en el periodo — funciona correctamente tanto con 1 evaluación (Lead) como con N (colaborador normal).

---

## 5. URLs y vistas (`apps/evaluations/`)

### 5.1 Nueva URL

```python
path("ownership/lead/iniciar/", views.ownership_lead_start, name="ownership_lead_start"),
```

Se inserta antes de los patrones `<int:pk>` en `urls.py`. El resto de URLs trabajan con el PK
de evaluación y no requieren cambio.

### 5.2 `ownership_list`

Añade una bifurcación al inicio:

- **Si `request.user.is_lead`:** construye una sola tarjeta con los proyectos vivos del Lead
  (query sobre `ProjectMembership` filtrada a proyectos activos) y el estado de la evaluación
  unificada (si existe). No se renderizan tarjetas por proyecto.
- **Si no es Lead:** comportamiento actual sin cambio.

La lista de proyectos activos del Lead se pasa como `lead_projects` al contexto.

### 5.3 `ownership_lead_start` (nueva vista)

Precondiciones: periodo abierto + usuario es Lead. Si ya existe una evaluación de Lead en el
periodo, redirige directamente a `ownership_edit`. Si no, presenta la pantalla de selección de
evaluador (mismo template `ownership_start.html`, con `project=None`).

POST: llama `get_or_create_ownership_evaluation(user, period, project=None, evaluator=evaluator)`,
luego `add_evaluator` para secundarios. Redirige a `ownership_edit`.

### 5.4 `_render_ownership` (ajustes)

- `page_title`: `evaluation.project.name` si `evaluation.project` existe; `"Todos mis proyectos"` si `project` es None.
- Contexto nuevo `lead_projects`: si `evaluation.project is None`, query viva de
  `evaluation.user.memberships.select_related("project").filter(project__is_active=True).order_by("project__name")`.
  De lo contrario, `None`.

### 5.5 Mensajes con `project.name` — fix

`ownership_save` y `ownership_reopen` referencian `evaluation.project.name` en mensajes de éxito.
Se cambia a: `evaluation.project.name if evaluation.project else "todos sus proyectos"`.

### 5.6 `ownership_validation`

- Ordering: `evaluation__project__name, evaluation__user__full_name` → `evaluation__user__full_name`
  (evita problemas con NULL en la columna de proyecto).
- `select_related` sigue incluyendo `evaluation__project` para el template.

---

## 6. Templates

### 6.1 `ownership_list.html`

Bloque lead (antes del grid de tarjetas regular):

```
Si is_lead:
  - Una sola card "Ownership · Todos tus proyectos"
  - Chips de los proyectos activos en los que participa (nombre + cliente)
  - Barra de progreso + promedio (si la evaluación existe)
  - Badge de estado (Sin iniciar / Abierta / Cerrada)
  - CTA: "Comenzar" → ownership_lead_start | "Continuar" → ownership_edit | "Ver" → ownership_view
```

El subtexto de la página cambia a:
- Lead: "Una sola evaluación transversal para todos tus proyectos."
- No Lead: "Una evaluación por proyecto." (actual)

### 6.2 `ownership_start.html`

Línea de subtítulo: `{% if project %}Proyecto: {{ project.name }}{% else %}Todos tus proyectos{% endif %}`.

### 6.3 `ownership_fill.html`

- Título (L16): `{% if evaluation.project %}{{ evaluation.project.name }}{% else %}Todos mis proyectos{% endif %}`.
- Card informativo de proyectos (insertar antes de la barra de progreso sticky): visible solo si
  `lead_projects` está en el contexto. Muestra: leyenda "Proyectos en los que participas —
  referencia para esta evaluación" + chips `nombre · cliente` en flex-wrap. El card es solo
  lectura e informativo, sin interacción.

### 6.4 `ownership_validation.html`

Línea de proyecto (L18): `{% if ev.project %}{{ ev.project.name }}{% else %}Todos sus proyectos{% endif %}`.

---

## 7. Dashboards (`apps/dashboards/views.py`)

### 7.1 `build_results`

Bifurcación para Leads:

**Lead:**
- `projects`: lista de membresías activas (`ProjectMembership`) con el score VD validado de cada
  proyecto. No se vincula al cuestionario de Ownership (que es transversal).
- `lead_eval`: la `OwnershipEvaluation` con `project=None` (para score + feedback). Puede ser None.
- `feedback`: `[lead_eval]` si está ENVIADA, `[]` si no.

**Colaborador normal:** sin cambio. `projects` sigue vinculando ownership + VD por proyecto.

Esto requiere extraer la query de VD por membresías separada de la query de ownership evals para Leads.

### 7.2 Templates de resultados (`_results_body.html`, `my_results.html`, `user_results.html`)

Detectan `lead_eval` en contexto:
- Sección "Evaluaciones de Ownership": si `lead_eval` → muestra score único del Lead + lista de
  proyectos con sus scores VD. Si no `lead_eval` → comportamiento actual (fila por proyecto).
- Sección "Retroalimentación": sin cambio (ya usa `feedback`, que ahora puede ser `[lead_eval]`).

### 7.3 `talent_table`

Se agrega al contexto `lead_projects_by_user`: dict `{user_id: [nombre_proyecto, ...]}` construido
para los usuarios Lead de la página actual (query sobre `ProjectMembership`). En el template, la
columna "Proyectos" para Leads muestra un tooltip/popover con los nombres al hacer hover sobre el
badge numérico, en lugar de solo el número.

### 7.4 `period_progress`

Sin cambio. Un Lead con evaluación cerrada contribuye 1 al conteo de `own_submitted`, igual que
cualquier colaborador.

### 7.5 `my_area`

`submitted_counts` es un dict `{user_id: count_de_evaluaciones_ENVIADAS}`. Para un Lead será 0 o 1.
En el template, si el usuario es Lead (`level.code == "LEAD"`), la columna de Ownership muestra
"Cerrada" / "Pendiente" en lugar de "X/N proyectos", evitando confusión por conteo.

---

## 8. Pruebas (a agregar)

| Test | Descripción |
|---|---|
| `test_lead_eval_no_project` | `get_or_create_ownership_evaluation(lead, period, project=None)` crea correctamente con `project=None`. |
| `test_lead_unique_constraint` | No se puede crear una segunda evaluación de Lead para el mismo usuario y periodo. |
| `test_non_lead_constraint_unchanged` | El constraint original sigue impidiendo duplicados para colaboradores normales. |
| `test_ownership_pillar_score_lead` | Con 1 eval (project=None) ENVIADA, `ownership_pillar_score` devuelve su score directamente. |
| `test_lead_list_shows_single_card` | `ownership_list` para un Lead muestra la tarjeta unificada (sin tarjetas por proyecto). |
| `test_non_lead_list_unchanged` | `ownership_list` para un colaborador normal sigue mostrando tarjetas por proyecto. |
| `test_lead_eval_context_projects` | `_render_ownership` para eval de Lead incluye `lead_projects` vivos en el contexto. |

---

## 9. Decisiones registradas

| Decisión | Razón |
|---|---|
| Lista de proyectos **viva** (no congelada) | Refleja la participación real actual del Lead; los cambios de membresía durante el periodo son raros y no justifican la complejidad de un snapshot. |
| **Sin restricción** de evaluador para Leads | Consistencia con el resto del sistema; el Lead elige libremente, igual que todos. |
| `project` nullable vs. modelo separado | El enfoque nullable reutiliza toda la maquinaria existente (scoring, evaluadores, cierre, reapertura) sin duplicación. |
| No data migration necesaria | Confirmado que en producción no existen evaluaciones de Ownership per-proyecto para usuarios con nivel LEAD. |
