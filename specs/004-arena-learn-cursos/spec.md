# Feature Specification: Arena Learn — solicitud, autorización y registro de cursos con costo

**Feature Branch**: `004-arena-learn-cursos`

**Created**: 2026-10-06

**Status**: Draft

**Input**: User description: "Arena Learn: solicitud y autorización de cursos con costo (externos, capacitaciones, certificaciones) dentro de la plataforma de Talento, reemplazando el proceso actual en Forms/SharePoint. Un colaborador solicita un curso (nuevo, capturando sus datos, o elegido del catálogo sugerido), pasa por autorización secuencial de su Lead, un Director y Talento; después se registra solo la modalidad de pago (reembolso, pago directo, etc.) sin gestionar el pago. Al terminar, el colaborador sube la evidencia (certificado PDF/captura) y su reseña (opinión, por qué y a quién lo recomienda). En el perfil de cada colaborador existe la sección 'Arena Learn' con sus cursos, consultable por todos."

## Contexto: proceso actual que se reemplaza

Hoy el proceso vive fuera de la plataforma (Forms + SharePoint + correo) en 5 pasos:

1. El colaborador llena un Forms "Da de alta tu curso"; llega a Talento y Cultura, que confirma fondos y recaba autorizaciones (por fuera, sin trazabilidad).
2. Talento confirma por correo; el curso aparece en "Mi Plan de Capacitación" en SharePoint.
3. El colaborador compra el curso y obtiene comprobante fiscal (preferente CFDI a nombre de Arena Analytics; si no, nota/recibo con razón social y dirección fiscal completa).
4. Solicita reembolso en otro Forms adjuntando la factura.
5. Adjunta su diploma en "Seguimiento cursos" y lo marca como completado; el archivo se copia a su carpeta de Evaluaciones de desempeño. **Es indispensable para solicitar otro curso.**

Esta feature trae a la plataforma los pasos 1, 2 y 5 completos, y **solo registra** (no gestiona) los pasos 3 y 4. El reembolso y la facturación siguen ocurriendo fuera; la plataforma guarda la modalidad elegida y el estado declarado.

## Clarifications

### Session 2026-10-06

- Q: ¿Quién es "el Lead" de un colaborador? → A: Un nuevo dato "Lead directo" por persona, asignado por Talento; respaldo: cualquier Lead del área; si no hay, se omite el nivel.
- Q: ¿Qué Director aprueba? → A: El Director asignado al área del solicitante (dato nuevo por área); respaldo: cualquier Director.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Solicitar un curso (Priority: P1)

Un colaborador entra a Arena Learn y crea una solicitud de curso. Puede elegir un curso del **catálogo sugerido** (los datos se precargan) o capturar uno **nuevo** con sus datos: nombre, proveedor/plataforma, liga, tipo (curso, certificación, capacitación, conferencia, otro), costo y moneda, duración estimada, fecha tentativa de inicio y fin, modalidad de pago propuesta y una **justificación** (qué problema resuelve, cómo se relaciona con su rol/proyectos y qué pilar o tema quiere fortalecer). Al enviar, la solicitud queda en la bandeja de su primer aprobador.

**Why this priority**: Es la puerta de entrada de todo el proceso; sin solicitud no hay autorización ni registro. Por sí sola ya reemplaza el Forms "Da de alta tu curso" con trazabilidad.

**Independent Test**: Un colaborador crea una solicitud desde el catálogo y otra nueva; ambas aparecen en "Mis solicitudes" con estado "En revisión del Lead" y en la bandeja del Lead correspondiente.

**Acceptance Scenarios**:

1. **Given** un curso en el catálogo sugerido, **When** el colaborador lo elige y envía la solicitud con su justificación, **Then** la solicitud queda registrada con los datos del curso precargados y en estado "En revisión del Lead".
2. **Given** un curso que no existe en el catálogo, **When** el colaborador captura todos los datos obligatorios y envía, **Then** la solicitud se registra como "curso nuevo" y sigue el mismo flujo.
3. **Given** una solicitud con datos obligatorios faltantes, **When** el colaborador intenta enviarla, **Then** el sistema indica qué falta y no la envía; puede guardarla como borrador.
4. **Given** que el colaborador tiene un curso aprobado previo **sin evidencia de cierre** (ni marcado como no concluido), **When** intenta enviar una nueva solicitud, **Then** el sistema la bloquea e indica qué curso debe cerrar primero.

