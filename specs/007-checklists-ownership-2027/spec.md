# Feature Specification: Checklists de Ownership versión 2027 (vigentes desde 2026-S2)

**Feature Branch**: `main` (directorio `007-checklists-ownership-2027`)

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Importar los 4 Excel de `docs/Checklists/Versión 2027` como versión 2 de los 16 cuestionarios de Ownership (CD/ID/PM/UXUI × JR/MID/SNR/LEAD) y publicarlos en producción. Agregar al reactivo los campos del checklist (entregable, formato, criterio de aceptación, frecuencia, comentarios/guía, expectativa por nivel); mostrarlos en el formulario de evaluación y en el editor. Conservar los títulos más específicos que ya existen cuando el Excel trae títulos genéricos; agrupar en secciones cuando haya categoría. Corregir la resincronización de cuestionario que borra respuestas. Importación repetible desde los xlsx. Entrega de Valor no cambia. Las hojas de metodología de PM quedan como material de referencia."

## Contexto: material recibido (2026-10-28)

Talento dejó en `docs/Checklists/Versión 2027/` cuatro libros (Científicos de Datos, Ingenieros de Datos, Product Management —oct 2026— y UX/UI Designer). Cada libro trae una hoja *Intro* y una hoja por nivel (Jr, Mid, Sr, Lead) con las columnas: **Actividad, Descripción, Entregable, Formato, Criterio de aceptación, Frecuencia, Comentarios, Expectativas por nivel de seniority** y, solo en Ingeniería de Datos Lead, **Categoría**. Ingeniería de Datos trae además columnas de respaldo con la redacción anterior. El libro de PM trae tres hojas extra de metodología: *Formato Prep Reuniones*, *Ejemplo Minuta* y *Rutinas de Gestión*. La versión anterior (2025) quedó en `docs/Checklists/Versión 2025/`.

Comparación contra lo publicado en producción (16 cuestionarios v1, ~420 reactivos):

- **En todas las áreas y niveles**: salen los 2 reactivos de "Cumplimiento de lineamientos de trabajo remoto" y entran "Estimación y cumplimiento de plazos" y "Apertura y aplicación de la retroalimentación" (en Ingeniería de Datos se desdoblan en 4: cumplimiento de tareas comprometidas, estimación de tiempos, apertura y aplicación de la retroalimentación).
- **Ciencia de Datos**: nuevo "QA de soluciones que utilizan IA" en los 4 niveles; renombres ("Comunicar el avance", "Aplicar estándares…"). **CD Mid v1 tenía 20 de 23 textos idénticos a CD Jr** (error del documento fuente 2025); la v2 trae textos propios de Mid.
- **Ingeniería de Datos**: redacción reescrita para ser observable (evidencias, plazos, porcentajes); 4–6 reactivos nuevos por nivel; Lead agrupado en 5 categorías.
- **Producto y UX/UI**: sin cambios de fondo salvo el par de reactivos anteriores. UX/UI Lead trae títulos genéricos repetidos ("Soporte comercial") donde la v1 tiene títulos específicos ("Soporte comercial — Construcción de propuestas").
- Entrega de Valor: sin versión nueva.
- Periodo 2026-S2 ABIERTO sin evaluaciones de Ownership; 2026-S1 CERRADO con 73 evaluaciones enviadas y 2 en borrador (PM Snr, 39 y 11 respuestas).

## Clarifications

### Session 2026-10-28

- Q: ¿Se agregan los campos del checklist al reactivo? → A: **Sí**, todos los que se necesiten.
- Q: ¿Títulos del Excel o los específicos actuales? → A: **Se conservan los específicos** (UX/UI Lead, Rutinas de Ingeniería de Datos y similares); lo demás se adapta a las convenciones del sistema.
- Q: ¿Quién valida los borradores? → A: El equipo técnico, con criterio propio. **No se dejan en borrador**: los que pasan la revisión se publican; cada cuestionario muestra su estado para saber cuál está activo.
- Q: ¿Se aplica directo en producción? → A: **Sí**, hoy mismo, con commit + push + migración.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Las evaluaciones nunca pierden respuestas por publicar una versión nueva (Priority: P1)

