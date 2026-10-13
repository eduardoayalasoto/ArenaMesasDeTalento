# Feature Specification: Arena Learn — planes anuales de capacitación por área, etiquetas gestionables e importación del catálogo

**Feature Branch**: `006-arena-learn-planes-anuales`

**Created**: 2026-10-12

**Status**: Draft

**Input**: User description: "Talento recibió la información completa de los planes de capacitación por año y por área (PM, UX/UI, Ingeniería de Datos, Ciencia de Datos / Ingeniería de IA), el catálogo de cursos por área y el avance de algunos colaboradores. Adaptar Arena Learn para alojar planes anuales por área, que cada colaborador arme su plan personal a partir del de su área, fortalecer las etiquetas como componente gestionable (autocompletable, varias por elemento) usado como filtro de búsqueda —la única etiqueta que se asigna al importar es 'KO' para los cursos sugeridos por el programa KO Upskilling—, importar el catálogo y los planes recibidos y, al final, los cursos ya tomados por los colaboradores."

## Contexto: material recibido (2026-10-12)

Talento entregó, en la carpeta *Información de plan de capacitación – Arena*:

1. **`Catalogo_Cursos_Plataforma_Capacitacion.xlsx`** — 4 hojas, una por área (PM, UX-UI, ID, CD); 346 filas (~250 cursos distintos) con nombre, liga, plataforma, tipo de aprendizaje y grupo dentro del plan. La hoja ID combina dos rutas: las filas "Ingeniería de Datos" (47) son del área ID y las filas "Ingeniería de IA" (87) son el plan de IA, que corresponde al área CD (86 de ellas ya están en la hoja CD); 7 cursos son de ambas.
2. **Cuatro planes en HTML** (PM, UX/UI, Ingeniería de IA, Ingeniería de IA + Ingeniería de Datos) — periodo del plan (abr/may–dic 2026), horas por semana sugeridas, tipos de aprendizaje (Estructurado/Horizontal, Certificado/Vertical, Puntual, Contextual, Soft Skills), **nivel recomendado por curso** en PM y UX/UI, **certificaciones** que no vienen en el Excel (PMP, PL-300, DP-900, AI-900/901, AI-103, AI-300, Claude Certified Architect, Google UX, DP-700, DP-203, Databricks DE Associate, AZ-400) y los cursos del **programa KO Upskilling**.
3. **Cursos actuales por colaborador (oct 2026)** — acceso a una lista de SharePoint; el contenido aún no se exporta. Se atiende al final (User Story 6).

Todos los planes son explícitamente **catálogos sugeridos**, no currículas obligatorias: cada colaborador elige según su nivel, proyectos y tiempo disponible.

## Clarifications

### Session 2026-10-12

- Q: ¿Qué se modela como etiqueta? → A: Solo lo que no es característica propia del curso y sirve como filtro. Al importar, **la única etiqueta asignada es "KO"** (curso sugerido por el programa KO Upskilling). Es informativa: no restringe quién puede tomar el curso. Gratuito/de pago, licencias, formato o marcas **no** se etiquetan.
- Q: ¿"Todos los niveles" es etiqueta? → A: No. Un curso sin niveles recomendados se entiende y se muestra como "Todos los niveles".
- Q: ¿Ingeniería de IA / Ingeniería de Datos son etiquetas? → A: No; son áreas internas de Arena. Las filas "Ingeniería de Datos" van al área ID y las de "Ingeniería de IA" al área CD.
- Q: ¿Cómo son las etiquetas? → A: Sencillas: solo un nombre, varias por elemento, con campo autocompletable que sugiere las existentes y permite crear nuevas ahí mismo. Talento las mantiene (renombrar, fusionar, desactivar). Sin grupos ni campos adicionales.
- Q: ¿Se modelan los pilares/dominios de cada plan? → A: No. Quedan fuera de alcance.
- Q: Si el catálogo de la plataforma tiene más atributos que los recibidos (costo, duración, tipo, etc.) → A: Se conservan; es una mejora sobre el material actual. Los cursos importados los dejan vacíos hasta que Talento los complete.
- Q: Dos versiones del plan de IA (v4 y v2) → A: Se importa la unión; cada curso existe una sola vez en el catálogo.
- Q: ¿Los cursos KO van en una sección propia del plan? → A: **No.** KO es solo una etiqueta. No existe agrupación KO: todos los cursos, sean KO o no, siguen la misma estructura y lineamientos de las guías HTML (tipo de aprendizaje y nivel recomendado). Los 20 cursos que el plan PM solo lista en su bloque "KO Upskilling" se clasifican con el criterio técnico (ver Assumptions).
- Q: ¿Dónde vive el nivel recomendado? → A: **Solo en el plan.** El curso del catálogo describe lo propio de la plataforma (nombre, liga, proveedor, tipo, duración, costo); asignar nivel es un criterio de Talento, puede variar por área y corregirse sin tocar el curso. El curso del catálogo deja de tener niveles.
- Q: ¿Los planes importados quedan en borrador? → A: **No.** Son los planes vigentes en producción: se importan **publicados**.
- Q: ¿El curso del catálogo conserva el pilar (Ownership / Entrega de Valor / Impacto Arena)? → A: **No.** Es criterio de Talento, no dato de la plataforma, y el material no lo trae. Se quita del catálogo. La solicitud del colaborador conserva "pilar que fortalece".
- Q: ¿El tipo de curso y las secciones de las guías (Estructurado, Certificado, Puntual, Contextual…) no se duplican? → A: **Sí, se duplicaban.** Queda **un solo dato del curso: Tipo de aprendizaje**, con nombre único en todos los planes: Estructurado, Certificación, Puntual, Contextual, Soft Skills y Evento. Reemplaza al tipo anterior (Curso, Certificación, Capacitación, Conferencia, Otro). "Habilidades Blandas" se llama **Soft Skills**. Los planes **no tienen secciones propias**: agrupan sus cursos por tipo de aprendizaje.
- Q: ¿Horizontal/Vertical es lo mismo que Estructurado/Certificación? → A: **No.** Son dos dimensiones distintas que **no se combinan ni se derivan una de otra**. **Tipo de aprendizaje** (Estructurado, Certificación, Puntual, Contextual, Soft Skills y Evento) dice qué clase de aprendizaje es. **Enfoque** (Horizontal = amplitud, Vertical = profundidad) dice si el curso da amplitud o profundidad. Todo curso lleva ambos datos. Cuando la guía dice "Aprendizaje Horizontal" o "Aprendizaje Vertical", eso es el **enfoque** del curso, no su tipo.
- Q: ¿Qué pasa con los datos de prueba actuales de Arena Learn? → A: Se borran antes de importar (cursos de catálogo, solicitudes, registros, pasos de aprobación, evidencias, reseñas y su historial). La configuración de Arena Learn se conserva. Las clasificaciones que falten las define el equipo técnico con criterio propio y quedan documentadas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Etiquetas gestionables y filtro por etiqueta (Priority: P1)

