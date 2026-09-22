# Quickstart: Salvaguardas de UX y completitud de datos para el cierre/apertura de Periodos de Evaluación

Guía de validación manual/exploratoria una vez implementada la feature.
Referencia `data-model.md` para las funciones nuevas y `spec.md` para el
detalle de cada requisito (FR-xxx).

## Prerrequisitos

- Migraciones y datos de 002-ciclo-vida-periodos ya aplicados.
- Un usuario Talento/admin.
- Un periodo Abierto con al menos una evaluación de Ownership sin enviar y
  una Entrega de Valor sin validar (para el Escenario 2).

## Escenario 1 — Confirmación antes de Abrir/Cerrar (FR-001 a FR-004)

1. En `/catalogo/periodos/`, clic en "Cerrar" sobre el periodo Abierto y **cancelar** el diálogo.
2. **Esperado**: el periodo sigue Abierto; nada cambió.
3. Repetir con "Abrir" sobre un periodo Planeado, cancelando.
4. **Esperado**: el periodo sigue Planeado.
5. Clic en "Cerrar" y **confirmar**.
6. **Esperado**: el texto de confirmación mencionó el nombre del periodo siguiente (si existía uno contiguo Planeado); el resultado del cierre es idéntico al de 002 (cierra y abre automáticamente).

## Escenario 2 — Resumen de actividad pendiente al cerrar (FR-005 a FR-008)

1. Con evaluaciones de Ownership sin enviar y Entregas de Valor sin validar en el periodo Abierto, clic en "Cerrar".
2. **Esperado**: el texto del `confirm()` incluye los conteos (p. ej. "3 evaluaciones de Ownership sin enviar, 2 Entregas de Valor sin validar, 1 calificación incompleta").
3. Completar toda la actividad pendiente y repetir el cierre de un periodo distinto sin pendientes.
4. **Esperado**: el texto indica explícitamente que no hay actividad pendiente.
5. Confirmar el cierre con pendientes aún abiertos.
6. **Esperado**: el cierre procede igual (el aviso no bloquea).

## Escenario 3 — Motivo y navegación histórica en Ownership (FR-009, FR-011, FR-011a, FR-013, Acceptance Scenario 5 de US3)

1. Cerrar un periodo con una evaluación de Ownership sin enviar.
2. Como Talento, ir a `evaluations:ownership_list` (o `ownership_validation`) y usar el selector de periodo para elegir el periodo recién Cerrado.
3. Abrir esa evaluación.
4. **Esperado**: aparece el campo de motivo, obligatorio para guardar, reabrir o autoguardar respuestas; el botón "Reiniciar" no aparece.
5. Guardar sin motivo.
6. **Esperado**: rechazado con el mensaje ya existente ("Debes capturar un motivo...").
7. Guardar con motivo.
8. **Esperado**: el cambio se guarda y el motivo queda en el historial (`history_change_reason`).
9. Repetir sin ser Talento/superusuario.
10. **Esperado**: la evaluación se ve en solo lectura, sin campo de motivo.

## Escenario 4 — Motivo en Entrega de Valor (FR-010, FR-011)

1. Con el mismo periodo Cerrado, ir a `evaluations:value_delivery_list` como Talento, elegir el periodo Cerrado y entrar a una Entrega de Valor existente.
2. **Esperado**: se ve la Entrega de Valor ya capturada (sin crear una nueva), con el campo de motivo.
3. Repetir el flujo de "sin motivo → rechazado" / "con motivo → guardado y auditado" en `value_delivery_review` (validar/rechazar/comentar).

## Verificación de regresión

- Ejecutar `pytest apps/core/tests/test_period_lifecycle.py` completo — no debe romperse ninguno de los 30 tests de 002.
- Ejecutar `pytest apps/core/tests/` completo — en particular `test_ownership_flow.py`, `test_value_delivery_flow.py`, `test_view_permissions.py` (por los cambios en `ownership_list`/`value_delivery_list`) y `test_final_flow.py`.
