# Feature Specification: Ownership ponderado por categorías (todas las áreas) + Consultoría

**Feature Branch**: `main` (directorio `008-ownership-ponderado-categorias`)

**Created**: 2026-11-12

**Status**: Draft

**Input**: User description: "Hacer que el pilar de Ownership calcule una calificación ponderada por categorías para todas las áreas (no solo Consultoría), con Consultoría (CONS) como primera área en adoptarlo. Cada pregunta tiene una categoría; cada cuestionario define el peso de sus categorías y de sus preguntas; toda pantalla que edite pesos valida en vivo que sumen 100%. Analítica y los cuestionarios actuales pasan a una categoría placeholder «General» al 100% sin cambiar sus resultados. Catálogo de Puestos (área × nivel → nombre visible). Cuatro cuestionarios de Ownership para CONS cargados desde la Matriz de Competencias y Pesos por Puesto v1.1. Score por categoría visible. Evaluador sugerido por proyecto. Los pendientes (360 al Gerente, seguimiento semestral, compuerta de Fundamentals, vertical, etc.) quedan documentados para specs propios."

## Contexto: material recibido (2026-11)

Dirección de Consultoría entregó dos documentos:

- **Matriz de Competencias y Pesos por Puesto v1.1** (4 de noviembre de 2026, VOBO pendiente). Cuatro puestos —Analista, Consultor, Consultor Sr y Gerente— con 17 competencias del modelo actual más 2 nuevas (IA como productividad y Disciplina de forma de trabajo) que se califican pero pesan 0% en este primer cierre. Cada competencia trae la descripción del nivel esperado (calificación 3), su peso por puesto y la escala 1–4. «Apego a los valores de Arena» se marca como filtro fuera del ponderado. Incluye además una hoja de evaluación 360 al Gerente (fuera de alcance de este spec).
- **Modelo de Evaluación y Desarrollo del Consultor v0.2** (borrador). Propone tres dimensiones de evaluación —Delivery al cliente, Desarrollo de producto y Herramientas de gestión— y un modelo de seguimiento, currícula y compuerta de cursos (fuera de alcance de este spec).

Hoy el sistema calcula el pilar Ownership como **promedio simple** de las respuestas (`scoring.ownership_evaluation_score`); el peso por pregunta que existe en el catálogo no interviene en el cálculo. El área `CONS` existe con 13 personas pero **no tiene cuestionario de Ownership** (decisión previa de 2026-S2 que esta spec revierte). Los niveles globales JR / MID / SNR / LEAD y la ponderación de los tres pilares por nivel (60/20/20, 50/25/25, 40/30/30, 30/35/35) **no cambian**.

## Decisiones tomadas con el solicitante (2026-11-12)

- Aplica **a todas las áreas**, sin excepciones por área: un solo modelo ponderado por categorías. Si todo pesa igual, el resultado es el de hoy.
- El motor de la calificación final **no se toca**: el score ponderado de Consultoría es su pilar Ownership.
- Las tres dimensiones del deck son **categorías de pregunta**, no pilares nuevos. Cada pregunta tiene una sola categoría.
- **Cumple / No cumple no es un tipo de pregunta nuevo**: «Apego a los valores» se redacta como pregunta de escala 1–4.
- El flujo de evaluación es el actual: el colaborador elige evaluador principal y secundarios al iniciar.
- Los pesos **siempre** deben sumar 100% y la pantalla lo valida a la vista antes de permitir guardar.
- Los pendientes (360 al Gerente, seguimiento semestral, compuerta de Fundamentals) se documentan aquí y se desarrollan en specs propios.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - La calificación de Ownership pondera por categoría sin alterar lo que ya existe (Priority: P1)

Todo cuestionario de Ownership califica con ponderación: cada pregunta pertenece a una categoría, cada categoría tiene un peso dentro del cuestionario y cada pregunta un peso dentro de su categoría. Los cuestionarios actuales de Analítica (CD, ID, PM, UXUI × JR/MID/SNR/LEAD) pasan a una única categoría «General» al 100% con sus preguntas en partes iguales, de modo que **ninguna calificación existente cambia**.