Cualquier persona que da de alta o edita un curso (Talento en el catálogo, el colaborador en su solicitud o registro) asigna **una o varias etiquetas** con un campo autocompletable: al escribir ve las etiquetas existentes y elige; si no existe, la crea en el momento. En el catálogo y en los planes, cualquier usuario filtra por una o varias etiquetas. Talento administra la lista de etiquetas: ve cuántos cursos usa cada una, la renombra, fusiona duplicados y desactiva las que ya no deben ofrecerse.

**Why this priority**: Es la base transversal del módulo: la importación (US4) depende de ella para marcar "KO", y el texto libre actual genera duplicados ("power bi" / "PowerBI") que impiden filtrar.

**Independent Test**: Talento crea "KO" desde el campo de un curso, la asigna a otros dos cursos escribiendo "ko"; un colaborador filtra el catálogo por "KO" y ve exactamente esos tres; Talento fusiona "PowerBI" en "Power BI" y los cursos de ambas quedan bajo "Power BI".

**Acceptance Scenarios**:

1. **Given** existen las etiquetas "KO" y "Power BI", **When** un usuario escribe "po" en el campo de etiquetas, **Then** se le sugiere "Power BI" y puede elegirla sin teclearla completa.
2. **Given** no existe la etiqueta "dbt", **When** el usuario escribe "dbt" y confirma, **Then** la etiqueta se crea y queda asignada al elemento.
3. **Given** un curso con las etiquetas "KO" y "Power BI", **When** se filtra el catálogo por "KO", **Then** el curso aparece; al filtrar por "KO" y "Fabric", solo aparecen cursos que tengan ambas.
4. **Given** las etiquetas "PowerBI" (3 cursos) y "Power BI" (5 cursos, 1 en común), **When** Talento fusiona "PowerBI" en "Power BI", **Then** "Power BI" queda en 7 cursos sin duplicados y "PowerBI" desaparece.
5. **Given** una etiqueta desactivada, **When** un usuario escribe su nombre, **Then** no se le sugiere ni se puede crear otra con el mismo nombre; los elementos que ya la tenían la conservan visible.
6. **Given** que las etiquetas de texto libre actuales solo existen en datos de prueba, **When** se lanza esta versión, **Then** el texto libre desaparece de cursos y solicitudes y solo quedan etiquetas gestionables.

---

### User Story 2 - Planes anuales por área (Priority: P1)

Talento publica, para cada área y año, un **plan de capacitación**: periodo (mes inicial y final), horas por semana sugeridas, una introducción breve, un texto opcional por tipo de aprendizaje (el de su guía) y la lista de cursos sugeridos con su orden. La vista del plan **agrupa los cursos por su tipo de aprendizaje** (Estructurado, Certificación, Puntual, Contextual, Soft Skills y Evento) en un orden fijo. Cada curso del plan puede indicar los niveles para los que es prioritario (Jr, Mid, Snr, Lead); sin niveles, aplica a todos. Cualquier colaborador consulta el plan de su área (y los de otras áreas), filtrando por tipo, nivel y etiqueta.

