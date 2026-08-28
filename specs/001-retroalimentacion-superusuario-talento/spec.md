# Feature Specification: Reapertura de retroalimentación y vista de superusuario para Talento

**Feature Branch**: `001-retroalimentacion-superusuario-talento`

**Created**: 2026-08-28

**Status**: Draft

**Input**: User description: "Tengo un requerimiento específico por parte de los usuarios, y es que cuando un usuario cierra una retroalimentación, esta ya no se puede volver a abrir jamás. Entonces, quisiera que pudieras poner un botón en la tarjeta de la retroalimentación que uno tiene que dar para que pudieran reabrir la retroalimentación que se cerró de manera incorrecta, para editar algo más adelante. Ese es en primera. Y en segunda, es que el usuario de talento que está fungiendo como superusuario, cuando entra retroalimentación, quiero que vea todas las retroalimentaciones con todos los estados posibles, con todas las acciones posibles de abrir, cerrar, etcétera, porque los usuarios que tengan ese perfil de talento tienen permiso para ver y poder operar absolutamente todo. Vamos a darle un tratamiento como si fuera un superusuario."

## Clarifications

### Session 2026-08-28

- Q: Para las retroalimentaciones sin cerrar que el superusuario de Talento ve en el listado ampliado, ¿el "cerrar el acuerdo" también debe poder hacerse con un botón directo en la tarjeta (igual que "Reabrir"), o basta con que entre al detalle para cerrarla ahí? → A: Cerrar solo se hace desde el detalle (como hoy); en la tarjeta solo aparece el enlace "Ver" y, cuando aplique, el botón "Reabrir".
- Q: ¿Quién puede reabrir además de Talento/superusuario: cualquier responsable asignado (principal o secundario) puede reabrir su propia retroalimentación cerrada, igual que hoy ya puede cerrarla? → A: Sí — el/los responsable(s) asignado(s) (principal o secundario) pueden reabrir su propia retroalimentación, con el mismo alcance de permiso que ya tienen para cerrarla; Talento/superusuario conserva además la capacidad de reabrir cualquiera, incluso donde no es responsable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reabrir una retroalimentación cerrada por error, desde su tarjeta (Priority: P1)

Como responsable asignado de una retroalimentación (principal o secundario) o como usuario con perfil de superusuario de Talento, cuando una retroalimentación se cerró por equivocación, necesito poder reabrirla con un solo botón visible directamente en su tarjeta del listado, sin tener que entrar a la pantalla de detalle, para poder seguir editándola más adelante.

**Why this priority**: Es el dolor concreto que reportaron los usuarios — hoy un cierre es irreversible para cualquiera, y corregir un cierre accidental es la necesidad más urgente y la que entrega valor por sí sola, sin depender de la Historia 2.

**Independent Test**: Se puede probar de forma aislada cerrando una retroalimentación cualquiera y verificando que, tanto su responsable asignado como un superusuario de Talento, ven un botón "Reabrir" en su tarjeta del listado que la regresa a estado editable sin salir de esa pantalla.

**Acceptance Scenarios**:

1. **Given** una retroalimentación en estado "Acordada · cerrada", **When** su responsable asignado (principal o secundario), o un usuario con perfil de superusuario de Talento, ve su tarjeta en el listado, **Then** la tarjeta muestra un control "Reabrir" utilizable ahí mismo, sin necesitar entrar al detalle.
2. **Given** que se presiona "Reabrir" en la tarjeta, **When** la acción se completa, **Then** esa retroalimentación deja de estar cerrada, vuelve a ser editable, y queda registrado quién y cuándo la reabrió.
3. **Given** un usuario que no es responsable asignado de esa retroalimentación ni tiene perfil de superusuario de Talento, **When** intenta reabrirla, **Then** el sistema se lo niega.
4. **Given** una retroalimentación en estado "Acordada · cerrada", **When** cualquier usuario (responsable o superusuario) revisa su tarjeta, **Then** NO aparece un botón de "Cerrar" directo en la tarjeta — cerrar el acuerdo sigue requiriendo entrar al detalle.

---

### User Story 2 - Ver y operar sobre todas las retroalimentaciones como superusuario (Priority: P2)

