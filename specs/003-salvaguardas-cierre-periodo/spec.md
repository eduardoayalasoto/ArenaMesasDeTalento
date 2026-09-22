# Feature Specification: Salvaguardas de UX y completitud de datos para el cierre/apertura de Periodos de Evaluación

**Feature Branch**: `003-salvaguardas-cierre-periodo`

**Created**: 2026-09-21

**Status**: Draft

**Input**: User description: "Construye sobre 002-ciclo-vida-periodos (ya implementada): (1) agregar confirmación explícita antes de Abrir/Cerrar un periodo, dado que cerrar es de alto impacto y en la práctica no reversible desde la interfaz; (2) al cerrar, mostrar a Talento un resumen de la actividad aún no completada (evaluaciones de Ownership sin enviar, Entregas de Valor sin validar, calificaciones finales incompletas) antes de confirmar, sin bloquear el cierre; (3) agregar el campo 'motivo' (ya exigido por el backend para corregir un registro de un periodo Cerrado) a las pantallas de Ownership y Entrega de Valor, que hoy no lo tienen aunque `feedback_session_detail.html` sí."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confirmación antes de abrir o cerrar un periodo (Priority: P1)

Talento hace clic en "Abrir" o "Cerrar" sobre un periodo en la pantalla de administración de periodos. Antes de que la acción se ejecute, el sistema le pide confirmar explícitamente, indicando qué va a pasar exactamente (incluyendo, al cerrar, qué periodo se abrirá automáticamente a continuación, si aplica). Si Talento cancela, no cambia nada.

**Why this priority**: Es la salvaguarda más simple y de mayor impacto: hoy un clic accidental en "Cerrar" congela de inmediato todos los registros del periodo y, en la práctica, no se puede deshacer desde la interfaz una vez que se abre el siguiente periodo automáticamente. Sin esto, cualquier otra mejora es secundaria.

**Independent Test**: Puede probarse haciendo clic en "Cerrar" y cancelando el diálogo de confirmación: el periodo debe seguir Abierto. Repitiendo y confirmando: el periodo debe cerrarse igual que hoy.

**Acceptance Scenarios**:

1. **Given** un periodo Abierto, **When** Talento hace clic en "Cerrar" y cancela la confirmación, **Then** el periodo sigue Abierto y no se abre ningún otro periodo.
2. **Given** un periodo Abierto y un periodo Planeado contiguo ya creado, **When** Talento hace clic en "Cerrar" y confirma, **Then** el mensaje de confirmación mencionó por nombre el periodo que se abriría automáticamente, y tras confirmar el cierre ocurre exactamente igual que hoy (periodo cerrado, siguiente abierto).
3. **Given** un periodo Planeado, **When** Talento hace clic en "Abrir" y cancela la confirmación, **Then** el periodo sigue Planeado.

---

### User Story 2 - Aviso de actividad pendiente al cerrar un periodo (Priority: P1)

Al iniciar el cierre de un periodo, Talento ve cuánta actividad de ese periodo todavía no está completa (evaluaciones de Ownership sin enviar, Entregas de Valor sin validar, calificaciones finales incompletas) antes de confirmar. Si decide cerrar de todas formas, el cierre procede: el aviso es informativo, no un bloqueo.

**Why this priority**: Sin este aviso, Talento puede cerrar un periodo sin darse cuenta de que hay trabajo a medias, que después queda congelado permanentemente en modo de solo lectura. Es tan importante como la confirmación simple porque convierte una decisión "a ciegas" en una decisión informada.

**Independent Test**: Puede probarse dejando algunas evaluaciones sin enviar en un periodo y verificando que, al iniciar su cierre, el aviso muestra esos conteos antes de confirmar; y que cerrando con todo completo, el aviso indica que no hay pendientes.

**Acceptance Scenarios**:

1. **Given** un periodo con 3 evaluaciones de Ownership sin enviar y 2 Entregas de Valor sin validar, **When** Talento inicia el cierre de ese periodo, **Then** ve esos conteos antes de poder confirmar.
2. **Given** un periodo donde toda la actividad ya está completa, **When** Talento inicia su cierre, **Then** el aviso indica explícitamente que no hay actividad pendiente.
3. **Given** el aviso de actividad pendiente ya mostrado, **When** Talento decide continuar con el cierre, **Then** el periodo se cierra igual que en la User Story 1, sin ninguna restricción adicional por los pendientes.