**Why this priority**: Es el cambio central que pide el material recibido: hoy Arena Learn solo maneja solicitudes curso por curso, sin noción de plan anual por área.

**Independent Test**: Talento crea el plan PM 2026 (may–dic, 3–10 h/semana) con cinco cursos de tres tipos distintos y con niveles; un PM Jr abre "Planes", ve el plan de su área agrupado por tipo, filtra por nivel Jr y por la etiqueta "KO".

**Acceptance Scenarios**:

1. **Given** un área sin plan 2026, **When** Talento crea el plan con periodo, horas y cursos del catálogo, **Then** el plan queda en borrador, visible solo para quien gestiona planes, hasta que lo publique.
2. **Given** un plan publicado, **When** un colaborador del área entra a Planes, **Then** ve primero el plan vigente de su área, agrupado por tipo de aprendizaje y, por curso, plataforma, liga, enfoque, niveles recomendados ("Todos los niveles" si no hay) y etiquetas.
3. **Given** un curso que aparece en los planes de PM y CD con niveles distintos, **When** se consulta cada plan, **Then** cada uno muestra sus propios niveles para ese curso.
4. **Given** el plan PM 2026, **When** Talento intenta crear otro plan PM 2026, **Then** el sistema lo impide e indica que ya existe uno para esa área y año.
5. **Given** un plan publicado del que un colaborador ya eligió cursos, **When** Talento quita un curso del plan, **Then** el curso deja de mostrarse en el plan pero se conserva en los planes personales que ya lo incluían.
6. **Given** un plan de un año anterior, **When** Talento lo archiva, **Then** sigue consultable como histórico pero ya no admite nuevas selecciones.

---

### User Story 3 - Mi plan: el colaborador arma y sigue su plan personal (Priority: P2)

El colaborador entra a **Mi plan** del año, agrega cursos desde el plan de su área (o de cualquier otro plan o del catálogo) y ve cada uno con su avance: Pendiente, En curso o Completado, más Descartado si decide no tomarlo. El avance se toma de lo que ya registra en Arena Learn: al iniciar un curso elige "Solicitar autorización" (si tiene costo, abre la solicitud con autorización existente) o "Empezar" (sin costo, pasa a En curso); al cerrarlo sube evidencia y reseña con el flujo de registro existente. Su Lead, Talento y Dirección consultan Mi plan de cada persona.

**Why this priority**: Da sentido al plan de área (US2) en el día a día, pero el plan por sí solo ya es útil como catálogo guiado; por eso va después.

**Independent Test**: Un colaborador agrega 4 cursos del plan de su área a Mi plan 2026, inicia uno gratuito (pasa a En curso), solicita uno con costo (queda En revisión del Lead), completa el gratuito con evidencia y reseña (pasa a Completado) y descarta otro; su Lead ve ese mismo estado.

**Acceptance Scenarios**:

1. **Given** el plan publicado de su área, **When** el colaborador agrega un curso a Mi plan, **Then** el curso aparece como Pendiente en Mi plan del año del plan.
2. **Given** un curso Pendiente, **When** el colaborador lo inicia con "Empezar" (sin costo), **Then** pasa a En curso sin requerir autorización.
3. **Given** un curso Pendiente, **When** el colaborador lo inicia con "Solicitar autorización" (tiene costo), **Then** se abre la solicitud de curso con los datos precargados y Mi plan muestra el estado de esa solicitud (p. ej. "En revisión del Lead").
4. **Given** un curso En curso, **When** el colaborador registra evidencia y reseña, **Then** el curso queda Completado en Mi plan y en su perfil de Arena Learn.
5. **Given** que el colaborador ya tiene completado un curso, **When** lo agrega a Mi plan, **Then** aparece directamente como Completado.
6. **Given** un curso en Mi plan, **When** el colaborador lo descarta, **Then** queda como Descartado y no cuenta como pendiente; puede reactivarlo después.
7. **Given** Mi plan de una persona, **When** su Lead, Talento o un Director lo consulta, **Then** ve los cursos y su avance; **When** otro colaborador sin esos permisos intenta verlo, **Then** el sistema lo impide (lo público sigue siendo solo la sección Arena Learn del perfil).

---

### User Story 4 - Importación del catálogo y de los planes recibidos (Priority: P1)

Antes de la primera carga se borran los datos de prueba de Arena Learn. Después se cargan los archivos recibidos (el Excel del catálogo y los cuatro planes): el sistema da de alta los cursos sin duplicarlos, los incluye en el plan del área de cada hoja, crea y **publica** los planes 2026 de cada área con sus cursos, niveles recomendados y certificaciones, y marca con la etiqueta "KO" los cursos del programa KO Upskilling, que reciben un tipo de aprendizaje como el resto. Al terminar se ve un resumen: cursos creados y actualizados, planes, y filas que no se pudieron interpretar. Si se corrigen los archivos y se vuelven a cargar, no se duplica nada.

