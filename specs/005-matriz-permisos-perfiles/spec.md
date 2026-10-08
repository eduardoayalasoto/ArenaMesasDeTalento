# Feature Specification: Matriz de permisos por perfiles

**Feature Branch**: `005-matriz-permisos-perfiles`

**Created**: 2026-10-07

**Status**: Draft

**Input**: User description: "Matriz de permisos por perfiles: reemplazar los permisos fijos por rol (Colaborador/Lead/Director/Talento) por perfiles configurables por Talento. Una matriz detallada pantalla × acción (ver, crear, editar, borrar, aprobar/validar, exportar, ser asignable/etiquetable) con alcance (propio / su área / todos), cubriendo todas las pantallas del sistema. Un selector de perfiles para asignarlos a los usuarios; perfiles semilla equivalentes al comportamiento actual; el perfil Lead se vuelve flexible y puede recibir funciones que hoy solo tienen los Directores (p. ej. ver/aprobar cursos, Mesa de Talento). Incluye un registro único de permisos y una verificación automática que falle si alguna pantalla o acción no está mapeada (base para un futuro agente auditor de permisos, que queda fuera de esta spec)."

## Contexto

Hoy los permisos están **fijos en el código** y dependen de tres cosas: el rol del usuario (Colaborador, Director, Talento), su nivel (si es LEAD se le considera Lead) y relaciones puntuales, como ser evaluador asignado, responsable o validador de un proyecto, o responsable de una retroalimentación.

Cualquier ajuste, como "este Lead también puede ver la Mesa de Talento" o "este Director no aprueba cursos", requiere cambiar código y desplegar.

Esta feature convierte esas reglas en **datos administrables**:
- Un **catálogo único de permisos** que lista todas las pantallas y acciones del sistema.
- **Perfiles**: conjuntos de permisos con alcance, creados y editados por Talento desde una matriz visual.
- La **asignación de perfiles a usuarios** desde la pantalla de Usuarios.

Las **reglas relacionales** se mantienen como condición adicional, no como permiso. Por ejemplo, "solo el evaluador asignado cierra esa evaluación": un perfil puede habilitar "validar Ownership", pero solo sobre las evaluaciones donde la persona es evaluadora, salvo que su alcance sea "todos".

### Hallazgos de la auditoría del código (2026-10-07, detalle en `research-permisos-actuales.md`)

- Hay **dos definiciones de "administrador"**. Una es Talento + superusuario. La otra es Talento + superusuario + **Director**, y por ella hoy un Director puede capturar cualquier Entrega de Valor, editar cualquier proyecto y ver a todas las personas, aunque el menú no se lo muestre.
- Los **Directores no son de solo lectura**: mueven Escenario Actual y editan proyectos y Entrega de Valor, pero no editan las notas de Mesa de Talento.
- Los **Leads editan todos los proyectos**, no solo los suyos.
- **Varias pantallas no verifican rol** y dependen solo de filtrar datos. Algunos controles existen solo en la plantilla.
- **"Ser Lead" depende del nivel de seniority**: no se pueden dar funciones de Lead sin cambiar el nivel, y cambiar el nivel cambia las ponderaciones y el cuestionario. Esta feature rompe ese acoplamiento.
- La pantalla de **Ponderaciones** está en el menú pero no existe.

## Clarifications

### Session 2026-10-07

- Q: ¿Cuántos perfiles puede tener una persona? → A: **Uno solo.** Las combinaciones se resuelven creando un perfil nuevo (p. ej. "Lead + Arena Learn").
- Q: ¿Los perfiles semilla replican el comportamiento real del código (con inconsistencias) o el intencional? → A: **El intencional** (lo que el menú muestra y la regla de negocio pretende). Las inconsistencias se corrigen el día de la activación; ver FR-011a.
- Q: ¿El nivel LEAD sigue otorgando el perfil Lead? → A: **No.** Solo se usa como sugerencia al migrar y al dar de alta; después el perfil es independiente del nivel (un Senior puede tener perfil Lead sin cambiar ponderación ni cuestionario).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Talento administra la matriz de un perfil (Priority: P1)

