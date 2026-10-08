# Avance del periodo — listado de personas con pendientes

Fecha: 2026-07-09

## Contexto

`avance-periodo/` (`dashboards:period_progress`) hoy solo muestra 3 tarjetas
con totales globales del periodo abierto: Ownership enviadas, Entrega de
Valor validadas, Calificaciones completas. Talento necesita ver, además,
**quién específicamente tiene pendientes** para poder darles seguimiento,
sin tener que adivinar a partir de los totales agregados.

## Objetivo

Agregar debajo de las tarjetas existentes una tabla con las personas que
tienen algo pendiente en el periodo abierto, con el detalle de qué les
falta, ordenadas de quien tiene más pendientes a quien tiene menos. Las
personas que ya están 100% completas (incluida la retroalimentación) no
aparecen en la tabla.

## Qué cuenta como "pendiente" por persona

Para cada usuario activo, no superusuario, en el periodo abierto:

1. **Ownership propia** — una autoevaluación esperada por cada membresía de
   proyecto activo (`ProjectMembership` con `project.is_active=True`), o la
   autoevaluación transversal (`project=None`) si la persona es Lead
   (`is_lead`). Pendiente si no existe la `OwnershipEvaluation` o su
   `status != ENVIADA`.
2. **Entrega de Valor (captura)** — proyectos activos donde
   `project.responsable == persona`. Pendiente si no existe
   `ValueDeliveryEvaluation` para ese proyecto/periodo o su
   `status == BORRADOR`.
3. **Validación** — proyectos activos donde `project.validador == persona`.
   Pendiente si existe `ValueDeliveryEvaluation` con
   `status == EN_VALIDACION` (ya capturada, esperando su validación).
4. **Retroalimentación** — `TalentSessionNote` del periodo donde la persona
   aparece como `FeedbackResponsible` (principal o secundario). Pendiente
   si `note.feedback_agreed == False`.

Impacto Arena **no** se incluye: lo captura Talento internamente y no es
una tarea delegada a un colaborador o lead.

`total_pendientes` = suma de las 4 categorías. Una persona aparece en la
tabla solo si `total_pendientes > 0`.

## Orden

Tabla única (no agrupada por área). Orden: `total_pendientes` descendente,
luego `full_name` ascendente como desempate. El área se muestra como dato
en cada fila, no como agrupador.

## Datos por fila

- Avatar (foto o iniciales, patrón `partials/avatar.html`), nombre, área,
  nivel.
- Badge "Ownership n/N" si aplica, con tooltip listando los proyectos
  pendientes (o "Autoevaluación transversal" si es el caso Lead).
- Badge "Entrega de Valor: N" si aplica, tooltip con nombres de proyecto.
- Badge "Validación: N" si aplica, tooltip con nombres de proyecto.
- Badge "Retroalimentación: N" si aplica, tooltip con nombres de las
  personas a quienes les falta dar/cerrar retroalimentación.
- Badge de total pendientes al final de la fila (el criterio de orden).
- Enlace "Ver" hacia `dashboards:talent_person` (la vista ya es de acceso
  Talento/Director, coherente con el guard existente de
  `period_progress`).

## UI / estilo

Reutiliza el lenguaje visual de `talent_table.html`: tabla en `.card`,
`thead` gris, filas con hover, mismo patrón de tooltip Alpine
(`x-data="{ open: false }"` + `@mouseenter`/`@mouseleave` + `x-show
x-cloak`) ya usado ahí para "Proyectos" del Lead — no se introduce un
componente de tooltip nuevo, se reutiliza el existente para consistencia.

Se invocará el skill de UX/UI y el de frontend-design durante la
implementación para pulir jerarquía visual, color de badges por severidad
y responsive de la tabla.

## Implementación (alto nivel)

- Nueva función helper en `apps/dashboards/views.py` (o
  `apps/core/services/`), p. ej. `pending_people(period)`, que devuelve la
  lista de dicts `{user, ownership_missing, vd_capture_missing,
  vd_validation_missing, feedback_missing, total}` ya ordenada.
- Se llama desde `period_progress` y se agrega `pending_rows` al contexto.
- Nuevo parcial `templates/dashboards/_pending_people_table.html` incluido
  desde `period_progress.html`.
- Sin cambios de modelo ni migraciones: todo se calcula a partir de datos
  existentes.

## Fuera de alcance

- Filtros de área/nivel en la nueva tabla (no se pidieron).
- Paginación (se asume volumen manejable para una sola empresa/periodo;
  si crece, se puede agregar después).
- Cambios a las 3 tarjetas de totales existentes.
