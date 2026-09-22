# Research: Ciclo de vida y continuidad de Periodos de Evaluación

No quedaron marcadores `NEEDS CLARIFICATION` en el Technical Context del plan
(el stack ya está fijado por el proyecto existente). Este documento resuelve,
en cambio, las decisiones de diseño técnico necesarias para implementar las
reglas de negocio de `spec.md` reutilizando los patrones ya presentes en el
código.

## Decisión 1: Unicidad de periodo Abierto (FR-001/FR-002)

- **Decisión**: `UniqueConstraint` parcial en `EvaluationPeriod`:
  `models.UniqueConstraint(fields=["status"], condition=models.Q(status="ABIERTO"), name="unique_open_period")`.
- **Rationale**: el proyecto ya usa exactamente este patrón para una regla de
  negocio equivalente —"solo una versión Publicada por (kind, area, level)"—
  en `QuestionnaireTemplate.Meta.constraints` (`unique_published_template`,
  `apps/questionnaires/models.py:134-138`). Un constraint a nivel de base de
  datos protege la invariante incluso ante bypasses de la capa de aplicación
  (Django admin, `manage.py shell`, comandos de management, fixtures de
  import), algo que una validación solo en `clean()`/vista no garantiza.
- **Alternativas consideradas**:
  - Validar solo en `clean()`/vista — rechazada: no protege contra escritura
    directa vía admin o shell, que sí existe hoy (`EvaluationPeriodAdmin`
    permite editar `status` libremente).
  - Modelo "singleton" separado que apunte al periodo activo — rechazada:
    sobreingeniería; el constraint parcial ya resuelve el problema con el
    patrón que el proyecto ya conoce y usa.

## Decisión 2: Continuidad sin huecos/traslapes (FR-003/FR-004)

- **Decisión**: validación en `EvaluationPeriod.clean()`, comparando
  `start_date`/`end_date` contra el periodo inmediato anterior y el
  inmediato siguiente (por fecha), disparada por `PeriodForm` vía
  `ModelForm.full_clean()` (ya ocurre automáticamente, sin cambios de forma).
  Aplica solo a periodos creados/editados a partir de esta funcionalidad
  (FR-004): la validación se ejecuta hacia adelante desde que se despliega,
  sin backfill de datos históricos.
- **Rationale**: mismo patrón que `ValueDeliveryEvaluation.clean()`
  (`apps/evaluations/models.py:185-190`) y `ScaleOption.clean()`
  (`apps/questionnaires/models.py:148-150`): reglas de negocio que dependen
  de más de un campo, o de comparar contra otros registros, viven en
  `clean()`, no en constraints de columna única.
- **Alternativas consideradas**:
  - `EXCLUDE USING gist` sobre `daterange(start_date, end_date)` en Postgres
    — más robusto a nivel de base de datos, pero SQLite (usado en dev y en
    la suite de `pytest`) no soporta exclusion constraints; adoptarlo
    rompería el entorno de tests actual o forzaría a correr tests contra
    Postgres, un cambio de infraestructura fuera del alcance de esta feature.
    Queda documentado como mejora futura opcional si el proyecto migra a
    Postgres-only en tests.
  - Validación solo al cerrar/abrir (no al crear/editar el periodo) —
    rechazada: dejaría crear periodos Planeados inconsistentes que solo
    fallarían más tarde, en el momento de apertura automática (Decisión 3),
    un mensaje de error menos útil y más tardío para Talento.

## Decisión 3: Cierre + apertura automática atómica (FR-005)

- **Decisión**: nueva función `period_lifecycle.close_and_open_next(period, actor)`
  en `apps/core/services/period_lifecycle.py`, envuelta en
  `transaction.atomic()`:
  1. Busca el periodo Planeado con `start_date == period.end_date + 1 día`.
  2. Si no existe, levanta `ValidationError` sin tocar nada (FR-005, caso de
     rechazo del cierre).
  3. Si existe, en la misma transacción: `period.status = CERRADO` +
     `next_period.status = ABIERTO`, ambos `save()`.
- **Rationale**: el proyecto ya concentra la orquestación de flujos de
  negocio con efectos colaterales en módulos de `apps/core/services/`
  (`ownership_flow.py`, `value_delivery_flow.py`, `final_flow.py`), nunca en
  señales de Django ni directamente en las vistas. `close_and_open_next` es
  el mismo tipo de función que, por ejemplo,
  `ownership_flow.reopen_ownership_evaluation`. Envolver en una transacción
  atómica es necesario porque el constraint parcial de Decisión 1 exige que
  nunca haya dos filas con `status=ABIERTO` simultáneamente: cerrar primero y
  abrir después (en ese orden, dentro de la misma transacción) evita
  cualquier violación intermedia del constraint.