Talento entra a **Catálogos → Perfiles y permisos** y ve una matriz.
- **Filas:** las pantallas del sistema, agrupadas por módulo (Evaluaciones, Mesa de Talento, Catálogos, Arena Learn…).
- **Columnas:** las acciones (Ver, Crear, Editar, Borrar, Aprobar/Validar, Exportar, Asignable).

Cada celda aplicable tiene un selector de alcance: **Sin acceso / Propio / Asignado / Su área / Todos**. Las celdas que no aplican a esa pantalla aparecen deshabilitadas; por ejemplo, "Exportar" en una pantalla que no exporta. Talento cambia celdas y guarda. El cambio aplica en el siguiente request de cualquier usuario con ese perfil.

**Why this priority**: es el corazón de la feature. Sin la matriz editable no hay flexibilidad.

**Independent Test**: Talento quita "Ver" de Mesa de Talento al perfil Director. Un Director ya no ve el ítem en el menú y recibe "sin acceso" si entra por la URL. Si Talento lo restablece, vuelve a verlo.

**Acceptance Scenarios**:

1. **Given** el perfil "Director" con Mesa de Talento → Ver = Todos, **When** Talento lo cambia a "Sin acceso" y guarda, **Then** los Directores dejan de ver el ítem del menú y la URL responde "sin acceso".
2. **Given** una pantalla sin acción de exportar, **When** Talento abre la matriz, **Then** esa celda aparece deshabilitada y no se puede activar.
3. **Given** Talento cambia una celda, **When** guarda, **Then** el cambio queda en una bitácora: quién, cuándo, valor anterior y valor nuevo.
4. **Given** el perfil que contiene "Administrar perfiles y permisos", **When** Talento intenta quitarse ese permiso a sí mismo y deja al sistema sin nadie que pueda administrar la matriz, **Then** el sistema lo impide con un mensaje claro.

---

### User Story 2 - Asignar perfiles a usuarios con un selector (Priority: P1)

En **Usuarios**, Talento ve el perfil de cada persona y lo cambia con un selector, individual o en asignación masiva con filtro. Al dar de alta un usuario, el perfil se propone según su rol y nivel actuales: un nivel LEAD propone el perfil Lead.

**Why this priority**: sin asignación, los perfiles no tienen efecto. Junto con US1 forma el MVP.

**Independent Test**: asignar el perfil "Lead extendido" a un Lead y verificar que gana exactamente los permisos del perfil.

**Acceptance Scenarios**:

1. **Given** un usuario con perfil "Colaborador", **When** Talento le asigna "Lead", **Then** desde su siguiente request ve las pantallas del perfil Lead.
2. **Given** un filtro activo en Usuarios, **When** Talento guarda una asignación masiva, **Then** solo cambian los usuarios visibles. Se preserva la regla vigente de no tocar filas que no llegaron en el envío.
3. **Given** un usuario sin perfil asignado, **When** entra al sistema, **Then** recibe el perfil mínimo "Colaborador". El sistema falla cerrado y nunca otorga más permisos por omisión.

---

### User Story 3 - Perfiles semilla con paridad exacta al comportamiento actual (Priority: P1)

Al activar la feature, el sistema crea los perfiles **Colaborador, Lead, Director, Talento** y el **Superusuario**, que es de sistema y no se puede editar ni quitar. Cada perfil replica lo que cada rol **debe** poder hacer hoy (el comportamiento intencional), y cada usuario recibe el perfil que corresponde a su rol y nivel actuales. Solo se pierden los accesos accidentales listados en FR-011a, con aviso previo a Talento.

**Why this priority**: es la condición para desplegar sin romper la operación de un periodo en curso.

**Independent Test**: una batería de pruebas de acceso recorre cada pantalla y acción con un usuario de cada rol, antes y después de la migración. Los resultados deben ser idénticos, salvo las correcciones intencionales listadas en FR-011a.