---

### User Story 3 - Campo de motivo en las pantallas de Ownership y Entrega de Valor (Priority: P2)

Cuando Talento/superusuario abre una evaluación de Ownership o una Entrega de Valor que pertenece a un periodo ya Cerrado, la pantalla le muestra un campo para capturar el motivo de la corrección antes de poder guardar cualquier cambio — el mismo patrón que ya existe en la pantalla de retroalimentación de Mesa de Talento.

**Why this priority**: El backend ya exige y audita este motivo (feature 002), pero sin el campo en la pantalla, la excepción de corrección es inutilizable en la práctica para estos dos pilares: hoy el guardado simplemente se rechaza sin que el usuario entienda por qué. Es P2 porque corregir un registro cerrado es un evento poco frecuente comparado con abrir/cerrar periodos (US1/US2).

**Independent Test**: Puede probarse cerrando un periodo con una evaluación de Ownership incompleta, entrando como Talento a corregirla, y verificando que la pantalla exige el motivo antes de guardar, y que dicho motivo queda auditado.

**Acceptance Scenarios**:

1. **Given** una evaluación de Ownership de un periodo Cerrado, **When** Talento/superusuario la abre para corregirla, **Then** ve un campo de motivo obligatorio antes de poder guardar cualquier cambio (respuestas, fortalezas/oportunidades, cerrar o reabrir). La acción de **reiniciar** (que elimina el registro por completo) no está disponible sobre un registro de un periodo Cerrado, ni siquiera con motivo (ver FR-011a).
2. **Given** el mismo escenario para una Entrega de Valor de un periodo Cerrado, **When** Talento/superusuario intenta capturar criterios, validar, rechazar o comentar, **Then** ve el mismo campo de motivo obligatorio antes de guardar.
3. **Given** un periodo Abierto, **When** cualquier usuario captura una evaluación de Ownership o una Entrega de Valor normalmente, **Then** no ve ningún campo de motivo (el flujo normal no cambia).
4. **Given** un usuario sin permiso de corrección (no Talento/superusuario), **When** consulta una evaluación de un periodo Cerrado, **Then** la ve en modo de solo lectura, sin el campo de motivo.
5. **Given** un periodo ya Cerrado con evaluaciones de Ownership y Entregas de Valor, **When** Talento/superusuario quiere consultarlas, **Then** puede elegir ese periodo desde las pantallas de listado correspondientes (igual que ya puede hacerlo hoy para retroalimentación de Mesa de Talento) y llegar a cada registro para consultarlo o corregirlo, en vez de que ese periodo sea inalcanzable.

---

### Edge Cases

- ¿Qué ocurre si Talento intenta cerrar un periodo sin ninguna actividad registrada en absoluto (cero evaluaciones de cualquier tipo)? El aviso debe mostrar el estado como "sin actividad pendiente" (equivalente a 0 de 0), no como un error ni como una advertencia alarmante.
- ¿Qué ocurre si Talento captura el motivo pero el guardado falla por otra razón (por ejemplo, un criterio de Entrega de Valor inválido)? El formulario debe volver a mostrarse conservando el motivo ya escrito, para no obligar a Talento a volver a redactarlo.
- ¿Qué ocurre si Talento/superusuario intenta guardar un cambio sobre un registro de un periodo Cerrado dejando el campo de motivo vacío? Debe rechazarse con el mismo mensaje ya usado hoy en retroalimentación de Mesa de Talento ("Debes capturar un motivo para corregir un registro de un periodo ya Cerrado"), sin perder el resto de lo capturado en el formulario.
- ¿Qué ocurre si Talento intenta reiniciar (eliminar) una evaluación de Ownership que pertenece a un periodo Cerrado? La acción no debe estar disponible (FR-011a): no se ofrece un campo de motivo para esto, se oculta o deshabilita directamente, distinto del resto de las acciones de edición.
- ¿Qué ocurre con el aviso de actividad pendiente si, entre que Talento lo ve y confirma el cierre, alguien más envía una evaluación (cambiando el conteo)? El aviso refleja el estado al momento de solicitarse; una pequeña variación de último momento no es crítica porque el aviso es informativo, no una condición de bloqueo.