---

### User Story 2 - Autorización en tres niveles: Lead → Director → Talento (Priority: P1)

Cada aprobador ve en su bandeja las solicitudes que le tocan, con toda la información del curso, la justificación y el historial de cursos del colaborador (incluyendo cuántos ha completado y sus costos en el año). Puede **Aprobar**, **Regresar con comentarios** (vuelve al colaborador para ajustes) o **Rechazar** (con motivo obligatorio). Al aprobar, la solicitud avanza al siguiente nivel. Talento es el último nivel y es quien confirma fondos; su aprobación deja el curso **Autorizado**.

**Why this priority**: La autorización trazable es el valor central que hoy se pierde en correos; junto con US1 forma el MVP.

**Independent Test**: Una solicitud recorre Lead → Director → Talento; cada paso queda registrado con quién, cuándo y comentario; un rechazo en cualquier nivel termina el flujo y notifica al colaborador.

**Acceptance Scenarios**:

1. **Given** una solicitud "En revisión del Lead", **When** el Lead aprueba, **Then** pasa a "En revisión de Dirección" y aparece en la bandeja del Director asignado al área del colaborador (o de cualquier Director si el área no tiene uno).
2. **Given** una solicitud en cualquier nivel, **When** el aprobador la rechaza sin escribir motivo, **Then** el sistema no permite el rechazo hasta que capture el motivo.
3. **Given** una solicitud en cualquier nivel, **When** el aprobador la regresa con comentarios, **Then** vuelve al colaborador en estado "Requiere ajustes", y al reenviarla reinicia en el **mismo nivel** que la regresó (no desde el inicio).
4. **Given** una solicitud aprobada por Director, **When** Talento la aprueba, **Then** queda "Autorizada", el colaborador es notificado y el curso aparece en su Arena Learn como "En curso".
5. **Given** un colaborador que no es aprobador de esa solicitud, **When** intenta aprobarla, **Then** el sistema lo impide.
6. **Given** que el solicitante es él mismo Lead (o Director), **When** envía la solicitud, **Then** el nivel donde él sería su propio aprobador se omite y la solicitud entra directamente al siguiente nivel; nadie aprueba su propia solicitud.

---

### User Story 3 - Registro de modalidad de pago y comprobante (Priority: P2)

Una vez autorizado, el colaborador (o Talento) registra la **modalidad de pago** — Reembolso al colaborador, Pago directo de Arena, Gratuito/beca, Otro — y, de forma opcional, el costo final real y el tipo de comprobante obtenido (CFDI a nombre de Arena Analytics / nota o recibo con razón social y dirección fiscal / sin comprobante). La plataforma muestra las instrucciones fiscales vigentes (datos para facturar) para que el colaborador las tenga a mano al comprar. No se gestiona el pago ni el reembolso: solo se registra el estado declarado ("Pendiente de compra", "Comprado", "Reembolso solicitado", "Reembolsado / pagado").

**Why this priority**: Da visibilidad a Talento de en qué está cada curso sin convertir la plataforma en un sistema de pagos; es útil pero el flujo funciona sin ello.

**Independent Test**: Sobre un curso autorizado, el colaborador elige "Reembolso" y marca "Comprado"; Talento ve el estado en su vista de seguimiento.

**Acceptance Scenarios**:

1. **Given** un curso Autorizado, **When** el colaborador abre su detalle, **Then** ve las instrucciones fiscales y puede registrar modalidad de pago y estado.
2. **Given** modalidad "Reembolso", **When** el colaborador marca "Reembolso solicitado", **Then** el estado queda registrado con fecha y es visible para Talento.
3. **Given** cualquier modalidad, **When** se registra, **Then** la plataforma no solicita datos bancarios ni procesa importes.

---

### User Story 4 - Cierre del curso: evidencia y reseña (Priority: P1)

Al terminar el curso, el colaborador lo marca como **Completado** subiendo la **evidencia** (certificado PDF, imagen o captura de pantalla) y su **reseña**: calificación general (1–5), opinión, por qué lo recomienda (o no), a quién lo recomienda (rol/área/nivel sugeridos) y aprendizajes clave/cómo lo aplicó. Si no lo terminó, puede marcarlo como **No concluido** con motivo. Talento puede **validar** la evidencia (o regresarla si es ilegible o no corresponde).