**Acceptance Scenarios**:

1. **Given** el sistema antes y después de activar los perfiles semilla, **When** se recorre la batería de acceso, **Then** el 100% de los casos dan el mismo resultado, salvo las correcciones de FR-011a, que aparecen listadas como cambios esperados.
2. **Given** un Director, **When** se activan los perfiles, **Then** sigue viendo Mesa de Talento, Escenario Actual y el Seguimiento de Arena Learn, igual que hoy.

---

### User Story 4 - Lead flexible: funciones antes exclusivas de Dirección (Priority: P2)

Talento puede dar al perfil **Lead**, o crear un perfil "Lead extendido", permisos que hoy solo tienen los Directores:
- ver la Mesa de Talento de **su área**;
- aprobar solicitudes de curso en la etapa de Dirección;
- ver el Seguimiento de Arena Learn de su área;
- consultar Escenario Actual.

El alcance "Su área" acota lo que ve un Lead a las personas de su área.

**Why this priority**: es el caso de negocio que motivó la feature. Depende de US1 y US2.

**Independent Test**: dar a "Lead" el permiso Mesa de Talento → Ver = Su área. El Lead ve solo a las personas de su área y recibe "sin acceso" con la de otra área.

**Acceptance Scenarios**:

1. **Given** el perfil Lead con Mesa de Talento → Ver = Su área, **When** un Lead de PM abre la Mesa de Talento, **Then** solo ve personas de PM.
2. **Given** el perfil Lead con Arena Learn → Aprobar (Dirección) = Su área, **When** una solicitud de su área llega a la etapa Dirección, **Then** el Lead la ve en "Aprobar cursos" y puede decidirla, y la bitácora lo registra como aprobador de esa etapa.
3. **Given** el mismo Lead, **When** la solicitud es de otra área, **Then** no aparece en su bandeja.

---

### User Story 5 - Permisos "asignables" (etiquetables) (Priority: P2)

La columna **Asignable** define quién puede ser elegido en los selectores del sistema:
- evaluador de Ownership;
- responsable, validador u owner de un proyecto;
- responsable de retroalimentación;
- Lead directo;
- Director de área;
- aprobador reasignado de Arena Learn.

Así Talento controla, por ejemplo, que solo los perfiles con "Asignable como Director de área" aparezcan en ese selector.

**Why this priority**: evita asignaciones inválidas y hace explícito quién puede recibir responsabilidades. Hoy esa regla está dispersa o ni siquiera existe.

**Independent Test**: quitar "Asignable como Validador de Entrega de Valor" al perfil Lead. Los Leads dejan de aparecer en el selector de Validador de proyecto, y las asignaciones previas se conservan con una alerta para Talento.

**Acceptance Scenarios**:

1. **Given** un perfil sin "Asignable como evaluador de Ownership", **When** un colaborador elige evaluador, **Then** las personas con ese perfil no aparecen en la lista.
2. **Given** una asignación existente que deja de ser válida tras un cambio de perfil, **When** Talento guarda el cambio, **Then** la asignación se conserva, el sistema muestra cuántas quedaron "fuera de perfil" y lista dónde están para que Talento decida.

---

### User Story 6 - Registro único y verificación automática de cobertura (Priority: P1)

Toda pantalla y toda acción del sistema existen en un **registro único de permisos**. Una verificación automática, que corre con la batería de pruebas, **falla** si:
- (a) una pantalla o acción del sistema no tiene permiso registrado;
- (b) un permiso registrado ya no corresponde a ninguna pantalla;
- (c) una pantalla no verifica su permiso al atender la solicitud.

**Why this priority**: sin esta garantía, la matriz se desactualiza con la primera pantalla nueva y deja huecos de seguridad. Es la base del futuro agente auditor.

**Independent Test**: agregar una pantalla nueva sin registrar su permiso. La verificación falla y nombra la pantalla.