**Why this priority**: Sin la carga, Talento tendría que capturar a mano ~250 cursos y 4 planes. Los planes ya están vigentes y la plataforma debe reflejarlos desde el día uno.

**Independent Test**: Tras borrar los datos de prueba, cargar los archivos recibidos produce ~250 cursos únicos más las certificaciones, 4 planes 2026 publicados (PM, UX/UI, ID, CD), sin agrupación KO, y la etiqueta "KO" en los cursos del programa. Repetir la carga no crea ningún curso nuevo.

**Acceptance Scenarios**:

1. **Given** un curso que aparece en las hojas CD e ID con la misma liga, **When** se importa, **Then** existe una sola vez en el catálogo, presente en ambos planes, y su ficha muestra ambas áreas.
2. **Given** las filas de la hoja ID marcadas "Ingeniería de IA", **When** se importan, **Then** se asocian al área CD y a su plan; las marcadas "Ingeniería de Datos", al área ID; las que tienen ambas, a las dos.
3. **Given** un curso con nivel "Mid-Snr" en el plan UX/UI, **When** se importa, **Then** en el plan UX/UI tiene los niveles Mid y Snr; si el plan dice "Todos" o no indica nivel, queda sin niveles.
4. **Given** un curso listado en el bloque del programa KO Upskilling o marcado como KO, **When** se importa, **Then** tiene la etiqueta "KO", un tipo de aprendizaje regular y su nivel recomendado en el plan; no existe agrupación KO y ningún otro curso recibe etiquetas en la importación.
5. **Given** las certificaciones listadas en los planes, **When** se importan, **Then** existen en el catálogo con tipo "Certificación", en el plan de su área, con su costo de examen de referencia cuando el plan lo indica.
6. **Given** un curso que ya existía en el catálogo y que Talento editó (p. ej. le puso costo y duración), **When** se vuelve a importar, **Then** la importación no sobrescribe esos datos: solo completa los campos vacíos y agrega planes y etiquetas faltantes.
7. **Given** una fila sin nombre o sin liga, o un archivo con un formato distinto al esperado, **When** se importa, **Then** la fila se reporta como no procesada con su motivo y el resto continúa.
8. **Given** los datos de prueba actuales (cursos, solicitudes, registros, aprobaciones y su historial), **When** se ejecuta la limpieza previa, **Then** Arena Learn queda sin cursos ni solicitudes, la configuración de Arena Learn se conserva y ningún dato de otros módulos ni del esquema de otros sistemas se toca.
9. **Given** la importación terminada, **When** un colaborador entra a Planes, **Then** ve los 4 planes 2026 publicados sin intervención adicional de Talento.

---

### User Story 5 - Seguimiento de planes para Talento y Leads (Priority: P3)

Talento y los Leads ven, por área y año, cuántas personas tienen Mi plan, cuántos cursos están pendientes, en curso, completados y descartados, y el detalle por persona, con exporte a Excel.

**Why this priority**: Aporta visibilidad agregada, pero el valor operativo ya existe con US2–US4; el tablero de seguimiento existente de Arena Learn cubre parte mientras tanto.

**Independent Test**: Con 3 personas del área PM con planes en distintos avances, Talento filtra PM 2026 y ve los totales correctos por estado y por persona; el exporte contiene las mismas cifras.

**Acceptance Scenarios**:

1. **Given** planes personales en distintos avances, **When** Talento filtra por área y año, **Then** ve totales por estado y la lista de personas con su avance (completados / total no descartados).
2. **Given** un Lead, **When** consulta el seguimiento, **Then** solo ve a las personas de su alcance según la matriz de permisos vigente.
3. **Given** el tablero filtrado, **When** Talento exporta, **Then** obtiene un Excel con el detalle por persona y curso.

---

### User Story 6 - Importación de cursos ya tomados por los colaboradores (Priority: P3)

Talento carga el listado de cursos que los colaboradores ya tomaron o están tomando (export de la lista de SharePoint "Cursos actuales por colaborador"). El sistema relaciona cada fila con la persona y, si existe, con el curso del catálogo; crea el registro histórico como Completado o En curso, aunque no traiga certificado ni reseña, marcado como "importado". Esos cursos se reflejan en el perfil de Arena Learn y en Mi plan si la persona los tiene en su plan.

**Why this priority**: Talento lo pidió al final; depende de que se exporte el archivo de SharePoint, cuyo formato aún no se conoce.

**Independent Test**: Un archivo con 10 filas (8 personas reconocidas, 2 no) crea 8 registros importados con su estado y reporta las 2 filas no reconocidas; repetir la carga no duplica registros.

**Acceptance Scenarios**:

1. **Given** una fila con una persona y un curso reconocidos, **When** se importa, **Then** se crea un registro histórico ligado al curso del catálogo, con el estado indicado (Completado o En curso) y marcado como importado.
2. **Given** una fila cuyo curso no está en el catálogo, **When** se importa, **Then** el registro se crea con los datos del curso de la fila, sin agregarlo al catálogo.
3. **Given** una fila sin evidencia ni reseña, **When** se importa, **Then** el registro se acepta; el colaborador puede agregar después su certificado y reseña.
4. **Given** una fila cuya persona no se reconoce, **When** se importa, **Then** se reporta como no procesada y no se crea nada.
5. **Given** un archivo ya importado, **When** se vuelve a cargar, **Then** no se duplican registros (misma persona y mismo curso).

---

### Edge Cases

- Curso con el mismo nombre pero ligas distintas (p. ej. una variante por plataforma): son dos cursos distintos; Talento puede archivar uno.
- Mismo curso con nombres distintos y la misma liga (p. ej. "Unilever Supply Chain Data Analyst" / "Supply Chain Analytics for Professionals"): un solo curso; se conserva el primer nombre y el otro se reporta en el resumen.
- Ligas a videos de una misma plataforma que solo difieren en parámetros (p. ej. YouTube `watch?v=`): el parámetro que identifica el recurso cuenta para distinguir cursos.
- Curso archivado en el catálogo que sigue en un plan publicado: el plan lo muestra como "No disponible" y no permite agregarlo a nuevos planes personales.
- Colaborador sin área asignada: Planes le muestra todos los planes publicados sin preseleccionar ninguno.
- Colaborador que cambia de área: su Mi plan del año se conserva; Planes le preselecciona el plan de su nueva área.
- Etiqueta creada con distinta capitalización o espacios ("ko", " KO "): se reconoce como la misma.
- Fusionar una etiqueta en sí misma o en una desactivada: no se permite.
- Curso con costo agregado a Mi plan mientras el colaborador tiene otro autorizado sin cerrar: aplica la regla vigente de Arena Learn (no puede enviar la nueva solicitud hasta cerrar la anterior); el curso permanece Pendiente.
- Plan sin cursos: puede guardarse en borrador pero no publicarse.
- Licencias que vencen (los planes dicen "Coursera disponible hasta agosto 2026"): no se modela; Talento puede archivar o editar los cursos afectados.

## Requirements *(mandatory)*

### Functional Requirements

**Etiquetas (US1)**

- **FR-001**: El sistema MUST manejar las etiquetas como un catálogo único y compartido por todo Arena Learn; una etiqueta es solo un nombre, único sin distinguir mayúsculas, acentos de captura ni espacios sobrantes.
- **FR-002**: Los cursos del catálogo y las solicitudes/registros de curso MUST admitir cero, una o varias etiquetas. Un curso dentro de un plan muestra las etiquetas de su curso del catálogo: la etiqueta describe el curso (p. ej. KO), no su lugar en el plan.
- **FR-003**: El campo de etiquetas MUST sugerir las etiquetas activas existentes mientras se escribe y MUST permitir crear una nueva en el mismo campo, sin salir del formulario.
- **FR-004**: Al elegir un curso del catálogo para una solicitud o registro, sus etiquetas MUST precargarse; el colaborador puede agregar o quitar.
- **FR-005**: Talento MUST poder ver la lista de etiquetas con el número de elementos que usa cada una, renombrarlas, fusionar una en otra (reasignando sus elementos sin duplicados) y desactivarlas/reactivarlas.
- **FR-006**: Una etiqueta desactivada MUST dejar de sugerirse y de poder crearse con el mismo nombre, y MUST seguir visible en los elementos que ya la tenían.
- **FR-007**: El catálogo y los planes MUST poder filtrarse por una o varias etiquetas; con varias, se muestran solo los elementos que tienen todas.
- **FR-008**: El campo de etiquetas de texto libre de cursos y solicitudes MUST reemplazarse por etiquetas gestionables. No se migra su contenido porque solo existe en datos de prueba, que se borran (FR-039).

**Planes anuales por área (US2)**