**Why this priority**: Es la condición que hoy habilita pedir otro curso, alimenta el expediente de desarrollo del colaborador y es la fuente del conocimiento compartido de Arena Learn.

**Independent Test**: Un curso En curso se cierra con un PDF y reseña; aparece como Completado en el perfil del colaborador y el colaborador ya puede enviar una nueva solicitud.

**Acceptance Scenarios**:

1. **Given** un curso En curso, **When** el colaborador sube un archivo válido y llena la reseña obligatoria, **Then** el curso pasa a "Completado — pendiente de validación" y queda visible en su Arena Learn.
2. **Given** un archivo de tipo no permitido o mayor al límite, **When** intenta subirlo, **Then** el sistema lo rechaza con un mensaje claro.
3. **Given** un curso Completado, **When** Talento valida la evidencia, **Then** queda "Completado y validado"; **When** la regresa, **Then** el colaborador recibe el comentario y puede reemplazar el archivo.
4. **Given** un curso que el colaborador no terminó, **When** lo marca "No concluido" con motivo, **Then** deja de bloquear nuevas solicitudes y queda en su historial con ese estado.

---

### User Story 5 - Sección Arena Learn en el perfil, consultable por todos (Priority: P2)

Cada colaborador tiene en su perfil una sección **Arena Learn** con sus cursos completados (y los En curso). Cualquier persona de Arena puede abrir el perfil de otro colaborador, ver la lista y entrar al detalle de un curso: nombre, proveedor, liga, tipo, fechas, la reseña completa (opinión, por qué, a quién lo recomienda, aprendizajes) y la evidencia.

**Why this priority**: Convierte una inversión individual en conocimiento colectivo; depende de que existan cursos cerrados (US4).

**Independent Test**: Un colaborador A abre el perfil de B y ve sus cursos completados con reseña y evidencia, sin ver datos de costo ni el detalle de las autorizaciones.

**Acceptance Scenarios**:

1. **Given** un colaborador con cursos completados, **When** cualquier usuario autenticado abre su perfil, **Then** ve la sección Arena Learn con esos cursos.
2. **Given** el detalle público de un curso, **When** lo consulta alguien distinto al dueño, Talento o sus aprobadores, **Then** no ve costo, modalidad de pago, estado de reembolso, justificación ni comentarios de autorización.
3. **Given** solicitudes rechazadas, en borrador o en revisión, **When** otra persona consulta el perfil, **Then** no aparecen.

---

### User Story 6 - Catálogo sugerido y explorador de cursos (Priority: P2)

Talento administra el **catálogo sugerido** (alta, edición, archivado de cursos con área, nivel, pilar y etiquetas de tema a los que se recomienda). Cualquier usuario puede explorar el catálogo y ver, por cada curso, cuántas personas de Arena lo han tomado, su calificación promedio y sus reseñas. Talento puede **promover** al catálogo un curso "nuevo" que alguien ya completó y reseñó bien.

**Why this priority**: Acelera las solicitudes, estandariza datos y es el mecanismo para que la reseña de uno guíe la decisión de otro.

**Independent Test**: Talento da de alta un curso en el catálogo; un colaborador lo encuentra filtrando por su área y lo usa para crear una solicitud precargada.

**Acceptance Scenarios**:

1. **Given** el catálogo, **When** un colaborador filtra por área, nivel o tipo, **Then** ve los cursos recomendados con su calificación promedio y número de personas que lo han tomado.
2. **Given** un curso "nuevo" completado con reseña, **When** Talento lo promueve, **Then** aparece en el catálogo y las reseñas existentes quedan asociadas.
3. **Given** un curso archivado, **When** un colaborador crea una solicitud, **Then** ya no lo ve como opción, pero los historiales que lo referencian se conservan.

---

### User Story 7 - Seguimiento para Talento (Priority: P3)

Talento (y Dirección, en solo lectura) ve un tablero con todas las solicitudes y cursos por estado, filtrable por área, persona, año y estado; con totales de costo autorizado por área y año, solicitudes atascadas (más de N días hábiles en un mismo nivel) y cursos autorizados sin evidencia vencidos. Puede exportarlo a Excel.

**Why this priority**: Sustituye el control manual de SharePoint y da la visión presupuestal; no bloquea el flujo de los colaboradores.

**Independent Test**: Con solicitudes en distintos estados, el tablero muestra conteos correctos y el exporte contiene las mismas filas.

