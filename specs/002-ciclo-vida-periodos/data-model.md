# Data Model: Ciclo de vida y continuidad de Periodos de Evaluación

No se crea ninguna app ni modelo nuevo (salvo un campo en uno existente). Esta
feature refuerza el ciclo de vida de `catalog.EvaluationPeriod` y extiende la
cobertura de auditoría a los 6 modelos que ya lo referencian.

## Entidad existente: `EvaluationPeriod` (`apps/catalog/models.py:75`)

| Campo | Tipo | Cambio |
|---|---|---|
| `name` | `CharField`, único | Sin cambios |
| `start_date` | `DateField` | Sin cambios de tipo; nueva regla de validación (ver abajo) |
| `end_date` | `DateField` | Sin cambios de tipo; nueva regla de validación (ver abajo) |
| `kind` | `CharField` (choices) | Sin cambios |
| `status` | `CharField` (choices: PLANEADO/ABIERTO/CERRADO) | Nueva regla de unicidad (ver abajo) |
| `history` | `HistoricalRecords` | Sin cambios (ya existente) |

### Constraint nuevo

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=["status"],
            condition=models.Q(status="ABIERTO"),
            name="unique_open_period",
        ),
    ]
```

Garantiza a nivel de base de datos que exista, a lo más, una fila con
`status=ABIERTO` (FR-001/FR-002). Mismo patrón que
`unique_published_template` en `QuestionnaireTemplate`.

### Validación nueva en `clean()`

- Al crear o editar un periodo con `start_date`/`end_date`, se valida contra
  el periodo inmediato anterior y el inmediato siguiente (por fecha) que:
  - No haya traslape (`start_date` no cae dentro del rango de otro periodo
    ni viceversa).
  - No haya hueco: si existe un periodo anterior por fecha, su `end_date` + 1
    día debe ser igual a este `start_date` (y simétricamente hacia el
    siguiente).
- Aplica solo hacia adelante (FR-004): no se ejecuta retroactivamente contra
  periodos ya existentes que no se estén editando.

### Métodos/propiedades nuevos (sobre los ya existentes `is_open`/`is_closed`)

- `has_content()`: `True` si algún registro de los 6 modelos listados abajo
  referencia este periodo (usado por `period_delete`, que ya bloquea el
  borrado vía `ProtectedError` — sin cambio de comportamiento, solo
  documentado aquí como regla vigente que esta feature no debe romper).

### Transiciones de estatus

```text
PLANEADO --(Talento abre, exige que no exista otro ABIERTO)--> ABIERTO
ABIERTO  --(Talento cierra, exige un PLANEADO contiguo)-->      CERRADO
                                                    └──(misma transacción)──> abre automáticamente el PLANEADO contiguo
```

No existe transición directa PLANEADO → CERRADO ni CERRADO → ABIERTO/PLANEADO
(fuera de alcance; no lo pide la spec).

## Entidad existente: `FinalScore` (`apps/evaluations/models.py:224`)

| Campo | Tipo | Cambio |
|---|---|---|
| `history` | `HistoricalRecords` | **Nuevo** — hoy `FinalScore` es el único de los 6 modelos con FK a `period` sin auditoría; se agrega para que FR-006 (excepción de corrección auditada) también lo cubra. Genera migración nueva (tabla `HistoricalFinalScore`). |

Resto de campos sin cambios.

## Entidades existentes sin cambio de esquema (solo nueva lógica de negocio en los flujos que las guardan)

Las 6 entidades de negocio que representan "elemento o componente de
retroalimentación" (Key Entities de `spec.md`), todas ya con FK uno-a-uno a
`EvaluationPeriod` vía `on_delete=models.PROTECT`:

| Modelo | Archivo | Rol en esta feature |
|---|---|---|
| `OwnershipEvaluation` | `apps/evaluations/models.py:9` | Bloqueo de edición si `period.is_closed` (vía `ownership_flow.py`) |
| `ValueDeliveryEvaluation` | `apps/evaluations/models.py:130` | Ídem (vía `value_delivery_flow.py`) |
| `ArenaImpactScore` | `apps/evaluations/models.py:193` | Ídem (vía vista `arena_impact_autosave`) |
| `FinalScore` | `apps/evaluations/models.py:224` | Ídem + `history` nuevo (arriba) |
| `TalentSessionNote` | `apps/evaluations/models.py:254` | Ídem — cubre tanto la nota del comité como el acuerdo de la sesión de retroalimentación (mismo registro) |
| `MesaProjectReview` | `apps/evaluations/models.py:335` | Ídem (sign-off de comité por proyecto) |

Ninguno cambia de esquema. El bloqueo de edición/eliminación cuando
`period.is_closed` se centraliza en
`period_lifecycle.assert_record_editable(record, actor)` (ver `research.md`,
Decisión 4) y se invoca desde el punto de guardado de cada uno, no se
duplica la regla en cada modelo.

## Elemento nuevo (no persistido): parámetro `reason` en la excepción de corrección

Cuando Talento/superusuario corrige un registro de un periodo Cerrado, la
vista/formulario correspondiente exige un campo de texto `reason` (motivo),
no persistido como columna propia del modelo: se pasa como
`instance._change_reason = reason` antes de `save()`, y
`django-simple-history` lo guarda en la columna `history_change_reason` de la
fila histórica generada por ese `save()`. No requiere migración adicional —
esa columna ya existe en toda tabla `Historical*`.

## Resumen de migraciones nuevas

1. `apps.catalog`: `AddConstraint` — `unique_open_period` sobre `EvaluationPeriod`.
2. `apps.evaluations`: agregar `HistoricalRecords` a `FinalScore` (crea `HistoricalFinalScore`).

Ninguna migración de datos (`RunPython`) es necesaria: FR-004 establece
explícitamente que la continuidad no se valida retroactivamente, así que no
hay que corregir periodos históricos existentes como parte del despliegue.