Talento publica una versión nueva de un cuestionario. Las evaluaciones ya iniciadas —en especial las de periodos cerrados— conservan su cuestionario y sus respuestas. Solo cuando a un colaborador le cambian área o nivel, y su evaluación sigue en borrador dentro del periodo abierto, el sistema le cambia el cuestionario al de su nuevo puesto.

**Why this priority**: Es condición para publicar la v2. Hoy, abrir una evaluación en borrador la cambia al cuestionario publicado más reciente y borra sus respuestas, aunque el periodo esté cerrado y aunque solo cambie la versión; publicar la v2 de PM Snr borraría 50 respuestas de 2026-S1.

**Independent Test**: Con una evaluación en borrador con respuestas sobre la v1, publicar la v2 del mismo puesto y abrir la evaluación: conserva v1 y sus respuestas. Cambiar el nivel del colaborador en un periodo abierto: la evaluación pasa al cuestionario del nuevo nivel. Repetirlo con el periodo cerrado: no cambia.

**Acceptance Scenarios**:

1. **Given** una evaluación en borrador sobre la v1 de PM/Snr con respuestas, **When** se publica la v2 de PM/Snr y alguien abre la evaluación, **Then** sigue en v1 con todas sus respuestas.
2. **Given** una evaluación en borrador de un periodo abierto y un colaborador que cambió de nivel, **When** se abre, **Then** pasa al cuestionario publicado del nuevo nivel (comportamiento vigente) y se avisa.
3. **Given** una evaluación en borrador de un periodo cerrado y un colaborador que cambió de nivel, **When** se abre, **Then** no se modifica.

---

### User Story 2 - El evaluador ve el criterio de aceptación de cada reactivo (Priority: P1)

Al llenar o revisar una evaluación de Ownership, cada reactivo muestra título y descripción como hoy y, además, un desplegable **"Ver criterio"** con lo que trae el checklist: criterio de aceptación, entregable esperado, formato, frecuencia, expectativa por nivel y comentarios. Así el colaborador y su evaluador califican contra el mismo estándar escrito.

**Why this priority**: Es el valor principal de los checklists 2027: el criterio de aceptación es lo que vuelve evaluable cada actividad.

**Independent Test**: Abrir una evaluación sobre la v2 de CD/Jr: el reactivo "Backlog de tareas" muestra el desplegable con su criterio y entregable; un reactivo sin datos extra no muestra desplegable.

**Acceptance Scenarios**:

1. **Given** un reactivo con criterio de aceptación, **When** se abre la evaluación, **Then** aparece "Ver criterio" cerrado; al abrirlo se ven solo los campos con contenido, cada uno con su etiqueta.
2. **Given** un reactivo de la v1 (sin campos extra), **When** se abre una evaluación de 2026-S1, **Then** se ve exactamente como antes, sin desplegable.
3. **Given** un criterio con viñetas o saltos de línea, **When** se muestra, **Then** se respetan los saltos de línea.

---

### User Story 3 - Talento edita los campos del checklist en el editor de cuestionarios (Priority: P2)

En el editor de cuestionarios, cada reactivo permite capturar y editar los mismos campos (criterio de aceptación, entregable, formato, frecuencia, expectativa por nivel, comentarios). Duplicar un cuestionario como versión nueva copia también estos campos.

**Why this priority**: Los checklists "están abiertos a mejoras" (Intro de los Excel); Talento debe poder ajustarlos sin depender del equipo técnico.

**Independent Test**: Editar el criterio de un reactivo en un borrador, guardar y verlo en la evaluación; duplicar el cuestionario y comprobar que la copia conserva los campos.

**Acceptance Scenarios**:

1. **Given** un cuestionario en borrador, **When** Talento cambia el criterio de aceptación de un reactivo y guarda, **Then** el cambio persiste.
2. **Given** un cuestionario publicado, **When** Talento lo duplica como versión nueva, **Then** la copia trae todos los campos del checklist de cada reactivo.
3. **Given** un cuestionario publicado o archivado, **When** Talento abre el editor, **Then** sigue aplicando la regla vigente de edición (solo borradores son editables).

---

### User Story 4 - Los 16 cuestionarios 2027 quedan publicados en producción (Priority: P1)

Se importan los 4 libros como **versión 2** de los 16 cuestionarios de Ownership, con sus campos de checklist, adaptados a las convenciones del sistema, se revisan y se publican. La v1 de cada puesto queda archivada (las evaluaciones de 2026-S1 la conservan). Talento ve en la lista de cuestionarios el estado de cada uno (Borrador / Publicado / Archivado). Las evaluaciones de 2026-S2 que se creen a partir de ese momento usan la v2.

**Why this priority**: Es el entregable de negocio: aplicar los checklists 2027 en el segundo semestre, hoy.

**Independent Test**: Tras la importación, la lista de cuestionarios muestra 16 Ownership v2 publicados, 16 v1 archivados y Entrega de Valor v1 publicado; crear una evaluación de 2026-S2 para un CD Jr usa la v2.

**Acceptance Scenarios**:

1. **Given** los 4 libros, **When** se ejecuta la importación, **Then** existe una v2 por cada uno de los 16 puestos con el mismo número de reactivos calificables que su hoja del Excel.
2. **Given** que la importación ya se ejecutó, **When** se vuelve a ejecutar, **Then** no crea duplicados: reconstruye la misma v2 mientras ninguno de sus reactivos tenga respuestas, y rechaza (sin tocar nada) el puesto cuya v2 ya tiene respuestas.
3. **Given** un reactivo cuyo título en el Excel es genérico y repetido dentro del mismo cuestionario (p. ej. "Soporte comercial", "Guía y soporte al equipo interno", "Rutinas de gestión y control interno"), **When** se importa, **Then** conserva el título específico de la v1 equivalente, o se le da un título específico derivado de su descripción si no existe equivalente, sin dejar títulos repetidos dentro del cuestionario.
4. **Given** una hoja con columna Categoría (ID Lead) o con Actividades repetidas (PM, CD Lead, rutinas de CD), **When** se importa, **Then** el reactivo se titula «Categoría — Subtema» (convención vigente de UX/UI Lead e ID) dentro de la sección única del cuestionario, en el orden del Excel.
5. **Given** la revisión técnica de cada v2, **When** pasa los criterios de revisión, **Then** se publica y su v1 se archiva; **When** no los pasa, **Then** queda en Borrador con la causa documentada.
6. **Given** una celda con "n/a" o vacía en Entregable/Formato, **When** se importa, **Then** el campo queda vacío (no se muestra "n/a").

---

### User Story 5 - Material de metodología de PM disponible como referencia (Priority: P3)

Las hojas de metodología del libro de PM (Formato de preparación de reuniones, Ejemplo de minuta, Rutinas de gestión) quedan documentadas en el repositorio como material de referencia, fuera de los cuestionarios, para que Talento y los PM las consulten.

**Why this priority**: Son guías de trabajo, no reactivos calificables; no bloquean la aplicación de los checklists.

**Independent Test**: El documento de referencia existe en el repositorio con el contenido de las tres hojas.

**Acceptance Scenarios**:

1. **Given** el libro de PM, **When** se termina la feature, **Then** existe un documento con las rutinas (duración, asistentes, agenda, indicadores), la estructura de minuta y el formato de preparación de reuniones.

---

### Edge Cases