**Acceptance Scenarios**:

1. **Given** una pantalla nueva sin permiso registrado, **When** corre la verificación, **Then** falla e indica la pantalla faltante.
2. **Given** el sistema actual, **When** corre la verificación, **Then** el 100% de las pantallas y acciones están mapeadas.

---

### User Story 7 - Ver "qué puede hacer esta persona" (Priority: P3)

Desde Usuarios, Talento abre a una persona y ve su **resumen de acceso efectivo**: perfil, permisos por módulo con su alcance y las responsabilidades relacionales vigentes, como evaluaciones donde es evaluadora o proyectos donde es responsable.

**Why this priority**: soporte y auditoría. Responde "¿por qué Ana no ve X?" sin revisar código.

**Independent Test**: abrir el resumen de un Lead y confirmar que coincide con lo que realmente puede abrir.

**Acceptance Scenarios**:

1. **Given** una persona con perfil Lead y dos proyectos como responsable, **When** Talento abre su resumen, **Then** ve los permisos del perfil y las dos responsabilidades.

---

### Edge Cases

- **Sin perfil o perfil eliminado:** el usuario cae al perfil mínimo "Colaborador". Un perfil con usuarios asignados no se puede eliminar; primero hay que reasignarlos.
- **Superusuario:** siempre tiene todo. Su perfil no aparece como editable y no se puede asignar desde la pantalla de Usuarios.
- **Auto-bloqueo:** no se puede guardar una configuración que deje al sistema sin nadie con "Administrar perfiles y permisos". El superusuario siempre conserva este permiso.
- **Reglas relacionales:** un permiso con alcance "Asignado" solo aplica a los registros donde la persona tiene la relación (evaluador, responsable, validador, aprobador de la etapa). "Todos" ignora la relación.
- **Periodo Cerrado:** las reglas de inmutabilidad y de corrección con motivo de la spec 002 siguen vigentes **además** de la matriz. Un perfil con "Editar" no salta la inmutabilidad de un periodo Cerrado. Solo "Corregir periodo cerrado" lo permite, con motivo.
- **Cambios en caliente:** si a alguien le quitan un permiso mientras tiene una pantalla abierta, su siguiente acción se rechaza con un mensaje claro y no se pierden datos ya guardados.
- **Menú y botones:** el menú, los botones y la campana se derivan de la misma matriz. Nunca se muestra un acceso que la pantalla luego niega, ni se permite una acción cuyo botón está oculto.
- **Datos privados de Arena Learn:** costo, pago y justificación siguen siendo un permiso aparte ("Ver datos privados de cursos"), distinto de "Ver cursos".
- **Exportes:** exportar requiere su propio permiso. Lo exportado respeta el alcance: un Lead con "Su área" solo exporta su área.
- **Ponderaciones:** el menú hoy referencia una pantalla de Ponderaciones que no existe. Se registra en la matriz como pantalla pendiente, deshabilitada, hasta que exista.

## Requirements *(mandatory)*

### Functional Requirements

#### Catálogo de permisos (US6)

- **FR-001**: El sistema MUST mantener un registro único de permisos con, para cada pantalla: módulo, nombre de negocio, acciones aplicables (Ver, Crear, Editar, Borrar, Aprobar/Validar, Exportar, Asignable u otras específicas como Reabrir, Reiniciar, Reasignar, Corregir periodo cerrado) y alcances permitidos por acción.
- **FR-002**: El registro MUST cubrir el 100% de las pantallas y acciones del sistema (ver el Anexo A, inventario mínimo).
- **FR-003**: Una verificación automática MUST fallar si existe una pantalla o acción sin permiso registrado, un permiso registrado sin pantalla, o una pantalla que no verifica su permiso al atender la solicitud.

#### Perfiles y matriz (US1)