- **FR-009**: Talento MUST poder crear, editar, publicar y archivar un plan de capacitación por área y año (máximo uno por combinación), con: título, periodo (mes inicial y mes final del año), horas por semana sugeridas (mínimo y máximo), introducción breve y un texto opcional por tipo de aprendizaje.
- **FR-010**: Cada curso del catálogo MUST tener un **tipo de aprendizaje** de la lista única (Estructurado, Certificación, Puntual, Contextual, Soft Skills y Evento) que reemplaza al tipo anterior. La vista de un plan MUST agrupar sus cursos por tipo de aprendizaje, en ese orden fijo. El plan MAY tener un texto descriptivo por tipo.
- **FR-010a**: Cada curso del catálogo MUST tener un **enfoque** (Horizontal = amplitud, Vertical = profundidad), independiente de su tipo de aprendizaje. El sistema MUST NOT derivar uno del otro. Talento captura y edita ambos por separado.
- **FR-011**: Cada curso de un plan MUST referenciar un curso del catálogo y tener orden, niveles recomendados (cero o más de Jr, Mid, Snr, Lead) y nota opcional; sin niveles se muestra "Todos los niveles". Un curso aparece una sola vez por plan.
- **FR-012**: El nivel recomendado MUST vivir solo en el curso de plan; cada plan tiene sus propios niveles para un mismo curso. El curso del catálogo MUST NOT tener niveles recomendados ni pilar, porque solo describe lo propio de la plataforma (nombre, liga, proveedor, tipo, enfoque, duración, costo). Sus áreas MUST mostrarse derivadas de los planes en que aparece, no capturadas a mano.
- **FR-013**: Un plan en borrador MUST ser visible solo para quien gestiona planes; uno publicado, para todo usuario autenticado; uno archivado, consultable como histórico sin admitir nuevas selecciones.
- **FR-014**: Un plan MUST NOT publicarse sin al menos un curso.
- **FR-015**: La vista de planes MUST preseleccionar el plan publicado vigente del área del usuario y permitir cambiar de área y de año.
- **FR-016**: La vista de un plan MUST permitir filtrar por tipo de aprendizaje, nivel y etiqueta, y mostrar por curso: nombre, plataforma, liga, tipo, enfoque, niveles recomendados, etiquetas y, si existen, costo de referencia, duración y calificación promedio de Arena Learn.

**Mi plan (US3)**

- **FR-017**: Cada colaborador MUST tener un plan personal por año al que puede agregar cursos desde cualquier plan publicado (van al año del plan) o desde el catálogo (van al año en curso).
- **FR-018**: Cada curso del plan personal MUST mostrar uno de estos estados: Pendiente, En curso, Completado o Descartado; El estado MUST derivarse de los registros de Arena Learn del colaborador para ese curso:
  - completado o validado → Completado;
  - en revisión, requiere ajustes o autorizado → En curso, con el detalle de su etapa;
  - "Empezar" sin solicitud → En curso;
  - borrador de solicitud → Pendiente, con la nota "Borrador de solicitud";
  - rechazado, cancelado, no concluido o sin registro → Pendiente.
- **FR-019**: Al iniciar un curso, el colaborador MUST elegir entre "Solicitar autorización" (tiene costo para Arena) y "Empezar" (sin costo). La opción sugerida se basa en el costo de referencia del catálogo, pero el colaborador decide, porque los cursos importados no traen costo. "Solicitar autorización" MUST abrir el flujo de solicitud existente con los datos precargados. "Empezar" MUST dejar el curso En curso sin autorización. Completar MUST usar el flujo existente de evidencia y reseña: cierre de la solicitud o registro directo.
- **FR-020**: Un curso agregado a Mi plan que el colaborador ya tenía completado MUST mostrarse como Completado.
- **FR-021**: El colaborador MUST poder descartar y reactivar cursos de su plan personal; los descartados no cuentan como pendientes.
- **FR-022**: El plan personal MUST ser visible para su dueño, su Lead, Talento y Dirección, conforme a la matriz de permisos; MUST NOT ser visible para otros colaboradores.

**Importación del catálogo y planes (US4)**

- **FR-023**: El sistema MUST importar el catálogo de cursos desde el Excel recibido (una hoja por área; columnas nombre, liga, plataforma, tipo de aprendizaje, grupo) y los planes desde los archivos de plan recibidos. Excel y HTML se cruzan una sola vez en un archivo de datos versionado y revisable (`apps/learning/data/planes_2026.json`), que es lo que carga el comando de importación. La importación la ejecuta soporte técnico en nombre de Talento; no es una pantalla de carga.
- **FR-024**: La importación MUST identificar un curso por su liga normalizada (sin distinguir `www`, mayúsculas del dominio ni diagonal final, conservando los parámetros que identifican el recurso); cursos con la misma liga se unifican en uno solo.
- **FR-025**: La importación MUST incluir cada curso en el plan del área de cada hoja en que aparece; en la hoja ID, las filas de la ruta "Ingeniería de IA" van al plan de CD y las de "Ingeniería de Datos" al plan de ID.
- **FR-026**: La importación MUST crear o actualizar el plan 2026 de cada área con su periodo, horas sugeridas, textos por tipo y cursos. De la columna de clasificación del material:
  - "Aprendizaje Estructurado / Certificado / Puntual / Contextual" y "Habilidades Blandas" MUST tomarse como **tipo de aprendizaje** (Habilidades Blandas → Soft Skills);
  - "Aprendizaje Horizontal / Vertical" MUST tomarse como **enfoque**;
  - el prefijo de ruta ("Ingeniería de IA — …", "Ingeniería de Datos — …") se ignora.
  Las certificaciones descritas en los planes MUST incluirse con tipo Certificación y su costo de examen de referencia cuando se indica.
