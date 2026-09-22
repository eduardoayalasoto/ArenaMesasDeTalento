# Quickstart: Ciclo de vida y continuidad de Periodos de Evaluación

Guía de validación manual/exploratoria una vez implementada la feature.
Referencia `data-model.md` para el esquema y `spec.md` para el detalle de
cada requisito (FR-xxx).

## Prerrequisitos

- Entorno local con `python manage.py migrate` aplicado (incluye las 2
  migraciones nuevas: `unique_open_period` y `HistoricalFinalScore`).
- Un usuario con rol Talento/admin (`request.user.is_admin`).
- Un usuario colaborador normal (sin rol admin) con al menos un registro de
  retroalimentación existente.

## Escenario 1 — Un solo periodo Abierto (FR-001/FR-002)

1. Crear dos periodos vía `catalog:period_create`, ambos con `status=Planeado`.
2. Abrir el primero (acción "Abrir").
3. Intentar abrir el segundo mientras el primero sigue Abierto.
4. **Esperado**: el sistema rechaza la operación e indica cuál periodo debe
   cerrarse primero. `EvaluationPeriod.objects.filter(status="ABIERTO").count()` nunca es mayor a 1.

## Escenario 2 — Continuidad sin huecos ni traslapes (FR-003/FR-004)

1. Crear un periodo "2026-S1" con `start_date=2026-01-01`, `end_date=2026-06-30`.
2. Intentar crear un periodo con `start_date=2026-07-05` (hueco de 4 días).
3. **Esperado**: rechazado, con mensaje explicando el hueco.
4. Crear un periodo con `start_date=2026-07-01` (contiguo).
5. **Esperado**: aceptado.
6. (Verificación de FR-004) Un periodo histórico previo a esta feature con
   fechas no contiguas a otro no debe fallar validación alguna al solo
   consultarse (sin editarse).

## Escenario 3 — Cierre abre el siguiente automáticamente (FR-005)

1. Con "2026-S1" Abierto y "2026-S2" Planeado (contiguo), ejecutar la acción
   "Cerrar periodo" sobre "2026-S1".
2. **Esperado**: en la misma operación, "2026-S1" queda Cerrado y "2026-S2"
   queda Abierto. En ningún momento intermedio hay 0 ni 2 periodos Abiertos.
3. Repetir el cierre de un periodo Abierto que **no** tenga un Planeado
   contiguo creado.
4. **Esperado**: el cierre se rechaza, indicando que falta crear el periodo
   siguiente.

## Escenario 4 — Bloqueo de creación sin periodo Abierto (FR-008/FR-009)

1. Dejar el sistema sin ningún periodo en estatus Abierto (todos Cerrados o
   Planeados).
2. Como líder de proyecto, intentar capturar una Entrega de Valor
   (`evaluations:value_delivery_capture`).
3. **Esperado**: mensaje claro de "no hay un periodo activo", sin excepción
   no controlada ni registro creado con `period=None`.

## Escenario 5 — Inmutabilidad con excepción auditada (FR-006)

1. Con "2026-S1" ya Cerrado, como colaborador normal, intentar editar una
   `TalentSessionNote` o `ValueDeliveryEvaluation` de ese periodo.
2. **Esperado**: rechazado; el dato solo se muestra en modo consulta.
3. Como Talento/admin, repetir la edición.
4. **Esperado**: el sistema exige un motivo (`reason`) antes de guardar; tras
   guardar, `HistoricalXxx.objects.filter(id=record.pk).latest("history_date").history_change_reason`
   contiene el motivo capturado.

## Escenario 6 — Histórico de solo lectura (FR-007/FR-015/FR-017)

1. Como el colaborador dueño de datos en "2026-S1" (Cerrado), consultar su
   listado de retroalimentación.
2. **Esperado**: ve sus acuerdos/calificaciones de "2026-S1" marcados como
   solo lectura, y los de "2026-S2" (Abierto) marcados como operables.
3. Como Talento/Lead/Director, consultar el panel/dashboard de un periodo
   Cerrado.
4. **Esperado**: acceso de solo lectura a la información agregada de ese
   periodo, sin necesidad de que el visor sea el dueño del dato.

## Verificación de regresión

- Ejecutar `pytest apps/core/tests/` completo — en particular
  `test_final_flow.py`, `test_value_delivery_flow.py`,
  `test_ownership_flow.py`, `test_talent_mesa_progress.py` y
  `test_feedback_session.py`, que hoy dependen de crear registros contra un
  periodo Abierto y no deben romperse por el nuevo constraint ni por las
  nuevas validaciones de `clean()`.