## Requirements *(mandatory)*

### Functional Requirements

#### Confirmación de Abrir/Cerrar (US1)

- **FR-001**: El sistema DEBE pedir confirmación explícita del usuario antes de ejecutar la acción de Abrir un periodo, nombrando el periodo a abrir.
- **FR-002**: El sistema DEBE pedir confirmación explícita del usuario antes de ejecutar la acción de Cerrar un periodo, nombrando el periodo a cerrar y advirtiendo que la acción no se puede deshacer desde la interfaz.
- **FR-003**: Si el usuario cancela la confirmación de cualquiera de las dos acciones, el sistema NO DEBE ejecutar ningún cambio de estatus ni ningún otro efecto secundario.
- **FR-004**: Cuando el cierre de un periodo vaya a abrir automáticamente el siguiente periodo contiguo, el mensaje de confirmación DEBE nombrar ese periodo siguiente, para que el usuario sepa exactamente qué va a ocurrir antes de confirmar.

#### Aviso de actividad pendiente al cerrar (US2)

- **FR-005**: Antes de que el usuario pueda confirmar el cierre de un periodo, el sistema DEBE mostrarle un resumen de la actividad de ese periodo aún no completada: evaluaciones de Ownership sin enviar, Entregas de Valor sin validar y calificaciones finales incompletas.
- **FR-006**: Si no hay actividad pendiente en ninguna de esas categorías, el sistema DEBE indicarlo explícitamente en el mismo resumen (no limitarse a omitir la advertencia).
- **FR-007**: El resumen de actividad pendiente NO DEBE impedir el cierre: el usuario puede confirmar y cerrar el periodo independientemente de cuánta actividad quede incompleta.
- **FR-008**: El resumen de actividad pendiente se presenta dentro del mismo diálogo de confirmación de cierre de FR-002 (un único paso, sin pantalla intermedia): el texto de esa confirmación incluye los conteos totales de cada categoría (evaluaciones de Ownership sin enviar, Entregas de Valor sin validar, calificaciones finales incompletas), no un desglose por persona.

#### Campo de motivo en Ownership y Entrega de Valor (US3)

- **FR-009**: El sistema DEBE mostrar un campo de texto "motivo" en la pantalla de una evaluación de Ownership cuando el periodo de esa evaluación esté Cerrado y quien la vea tenga permiso de corrección (Talento/superusuario).
- **FR-010**: El sistema DEBE mostrar el mismo campo de texto "motivo" en las pantallas de captura y de validación de Entrega de Valor, bajo la misma condición (periodo Cerrado y permiso de corrección).
- **FR-011**: El campo "motivo" DEBE ser obligatorio para completar cualquier acción de **edición** sobre un registro de un periodo Cerrado (guardar respuestas/comentarios, cerrar o reabrir una evaluación de Ownership; capturar criterios, enviar a validación, validar, rechazar o comentar una Entrega de Valor), consistente con la validación ya existente en el backend.
- **FR-011a**: La acción de **reiniciar** una evaluación de Ownership (que la elimina por completo, no la edita) NO DEBE estar disponible sobre un registro de un periodo Cerrado, ni siquiera para Talento/superusuario con motivo: eliminar el registro destruiría la referencia histórica que un periodo Cerrado debe preservar (FR-006 de 002-ciclo-vida-periodos), algo que un campo de motivo no compensa. El botón/acción de reiniciar debe ocultarse o deshabilitarse cuando el periodo del registro esté Cerrado.
- **FR-012**: El campo "motivo" NO DEBE mostrarse mientras el periodo del registro esté Abierto: el flujo normal de captura no cambia.
- **FR-013**: Un usuario sin permiso de corrección que consulte un registro de un periodo Cerrado DEBE seguir viéndolo en modo de solo lectura, sin el campo de motivo (comportamiento ya existente, sin cambios).