- Celdas con saltos de línea o viñetas ("•") en el criterio: se conservan tal cual.
- Hojas con encabezados distintos (PM Jr trae la escala 1–4 en columnas H–K; otras traen "Calificación"): se ignoran las columnas de escala y "Calificación"; la escala sigue siendo la del cuestionario (1–4 + N/A).
- Columnas de respaldo de Ingeniería de Datos ("Descripción original", "Entregable original"): no se importan.
- Filas sin Actividad (notas sueltas, leyendas de escala en columnas L/K): se ignoran.
- Una evaluación de 2026-S2 creada antes de publicar la v2: no existe hoy (0 evaluaciones); si existiera en borrador, conserva su versión por la regla de US1.
- Reactivos que existían en la v1 y no existen en la v2 (trabajo remoto): no se borran de la v1; solo dejan de aparecer en evaluaciones nuevas.
- Textos mayores al límite de título: el título se recorta sin perder la descripción.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La resincronización automática del cuestionario de una evaluación MUST ocurrir solo si: (a) se abre en modo edición por alguien que puede editar respuestas (nunca en la vista de solo lectura), (b) la evaluación está en borrador y **nunca ha sido enviada** (una evaluación reabierta conserva su cuestionario), (c) su periodo está en estado **Abierto**, y (d) el área o el nivel del cuestionario guardado difieren del área o nivel actual del colaborador. Un cambio de versión del mismo puesto MUST NOT cambiar el cuestionario de una evaluación existente. El cambio y el borrado de respuestas ocurren en una sola operación atómica.
- **FR-002**: Cada reactivo MUST poder guardar, de forma opcional: criterio de aceptación, entregable, formato, frecuencia, expectativa por nivel y comentarios (guía).
- **FR-003**: El formulario de evaluación de Ownership (llenado y consulta) MUST mostrar esos campos en un desplegable "Ver criterio" por reactivo, solo con los campos que tengan contenido y respetando saltos de línea; sin contenido, no hay desplegable.
- **FR-004**: El editor de cuestionarios MUST permitir capturar y editar esos campos en los reactivos de cuestionarios editables; duplicar como versión nueva MUST copiarlos.
- **FR-005**: MUST existir una importación repetible en dos pasos auditables: (1) conversión de los 4 libros a un archivo de datos versionado y revisable en el repositorio; (2) carga de ese archivo como **versión 2** (llave: tipo + área + nivel + versión 2) de cada uno de los 16 puestos, reportando por puesto cuántos reactivos cargó. Si la v2 ya existe y **ningún** reactivo suyo tiene respuestas, su contenido se reconstruye (no se duplica); si alguno tiene respuestas, la carga de ese puesto se rechaza sin tocar nada. Borradores sobrantes de versiones posteriores sin respuestas (p. ej. CD Jr v3, copia de prueba de la v1) se archivan.
- **FR-006**: La importación MUST mapear áreas (Científicos de Datos→CD, Ingenieros de Datos→ID, Product Management→PM, UX/UI→UXUI) y niveles (Jr→JR, Mid→MID, Sr→SNR, Lead→LEAD).
- **FR-007**: La importación MUST garantizar títulos únicos y específicos dentro de cada cuestionario, conservando el título de la v1 cuando el reactivo equivalente tiene un título más específico.
- **FR-008**: Cada cuestionario v2 MUST tener una sola sección (como la v1). Cuando la Actividad del Excel es una categoría (columna Categoría o Actividad repetida en la hoja), el título del reactivo MUST seguir la convención vigente «Categoría — Subtema».
- **FR-014**: Publicar un cuestionario MUST validar que tiene al menos un reactivo de escala, títulos únicos y escala definida; el archivado del publicado anterior MUST quedar en el historial de cambios.
- **FR-015**: La siembra inicial de cuestionarios MUST NOT reactivar ni reconstruir una v1 cuando ya existe una versión posterior del mismo puesto; en entornos nuevos, la siembra MUST cargar también la v2 publicada.
- **FR-016**: La lista de cuestionarios MUST distinguir visualmente el estado Publicado (activo) de Borrador y Archivado.
- **FR-017**: La descripción y los campos del checklist MUST mostrarse respetando saltos de línea, en el formulario de evaluación y en el editor (también en solo lectura).
- **FR-009**: Los reactivos importados MUST ser de escala 1–4 con N/A permitido, peso 1 y obligatorios, y la escala del cuestionario MUST copiarse de la v1 del mismo puesto (mismas etiquetas, descriptores y nota de escala).
- **FR-010**: Publicar una v2 MUST archivar la v1 del mismo puesto (regla vigente: un solo publicado por puesto) sin modificar evaluaciones existentes.
- **FR-011**: MUST quedar un reporte de revisión por cuestionario (conteos, títulos ajustados, observaciones y estado resultante).
- **FR-012**: Entrega de Valor MUST NOT modificarse.
- **FR-013**: El material de metodología de PM MUST quedar documentado como referencia en el repositorio.