**Acceptance Scenarios**:

1. **Given** solicitudes en distintos estados, **When** Talento abre el tablero, **Then** ve conteos por estado y el costo autorizado acumulado por área en el año.
2. **Given** una solicitud con más de 5 días hábiles en el mismo nivel, **When** Talento abre el tablero, **Then** aparece marcada como atascada.
3. **Given** un curso autorizado cuya fecha de fin estimada pasó hace más de 30 días sin evidencia, **When** Talento abre el tablero, **Then** aparece como vencido.

---

### Edge Cases

- **Solicitante es Lead**: se omite el nivel Lead y entra a Dirección. **Solicitante es Director**: se omiten Lead y Dirección; entra a Talento. **Solicitante es Talento**: lo aprueba otra persona de Talento (nunca él mismo).
- **No existe Lead asignado** para el colaborador (hoy ocurre en UX/UI, que no tiene ningún usuario de nivel LEAD): la solicitud entra directamente a Dirección y queda marcada "sin Lead" para que Talento lo corrija en el catálogo de usuarios.
- **El aprobador cambia** (baja, cambio de área) mientras la solicitud está en su nivel: la solicitud se reasigna al nuevo aprobador vigente; Talento puede reasignar manualmente.
- **El colaborador edita la solicitud** después de enviarla: solo puede hacerlo si se le regresó con comentarios; los cambios quedan en el historial.
- **El colaborador cancela** una solicitud: posible mientras no esté Autorizada; si ya está Autorizada, solo Talento puede cancelarla (con motivo).
- **Curso gratuito**: se puede registrar en Arena Learn sin flujo de autorización ("registro directo"), solo con evidencia y reseña — no consume presupuesto, pero suma al conocimiento compartido.
- **Cursos tomados antes del lanzamiento** (historial de SharePoint): Talento puede cargarlos como registros históricos ya Completados.
- **Cambio de costo**: si el costo final real supera el autorizado en más de un 10%, el sistema lo señala a Talento para revisión (no bloquea).
- **Baja del colaborador**: su sección Arena Learn y reseñas se conservan como historial (de solo lectura).
- **Varias solicitudes simultáneas**: permitidas mientras ninguna autorizada previa esté pendiente de evidencia (regla de bloqueo de US1).
- **Evidencia con datos sensibles** (p. ej. el CFDI con RFC o importes): la evidencia pública es el **certificado**; el comprobante fiscal, si se sube, es privado (dueño + Talento).

## Requirements *(mandatory)*

### Functional Requirements

#### Solicitud (US1)

- **FR-001**: El sistema MUST permitir a cualquier usuario autenticado crear una solicitud de curso, a partir del catálogo sugerido o capturando un curso nuevo.
- **FR-002**: La solicitud MUST capturar: nombre del curso, proveedor/plataforma, liga, tipo (curso, certificación, capacitación, conferencia, otro), costo estimado y moneda, duración estimada en horas, fecha tentativa de inicio y de fin, modalidad de pago propuesta, pilar del modelo que fortalece (Ownership, Entrega de Valor, Impacto Arena; opcional) y etiquetas temáticas libres (p. ej. "Power BI", "MLOps"), y justificación. Al elegir del catálogo, los datos del curso se precargan y solo la justificación y fechas son obligatorias.
- **FR-003**: El sistema MUST permitir guardar la solicitud como borrador y enviarla después.
- **FR-004**: El sistema MUST impedir enviar una nueva solicitud si el colaborador tiene un curso Autorizado previo sin cerrar (sin evidencia o sin marcar No concluido), indicando cuál.

#### Autorización (US2)