**Why this priority**: Es la base del modelo y su mayor riesgo. Si altera un solo score de 2026-S1 o de lo vigente en 2026-S2, se pierde la confianza en la evaluación.

**Independent Test**: Con las evaluaciones enviadas de 2026-S1 y las vigentes de 2026-S2, recalcular el score de cada una con el modelo nuevo y comparar contra el guardado: diferencia cero. Con un cuestionario de prueba de 2 categorías (60/40) y respuestas conocidas, el score coincide con el cálculo manual.

**Acceptance Scenarios**:

1. **Given** una evaluación con todas las preguntas de la misma categoría «General» y promedio simple de 3.20, **When** se calcula con el modelo ponderado, **Then** el score es 3.20.
2. **Given** un cuestionario con categorías A (60%) y B (40%), A promedia 4.00 y B promedia 2.00, **When** se calcula, **Then** el score es 3.20.
3. **Given** una pregunta con peso 0 dentro de su categoría, **When** se califica, **Then** su valor se registra y se muestra, pero no modifica el score de la categoría ni el del cuestionario.
4. **Given** una categoría cuyas preguntas están todas en N/A, **When** se calcula, **Then** esa categoría se excluye y el 100% se redistribuye proporcionalmente entre las demás.
5. **Given** todas las preguntas en N/A, **When** se intenta cerrar, **Then** se comporta como hoy (sin score calculable).
6. **Given** una evaluación enviada de un periodo cerrado, **When** se publica o edita cualquier configuración de pesos, **Then** su score guardado no cambia.

---

### User Story 2 - Talento edita pesos con validación visible que garantiza 100% (Priority: P1)

Talento, al armar o editar un cuestionario, define el peso de cada categoría (porcentaje) y el de cada pregunta dentro de su categoría. En toda pantalla donde se editen pesos se muestra en vivo el total, con un aviso del tipo «Suma actual 97.5% — debe llegar a 100%», y no se puede guardar ni publicar mientras el total no sea exactamente 100%. Un botón «Repartir en partes iguales» llena los pesos con decimales limpios que suman 100 exacto.

**Why this priority**: Una ponderación que no suma 100% produce calificaciones mal calculadas sin que nadie lo note. El solicitante pidió explícitamente que la pantalla lo impida.

**Independent Test**: En el editor, cambiar un peso hasta que la suma sea 99.9%: el aviso aparece, guardar y publicar están bloqueados; corregir a 100.0%: se habilitan. Repartir en partes iguales entre 3 categorías produce 33.4 / 33.3 / 33.3.

**Acceptance Scenarios**:

1. **Given** un cuestionario en edición, **When** Talento modifica el peso de una categoría, **Then** el total de categorías se recalcula en pantalla al instante y muestra si está en 100% o cuánto falta o sobra.
2. **Given** una suma distinta de 100%, **When** Talento intenta guardar o publicar, **Then** el sistema lo impide, indica qué grupo no cuadra y conserva lo capturado.
3. **Given** una categoría con preguntas, **When** Talento edita los pesos de sus preguntas, **Then** esas preguntas también deben sumar 100% dentro de la categoría, con el mismo aviso en vivo.
4. **Given** pesos con más de un decimal, **When** se capturan, **Then** el sistema los rechaza o los limita a un decimal (nunca guarda 4.5454%).
5. **Given** que alguien intenta guardar pesos inválidos saltándose la pantalla (importación o petición directa), **When** se procesa, **Then** el sistema también lo rechaza con el mismo mensaje.
6. **Given** una categoría con peso 0%, **When** se guarda, **Then** es válido siempre que el total siga sumando 100%.

---

### User Story 3 - El personal de Consultoría contesta su Ownership por puesto (Priority: P2)

Los colaboradores del área Consultoría inician su evaluación de Ownership por proyecto igual que en Analítica: eligen evaluador principal y secundarios y contestan las competencias de su puesto (Analista, Consultor, Consultor Sr, Gerente). El evaluador complementa Fortalezas y Oportunidades y cierra. El score final del cuestionario sigue las ponderaciones de la matriz.

