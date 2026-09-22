# Feature Specification: Ciclo de vida y continuidad de Periodos de Evaluación

**Feature Branch**: `002-ciclo-vida-periodos`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Ciclo de vida y continuidad de los Periodos de Evaluación (EvaluationPeriod) como agrupador mayor de retroalimentación. Un único periodo ABIERTO a la vez en todo el sistema; continuidad temporal sin huecos entre periodos; al cerrar un periodo, todos los elementos y componentes de retroalimentación creados durante él quedan fijos como referencia histórica de solo lectura; un colaborador siempre puede consultar en modo histórico sus acuerdos, calificaciones y estatus de periodos pasados; al abrir un nuevo periodo, este ofrece la misma operatividad que los anteriores pero de forma aislada; se mantiene la relación uno a uno entre cada elemento de retroalimentación y su periodo, reforzando que ningún flujo permita asociar un registro a un periodo distinto del ABIERTO vigente."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Un solo periodo activo a la vez (Priority: P1)

Talento (administración) gestiona la apertura y el cierre de los Periodos de Evaluación. En todo momento el sistema garantiza que exista, a lo más, un periodo con estatus Abierto. Talento no puede abrir un periodo nuevo mientras otro siga Abierto: primero debe cerrarse el periodo activo.

**Why this priority**: Es la regla que evita el riesgo central señalado por el negocio: que un registro de retroalimentación pueda confundirse entre dos periodos simultáneos. Sin esta garantía, ninguna otra regla de continuidad o histórico tiene sentido.

**Independent Test**: Puede probarse creando dos periodos y verificando que el sistema rechaza la apertura del segundo mientras el primero siga Abierto, y que sí permite abrirlo una vez cerrado el primero.

**Acceptance Scenarios**:

1. **Given** el periodo "2026-S1" está Abierto, **When** Talento intenta poner en estatus Abierto al periodo "2026-S2", **Then** el sistema rechaza la operación y explica que primero debe cerrarse "2026-S1".
2. **Given** el periodo "2026-S1" está Abierto y "2026-S2" está Planeado con fecha de inicio contigua, **When** Talento cierra "2026-S1", **Then** el sistema abre automáticamente "2026-S2" en la misma operación y en ningún momento existen dos periodos Abiertos simultáneamente ni una ventana sin periodo activo.
3. **Given** el periodo "2026-S1" está Abierto y no existe ningún periodo Planeado con fecha de inicio contigua a su fecha de fin, **When** Talento intenta cerrar "2026-S1", **Then** el sistema rechaza el cierre y advierte que no hay un periodo siguiente disponible para sucederlo.

---

### User Story 2 - Continuidad del calendario sin huecos (Priority: P1)

Talento planifica los periodos futuros de forma que, en conjunto, cubran el año calendario sin dejar días sin asignar y sin traslapar fechas entre periodos.

**Why this priority**: Sin continuidad garantizada, podrían existir fechas "huérfanas" en las que ningún periodo cubre la operación diaria, dejando sin agrupador a la retroalimentación generada en esos días. Es tan crítica como la regla de unicidad porque ambas protegen la misma garantía de integridad.

**Independent Test**: Puede probarse intentando crear o editar un periodo cuya fecha de inicio no sea exactamente el día siguiente a la fecha de fin del periodo anterior (o que se traslape con otro periodo existente) y verificando que el sistema lo rechaza.

**Acceptance Scenarios**:

1. **Given** el periodo "2026-S1" termina el 30 de junio de 2026, **When** Talento crea un periodo "2026-S2" con fecha de inicio 1 de julio de 2026, **Then** el sistema lo acepta por ser contiguo.
2. **Given** el periodo "2026-S1" termina el 30 de junio de 2026, **When** Talento intenta crear un periodo con fecha de inicio 5 de julio de 2026 (dejando un hueco de días sin periodo), **Then** el sistema rechaza la operación y explica el hueco detectado.
3. **Given** el periodo "2026-S1" cubre del 1 de enero al 30 de junio de 2026, **When** Talento intenta crear un periodo con fecha de inicio 15 de junio de 2026 (traslape), **Then** el sistema rechaza la operación por traslape de fechas.

---

### User Story 3 - Histórico de solo lectura para el colaborador (Priority: P2)

Un colaborador puede consultar, en cualquier momento, sus acuerdos de mesas de retroalimentación, sus calificaciones y el estatus de los periodos en los que participó, incluyendo periodos ya cerrados, sin que el periodo actualmente activo se lo impida.

**Why this priority**: Es el valor directo para el colaborador: preserva su historial de desempeño como referencia permanente, aun cuando el sistema haya avanzado a un periodo distinto.