- **FR-004**: Talento MUST poder crear, renombrar, duplicar, editar y eliminar perfiles. El Superusuario es de sistema e inmutable.
- **FR-005**: La matriz MUST mostrar pantallas agrupadas por módulo y acciones como columnas, con un selector de alcance por celda: Sin acceso < Propio < Asignado < Su área < Todos (cada uno incluye a los anteriores), limitado a los alcances que la acción permite.
- **FR-006**: Cada cambio en la matriz o en la asignación de perfiles MUST quedar en una bitácora: quién, cuándo, perfil, permiso, valor anterior y valor nuevo.
- **FR-007**: El sistema MUST impedir guardar una configuración que deje sin ningún usuario activo con "Administrar perfiles y permisos" (además del superusuario).
- **FR-008**: Un cambio en la matriz MUST aplicar a partir del siguiente request de los usuarios afectados, sin necesidad de volver a iniciar sesión.

#### Asignación (US2)

- **FR-009**: Cada usuario MUST tener **exactamente un perfil** asignado desde Usuarios, con selector individual y asignación masiva respetando filtros.
- **FR-010**: Un usuario sin perfil válido MUST recibir el perfil mínimo "Colaborador". El sistema falla cerrado.

#### Paridad (US3)

- **FR-011**: La activación MUST crear los perfiles semilla Colaborador, Lead, Director, Talento y Superusuario, asignar a cada usuario el perfil que corresponde a su rol y nivel actuales, y reproducir el **comportamiento intencional** (el que muestra el menú y pretende la regla de negocio) documentado en `research-permisos-actuales.md`.
- **FR-011a**: Las inconsistencias actuales se corrigen al activar, y la batería de paridad las trata como cambios **esperados**, no como regresiones:
  - **Directores ya no capturan cualquier Entrega de Valor**: solo la de proyectos donde son Responsables, salvo que su perfil diga otra cosa. Producción: hay 1 caso histórico, Urrea Bolsa de Horas, 2026-S1, capturado por Héctor Rangel y ya VALIDADO, que se conserva intacto.
  - **Accesos solo por URL dejan de funcionar**: pantallas que hoy se abren escribiendo la dirección aunque el menú no las muestre, como "Mis evaluaciones" para Director y Talento, "Mi área" para Colaborador, el exporte de calificaciones para Colaborador y las listas de validación sin asignaciones. Pasan a "sin acceso".
  - **Una sola definición de "administrador"** (Talento + superusuario). El Director conserva solo lo que su perfil le concede explícitamente.
  - Lo que **no** cambia porque sí es intencional: el Director ve y mueve Escenario Actual, ve la Mesa de Talento y edita proyectos; el Lead edita proyectos.
- **FR-011b**: Antes de activar, el sistema MUST generar un reporte para Talento con cada acceso que se pierde (persona, pantalla y uso histórico, si lo hay), para comunicarlo a los afectados.
- **FR-012**: MUST existir una batería de pruebas de acceso (rol × pantalla × acción) cuyo resultado sea idéntico antes y después de la activación.
- **FR-013**: El nivel de seniority MUST seguir determinando cuestionarios y ponderaciones. A partir de esta feature, las capacidades de "Lead" las define **solo el perfil asignado**. El nivel LEAD únicamente sugiere el perfil Lead al migrar y al dar de alta a alguien.

#### Evaluación de permisos y alcance

- **FR-014**: Toda pantalla y acción MUST verificar su permiso en el servidor. Ocultar el botón nunca basta.
- **FR-015**: El alcance MUST aplicarse al filtrar listados y al abrir registros individuales. "Su área" se limita al área del usuario; "Asignado" se limita a registros con relación vigente; "Propio" se limita a los registros de la persona.
- **FR-016**: El menú lateral, la campana de pendientes y los botones de acción MUST derivarse de los mismos permisos que las pantallas.
- **FR-017**: Las reglas de inmutabilidad de periodo Cerrado (spec 002) y las reglas de flujo (p. ej. nadie aprueba su propia solicitud de curso) MUST seguir aplicando además de la matriz.

#### Lead flexible (US4)