**Why this priority**: Es el motivo de negocio de la spec; depende de las historias 1 y 2 y del catálogo de puestos.

**Independent Test**: Un Analista de CONS inicia su evaluación en un proyecto vigente, ve 17 competencias en categorías con su descripción del nivel esperado, califica, el evaluador cierra y el score coincide con el cálculo manual de la matriz (± 0.01).

**Acceptance Scenarios**:

1. **Given** un usuario de CONS con nivel JR, **When** inicia su evaluación, **Then** se le asigna el cuestionario de «Analista» de CONS versión 1 y ve su puesto nombrado como Analista.
2. **Given** un cuestionario de Consultor, **When** se abre, **Then** no incluye Administración de recursos (la matriz no la aplica a ese puesto) y las competencias nuevas aparecen calificables pero sin peso.
3. **Given** la pregunta «Apego a los valores de Arena», **When** se califica, **Then** es una pregunta de escala 1–4 cuya redacción define que 3 es «cumple», con peso 0 dentro de su categoría.
4. **Given** un Gerente (nivel LEAD) de CONS, **When** inicia su evaluación, **Then** recibe la evaluación transversal sin proyecto, como los demás Leads hoy.
5. **Given** el cuestionario de CONS, **When** se muestra la escala, **Then** usa las etiquetas de Consultoría (No cumple, Necesita mejorar, Cumple satisfactoriamente, Excede) sin afectar las de Analítica.

---

### User Story 4 - Cada área nombra sus puestos desde un catálogo (Priority: P2)

Talento administra un catálogo de **Puestos**: la relación entre un área y un nivel y el nombre con que se muestra. Analítica conserva Junior, Mid, Senior y Lead; Consultoría muestra Analista, Consultor, Consultor Sr y Gerente. Con esto cada área puede tener su propia escalera sin cambiar los niveles globales que gobiernan la ponderación de los pilares.

**Why this priority**: Evita casos especiales por área y da escalabilidad; sin él, Consultoría se vería como «Junior/Mid/Senior/Lead» y no como sus puestos reales.

**Independent Test**: En Catálogos, ver la tabla área × nivel con nombres; renombrar el puesto JR de CONS: el nombre cambia en perfil, listas, cuestionarios y evaluaciones; el cálculo de pilares del usuario no cambia.

**Acceptance Scenarios**:

1. **Given** el catálogo sembrado, **When** se consulta, **Then** CONS: JR = Analista, MID = Consultor, SNR = Consultor Sr, LEAD = Gerente; y las 4 áreas de Analítica conservan sus nombres actuales.
2. **Given** un usuario con área y nivel, **When** se muestra su puesto, **Then** aparece el nombre del catálogo.
3. **Given** un área y nivel sin puesto en el catálogo, **When** se intenta asignar a un usuario o publicar un cuestionario para esa combinación, **Then** el sistema lo señala como combinación no definida.
4. **Given** que se renombra un puesto, **When** se consulta el histórico de evaluaciones, **Then** nada cambia en los scores ni en las asignaciones.

---

### User Story 5 - El informe muestra el score por categoría (Priority: P3)

En la vista de evaluación y en el informe de resultados, además del score total de Ownership, se muestra el score obtenido en cada categoría y su peso, para saber de dónde viene la calificación (por ejemplo, Delivery al cliente 3.4, Desarrollo de producto 2.9). Para las áreas con una sola categoría «General» el desglose no agrega información y se oculta.

**Why this priority**: Es el valor analítico buscado con las categorías; puede entregarse después de que el cálculo funcione.

**Independent Test**: Cerrar una evaluación de CONS y abrir el informe: aparece una fila por categoría con su score y peso; abrir el de un colaborador de Analítica: sin desglose visible.

**Acceptance Scenarios**:

