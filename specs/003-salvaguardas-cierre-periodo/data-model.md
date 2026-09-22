# Data Model: Salvaguardas de UX y completitud de datos para el cierre/apertura de Periodos de Evaluación

Sin migraciones ni cambios de esquema. Esta feature es de interfaz y de dos
funciones de solo lectura nuevas sobre modelos ya existentes.

## Funciones nuevas en `apps/core/services/period_lifecycle.py`

### `pending_activity_counts(period) -> dict`

Sin efectos secundarios. Replica las queries que hoy calcula
`dashboards.period_progress` inline:

| Clave | Significado |
|---|---|
| `own_total` | `OwnershipEvaluation.objects.filter(period=period).count()` |
| `own_submitted` | ídem con `status=ENVIADA` |
| `vd_total` | `ValueDeliveryEvaluation.objects.filter(period=period).count()` |
| `vd_validated` | ídem con `status=VALIDADA` |
| `finals_total` | `FinalScore.objects.filter(period=period).count()` |
| `finals_complete` | ídem con `is_complete=True` |

Se usa desde:
- `apps.dashboards.views.period_progress` (reemplaza las queries inline).
- `apps.catalog.views.period_admin` (para armar el texto del `confirm()` de
  cierre del periodo Abierto).

### `resolve_requested_period(request, *, fallback=None) -> EvaluationPeriod | None`

Sin efectos secundarios. Lee `request.GET.get("periodo")`; si es un id
válido de `EvaluationPeriod`, lo retorna (sin filtrar por estatus — puede
ser Planeado/Abierto/Cerrado); si no viene o no existe, retorna `fallback()`
si se da como callable, o `None`. Reemplaza la lógica hoy duplicada como
`_resolve_period` en `apps/dashboards/views.py` (que queda como un
envoltorio de una línea sobre esta función, con `fallback=_open_period`).

Se usa desde:
- `apps.dashboards.views._resolve_period` (ya existente, ahora delegando).
- `apps.evaluations.views.ownership_list`, `ownership_validation`,
  `value_delivery_list`, `value_delivery_capture` (nuevo uso).

## Cambios de view-model (contexto de plantilla), sin nuevos campos de modelo

| Vista | Campo de contexto nuevo | Uso |
|---|---|---|
| `catalog.period_admin` | `next_period_name` y `pending` (dict de `pending_activity_counts`) por la fila del periodo Abierto | Construir el texto del `confirm()` de cierre (FR-004/FR-005/FR-006/FR-008) |
| `evaluations._render_ownership` | `can_correct_closed` (`evaluation.period.is_closed and permissions.is_period_correction_allowed(viewer)`) | Mostrar el input de motivo y habilitar edición pese a `is_submitted`/periodo Cerrado |
| `evaluations._render_ownership` | `can_reset` ahora incluye `and not evaluation.period.is_closed` | Ocultar "Reiniciar" sobre un periodo Cerrado (FR-011a) |
| `evaluations.ownership_list`/`ownership_validation` | `period` (resuelto, no siempre Abierto) + `periods` (todos, para el selector) | Selector de periodo, igual que `feedback_session_list` en 002 |
| `evaluations.value_delivery_list`/`value_delivery_capture` | ídem | ídem; en `value_delivery_capture`, si el periodo resuelto es Cerrado, la VD se busca con `.filter(...).first()` (sin crear), nunca con `get_or_create_vd` |
| `evaluations.value_delivery_review` (por tarjeta) | `vd.period.is_closed` y el permiso del viewer, evaluados en el template | Mostrar el input de motivo en los 3 formularios de cada tarjeta (validar/rechazar/comentar) |

## Parámetro nuevo (no persistido): `reason`

Igual que en 002: se lee de `request.POST.get("reason")` (formularios
planos) o del payload JSON (`ownership_autosave`), se pasa a
`period_lifecycle.assert_record_editable(record, actor, reason)`, que ya
existe sin cambios desde 002. No requiere columna nueva — se audita vía
`history_change_reason` de `django-simple-history`, como ya documentó
002/data-model.md.

## Sin cambios

- No se modifica ningún modelo (`EvaluationPeriod`, `OwnershipEvaluation`,
  `ValueDeliveryEvaluation`, `FinalScore`, etc.).
- No se modifica `period_lifecycle.open_period`, `close_and_open_next` ni
  `assert_record_editable` (solo se agregan las 2 funciones nuevas descritas
  arriba, ambas de solo lectura).
- No se modifica `ownership_flow.py` ni `value_delivery_flow.py` (ya
  aceptan `actor`/`reason` desde 002).