**Independent Test**: Puede probarse cerrando un periodo con datos de un colaborador y verificando que ese colaborador sigue pudiendo ver (pero no editar) esa información después de que se abra el periodo siguiente.

**Acceptance Scenarios**:

1. **Given** el periodo "2025-S2" está Cerrado y el colaborador tiene acuerdos y calificaciones registrados en él, **When** el colaborador consulta su historial, **Then** puede ver esa información marcada como perteneciente a "2025-S2" y con estatus de solo lectura.
2. **Given** el periodo "2026-S1" está Abierto, **When** el colaborador consulta su historial, **Then** ve tanto la información del periodo activo (editable según los flujos vigentes) como la de periodos cerrados anteriores (solo lectura), claramente diferenciadas.

---

### User Story 4 - Cierre de periodo congela los datos como referencia histórica (Priority: P2)

Al cerrar un periodo, todos los elementos y componentes de retroalimentación creados durante ese periodo (entregas de valor, evaluaciones de ownership, notas, acuerdos de mesas de retroalimentación, calificaciones, Arena Impact Score) quedan fijos: pueden consultarse pero ya no editarse.

**Why this priority**: Garantiza que el histórico consultado en la User Story 3 sea confiable e inalterable, y evita que se sigan capturando o corrigiendo datos de un ciclo que el negocio ya dio por cerrado.

**Independent Test**: Puede probarse intentando editar una calificación o un acuerdo de mesa de retroalimentación que pertenece a un periodo Cerrado y verificando que el sistema lo bloquea.

**Acceptance Scenarios**:

1. **Given** una Entrega de Valor pertenece a un periodo que acaba de pasar a Cerrado, **When** un usuario intenta editar su calificación, **Then** el sistema rechaza el cambio e informa que el periodo está cerrado.
2. **Given** un acuerdo de una mesa de retroalimentación pertenece a un periodo Cerrado, **When** un usuario intenta modificarlo o eliminarlo, **Then** el sistema lo impide y solo permite su consulta.

---

### User Story 5 - Nuevo periodo con la misma operatividad, de forma aislada (Priority: P3)

Al abrir un nuevo periodo, los usuarios cuentan con los mismos recursos y flujos de operación que tenían en periodos anteriores (formularios, evaluaciones, mesas de retroalimentación), pero todo lo que se genera queda asociado exclusivamente al periodo recién abierto, sin posibilidad de mezclarse con datos de otro periodo.

**Why this priority**: Es la confirmación de que la operación diaria no se ve degradada por introducir el nuevo agrupador; es de menor prioridad porque depende de que las reglas de las historias P1 ya estén garantizadas.

**Independent Test**: Puede probarse abriendo un periodo nuevo y verificando que todos los flujos existentes (crear entrega de valor, evaluar ownership, generar acuerdos de mesa) siguen disponibles y que los registros nuevos quedan asociados únicamente al periodo recién abierto.

**Acceptance Scenarios**:

1. **Given** se acaba de abrir el periodo "2026-S2", **When** un responsable crea una nueva Entrega de Valor, **Then** el sistema la asocia automáticamente al periodo "2026-S2" sin permitir elegir otro periodo.
2. **Given** existen registros de retroalimentación en el periodo "2026-S1" (ya Cerrado) y en "2026-S2" (Abierto), **When** se audita cualquier registro nuevo, **Then** ninguno aparece asociado simultáneamente a ambos periodos.

---

### Edge Cases