1. **Given** una evaluación de CONS cerrada, **When** se abre el informe, **Then** se ven las cuatro categorías con su score, su peso y el total.
2. **Given** una categoría con todas sus preguntas en N/A, **When** se muestra, **Then** aparece como «sin calificar» y no como 0.
3. **Given** varios proyectos evaluados en el periodo, **When** se consolida el pilar, **Then** el score por categoría se promedia igual que el score total (promedio de las evaluaciones enviadas).

---

### User Story 6 - Cada proyecto sugiere quién evalúa (Priority: P3)

Al crear o editar un proyecto, Talento (o quien lo administra) puede indicar un **evaluador sugerido**. Cuando el colaborador inicia su evaluación en ese proyecto, el evaluador sugerido aparece preseleccionado como principal y el colaborador puede cambiarlo o agregar secundarios, como hoy.

**Why this priority**: Reduce errores al elegir evaluador y alinea la práctica de Consultoría («líder + gerente») con el flujo existente. No bloquea el cálculo.

**Independent Test**: Crear un proyecto con evaluador sugerido; un integrante inicia su evaluación y ve esa persona preseleccionada; la cambia y queda guardada su elección.

**Acceptance Scenarios**:

1. **Given** un proyecto con evaluador sugerido, **When** un integrante inicia su evaluación, **Then** el sugerido aparece preseleccionado como principal y editable.
2. **Given** un proyecto sin evaluador sugerido, **When** se inicia la evaluación, **Then** se preselecciona el líder o el responsable del proyecto si existe; si no, no se preselecciona a nadie.
3. **Given** que el colaborador es el propio evaluador sugerido, **When** inicia la evaluación, **Then** no se le preselecciona a sí mismo.

---

### Edge Cases

- **Pesos que suman 100.0 pero con una categoría vacía** (sin preguntas): se rechaza al publicar, a menos que su peso sea 0%.
- **Categoría con peso mayor a 0% cuyas preguntas pesan todas 0**: se rechaza al publicar, porque la categoría nunca podría aportar al score.
- **Repartir en partes iguales sin cociente exacto** (3 categorías, 100%): se reparte con un decimal usando el método del mayor residuo para sumar exactamente 100.0.
- **Peso null en preguntas** (cuestionarios actuales): significa partes iguales; el editor lo muestra como reparto igual calculado, sin escribir valores hasta que Talento edite.
- **Edición parcial** de pesos de una categoría (unas preguntas con peso, otras sin): no se permite; al editar pesos de una categoría deben quedar todos definidos.
- **Editar pesos de un cuestionario publicado que ya tiene evaluaciones**: sigue las reglas de versionado vigentes (se crea una versión nueva; las evaluaciones existentes conservan la suya).
- **Pregunta de texto largo** en un cuestionario ponderado: no participa en el cálculo y no pertenece a una categoría ponderada.
- **Usuario de CONS sin nivel o con combinación no definida en Puestos**: mismo mensaje que hoy de «área y nivel por asignar».
- **Reapertura de una evaluación cerrada**: se recalcula con el modelo ponderado; en cuestionarios «General» el resultado es idéntico al anterior.
- **Consultor Jr** (puesto fuera de este cierre según la matriz): en el sistema, JR de CONS es Analista; si más adelante se separa, requerirá un nivel global nuevo con su ponderación de pilares (fuera de alcance).
- **Peso de pregunta 0 en las 2 competencias nuevas**: se califican y se ven en el informe, pero un 1 en ellas no baja el score.

## Requirements *(mandatory)*

### Functional Requirements

**Categorías y ponderación**