- **FR-018**: La matriz MUST permitir asignar a cualquier perfil, incluido Lead, los permisos hoy exclusivos de Dirección: Mesa de Talento (ver y editar), Escenario Actual, validar Entrega de Valor, aprobar cursos en la etapa Dirección, Seguimiento de Arena Learn y los exportes correspondientes, con alcance "Su área" o "Todos".
- **FR-019**: En Arena Learn, la etapa Dirección MUST resolverse con quienes tengan "Aprobar cursos — etapa Dirección" con el alcance adecuado, en lugar de por el rol Director. Se conserva la preferencia por el Director asignado al área.

#### Asignables (US5)

- **FR-020**: Los selectores de personas MUST listar solo a quienes tienen el permiso "Asignable como …" correspondiente. Aplica a: evaluador de Ownership, responsable, validador y owner de proyecto, responsable de retroalimentación, Lead directo, Director de área y aprobador reasignado de Arena Learn.
- **FR-021**: Cuando un cambio de perfil deja asignaciones existentes "fuera de perfil", el sistema MUST conservarlas y mostrar a Talento cuántas son y dónde están.

#### Acceso efectivo (US7)

- **FR-022**: Talento MUST poder consultar, por persona, su acceso efectivo: perfil, permisos con alcance y responsabilidades relacionales vigentes.

### Key Entities

- **Permiso (catálogo)**: pantalla y acción, con módulo, nombre de negocio, alcances permitidos y estado (activa o pendiente). Lo define el sistema, no Talento.
- **Perfil**: nombre, descripción, si es de sistema, y el conjunto de concesiones.
- **Concesión**: un permiso dentro de un perfil con su alcance (Sin acceso, Propio, Su área, Asignado o Todos).
- **Asignación de perfil**: la relación usuario ↔ perfil, con fecha y autor.
- **Bitácora de permisos**: cambios a perfiles, concesiones y asignaciones.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las pantallas y acciones del sistema aparecen en la matriz, y la verificación automática lo comprueba en cada corrida de pruebas.
- **SC-002**: El día de la activación, el 100% de los casos de la batería de acceso (rol × pantalla × acción) dan el mismo resultado que antes, salvo las correcciones intencionales de FR-011a, todas listadas en el reporte previo.
- **SC-003**: Talento cambia un permiso de un perfil en menos de 1 minuto, sin intervención técnica ni despliegue.
- **SC-004**: Talento responde "¿por qué esta persona no ve X?" en menos de 2 minutos desde el resumen de acceso efectivo.
- **SC-005**: Ninguna pantalla muestra un acceso que luego niegue, ni permite una acción cuyo control está oculto (verificable con la batería de acceso).
- **SC-006**: Agregar una pantalla nueva sin registrar su permiso hace fallar la verificación el 100% de las veces.

## Assumptions

- La matriz la administra Talento. Los Directores no editan perfiles salvo que un perfil se los conceda.
- El alcance "Su área" usa el área del usuario. Un usuario sin área tiene "Su área" vacía.
- El rol actual (Colaborador, Director o Talento) se conserva como dato histórico, pero deja de decidir permisos tras la activación.
- Las reglas de negocio que no son permisos se mantienen en código: ponderaciones, bandas, inmutabilidad de periodos y "nadie se aprueba a sí mismo".
- El inicio de sesión, el cambio de contraseña y "Mi perfil" son accesibles para todo usuario autenticado y no se configuran en la matriz.
- **Fuera de alcance:** el agente auditor de permisos (spec posterior), permisos a nivel de campo individual y una API externa de permisos.

## Anexo A — Inventario mínimo de pantallas y acciones a registrar