- ¿Qué ocurre si Talento intenta cerrar el único periodo Abierto sin que exista todavía un periodo Planeado contiguo que lo suceda? El sistema debe rechazar el cierre y advertir del hueco resultante (FR-005); Talento debe crear primero el periodo Planeado contiguo.
- ¿Qué ocurre si se intenta eliminar un periodo (Planeado, Abierto o Cerrado) que ya tiene registros de retroalimentación vinculados? Debe impedirse, igual que hoy ocurre para proyectos protegidos.
- ¿Qué ocurre si se intenta editar la fecha de inicio o fin de un periodo Planeado de forma que genere un hueco o un traslape con los periodos adyacentes? Debe rechazarse con el mismo criterio de continuidad usado al crear.
- ¿Qué ocurre si existe más de un periodo Planeado con fecha de inicio contigua al periodo que se está cerrando (dato inconsistente)? No debería ser posible por la validación de continuidad de FR-003, que impide traslapes entre periodos Planeados; el cierre automático (FR-005) debe operar sobre, a lo más, un candidato contiguo.
- ¿Qué ocurre si dos solicitudes de cierre llegan casi al mismo tiempo (condición de carrera)? El sistema debe garantizar que, incluso así, nunca queden dos periodos Abiertos ni un registro se guarde sin un periodo Abierto vigente.
- ¿Qué ocurre si un usuario tiene una captura sin guardar (por ejemplo, un formulario de mesa de retroalimentación abierto en su navegador) en el instante en que Talento cierra el periodo? El intento de guardado posterior debe rechazarse igual que cualquier otra edición sobre un periodo ya cerrado.
- ¿Qué ocurre con los periodos históricos que ya existen hoy en el sistema antes de esta funcionalidad, si sus fechas no son estrictamente contiguas entre sí? No se corrigen ni se bloquean retroactivamente (FR-004); la validación de continuidad solo aplica hacia adelante.
- ¿Qué ocurre si Talento/superusuario corrige un registro de un periodo Cerrado bajo la excepción de FR-006 pero no captura un motivo? El sistema debe exigir el motivo como campo obligatorio antes de permitir guardar la corrección.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE garantizar que exista, en todo momento, a lo más un Periodo de Evaluación con estatus Abierto en todo el sistema.
- **FR-002**: El sistema DEBE rechazar cualquier intento de poner un periodo en estatus Abierto mientras exista otro periodo ya Abierto, indicando cuál es el periodo activo que debe cerrarse primero.
- **FR-003**: El sistema DEBE validar, al crear o editar el rango de fechas (inicio/fin) de un periodo, que dicho rango no se traslape con el de ningún otro periodo existente y que no deje días del calendario sin cobertura entre periodos consecutivos (la fecha de inicio de un periodo debe ser exactamente el día siguiente a la fecha de fin del periodo inmediato anterior).
- **FR-004**: La validación de continuidad de FR-003 DEBE aplicarse únicamente de forma prospectiva: rige para los periodos creados o editados a partir de la entrada en vigor de esta funcionalidad. Los periodos históricos ya existentes no requieren corrección ni reconciliación de fechas y quedan excluidos de esta validación.
- **FR-005**: Cuando un periodo pasa de Abierto a Cerrado, el sistema DEBE abrir automáticamente, en la misma operación, el siguiente periodo Planeado cuya fecha de inicio sea contigua a la fecha de fin del periodo recién cerrado. Si no existe un periodo Planeado contiguo disponible, el sistema DEBE impedir el cierre y advertir del hueco resultante (ver Edge Cases).
- **FR-006**: Una vez que un periodo pasa a estatus Cerrado, el sistema DEBE impedir la edición o eliminación de cualquier elemento o componente de retroalimentación asociado a ese periodo: evaluaciones de Ownership, Entregas de Valor, Arena Impact Score, calificación final, notas y acuerdos de Mesa de Talento (nota y acuerdo de la sesión de retroalimentación son un mismo registro por colaborador-periodo), y las revisiones de comité por proyecto (sign-off de Mesa de Talento por proyecto). Todos quedan disponibles únicamente en modo de consulta para todos los roles, excepto Talento/superusuario. Como excepción, Talento/superusuario puede corregir un registro de un periodo Cerrado; toda corrección de este tipo DEBE quedar registrada en auditoría con usuario, fecha, motivo y el valor anterior y nuevo del dato corregido.
- **FR-007**: El sistema DEBE permitir a cualquier colaborador autorizado consultar, en modo de solo lectura, sus propios acuerdos de mesas de retroalimentación, calificaciones y el estatus del periodo correspondiente, sin importar si ese periodo está Abierto o Cerrado.
- **FR-008**: El sistema DEBE asociar todo elemento o componente de retroalimentación de nueva creación exclusivamente al periodo que tenga estatus Abierto en ese momento.
- **FR-009**: El sistema DEBE bloquear la creación de cualquier elemento o componente de retroalimentación cuando no exista ningún periodo con estatus Abierto, informando al usuario que no hay un periodo activo.
- **FR-010**: El sistema DEBE impedir que cualquier flujo (creación, edición o reasignación) asocie un elemento o componente de retroalimentación a un periodo distinto del que tenía al momento de su creación, o distinto del periodo Abierto vigente en el caso de registros nuevos.
- **FR-011**: El sistema DEBE mantener la relación de uno a uno entre cada elemento o componente de retroalimentación y su periodo (un registro pertenece exactamente a un periodo), sin introducir la posibilidad de que un registro quede asociado a más de un periodo.
- **FR-012**: El sistema DEBE seguir impidiendo la eliminación de un periodo que tenga cualquier elemento o componente de retroalimentación asociado, independientemente de su estatus (Planeado, Abierto o Cerrado).
- **FR-013**: El sistema DEBE impedir modificar la fecha de inicio, la fecha de fin o el tipo de un periodo una vez que su estatus sea Abierto o Cerrado, para proteger la continuidad ya validada; estos campos solo son editables mientras el periodo está en estatus Planeado.
- **FR-014**: El sistema DEBE permitir a Talento (administración) crear periodos futuros en estatus Planeado con antelación, de forma que exista un periodo contiguo disponible para suceder al periodo Abierto vigente cuando este se cierre.
- **FR-015**: El sistema DEBE mostrar de forma diferenciada, en las vistas de consulta de retroalimentación, si un registro pertenece al periodo actualmente Abierto (operable) o a un periodo Cerrado (histórico, solo lectura).
- **FR-016**: El sistema DEBE registrar de forma auditable cada transición de estatus de un periodo (quién la realizó, cuándo, y el estatus anterior y nuevo).
- **FR-017**: El sistema DEBE permitir a los roles con acceso a reportes y paneles de Mesa de Talento (Talento, Leads, Directores) consultar en modo de solo lectura la información agregada de cualquier periodo, esté Abierto o Cerrado, y no solo a la persona dueña del registro.