- **FR-001**: El sistema MUST ofrecer un catálogo administrable de **Categorías de pregunta**, y cada pregunta de escala MUST pertenecer a exactamente una.
- **FR-002**: Cada cuestionario MUST definir el peso de cada una de sus categorías como porcentaje con **máximo un decimal**; los pesos de un cuestionario MUST sumar exactamente 100.0%; se permite 0%.
- **FR-003**: Cada pregunta MUST tener un peso dentro de su categoría. Si no se definió peso, se interpreta como **partes iguales**; el peso 0 significa «se califica pero no pondera». Cuando se definen pesos de preguntas de una categoría, todas MUST definirse y sumar 100.0%.
- **FR-004**: El score de una categoría MUST ser el promedio ponderado de sus preguntas calificadas, con los N/A excluidos; el score del cuestionario MUST ser la suma de los scores de categoría multiplicados por su peso.
- **FR-005**: Si una categoría no tiene ninguna pregunta ponderada calificada, el sistema MUST excluirla y redistribuir el 100% proporcionalmente entre las categorías calificadas.
- **FR-006**: Los promedios MUST redondearse a 2 decimales con la regla vigente (mitad hacia arriba) y las bandas de interpretación MUST seguir siendo las actuales.
- **FR-007**: La calificación final del colaborador MUST calcularse sin cambios: el pilar Ownership sigue siendo el promedio de sus evaluaciones enviadas y los pesos de los tres pilares por nivel no cambian.

**Compatibilidad con lo existente**

- **FR-008**: Todos los cuestionarios de Ownership existentes MUST migrar a una única categoría «General» al 100% con preguntas en partes iguales, y el score recalculado de **toda** evaluación existente MUST ser idéntico al guardado (verificado con conteo antes y después).
- **FR-009**: Las evaluaciones enviadas y los periodos cerrados MUST conservar sus scores guardados; ningún cambio de pesos o categorías los modifica ni mueve sus respuestas.
- **FR-010**: Los cuestionarios de Entrega de Valor MUST quedar sin cambios.

**Edición y validación de pesos**

- **FR-011**: Toda pantalla donde se editen pesos de categorías o de preguntas MUST mostrar en vivo la suma y un aviso del tipo «Suma actual X% — debe llegar a 100%» mientras no cuadre, y MUST impedir guardar y publicar hasta que la suma sea exactamente 100.0%.
- **FR-012**: El editor MUST ofrecer «Repartir en partes iguales» para categorías y para preguntas de una categoría, con un decimal y suma exacta de 100.0 (mayor residuo).
- **FR-013**: La misma validación MUST aplicarse del lado del servidor y en la importación de cuestionarios, de modo que ningún camino permita guardar o publicar pesos que no sumen 100.0%.
- **FR-014**: El editor MUST impedir publicar un cuestionario con una categoría sin preguntas y con peso mayor a 0, o con una categoría con peso mayor a 0 cuyas preguntas pesen todas 0.
- **FR-015**: Los pesos MUST mostrarse y capturarse sin decimales largos (nunca más de un decimal).

**Tipo de pregunta**

- **FR-016**: El sistema MUST NOT agregar un tipo de pregunta nuevo; «Apego a los valores de Arena» MUST ser una pregunta de escala 1–4 con peso 0 dentro de su categoría y redacción donde 3 = cumple.

**Puestos**

- **FR-017**: El sistema MUST ofrecer un catálogo administrable de **Puestos** (área × nivel → nombre visible, activo/inactivo), con una sola entrada por combinación.
- **FR-018**: La siembra inicial MUST conservar los nombres actuales de Analítica y definir para CONS: JR = Analista, MID = Consultor, SNR = Consultor Sr, LEAD = Gerente.
- **FR-019**: Las pantallas que hoy muestran el nivel como Jr / Mid / Sr / Lead MUST mostrar el nombre del puesto del catálogo; los niveles globales siguen gobernando permisos de tipo de evaluación y ponderación de pilares.
- **FR-020**: Publicar un cuestionario o asignar un puesto a un usuario con una combinación área × nivel inexistente en el catálogo MUST señalarse como error claro.

**Cuestionarios de Consultoría**