- **FR-005**: Toda solicitud enviada MUST recorrer en orden los niveles Lead → Dirección → Talento, omitiendo los niveles en que el solicitante sería su propio aprobador.
- **FR-006**: El aprobador de nivel Lead MUST ser el **Lead directo** asignado al colaborador (dato nuevo por persona, editable por Talento en Usuarios). Si el colaborador no tiene Lead directo asignado, MUST poder resolverlo cualquier usuario de nivel LEAD de su área; si su área no tiene Leads, el nivel se omite y la solicitud queda marcada "sin Lead" para Talento.
- **FR-007**: El nivel Dirección MUST resolverlo el **Director asignado al área** del solicitante (dato nuevo por área, editable por Talento); si el área no tiene Director asignado, cualquier usuario con rol Director; el nivel Talento, cualquier usuario con rol Talento distinto del solicitante.
- **FR-008**: En cada nivel, el aprobador MUST poder Aprobar, Regresar con comentarios o Rechazar; Rechazar y Regresar exigen comentario.
- **FR-009**: Una solicitud regresada MUST, al reenviarse, reanudar en el nivel que la regresó.
- **FR-010**: El sistema MUST registrar en un historial inmutable cada transición: quién, cuándo, de qué estado a cuál y comentario.
- **FR-011**: El aprobador MUST ver, junto a la solicitud, el historial de Arena Learn del colaborador (cursos completados, no concluidos, en curso) y el costo autorizado acumulado del colaborador en el año.
- **FR-012**: El sistema MUST notificar (siempre en la campana de pendientes de la plataforma y, cuando el envío de correo esté habilitado en el entorno, también por correo) al siguiente aprobador cuando una solicitud llegue a su nivel, y al colaborador cuando su solicitud sea aprobada, regresada o rechazada.
- **FR-013**: Talento MUST poder reasignar manualmente el aprobador de una solicitud en revisión y cancelar una solicitud autorizada, con motivo.

#### Pago (US3)

- **FR-014**: En un curso Autorizado, el colaborador y Talento MUST poder registrar la modalidad de pago (Reembolso al colaborador, Pago directo de Arena, Gratuito/beca, Otro) y su estado (Pendiente de compra, Comprado, Reembolso solicitado, Reembolsado/pagado).
- **FR-015**: El sistema MUST mostrar al colaborador las instrucciones fiscales vigentes (razón social, dirección fiscal, preferencia por CFDI), editables por Talento.
- **FR-016**: El sistema MAY permitir adjuntar el comprobante fiscal como archivo **privado** (visible solo para el dueño y Talento) y registrar el costo final real; MUST señalar a Talento cuando el costo real supere el autorizado en más de 10%.
- **FR-017**: El sistema MUST NOT procesar pagos, capturar datos bancarios ni calcular reembolsos.

#### Cierre (US4)

- **FR-018**: El colaborador MUST poder marcar un curso Autorizado como Completado subiendo al menos un archivo de evidencia (PDF, PNG, JPG/JPEG o WEBP, máximo 4 MB por archivo) y llenando la reseña.
- **FR-019**: La reseña MUST incluir calificación (1–5), opinión, ¿lo recomiendas? (sí/no/con reservas) y por qué, a quién lo recomienda (áreas y niveles sugeridos, más texto libre) y aprendizajes clave/aplicación en su trabajo.
- **FR-020**: El colaborador MUST poder marcar un curso como No concluido con motivo; esto libera el bloqueo de FR-004.
- **FR-021**: Talento MUST poder validar la evidencia o regresarla con comentario; el colaborador puede reemplazar el archivo mientras no esté validada.
- **FR-022**: El colaborador MUST poder registrar directamente (sin autorización) un curso gratuito o pagado por él mismo, con evidencia y reseña.

#### Perfil y visibilidad (US5)

- **FR-023**: El perfil de cada colaborador MUST incluir una sección Arena Learn visible para todo usuario autenticado, con sus cursos Completados y En curso. Esto es una **excepción explícita y acotada** a la regla de visibilidad vigente (un colaborador solo ve su propia información; un Lead, la de su área): la excepción cubre únicamente la ficha pública (nombre, foto, área, nivel) y la sección Arena Learn; calificaciones, evaluaciones, escenarios y retroalimentación siguen con la regla actual. Requiere una vista de perfil de otra persona y un directorio/buscador de personas, que hoy no existen.
- **FR-024**: La vista pública de un curso MUST mostrar datos del curso, fechas, reseña y evidencia de completado; y MUST ocultar costo, modalidad y estado de pago, comprobante fiscal, justificación y comentarios de autorización, salvo al dueño, a sus aprobadores, a Talento y a Directores.
- **FR-025**: Las solicitudes en borrador, en revisión, rechazadas o canceladas MUST ser visibles solo para el dueño, sus aprobadores, Talento y Directores.
- **FR-026**: La evidencia de un curso MUST ser accesible solo a usuarios autenticados de Arena (nunca por liga pública).

#### Catálogo (US6)

