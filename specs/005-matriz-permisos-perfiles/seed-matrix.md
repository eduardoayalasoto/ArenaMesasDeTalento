# Matriz semilla "deber ser" — para revisión del usuario antes de implementar

**Leyenda de alcance** (cada uno incluye a los anteriores):
- **—** sin acceso
- **P** propio
- **A** asignado: lo propio más donde la persona tiene una relación (evaluador, responsable, validador, aprobador de la etapa, receptor, Lead directo)
- **Ár** su área: lo anterior más las personas de su área
- **T** todos

El **Superusuario** tiene T en todo y no aparece en la tabla.

Las filas marcadas con **⚠** cambian respecto al comportamiento actual del código (FR-011a).

## General

| Permiso (clave) | Pantalla / acción | Colaborador | Lead | Director | Talento |
|---|---|---|---|---|---|
| `dashboard.home.view` | Mi tablero (mis resultados) | P | P | P | P |
| `people.results.view` | Mi área y resultados de otra persona | — ⚠ | Ár | T | T |
| `people.results.export` | Exportar calificaciones (.xlsx) | — ⚠ | Ár | T | T |

*Exentas (siempre accesibles):* ayuda, Mi perfil, cambiar contraseña, foto de usuario, login y logout.

## Evaluaciones

| Permiso | Pantalla / acción | Colaborador | Lead | Director | Talento |
|---|---|---|---|---|---|
| `ownership.self.manage` | Mis evaluaciones: iniciar, responder, elegir evaluadores | P | P | — ⚠ | — ⚠ |
| `ownership.view` | Ver evaluaciones de Ownership | A | Ár | T | T |
| `ownership.validate` | Validación de Ownership: complementar y cerrar | A | A | A | T |
| `ownership.admin` | Reabrir, reiniciar y reiniciar por usuario | — | — | — | T |
| `period.closed.correct` | Corregir registros de periodo Cerrado (con motivo) | — | — | — | T |
| `value_delivery.capture` | Entrega de Valor: lista y captura | A | A | A ⚠ | T |
| `value_delivery.validate` | Validar, regresar y comentar Entrega de Valor | A | A | A | T |
| `arena_impact.edit` | Impacto Arena | — | — | — | T |

## Retroalimentación y Mesa de Talento

| Permiso | Pantalla / acción | Colaborador | Lead | Director | Talento |
|---|---|---|---|---|---|
| `feedback.view` | Retroalimentación: lista y detalle | A | A | A | T |
| `feedback.edit` | Editar y reabrir sesión de retroalimentación | A | A | A | T |
| `talent_table.view` | Mesa de Talento (tabla y ficha) | — | — | T | T |
| `talent_table.edit` | Ficha: notas, escenarios S+1/S+2 y proyectos revisados | — | — | — | T |
| `talent_table.assign_feedback` | Asignar o quitar responsables de retroalimentación | — | — | — | T |
| `current_scenario.view` | Escenario Actual: ver tablero | — | — | T | T |
| `current_scenario.move` | Escenario Actual: mover personas | — | — | T | T |
| `period_progress.view` | Avance del periodo | — | — | — | T |

## Catálogos

| Permiso | Pantalla / acción | Colaborador | Lead | Director | Talento |
|---|---|---|---|---|---|
| `users.manage` | Usuarios: ver, alta, editar área/nivel/rol, Lead directo | — | — | — | T |
| `users.reset_password` | Resetear contraseña | — | — | — | T |
| `users.delete` | Eliminar o desactivar usuario | — | — | — | T |
| `projects.edit` | Proyectos: ver, crear, editar y equipo | — | T | T | T |
| `projects.close` | Cerrar, reabrir y eliminar proyecto | — | — | — | T |
| `periods.manage` | Periodos: alta, edición, abrir, cerrar y borrar | — | — | — | T |
| `areas.manage` | Áreas: Director por área | — | — | — | T |
| `scenarios.manage` | Escenarios | — | — | — | T |
| `questionnaires.manage` | Cuestionarios: editar, versionar y publicar | — | — | — | T |
| `weights.manage` | Ponderaciones *(pantalla pendiente)* | — | — | — | T |
| `access.manage` | **Perfiles y permisos** (nueva): matriz y asignación de perfiles | — | — | — | T |