| Módulo | Pantalla | Acciones |
|---|---|---|
| General | Mi tablero (resultados) | Ver (Propio) |
| General | Resultados de otra persona | Ver (Su área/Todos) |
| General | Mi área | Ver (Su área/Todos), Exportar |
| General | Ayuda | Ver (todos) |
| Evaluaciones | Mis evaluaciones de Ownership | Ver, Crear, Editar (Propio); elegir evaluadores |
| Evaluaciones | Validación de Ownership | Ver, Editar, Validar/Cerrar (Asignado/Todos) |
| Evaluaciones | Evaluación de Ownership — administración | Reabrir, Reiniciar, Reiniciar por usuario, Corregir periodo cerrado |
| Evaluaciones | Entrega de Valor — captura | Ver, Crear, Editar (Asignado como responsable/Todos) |
| Evaluaciones | Entrega de Valor — validación | Ver, Validar, Regresar, Comentar (Asignado como validador/Todos) |
| Evaluaciones | Impacto Arena | Ver, Editar (Todos) |
| Retroalimentación | Lista de retroalimentación | Ver (Propio/Asignado/Todos) |
| Retroalimentación | Detalle de sesión | Ver, Editar, Reabrir (Asignado/Todos) |
| Mesa de Talento | Mesa de Talento (tabla) | Ver (Su área/Todos) |
| Mesa de Talento | Ficha de persona: notas, escenarios, proyectos revisados, responsables | Ver, Editar (Su área/Todos) |
| Mesa de Talento | Escenario Actual (tablero) | Ver, Mover (Su área/Todos) |
| Mesa de Talento | Avance del periodo | Ver (Todos) |
| Mesa de Talento | Exporte de calificaciones | Exportar (Su área/Todos) |
| Catálogos | Usuarios | Ver, Crear, Editar, Borrar, Resetear contraseña, Asignar perfil |
| Catálogos | Proyectos | Ver, Crear, Editar, Cerrar/Reabrir, Borrar |
| Catálogos | Periodos | Ver, Crear, Editar, Abrir/Cerrar, Borrar |
| Catálogos | Áreas | Ver, Editar (Director de área) |
| Catálogos | Escenarios | Ver, Crear, Editar, Activar/Desactivar, Borrar |
| Catálogos | Cuestionarios | Ver, Editar, Versionar/Publicar |
| Catálogos | Ponderaciones | Ver, Editar *(pantalla pendiente: hoy no existe)* |
| Catálogos | Perfiles y permisos *(nueva)* | Ver, Crear, Editar, Borrar, Asignar |
| Arena Learn | Mis cursos / solicitar / registrar ya tomado | Ver, Crear, Editar, Cancelar (Propio) |
| Arena Learn | Aprobar cursos — etapa Lead | Ver, Aprobar/Regresar/Rechazar (Asignado/Su área/Todos) |
| Arena Learn | Aprobar cursos — etapa Dirección | Ver, Aprobar/Regresar/Rechazar (Su área/Todos) |
| Arena Learn | Aprobar cursos — etapa Talento | Ver, Aprobar/Regresar/Rechazar (Todos) |
| Arena Learn | Todas las solicitudes en revisión | Ver (Su área/Todos), Reasignar aprobador |
| Arena Learn | Datos privados de cursos (costo, pago, justificación, comprobante) | Ver (Propio/Asignado/Su área/Todos) |
| Arena Learn | Pago del curso | Editar (Propio/Todos) |
| Arena Learn | Evidencias | Ver (público/privado), Validar/Regresar (Todos), Reemplazar (Propio) |
| Arena Learn | Catálogo de cursos | Ver (todos), Crear, Editar, Archivar, Promover |
| Arena Learn | Personas y perfil público | Ver (todos) |
| Arena Learn | Seguimiento | Ver, Exportar (Su área/Todos) |
| Arena Learn | Carga histórica | Crear (Todos) |
| Arena Learn | Instrucciones fiscales | Editar (Todos) |
| Asignables | Evaluador de Ownership, responsable/validador/owner de proyecto, responsable de retroalimentación, Lead directo, Director de área, aprobador reasignado | Asignable |

La paridad exacta, ruta por ruta, se documenta en `research-permisos-actuales.md`.