- **FR-027**: Talento MUST poder dar de alta, editar y archivar cursos del catálogo sugerido, indicando áreas, niveles, pilar y etiquetas recomendados.
- **FR-028**: Todo usuario MUST poder explorar el catálogo filtrando por área, nivel, tipo, pilar y etiqueta, viendo calificación promedio, número de personas que lo completaron y sus reseñas.
- **FR-029**: Talento MUST poder promover al catálogo un curso nuevo ya completado, conservando las reseñas asociadas.

#### Seguimiento (US7)

- **FR-030**: Talento MUST contar con un tablero de solicitudes y cursos por estado, filtrable por área, persona, año y estado, con costo autorizado acumulado por área/año, solicitudes atascadas (> 5 días hábiles en un nivel) y cursos vencidos sin evidencia (> 30 días después de la fecha de fin estimada).
- **FR-031**: Talento MUST poder exportar el tablero a Excel.
- **FR-032**: Talento MUST poder cargar registros históricos (cursos completados antes del lanzamiento) con su evidencia.

### Key Entities

- **Curso de catálogo**: curso recomendado por Talento — nombre, proveedor, liga, tipo, costo de referencia, duración, áreas/niveles/pilar/etiquetas recomendados, estado (activo/archivado). Agrega calificación promedio y conteo de completados.
- **Solicitud de curso**: pertenece a un colaborador; referencia opcional a un Curso de catálogo o datos propios de curso nuevo; costo, fechas, justificación, modalidad de pago propuesta, estado del flujo (Borrador, En revisión Lead, En revisión Dirección, En revisión Talento, Requiere ajustes, Rechazada, Cancelada, Autorizada, Completada, Completada y validada, No concluida) y origen (solicitud / registro directo / histórico).
- **Paso de autorización**: historial inmutable — solicitud, nivel, actor, acción (aprobar/regresar/rechazar/reasignar/cancelar), comentario, fecha.
- **Registro de pago**: modalidad, estado declarado, costo final real, tipo de comprobante, archivo de comprobante privado.
- **Evidencia**: uno o más archivos asociados a la solicitud, con estado de validación por Talento.
- **Reseña**: calificación, opinión, recomendación y su porqué, audiencia sugerida (áreas/niveles), aprendizajes; una por curso completado.
- **Instrucciones fiscales**: texto configurable por Talento mostrado en el paso de compra.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las solicitudes de cursos con costo se hacen dentro de la plataforma a partir de 30 días después del lanzamiento (el Forms se da de baja).
- **SC-002**: Un colaborador completa una solicitud desde el catálogo en menos de 3 minutos, y una de curso nuevo en menos de 6 minutos.
- **SC-003**: La mediana de tiempo desde el envío hasta la autorización final baja a 5 días hábiles o menos, medible porque cada transición queda fechada.
- **SC-004**: Al menos el 90% de los cursos autorizados tienen evidencia y reseña registradas dentro de los 30 días posteriores a su fecha de fin.
- **SC-005**: Cualquier usuario encuentra quién en Arena ya tomó un curso o tema dado en menos de 1 minuto desde el catálogo o el perfil.
- **SC-006**: Talento obtiene el costo autorizado por área y año sin consolidar archivos externos (0 hojas de cálculo manuales para ese reporte).
- **SC-007**: Ningún usuario no autorizado puede ver costos, justificaciones o comprobantes fiscales de otro colaborador (verificable con pruebas de acceso por rol).

## Assumptions

- "Consultable por todos" = todo usuario autenticado de Arena; nada es público fuera de la organización.
- Lo público es el **aprendizaje** (curso, reseña, certificado); lo financiero y la deliberación de autorización son privados.
- Se conserva la regla vigente "indispensable para solicitar otro curso": no se puede enviar una nueva solicitud con un curso autorizado sin cerrar.
- No hay tope presupuestal automático por persona en esta versión: Talento decide con la información del costo acumulado (FR-011); un tope configurable queda como mejora futura.
- Los cursos de Arena Learn **no** modifican automáticamente la calificación de desempeño; pueden consultarse como insumo cualitativo en Mesa de Talento.
- Las notificaciones por correo reutilizan el mecanismo de recordatorios/pendientes existente en la plataforma.
- La moneda por defecto es MXN; se permite USD para plataformas internacionales, sin conversión automática.
- Los historiales previos de SharePoint se migran por carga de Talento (FR-032), no por integración automática.
- Fuera de alcance: gestión de pagos/reembolsos, conexión con contabilidad o con SharePoint, compra de licencias corporativas.