Como usuaria/o con perfil de superusuario de Talento, cuando entro al listado de retroalimentación, necesito ver todas las retroalimentaciones del periodo activo —en cualquier estado y sin importar si soy la persona responsable asignada—, con acceso a todas las acciones correspondientes (ver, editar, cerrar, reabrir), igual que lo haría un superusuario del sistema.

**Why this priority**: Depende conceptualmente de que exista la acción de reabrir (Historia 1), pero aporta valor independiente: hoy hay retroalimentaciones que son invisibles para Talento simplemente porque no está asignado como responsable, lo que le impide dar seguimiento y supervisión completa.

**Independent Test**: Se puede probar de forma aislada creando una retroalimentación donde el usuario de Talento no es responsable asignado ni receptor, y verificando que de todas formas aparece en su listado, con badge de estado correcto y con las acciones de ver/editar/cerrar/reabrir disponibles.

**Acceptance Scenarios**:

1. **Given** una retroalimentación del periodo activo donde el usuario de Talento no es responsable asignado ni receptor, **When** ese usuario entra al listado de retroalimentación, **Then** esa retroalimentación aparece igual, con su estado real (sin iniciar / con avance / cerrada).
2. **Given** que el usuario de Talento está viendo esa tarjeta ajena, **When** revisa las acciones disponibles, **Then** puede ver/editar, cerrar el acuerdo o reabrir, según el estado, exactamente igual que si fuera el responsable asignado.
3. **Given** un usuario Colaborador o Director sin perfil de superusuario de Talento, **When** entra al listado de retroalimentación, **Then** sigue viendo únicamente sus propias tarjetas (como responsable o receptor), sin ningún cambio de alcance.

---

### Edge Cases

- Una retroalimentación sin ningún responsable asignado (huérfana) es hoy invisible para todo el mundo salvo su receptor; con esta feature debe volverse visible para el superusuario de Talento en el listado del periodo activo.
- Si dos personas autorizadas (responsable y/o superusuario de Talento) reabren o cierran la misma retroalimentación casi al mismo tiempo, gana la última escritura — no se requiere bloqueo optimista para esta feature.
- Reabrir una retroalimentación que ya está abierta (no cerrada) no debe tener efecto ni producir un error visible.
- El acceso ampliado de "ver todo" (Historia 2) no debe extenderse accidentalmente a perfiles que hoy no tienen ese nivel de permiso en este dominio (por ejemplo, Director); la capacidad de reabrir la propia retroalimentación (Historia 1) sí se extiende a cualquier responsable asignado, no solo a Talento.
- Un usuario que deja de ser responsable asignado de una retroalimentación (por ejemplo, se le quita vía "quitar responsable") pierde también, a partir de ese momento, la capacidad de reabrirla.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE mostrar, directamente en la tarjeta de una retroalimentación cerrada, un control de "Reabrir" para: (a) todo responsable asignado (principal o secundario) de esa retroalimentación, sobre su propia tarjeta, y (b) todo usuario con perfil de superusuario de Talento, sobre cualquier tarjeta.
- **FR-002**: Al usar el control "Reabrir" de la tarjeta, el sistema DEBE dejar la retroalimentación en estado editable (no cerrado), con el mismo efecto que la reapertura ya disponible desde el detalle.
- **FR-003**: El sistema DEBE limitar quién puede reabrir una retroalimentación a: el/los responsable(s) asignado(s) de esa retroalimentación específica (el mismo alcance de permiso que ya tienen para cerrarla) y a todo usuario con perfil de superusuario de Talento (que puede reabrir cualquiera, sea o no responsable); ningún otro usuario debe poder reabrirla.
- **FR-004**: El sistema DEBE dejar registro auditable de quién reabrió una retroalimentación y cuándo, y de quién la había cerrado originalmente y cuándo — ese registro puede vivir en el historial de auditoría general del sistema; no es necesario que los campos "vigentes" de la retroalimentación conserven ambos datos a la vez.
- **FR-005**: El listado de retroalimentación DEBE mostrar, a todo usuario con perfil de superusuario de Talento, la totalidad de las retroalimentaciones del periodo de evaluación activo, sin limitarse a aquellas donde el usuario es responsable asignado o receptor.
- **FR-006**: En esa vista ampliada, cada retroalimentación DEBE mostrar su estado real (sin iniciar / con avance / cerrada) sin importar quién la esté consultando.
- **FR-007**: En esa vista ampliada, el usuario con perfil de superusuario de Talento DEBE tener disponibles todas las acciones aplicables al estado de cada retroalimentación (ver/editar y cerrar el acuerdo desde el detalle; reabrir desde la tarjeta o el detalle), incluso sobre retroalimentaciones donde no es responsable asignado.
- **FR-008**: Los usuarios sin perfil de superusuario de Talento DEBEN seguir viendo únicamente sus propias retroalimentaciones (como responsable principal, secundario o receptor), sin cambios respecto al alcance actual.
- **FR-009**: El sistema DEBE seguir denegando cualquier intento de cerrar, reabrir o editar una retroalimentación por parte de un usuario que no sea su responsable asignado ni tenga perfil de superusuario de Talento, incluso si ahora puede *ver* más retroalimentaciones gracias a FR-005.
- **FR-010**: El tratamiento de "superusuario" descrito en FR-005 a FR-007 DEBE aplicar a todo usuario con perfil de Talento y a todo superusuario del sistema, y NO DEBE extenderse a otros perfiles (por ejemplo, Director) que hoy no tienen ese nivel de permiso en este dominio.
- **FR-011**: El sistema NO DEBE agregar un control de "cerrar el acuerdo" directo en la tarjeta del listado; esa acción permanece disponible únicamente al entrar al detalle de la retroalimentación, tanto para responsables asignados como para el superusuario de Talento — sin cambio respecto al comportamiento actual.

