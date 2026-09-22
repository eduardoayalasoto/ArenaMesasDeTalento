# Research: Salvaguardas de UX y completitud de datos para el cierre/apertura de Periodos de Evaluación

No quedó ningún `NEEDS CLARIFICATION` sin resolver en `spec.md` (FR-008 ya
se decidió con el usuario). Este documento resuelve las decisiones técnicas
para implementar los 3 requisitos reutilizando el motor de 002.

## Decisión 1: Confirmación de Abrir/Cerrar (US1)

- **Decisión**: `onclick="return confirm('...')"` en los botones "Abrir"/"Cerrar"
  de `templates/catalog/period_admin.html`, mismo patrón que ya usa el botón
  "Eliminar periodo" en esa misma plantilla. El texto se arma en Django
  (interpolando `p.name`, y para "Cerrar" también el nombre del periodo
  siguiente y los conteos de FR-005/FR-008), escapado con el filtro
  `escapejs` para evitar romper la cadena JS si un nombre de periodo llegara
  a contener comillas.
- **Rationale**: consistencia visual y de patrón con el resto del proyecto;
  cero dependencias nuevas (sin librería de modales). El usuario ya
  descartó explícitamente una pantalla/modal intermedia (ver FR-008).
- **Alternativas consideradas**: modal propio con Alpine.js (como ya usa
  `ownership_fill.html` para reabrir/reiniciar) — más rico visualmente, pero
  el usuario pidió explícitamente el `confirm()` simple; se documenta como
  posible mejora futura si el equipo quiere una confirmación más visual.

## Decisión 2: Conteos de actividad pendiente compartidos (US2)

- **Decisión**: nueva función `period_lifecycle.pending_activity_counts(period)`
  que replica exactamente las queries que hoy están inline en
  `apps/dashboards/views.py::period_progress` (líneas ~648-662):
  `OwnershipEvaluation`/`ValueDeliveryEvaluation`/`FinalScore` filtradas por
  `period`, con sus conteos totales y de completadas. `period_progress` se
  refactoriza para llamarla en vez de repetir las queries; `period_admin`
  la llama para el periodo Abierto (el único que se puede cerrar) al
  construir el contexto de la fila.
- **Rationale**: evita la disyuntiva "duplicar consultas" vs. "hacer que
  `apps.catalog` dependa de `apps.dashboards`" — ambas opciones violarían
  el principio de capa de services ya establecido por 002. `apps.core.services`
  es el lugar neutral del que ya dependen las tres apps involucradas.
- **Alternativas consideradas**: exponer la función en `apps/core/services/final_flow.py`
  (donde ya vive `recompute_final_score`) — se descartó porque
  `period_lifecycle.py` es más descriptivo del propósito (información sobre
  el periodo, no sobre el cálculo de una calificación) y ya es el punto de
  entrada natural para todo lo relacionado con el ciclo de vida del periodo.

## Decisión 3: Campo de motivo — patrón de UI (US3)

- **Decisión**: reutilizar exactamente el patrón ya implementado en
  `templates/dashboards/feedback_session_detail.html` (002): un input de
  texto `name="reason"`, mostrado solo cuando
  `record.period.is_closed and permissions.is_period_correction_allowed(viewer)`,
  obligatorio (`required`) en ese caso. En `ownership_fill.html`, que usa
  Alpine.js para sus modales de reabrir/reiniciar/cerrar (a diferencia del
  patrón de formularios planos de `feedback_session_detail.html`), el input
  se integra como un campo `x-model` más dentro del estado Alpine ya
  existente (`ownershipForm`), y se envía también en el `fetch()` de
  autosave de respuestas (como parte del JSON, no de `request.POST`).
- **Rationale**: consistencia de patrón ya validado en 002, sin introducir
  un tercer enfoque de UI para el mismo concepto.
- **Hallazgo de código**: `ownership_autosave` (`apps/evaluations/views.py`)
  ya llama a `period_lifecycle.assert_record_editable(evaluation, request.user)`
  sin pasar `reason` (lo agregó 002, sin UI todavía). Debe leer
  `payload.get("reason")` del cuerpo JSON, después de parsear el payload
  (hoy la llamada ocurre antes de `json.loads`; hay que reordenar).

## Decisión 4: Reachability — sin navegación histórica, el motivo es inalcanzable

- **Hallazgo de código** (verificado leyendo los archivos reales, no de
  memoria): `ownership_list`, `ownership_validation` y `value_delivery_list`
  calculan siempre `period = _open_period()`; `value_delivery_capture`
  resuelve siempre `period = period_lifecycle.require_open_period()` en cada
  solicitud. Ninguna de las cuatro permite ver ni operar sobre un periodo
  distinto al Abierto vigente. `_render_ownership` (usada por
  `ownership_view`/`ownership_edit`) sí busca la evaluación solo por `pk`,
  sin filtrar por periodo — es alcanzable con una URL directa, pero nada en
  la interfaz ofrece esa URL para un periodo ya Cerrado.
- **Decisión**: extraer el helper `_resolve_period` (hoy vive solo en
  `apps/dashboards/views.py`, introducido por 002) a
  `period_lifecycle.resolve_requested_period(request)`, y usarlo en
  `ownership_list`, `ownership_validation` y `value_delivery_list` (agregando
  un selector de periodo igual al de `feedback_session_list`) y en
  `value_delivery_capture` (para poder *consultar* una VD de un periodo
  Cerrado). `apps/dashboards/views.py::_resolve_period` pasa a ser un
  envoltorio de una línea sobre la función compartida, para no duplicar la
  lógica una tercera vez.