### Key Entities

- **Periodo de Evaluación**: agrupador temporal mayor de la retroalimentación. Tiene nombre, fecha de inicio, fecha de fin, tipo y estatus (Planeado, Abierto, Cerrado). Reglas clave: a lo más un periodo Abierto en todo el sistema; el conjunto de periodos cubre el calendario sin huecos ni traslapes; una vez Cerrado, los datos que agrupa pasan a ser de solo lectura.
- **Elemento o componente de retroalimentación**: los seis tipos de registro que hoy pertenecen a un Periodo de Evaluación mediante relación uno a uno: evaluación de Ownership, Entrega de Valor, Arena Impact Score, calificación final (resultado consolidado por colaborador-periodo), nota y acuerdo de sesión de Mesa de Talento (un mismo registro por colaborador-periodo: incluye tanto la nota del comité como el acuerdo de desarrollo pactado con el colaborador), y revisión de comité por proyecto (sign-off de Mesa de Talento por colaborador-proyecto-periodo). Todos heredan el estatus operable/histórico de su periodo.
- **Colaborador**: persona evaluada cuyo histórico de acuerdos, calificaciones y estatus de periodos pasados debe permanecer siempre consultable, independientemente del periodo actualmente activo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En el 100% de las verificaciones del estado del sistema, existe exactamente cero o un periodo con estatus Abierto; nunca se observan dos o más periodos Abiertos simultáneamente.
- **SC-002**: Para los periodos creados o editados a partir de la entrada en vigor de esta funcionalidad, el 100% de los días quedan cubiertos por exactamente un periodo, sin huecos ni traslapes (no aplica de forma retroactiva a periodos históricos previos; ver FR-004).
- **SC-003**: El 100% de los intentos de crear un elemento de retroalimentación sin un periodo Abierto vigente son rechazados por el sistema con un mensaje explicativo.
- **SC-004**: El 100% de los intentos de editar o eliminar un elemento de retroalimentación cuyo periodo está Cerrado son rechazados por el sistema.
- **SC-005**: Un colaborador puede localizar y consultar sus acuerdos y calificaciones de cualquier periodo pasado (Cerrado) en el que haya participado, sin restricciones adicionales por el hecho de que exista un periodo distinto actualmente Abierto.
- **SC-006**: Cero incidentes reportados de un elemento de retroalimentación asociado a más de un periodo o a un periodo distinto del que le correspondía al momento de su creación.

## Assumptions

- Los roles con permiso para crear, editar y transicionar el estatus de los periodos son los mismos que hoy administran el catálogo (Talento/administración), conforme a los controles de acceso ya existentes.
- El estatus Planeado representa periodos futuros ya definidos en fechas, creados con antelación por Talento para sostener la continuidad del calendario antes de que les corresponda entrar en operación.
- El tipo de periodo (Semestral/Trimestral) y demás catálogos relacionados no cambian con esta funcionalidad; solo se refuerzan las reglas de ciclo de vida (unicidad de periodo Abierto, continuidad de fechas e inmutabilidad al cerrar).
- Antes de activar esta funcionalidad, el estado actual de los periodos existentes se habrá reconciliado manualmente (fuera del alcance funcional de esta spec) para que exista, a lo más, un periodo en estatus Abierto; esta funcionalidad garantiza la invariante hacia adelante mediante las validaciones de FR-001 a FR-005, pero no corrige por sí misma datos preexistentes que ya la violen.
- El cierre de un periodo no recalcula ni modifica retroactivamente calificaciones o puntajes ya generados; únicamente impide su edición futura.
- Los mecanismos de solo lectura para colaboradores reutilizan las vistas de consulta existentes, añadiendo la indicación de periodo Cerrado en lugar de crear una sección totalmente nueva.