## Arena Learn

| Permiso | Pantalla / acción | Colaborador | Lead | Director | Talento |
|---|---|---|---|---|---|
| `learn.self` | Mis cursos: solicitar, registrar, editar, cancelar, pago propio, cerrar y reseña | P | P | P | P |
| `learn.public.view` | Catálogo, Personas, perfil y curso públicos | T | T | T | T |
| `learn.private.view` | Datos privados: costo, pago, justificación, comprobante y bitácora | A | A | T | T |
| `learn.approve.lead` | Aprobar cursos, etapa Lead | A | Ár | A | A |
| `learn.approve.direction` | Aprobar cursos, etapa Dirección | — | — | T | — |
| `learn.approve.talento` | Aprobar cursos, etapa Talento | — | — | — | T |
| `learn.all_requests.view` | Ver todas las solicitudes en revisión | — | — | — | T |
| `learn.reassign` | Reasignar aprobador y cancelar autorizadas | — | — | — | T |
| `learn.evidence.validate` | Validar o regresar evidencias | — | — | — | T |
| `learn.catalog.manage` | Catálogo: alta, edición, archivar y promover | — | — | — | T |
| `learn.tracking.view` | Seguimiento: tablero y exporte | — | — | T | T |
| `learn.historic.create` | Carga histórica | — | — | — | T |
| `learn.settings.edit` | Instrucciones fiscales | — | — | — | T |

*Nota:* en `learn.approve.lead`, el alcance **A** corresponde a ser el Lead directo de la persona o el aprobador reasignado. **Ár** corresponde a cualquier Lead del área cuando la persona no tiene Lead directo, igual que hoy. En la etapa Dirección se conserva la preferencia por el Director asignado al área.

## Asignables (quién puede ser elegido en los selectores)

| Permiso | Selector | Colaborador | Lead | Director | Talento |
|---|---|---|---|---|---|
| `assign.ownership_evaluator` | Evaluador de Ownership | T | T | T | T |
| `assign.project_role` | Owner, Responsable, Validador y miembro de proyecto | T | T | T | T |
| `assign.feedback_responsable` | Responsable de retroalimentación | T | T | T | T |
| `assign.direct_lead` | Lead directo | — ⚠ | T | T | — |
| `assign.area_director` | Director de área | — | — | T | — |
| `assign.learn_approver` | Aprobador reasignado (Arena Learn) | — ⚠ | T | T | T |

En los asignables, el valor significa "puede aparecer en el selector": T sí, — no.

## Cambios contra hoy (⚠), que entran en el reporte previo FR-011b

1. **Director:** deja de capturar Entrega de Valor de proyectos donde no es Responsable. Hay 1 caso histórico en producción, que se conserva.
2. **Director y Talento:** "Mis evaluaciones" pasa a sin acceso. Hoy solo se oculta en el menú; la ruta sigue abierta.
3. **Colaborador:** "Mi área", resultados de otra persona y el exporte pasan a sin acceso. Hoy solo veía su propia fila escribiendo la URL.
4. **Asignables:** Lead directo y aprobador reasignado se limitan a Lead, Director y Talento. Hoy aceptan a cualquier usuario. En producción no hay ninguna asignación vigente afectada.

## Asignación inicial en producción (verificado 2026-10-07)

Perfil sugerido por rol y nivel: **51 Colaborador · 4 Lead · 5 Director · 2 Talento**. El superusuario queda aparte. No hay ningún Lead directo asignado, y la única reasignación de Arena Learn apunta a Talento, así que el punto 4 no afecta a nadie.

## Lo que el usuario puede ajustar ya en esta revisión

- ¿Dar a **Lead** Mesa de Talento o Escenario Actual con alcance **Ár** desde el día 1? Hoy no lo tiene.
- ¿Dar a **Lead** `learn.approve.direction` con **Ár**? Hoy no lo tiene.
- ¿**Director** con `talent_table.edit`? Hoy no lo tiene.