### Key Entities

- **Cuestionario (versión)**: puesto (área + nivel), versión, estado (Borrador / Publicado / Archivado), nota de escala, secciones, escala.
- **Sección**: agrupador ordenado de reactivos (categoría del checklist cuando existe).
- **Reactivo**: título, descripción y, nuevo, criterio de aceptación, entregable, formato, frecuencia, expectativa por nivel y comentarios; tipo, peso, permite N/A, obligatorio.
- **Evaluación de Ownership**: queda ligada a la versión de cuestionario con la que se creó; solo cambia de cuestionario por cambio de puesto en periodo abierto.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 16 de 16 cuestionarios de Ownership v2 publicados en producción el 2026-10-28, cada uno con el mismo número de reactivos que su hoja del Excel.
- **SC-002**: 0 respuestas perdidas: las 2.116 respuestas existentes (incluidas las 50 de las 2 evaluaciones en borrador de 2026-S1) siguen intactas después de publicar.
- **SC-003**: 100 % de los reactivos v2 con criterio de aceptación en el Excel lo muestran en la evaluación.
- **SC-004**: 0 títulos repetidos dentro de un mismo cuestionario v2.
- **SC-005**: Volver a correr la importación no crea registros nuevos.

## Assumptions

- Los libros 2027 son la fuente de verdad del contenido; la v1 solo aporta títulos específicos y la escala.
- Los textos del Excel se importan como vienen (sin corregir redacción), salvo recorte de espacios y "n/a" → vacío.
- La escala 1–4 + N/A no cambia (los Excel usan la misma: 1 No cumple, 2 Cumple parcial, 3 Cumple, 4 Excede expectativas).
- El peso de cada reactivo sigue siendo 1 (los Excel no traen pesos).
- La matriz de permisos no cambia: los campos nuevos se ven donde hoy se ve el reactivo y se editan donde hoy se edita.
- La migración de esquema se aplica a Neon antes del push (Vercel no corre migraciones).
- La creación de evaluaciones ya toma el cuestionario publicado más reciente del puesto: las de 2026-S2 usarán la v2 sin cambios en ese flujo.
- El formulario de evaluación es el único lugar que muestra reactivos (no hay PDF, API ni exportes que los lean); el scoring promedia respuestas sin depender de títulos, orden ni versión.
- Fuera de alcance: crear, renombrar o reordenar secciones desde el editor; escala por reactivo.

### Auditoría de la spec (2026-10-28)

Revisión adversarial contra el código (14 hallazgos). Incorporados: FR-001 (solo edición, nunca enviada, periodo Abierto, atómico), FR-005 (llave de idempotencia, rechazo si hay respuestas, borrador sobrante CD Jr v3), FR-008 (sección única + convención de título, en vez de secciones por categoría que el editor no permite administrar), FR-014 (validación y historial al publicar), FR-015 (siembra segura), FR-016 (estado visible), FR-017 (saltos de línea); FR-004 ya cubre la copia de campos al duplicar y su despliegue en solo lectura del editor. Detalle en `research.md`.