- **Alternativas consideradas**:
  - Señal `post_save` en `EvaluationPeriod` que dispare la apertura del
    siguiente — rechazada: dispersaría la lógica de negocio fuera de la capa
    de services ya establecida, dificultando pruebas y trazabilidad.
  - Tarea programada (cron/celery) que abra el siguiente periodo por fecha
    — rechazada: el proyecto no tiene infraestructura de tareas en segundo
    plano hoy, y la spec pide que el cierre y la apertura ocurran en la
    misma operación (Q1 de clarificación, respondida como "apertura
    automática").

## Decisión 4: Inmutabilidad con excepción auditada (FR-006)

- **Decisión**: `period_lifecycle.assert_record_editable(record, actor)`,
  reutilizado desde cada punto de guardado existente (`ownership_flow.py`,
  `value_delivery_flow.py`, y las vistas de `ArenaImpactScore`,
  `TalentSessionNote`, `MesaProjectReview`, `FinalScore`). Si
  `record.period.is_closed` (propiedad ya existente en `EvaluationPeriod`) y
  `actor` no cumple `permissions.is_period_correction_allowed(actor)`
  (Talento/superusuario), levanta `PermissionDenied`. Si sí cumple, exige un
  `reason` no vacío y lo asigna a `record._change_reason` antes de
  `record.save()`, aprovechando el soporte nativo de `django-simple-history`
  para persistir el motivo en la fila histórica correspondiente (columna
  `history_change_reason`, ya presente en toda tabla `Historical*` generada
  por `HistoricalRecords`).
- **Rationale**: no requiere modelo de auditoría nuevo — los 6 modelos
  afectados usan (o deben usar, ver hallazgo abajo) `HistoricalRecords`, que
  ya registra `history_user`, `history_date` y ahora también
  `history_change_reason` por cada `save()`. Este es el mismo mecanismo que
  ya resolvió un requisito de auditoría equivalente en la feature
  `001-retroalimentacion-superusuario-talento` (ver su `data-model.md`,
  sección "Nota de auditoría").
- **Hallazgo de código**: `FinalScore` (`apps/evaluations/models.py:224-251`)
  es el único de los 6 modelos con FK a `EvaluationPeriod` que **no** tiene
  `history = HistoricalRecords()`. Los otros cinco
  (`OwnershipEvaluation`, `ValueDeliveryEvaluation`, `ArenaImpactScore`,
  `TalentSessionNote`, `MesaProjectReview`) sí lo tienen. Esta feature debe
  agregarlo (con su migración) para que la excepción auditada de FR-006
  también cubra correcciones a la calificación final.
- **Alternativas consideradas**:
  - Modelo `PeriodCorrectionLog` dedicado — rechazada: duplicaría lo que
    `simple_history` ya resuelve para los demás campos y modelos del
    proyecto; añadiría una tabla y una vista de auditoría paralelas sin
    beneficio claro sobre extender la cobertura de `HistoricalRecords`.

## Decisión 5: Bloqueo de creación sin periodo Abierto (FR-008/FR-009)

- **Decisión**: los puntos de entrada de creación ya usan (o deben empezar a
  usar) el helper `_open_period()` existente
  (`apps/evaluations/views.py:34`: `EvaluationPeriod.objects.filter(status=ABIERTO).first()`).
  Se agrega una validación explícita inmediatamente después: si
  `period is None`, la vista debe responder con un mensaje claro ("no hay un
  periodo activo") en vez de continuar el flujo de creación.
- **Rationale / hallazgo de código**: hoy, si no hay periodo Abierto,
  `_open_period()` devuelve `None` y algunos flujos igual intentan crear el
  registro con `period=None` (p. ej. `value_delivery_capture` llama
  `value_delivery_flow.get_or_create_vd(project, period, ...)` sin comprobar
  `period` primero). Como el campo `period` de estos modelos no admite nulos,
  esto hoy terminaría en un `IntegrityError` de base de datos sin manejar,
  no en el mensaje de negocio claro que pide FR-009. Esta feature cierra ese
  gap explícitamente en cada punto de entrada, no solo en el nuevo código.
- **Alternativas consideradas**: middleware global que bloquee cualquier
  POST si no hay periodo Abierto — rechazada: demasiado amplio (afectaría
  vistas no relacionadas con retroalimentación, como administración de
  catálogos) frente a validar en cada punto de entrada de creación ya
  identificado.

## Decisión 6: Roles con excepción de corrección y acceso a reportes (FR-006/FR-017)

- **Decisión**: reutilizar los helpers de rol ya existentes en
  `apps/core/services/permissions.py` y en `request.user`
  (`is_admin`, `is_lead`, `is_director`, ya usados por ejemplo en
  `apps/dashboards/views.py:period_progress` y `talent_person` para acotar
  acceso a Talento/Dirección). Se agrega
  `permissions.is_period_correction_allowed(user)` como una función nueva de
  ese mismo módulo, no un sistema de permisos paralelo.
- **Rationale**: consistencia con el resto del proyecto, que centraliza toda
  decisión de autorización en `apps/core/services/permissions.py` (ver
  `001-retroalimentacion-superusuario-talento/plan.md`, que documenta este
  mismo principio de facto).