- **FR-021**: El sistema MUST contar con cuatro cuestionarios de Ownership para CONS (Analista, Consultor, Consultor Sr y Gerente), versión 1, publicados, cargados desde la matriz mediante la importación repetible del sistema (idempotente y que rechaza versiones con respuestas).
- **FR-022**: Las categorías de CONS MUST ser: **Delivery al cliente**, **Desarrollo de producto**, **Herramientas de gestión** y **Actitud y persona**, con este mapeo por bloque del catálogo de la matriz:
  - Gestión de cliente y stakeholders (Habilidad de comunicación, Nivel de relación con el cliente), Dimensionamiento (Comprensión del alcance), Diagnóstico y análisis de negocio (Sentido de negocio) y Gestión del cambio y adopción (Transformación organizacional) → *Delivery al cliente*.
  - Análisis de datos (Capacidad de análisis, Dominio de herramientas), Especificación y modelado (Capacidad de síntesis) e IA como productividad → *Desarrollo de producto*.
  - Disciplina de WoW y gestión (Planificación del trabajo, Generación de conocimiento, Administración de recursos, Disciplina de forma de trabajo) → *Herramientas de gestión*.
  - Competencias de persona sin bloque (Proactividad, Búsqueda de la excelencia, Innovación y creatividad, Contribución al equipo, Orientación a resultados) y Apego a los valores → *Actitud y persona*.
- **FR-023**: Los pesos de categoría de cada puesto MUST derivarse de la matriz (suma de los pesos de sus competencias), redondeados a un decimal con suma exacta de 100.0, y el peso de cada pregunta MUST ser el de su competencia normalizado dentro de su categoría:

  | Puesto | Delivery al cliente | Desarrollo de producto | Herramientas de gestión | Actitud y persona |
  |---|---|---|---|---|
  | Analista | 13.6% | 22.7% | 18.2% | 45.5% |
  | Consultor | 30.2% | 20.9% | 14.0% | 34.9% |
  | Consultor Sr | 32.7% | 18.2% | 21.8% | 27.3% |
  | Gerente | 32.3% | 16.1% | 19.3% | 32.3% |

- **FR-024**: Una competencia que no aplica a un puesto (por ejemplo Administración de recursos para Consultor, o Transformación organizacional, Sentido de negocio y Administración de recursos para Analista) MUST no aparecer en su cuestionario.
- **FR-025**: Las dos competencias nuevas MUST aparecer calificables con peso 0 en los cuatro puestos.
- **FR-026**: Los cuestionarios de CONS MUST usar las etiquetas de escala propias de Consultoría por cuestionario, sin afectar a Analítica.
- **FR-027**: El **flujo de evaluación** de Consultoría MUST ser el vigente: por proyecto, con evaluador principal y secundarios elegidos por el colaborador, cierre con Fortalezas y Oportunidades; el Gerente (LEAD) conserva la evaluación transversal sin proyecto.

**Visibilidad**

- **FR-028**: La vista de evaluación y el informe de resultados MUST mostrar el score por categoría y su peso cuando el cuestionario tenga más de una categoría, y MUST ocultar el desglose cuando solo exista «General».
- **FR-029**: Una categoría totalmente en N/A MUST mostrarse como «sin calificar», nunca como 0.

**Evaluador sugerido**

- **FR-030**: El proyecto MUST permitir registrar un evaluador sugerido; al iniciar su evaluación el colaborador MUST verlo preseleccionado como principal y poder cambiarlo o agregar secundarios. Sin sugerido, se preselecciona al líder o responsable del proyecto cuando exista, y nunca al propio colaborador.

**Permisos y datos**

- **FR-031**: Las pantallas nuevas MUST regirse por la matriz de perfiles vigente (clave por vista y fila en la matriz sembrada), con la misma restricción que el editor de cuestionarios actual; ninguna decisión por rol.
- **FR-032**: Las migraciones de datos (categoría «General», puestos y cuestionarios de CONS) MUST ser aditivas, simularse antes de ejecutarse y registrar conteos antes y después, conforme a la constitución.

### Key Entities