### Key Entities

- **Retroalimentación**: la sesión de retroalimentación de una persona en un periodo de evaluación. Su estado (sin iniciar / con avance / cerrada) determina qué acciones aplican; queda trazable —vía el historial de auditoría del sistema, no necesariamente en sus campos "actuales"— quién y cuándo la cerró, y quién y cuándo la reabrió.
- **Responsable de retroalimentación**: usuario(s) asignado(s) para dar seguimiento y cerrar una retroalimentación (uno principal, opcionalmente varios secundarios).
- **Perfil de superusuario de Talento**: condición que cumple todo usuario con perfil "Talento" o con superusuario del sistema, y que determina el acceso ampliado y las acciones especiales de esta feature.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un responsable asignado o un usuario con perfil de superusuario de Talento puede reabrir una retroalimentación cerrada por error en un solo paso, sin salir del listado.
- **SC-002**: El 100% de las retroalimentaciones del periodo activo son visibles para el superusuario de Talento en el listado, incluyendo aquellas sin responsable asignado.
- **SC-003**: El 100% de los usuarios que no son responsables asignados de una retroalimentación ni tienen perfil de superusuario de Talento siguen sin ninguna capacidad de reabrirla, cerrarla o editarla (sin regresiones de permisos hacia terceros ajenos).
- **SC-004**: El 100% de las acciones de cierre y reapertura quedan trazables a quién las realizó y cuándo.

## Assumptions

- "Perfil de superusuario de Talento" corresponde a los usuarios con rol Talento o con superusuario del sistema — la misma noción ya usada hoy en el resto del dominio de Mesa de Talento y retroalimentación — y excluye explícitamente a Director.
- El listado ampliado de la Historia 2 se limita al periodo de evaluación activo, igual que el resto de las pantallas de Mesa de Talento; no se agrega en esta iteración un selector para consultar periodos históricos.
- Reabrir desde la tarjeta es una acción directa (un solo clic), sin un paso adicional de confirmación más allá del que ya exista hoy en el detalle.
- Toda acción de cierre o reapertura sigue quedando registrada (quién, cuándo), reutilizando el mecanismo de auditoría ya existente en el dominio.
- Quién puede reabrir una retroalimentación queda alineado con quién ya puede editarla/cerrarla hoy (responsable principal, responsable secundario, o superusuario de Talento); no se introduce un permiso nuevo y distinto solo para reabrir.
- "Cerrar el acuerdo" no se convierte en una acción de un solo clic desde la tarjeta en esta iteración — se asume que cerrar sigue requiriendo revisar/completar el contenido de la sesión en el detalle antes de comprometerse, tanto para responsables como para el superusuario de Talento.