- **Hallazgo de código adicional (bug latente, no introducido por esta
  feature, pero relevante para no empeorarlo)**: `value_delivery_capture`
  llama a `value_delivery_flow.get_or_create_vd(project, period, ...)` con
  el periodo recién resuelto. Si se resuelve el periodo Abierto (caso
  normal, sin `?periodo=`), el comportamiento no cambia. Si se solicita
  explícitamente un periodo Cerrado vía `?periodo=<id>`, la vista NO debe
  usar `get_or_create_vd` (crearía una VD nueva en un periodo Cerrado,
  violando la inmutabilidad de 002) — debe hacer un `filter(...).first()` de
  solo lectura y, si no existe, mostrar que no hay Entrega de Valor
  capturada ese periodo, en vez de crear una.
- **Alternativas consideradas**: no tocar estas vistas y dejar el campo de
  motivo sin uso real — rechazada porque contradice el objetivo explícito
  de esta feature (que la excepción de corrección sea utilizable en la
  práctica, no solo en el backend).

## Decisión 5: Excepción de corrección real sobre registros ya "cerrados por su propio estatus"

- **Hallazgo de código** (encontrado en `/speckit-analyze`, verificado
  leyendo `apps/evaluations/views.py`): el campo de motivo por sí solo no
  habilita nada. `_can_edit_answers`/`_can_complement` retornan `False`
  incondicionalmente cuando `evaluation.is_submitted` es `True` (el estado
  normal de una evaluación de Ownership en un periodo ya Cerrado), sin
  ninguna excepción. Lo mismo en Entrega de Valor:
  `templates/evaluations/_vd_criterion.html` deshabilita los campos con
  `disabled == 'VALIDADA'` sin mirar el periodo, y
  `apps/evaluations/views.py::value_delivery_capture` solo procesa el POST
  cuando `vd.status != 'VALIDADA'` (ni siquiera renderiza un botón de guardar
  si ya está validada). Sin resolver esto, el campo de motivo se mostraría
  pero la corrección seguiría siendo imposible en la práctica.
- **Decisión**: agregar una rama de excepción explícita, evaluada *antes*
  del chequeo de estatus propio del registro, en las 4 funciones/vistas
  afectadas: `_can_edit_answers`, `_can_complement`
  (`apps/evaluations/views.py`), y en `value_delivery_capture` +
  `_vd_criterion.html`/`value_delivery_capture.html`. La rama de corrección
  guarda los datos y recalcula el score/calificación correspondiente, pero
  **no** reabre el flujo normal de cierre/envío a validación (no debe volver
  a poner `EN_VALIDACION` una Entrega de Valor ya `VALIDADA`, ni re-disparar
  `close_ownership_evaluation` sobre una evaluación ya `ENVIADA`).
- **Rationale**: mantiene la garantía de 002 (un registro de periodo Cerrado
  solo cambia mediante la excepción auditada, nunca mediante los flujos
  normales de negocio) mientras hace que esa excepción sea genuinamente
  utilizable, que es el objetivo completo de esta spec 003.

## Decisión 6b: `value_delivery_review.html` no recibe el campo de motivo

- **Decisión**: no se agrega el input de motivo a
  `templates/evaluations/value_delivery_review.html`. Se documenta en vez
  de implementarlo.
- **Rationale**: la cola de ese template siempre filtra
  `ValueDeliveryEvaluation.objects.filter(period=period, status=EN_VALIDACION)`
  con `period = _open_period()` (sin cambios en esta feature): una VD de un
  periodo Cerrado nunca aparece en esa lista, así que el campo jamás se
  renderizaría bajo navegación normal — sería código muerto. El guardado en
  sí sigue protegido (`validate_vd`/`reject_vd`/`save_vd_comment` ya llaman
  `assert_record_editable` desde 002) para el caso residual de un POST directo
  por pk sobre un registro que se cerró después de cargar la página; ese caso
  ya se rechaza con un mensaje de error claro, solo que sin una forma de
  capturar el motivo desde esta pantalla en particular. Mismo criterio que
  `ArenaImpactScore` en 002: no se agrega UI para un camino inalcanzable.
- **Alternativa considerada**: extender la cola para listar también periodos
  Cerrados — rechazada por alcance: el punto de navegación histórica para
  Entrega de Valor ya lo resuelve `value_delivery_list` → `value_delivery_capture`
  (T015-T017), que es la pantalla del Responsable, no la del Validador.

## Decisión 6: Exclusión de "Reiniciar" en periodo Cerrado (FR-011a)

- **Decisión**: en `_render_ownership` (`apps/evaluations/views.py`),
  `can_reset` pasa de `request.user.is_admin` a
  `request.user.is_admin and not evaluation.period.is_closed`. El bloque de
  "Reiniciar" en `ownership_fill.html` ya está condicionado a `can_reset`,
  así que desaparece automáticamente sin tocar el template.
- **Rationale**: `reset_ownership_evaluation` hace `evaluation.delete()`
  (`apps/core/services/ownership_flow.py`) — es una eliminación total, no
  una corrección. Permitirla sobre un periodo Cerrado (incluso con motivo)
  destruiría la referencia histórica que 002 (FR-006) existe para proteger.
  No se le agrega un campo de motivo: se bloquea directamente, sin
  excepción, igual que ya decidió `spec.md` (FR-011a).