- **Categoría**: agrupación temática de preguntas, con nombre, orden y estado; catálogo común a todas las áreas. «General» es la categoría de arranque de las áreas existentes.
- **Peso de categoría por cuestionario**: porcentaje (un decimal) que cada categoría aporta al score de un cuestionario concreto; los de un cuestionario suman 100.0.
- **Pregunta (ampliada)**: pertenece a una categoría y tiene un peso dentro de ella (vacío = partes iguales; 0 = se califica sin ponderar).
- **Puesto**: relación única área × nivel con nombre visible (Analista, Consultor, Junior, etc.); no altera los niveles globales.
- **Evaluador sugerido (de proyecto)**: persona preseleccionada para evaluar a los integrantes del proyecto; no es obligatoria.
- **Score por categoría**: resultado derivado de las respuestas de una evaluación, calculable en cualquier momento; no sustituye al score total guardado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las evaluaciones existentes (enviadas y vigentes) conserva exactamente el mismo score tras la migración al modelo ponderado.
- **SC-002**: Una evaluación de CONS de prueba con respuestas conocidas obtiene el mismo score que el cálculo manual de la matriz, con diferencia máxima de 0.01, en los cuatro puestos.
- **SC-003**: Es imposible dejar guardado o publicado un cuestionario cuyos pesos no sumen exactamente 100.0%: 0 casos por la pantalla, por importación o por petición directa.
- **SC-004**: Un usuario de Talento detecta en menos de 5 segundos si los pesos de un cuestionario cuadran, sin calculadora, y puede corregirlos y guardar en menos de 2 minutos.
- **SC-005**: Los 13 colaboradores de Consultoría pueden iniciar y completar su Ownership en 2026-S2 sin intervención técnica (puesto asignado, cuestionario publicado, evaluador elegido).
- **SC-006**: Agregar una nueva área o renombrar los puestos de un área se hace desde catálogos, sin cambios de código.
- **SC-007**: El informe de una evaluación de CONS muestra el score de las cuatro categorías y la suma ponderada coincide con el score total.
- **SC-008**: Las pruebas de no regresión del cálculo (promedio simple vs ponderado «General») pasan al 100% y se agregan al conjunto de pruebas del proyecto.

## Assumptions

- El score ponderado de Consultoría es su pilar Ownership; Entrega de Valor e Impacto Arena siguen como hoy y su captura para CONS queda fuera de esta spec.
- Los pesos de la matriz v1.1 se cargan tal como están (redondeados a un decimal con suma exacta de 100.0); la diferencia contra la matriz original no pasa de 0.1 punto por competencia. Si Dirección de Consultoría ajusta pesos, se hace desde el editor con la validación de 100%.
- Se usan las cuatro categorías propuestas (las tres dimensiones del deck más «Actitud y persona»); las categorías son datos, así que cambiarlas o sustituirlas por los bloques C1–C10 en la siguiente iteración es una versión nueva de cuestionario.
- «Apego a los valores» pesa 0 y queda en «Actitud y persona»; una calificación baja se ve en el informe, pero no genera alerta automática ni limita la banda final (posible mejora futura).
- Cada área tiene máximo un puesto por nivel global; por ahora no se agrega un quinto nivel (Consultor Jr).
- Las etiquetas de escala de CONS son propias del cuestionario; Analítica conserva las suyas.
- El Gerente de CONS conserva la evaluación transversal sin proyecto hasta que se defina el 360 (spec 009).
- Los scores por categoría se calculan a partir de las respuestas; no se guarda un score por categoría congelado en la evaluación.
- El flujo de periodos, cierre, reapertura, permisos y recordatorios no cambia.
- Entrega de Valor, Arena Learn y la Mesa de Talento no cambian en este spec.
- Se respetan las reglas de la constitución del proyecto: servicios para la lógica, permisos por matriz de perfiles, pruebas compactas por escenario, migraciones aditivas aplicadas a Neon antes del push, y diseño del `DESIGN_SYSTEM.md`.

## Fuera de alcance / Backlog documentado (cada uno en su propio spec)