- **FR-026a**: Si el material no indica el tipo o el enfoque de un curso, o le da dos tipos distintos, el dato MUST asignarse con el criterio técnico documentado (ver Assumptions) y marcarse como **propuesto** en el archivo de datos. Talento lo revisa antes de la corrida en producción. Al 2026-10-12, de 249 cursos: 58 sin tipo, 206 sin enfoque y 5 con dos tipos.
- **FR-027**: La importación MUST asignar niveles recomendados por plan a partir de las marcas de nivel del material (Jr, Mid, Snr y rangos como "Jr-Mid" o "Mid-Snr"). "Todos" o la ausencia de marca significa sin niveles, salvo la regla de FR-028a.
- **FR-028**: La importación MUST asignar la etiqueta "KO" a los cursos del programa KO Upskilling y a los marcados como KO en el material, y MUST NOT asignar ninguna otra etiqueta. Ningún plan MUST tener una agrupación KO.
- **FR-028a**: Los cursos que el material solo lista en el bloque "KO Upskilling" (20, todos del plan PM) MUST importarse con tipo **Puntual**. Su nivel recomendado MUST derivarse de la fase KO: Foundations → Jr, Intermediate → Mid, Advanced → Snr. Los cursos KO que el material ya clasifica conservan su tipo y su nivel.
- **FR-029**: La importación MUST ser repetible sin duplicar cursos, planes ni asignaciones, y MUST NOT sobrescribir datos de un curso ya existente (incluidos tipo y enfoque): solo completa campos vacíos y agrega planes y etiquetas faltantes.
- **FR-030**: Al terminar, la importación MUST mostrar un resumen con cursos creados, actualizados y sin cambios, planes creados, etiquetas asignadas, cursos unificados con nombres distintos, cursos con dos tipos en el material y filas no procesadas con su motivo.
- **FR-031**: Los planes creados por la importación MUST quedar **publicados**, porque son los planes vigentes. Volver a importar MUST NOT cambiar el estado de un plan que Talento ya archivó.

**Seguimiento (US5)**

- **FR-032**: Talento MUST contar con un tablero de planes personales filtrable por área, año y persona, con totales por estado y avance por persona (completados / total no descartados), exportable a Excel.
- **FR-033**: Un Lead MUST ver en ese tablero solo a las personas de su alcance según la matriz de permisos.

**Cursos ya tomados (US6)**

- **FR-034**: Talento MUST poder importar un listado de cursos tomados por colaboradores (formato a definir cuando se exporte la lista de SharePoint), relacionando a la persona por correo o nombre y al curso por liga o nombre con el catálogo.
- **FR-035**: Cada fila reconocida MUST crear un registro histórico de Arena Learn en estado Completado o En curso, marcado como "importado", aun sin evidencia ni reseña; el colaborador MUST poder agregar después su certificado y reseña.
- **FR-036**: La importación de cursos tomados MUST ser repetible sin duplicar registros de la misma persona y curso, y MUST reportar las filas no reconocidas.

**Transversales**

- **FR-037**: Toda pantalla o acción nueva (gestionar etiquetas, gestionar planes, ver seguimiento, ver Mi plan de otros) MUST estar gobernada por la matriz de permisos por perfil vigente, con claves propias. Los comandos de soporte (limpieza e importación) no tienen pantalla y quedan fuera de la matriz.
- **FR-038**: Las reglas vigentes de Arena Learn (autorización en tres niveles, bloqueo por curso autorizado sin cerrar, visibilidad pública/privada) MUST mantenerse sin cambios.

**Limpieza de datos de prueba**

- **FR-039**: Antes de la primera importación MUST borrarse todo el contenido de prueba de Arena Learn: cursos del catálogo, solicitudes y registros, pasos de aprobación, evidencias, reseñas y su historial de cambios. Al 2026-10-12 son 5 cursos, 4 solicitudes/registros, 5 pasos, 0 evidencias, 0 reseñas y 7 filas de historial.
- **FR-040**: La limpieza MUST conservar la configuración de Arena Learn y MUST NOT tocar usuarios, áreas, niveles, otros módulos ni el esquema de otros sistemas. Debe ejecutarse una sola vez, con un respaldo previo, y mostrar los conteos de lo que borró.

### Key Entities