### Key Entities

- **Periodo de Evaluación**: sin cambios de esquema; esta feature es de interfaz sobre el ciclo de vida ya construido en 002-ciclo-vida-periodos.
- **Resumen de actividad pendiente**: información ya calculada hoy por la pantalla de avance del periodo (conteos de evaluaciones de Ownership, Entregas de Valor y calificaciones finales, completas vs. totales); esta feature la reutiliza en el momento de cerrar, no introduce un cálculo nuevo.
- **Motivo de corrección**: dato ya definido y auditado por 002-ciclo-vida-periodos (se guarda en el historial de auditoría del registro corregido); esta feature solo agrega el campo de captura en las pantallas que hoy no lo tienen.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los clics en "Abrir" o "Cerrar" un periodo muestran una confirmación explícita antes de ejecutar el cambio; cancelar la confirmación deja el estado exactamente igual a como estaba.
- **SC-002**: El 100% de los intentos de cierre de un periodo muestran el resumen de actividad pendiente (o la indicación de que no hay pendientes) antes de que el cierre pueda confirmarse.
- **SC-003**: El 100% de las correcciones guardadas con éxito sobre un registro de Ownership o Entrega de Valor de un periodo Cerrado quedan con un motivo capturado y verificable en su historial de auditoría.
- **SC-004**: Cero incidentes reportados de un registro de un periodo Cerrado editado sin que quede un motivo registrado en su auditoría, y cero casos de un registro de un periodo Cerrado eliminado por la acción de reiniciar.

## Assumptions

- La confirmación de Abrir/Cerrar reutiliza el mismo patrón visual ya usado en el proyecto para acciones irreversibles (`onclick="return confirm(...)"`, como en "Eliminar periodo"/"Eliminar proyecto"); el resumen de actividad pendiente (FR-008) va dentro de ese mismo texto de confirmación, no en una pantalla aparte.
- El campo de motivo en Ownership y Entrega de Valor sigue el mismo patrón visual y de validación ya implementado en `feedback_session_detail.html` (campo de texto obligatorio, visible únicamente cuando aplica).
- No se modifican ni se agregan roles o permisos: sigue aplicando exactamente `permissions.is_period_correction_allowed` y el resto de los controles de acceso ya existentes.
- No se toca la lógica de negocio del ciclo de vida de periodos (`period_lifecycle.py`: `open_period`, `close_and_open_next`, `assert_record_editable`) ni las reglas de continuidad/unicidad ya implementadas en 002-ciclo-vida-periodos: esta feature es enteramente de interfaz sobre ese motor ya construido y probado.
- El resumen de actividad pendiente reutiliza los mismos cálculos que ya existen para `/avance-periodo` (mismas consultas/conteos), no introduce una nueva fuente de verdad. Nota para la fase de plan: esos cálculos hoy viven en `apps.dashboards`, mientras que la confirmación de cierre vive en `apps.catalog`; `/speckit-plan` debe decidir cómo compartirlos (p. ej. moverlos a `apps.core.services`) sin duplicar consultas ni crear una dependencia de `catalog` hacia `dashboards`.
- Para que el campo de motivo (US3) sea utilizable en la práctica y no solo un campo que nunca se llega a mostrar: las pantallas de listado de Ownership (`ownership_list`, `ownership_validation`) y de Entrega de Valor (`value_delivery_list`) hoy solo muestran/operan sobre el periodo Abierto vigente, y `value_delivery_capture` siempre resuelve el periodo Abierto vigente en cada solicitud (nunca uno específico). Sin ampliar esas vistas para poder consultar un periodo Cerrado específico (mismo patrón `?periodo=<id>` ya usado en 002 para retroalimentación de Mesa de Talento y avance del periodo), Talento no tendría manera de *llegar* a una evaluación de Ownership o Entrega de Valor de un periodo ya Cerrado para corregirla — el campo de motivo existiría pero sería inalcanzable por navegación normal. Esta feature incluye esa extensión de navegación como parte necesaria de US3, no como alcance nuevo independiente.