| # | Tema | Qué queda por desarrollar | Dependencias y notas |
|---|---|---|---|
| 009 | **Evaluación 360 al Gerente** | Cuestionario Likert 1–4 de 30 preguntas en 10 dimensiones (peso 12.5% en 8 dimensiones y 0% en las 2 nuevas), respondido por el equipo sobre el Gerente; reglas de anonimato y número mínimo de respondientes; agregación por dimensión. Evaluar si aplica también a Producto o dejarlo como **opción de proceso** configurable. | Reutiliza categorías y pesos validados de esta spec. Hoja 03 de la matriz v1.1. Decidir cómo se integra al score del Gerente. |
| 010 | **Seguimiento semestral** | Foco máximo de 3 competencias por persona por semestre con evidencia esperada, mentor, bitácora de desempeño y actualización de nivel al cierre. | Requiere una **clave estable de competencia por pregunta** para comparar entre versiones y niveles (no existe hoy). |
| 011 | **Compuerta de Fundamentals en Arena Learn** | Ligar cursos a competencias; sin Fundamentals acreditado no se autoriza un curso de Especialización, por competencia; acreditación por evidencia en el trabajo. | Se apoya en planes por área y año de Arena Learn y en la clave de competencia de la 010. |
| — | **Atributo vertical** y competencia de especialidad | Comercial CPG, Soluciones de Cadena y Optimización y Automatización como atributo de la persona, con su módulo de especialidad (10, 12 y 12 skills) para el cierre 2026-S2 de 2027. | No convertir las verticales en áreas: afectaría Arena Learn y «Mi área». |
| — | **Núcleo común C1–C10** | Reemplazar las 17 competencias por los bloques C1–C10 del núcleo común en una versión nueva de cuestionario. | Depende de validar el catálogo (ver inconsistencias). |
| — | **Nivel objetivo N1–N4**, banda salarial y promoción | Decisión de Dirección de Consultoría sobre cómo se refleja el nivel en banda salarial y promoción. | Sin impacto en el cálculo actual: la calificación 3 ya es «cumple para su puesto». |
| — | **Odoo** | Integración o importación de las competencias autodeclaradas. | La línea base la establece cada líder con evidencia, no el archivo. |
| — | **Alerta de valores** | Alerta visible o tope de banda cuando «Apego a los valores» sea bajo. | Decisión de negocio pendiente de Dirección y Talento. |
| — | **Quinto nivel global** | Alta de un nivel global (p. ej. Consultor Jr) con su ponderación de pilares. | Solo si el negocio separa Jr de Analista. |

## Por confirmar con Analítica

Para que ID, CD, PM y UXUI adopten el modelo más allá de «General», falta definir con sus líderes:

1. **Categorías reales** que quieren en lugar de «General» y **con qué pesos** por nivel.
2. Si dentro de una categoría **sus actividades del checklist 2027 pesarían distinto** entre sí (hoy todas valen igual).
3. **Cómo se mapearían sus actividades a categorías comunes** con Consultoría (p. ej. las tres dimensiones) si se quiere comparar entre áreas.
4. Si usarán las **etiquetas de escala nuevas** (Necesita mejorar, Cumple satisfactoriamente) o conservan las actuales.
5. Si quieren **ver el score por categoría en su informe** o mantener el total solamente.
6. Si el **peso 0** («se califica pero no pondera») tiene alguna actividad candidata en su checklist.

Hasta tener estas respuestas, Analítica queda en «General» al 100%, sin cambio visible.

## Por resolver antes de cargar la matriz de Consultoría

- El deck habla de **9 y de 10 competencias** y de **33 y de 37 skills** en láminas distintas; la matriz habla de diez bloques del catálogo.
- La matriz v1.1 tiene el **VOBO pendiente** en la bitácora.
- Los pesos de la matriz suman 1.0000000000000002 en Analista, 0.99999999999999956 en Consultor Sr y 1.0000000000000007 en Gerente (se normalizan al cargar).
- Los bloques «Análisis de datos y validación» y «Disciplina de WoW y gestión» se repiten en varias competencias, por lo que esos bloques pesan más de lo que parece.
- Confirmar que Jr de CONS equivale al puesto de Analista (Consultor Jr queda fuera del cierre según la matriz).
- Confirmar el correo y el nivel real de las personas de CONS marcadas «Jr por definir» antes de abrir las evaluaciones.