- **Etiqueta**: nombre único (normalizado), activa/inactiva. Se asigna a cursos del catálogo y a solicitudes/registros. Reemplaza las etiquetas de texto libre actuales.
- **Curso de catálogo** (existente, se ajusta): describe lo propio de la plataforma. Cambios: gana etiquetas gestionables en lugar de texto libre y **enfoque** (Horizontal/Vertical); **pierde** los niveles recomendados (pasan al curso de plan), el pilar y las áreas capturadas a mano (ahora se derivan de los planes). Conserva tipo, costo, duración y descripción.
- **Tipo de aprendizaje**: lista única (Estructurado, Certificación, Puntual, Contextual, Soft Skills y Evento). Es atributo del curso del catálogo y de la solicitud.
- **Enfoque**: Horizontal o Vertical. Es atributo del curso del catálogo, independiente del tipo.
- **Plan de capacitación**: área, año, título, periodo (mes inicial–final), horas por semana sugeridas, introducción, textos por tipo de aprendizaje, estado (borrador / publicado / archivado). Único por área y año.
- **Curso de plan**: liga un curso del catálogo con un plan; orden, niveles recomendados propios del plan y nota. Tipo, enfoque y etiquetas se toman del curso del catálogo.
- **Plan personal**: colaborador + año.
- **Curso del plan personal**: curso del catálogo elegido (con referencia opcional al curso de plan de origen), descartado sí/no, fecha en que se agregó; su avance se deriva de los registros de Arena Learn del colaborador para ese curso.
- **Solicitud / registro de curso** (existente, se amplía): etiquetas gestionables; marca "importado" para registros históricos cargados sin evidencia ni reseña, que pueden quedar En curso o Completados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con los archivos recibidos, soporte deja cargados los 4 planes 2026 y el catálogo completo (~250 cursos + certificaciones) en menos de 15 minutos, sin captura manual de cursos.
- **SC-002**: El catálogo resultante no tiene cursos duplicados por liga (0 duplicados verificables).
- **SC-003**: Volver a cargar los mismos archivos crea 0 cursos y 0 planes nuevos.
- **SC-004**: Un colaborador encuentra los cursos KO de su área para su nivel en menos de 30 segundos desde la vista de planes.
- **SC-005**: Un colaborador arma su plan personal con 5 cursos del plan de su área en menos de 3 minutos.
- **SC-006**: Tras 3 meses de uso, el número de etiquetas duplicadas por variación de escritura es 0 (verificable en la lista de etiquetas).
- **SC-007**: Talento obtiene el avance de planes por área y persona sin consolidar hojas de cálculo externas (0 archivos manuales para ese reporte).
- **SC-008**: Ningún colaborador puede ver el plan personal de otro sin permiso (verificable con pruebas de acceso por perfil).

## Assumptions

- Las áreas siguen siendo las cuatro vigentes (ID, CD, PM, UXUI); "Ingeniería de IA" corresponde al área CD y "Ingeniería de Datos" al área ID. Renombrar el área CD es decisión de Talento y no afecta esta feature.
- Los niveles son los cuatro vigentes (Jr, Mid, Snr, Lead). Los planes de Ingeniería de IA e Ingeniería de Datos no traen nivel por curso, así que sus cursos quedan "para todos los niveles" hasta que Talento los ajuste.
- El tipo de aprendizaje y el enfoque se toman de la columna "Planes" del Excel, cada uno por separado (FR-026). Los tipos anteriores se mapean: Curso y Capacitación → Estructurado, Conferencia → Evento, Otro → Puntual.
- Criterio técnico para los huecos (FR-026a), con cada dato marcado como propuesto:
  - **Tipo**: ruta o programa completo de varios módulos → Estructurado; módulo o curso corto de un solo tema → Puntual; industria o negocio → Contextual; habilidades interpersonales → Soft Skills.
  - **Enfoque**: el curso cubre varios temas o fundamentos → Horizontal; profundiza en una herramienta, técnica o especialidad → Vertical.
  - **Curso con dos tipos**: se elige el que mejor describe el curso completo.
- Criterio técnico para los 20 cursos que solo aparecen en el bloque "KO Upskilling" del plan PM: son cursos cortos y focalizados (0.5–9.5 h), por eso su tipo es Puntual; su enfoque se asigna con el criterio técnico. Las fases del programa KO son progresivas, así que se usan como nivel (Foundations → Jr, Intermediate → Mid, Advanced → Snr). Talento puede ajustarlo en el plan.
- Los 3 cursos PM que el material marca a la vez como "Aprendizaje Puntual" y "KO Upskilling" quedan con tipo Puntual y el nivel que les da el plan.
- Los subgrupos temáticos de cada plan (dominios/pilares 01–08, fases y módulos KO) no se modelan; el orden del material se conserva como orden dentro del plan.
- Los planes son sugeridos: no hay cursos obligatorios ni metas mínimas por persona en esta versión.
- El costo de referencia de las certificaciones se importa en USD cuando el plan lo indica; los cursos sin costo indicado quedan sin costo de referencia (no se infiere "gratuito").
- La importación del catálogo y los planes la ejecuta soporte técnico en nombre de Talento sobre los archivos tal como se recibieron; si Talento cambia su estructura, se ajusta el importador.
- Los planes en HTML incluyen herramientas de edición en el navegador (equipo, periodo, exportar JSON); esa funcionalidad no se replica: la plataforma es ahora la fuente oficial.
- Fuera de alcance: pilares/dominios de los planes, etiquetas automáticas distintas de "KO" (gratuito, licencia, formato, marca), vencimiento de licencias, metas obligatorias, integración en vivo con SharePoint.
