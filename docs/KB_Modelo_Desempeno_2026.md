# Knowledge Base — Modelo de Desempeño Analítica 2026 (Arena Analytics)

> **Propósito de este documento:** fuente única de verdad del modelo de evaluación de desempeño del equipo de Analítica. Contiene todos los valores, escalas, fórmulas, procesos, validaciones, workflows, flujos de información, permisos y dependencias. Está diseñado para usarse como knowledge base en la construcción de un sistema de software que implemente este modelo.
>
> **Versión:** 1.0 — 9 de junio de 2026
> **Vigencia del modelo:** a partir del 2 de marzo de 2026, para todo el equipo de Analítica.
> **Decisiones de diseño ya tomadas:** ver sección 13. Las reglas aquí descritas son definitivas salvo lo marcado como `[PENDIENTE]`.

---

## 1. Resumen ejecutivo del modelo

El desempeño de cada colaborador de Analítica se evalúa **semestralmente** mediante **3 pilares**, cada uno con calificación en escala **1 a 4** (4 es la más alta). La **calificación final** es un **promedio ponderado** de los 3 pilares, donde los pesos dependen del **nivel de seniority** del colaborador.

| # | Pilar | Qué mide | Quién lo genera |
|---|-------|----------|-----------------|
| 1 | **Ownership** (desempeño individual) | Cómo ejecuta y da seguimiento a sus responsabilidades a lo largo del proyecto y con qué calidad | El colaborador llena el checklist; el líder lo valida en sesión conjunta |
| 2 | **Entrega de Valor** (desempeño del proyecto) | Cómo contribuye el equipo a lo comprometido con el cliente: resultados, calidad y tiempos | El líder del proyecto, con validación del director |
| 3 | **Impacto Arena** (alineación organizacional) | Contribución a la evolución de Arena y al fortalecimiento de la colaboración | Talento y Cultura (input manual) |

**Objetivo del modelo:** evaluar el desempeño de manera integral y objetiva, reconociendo la contribución individual, la aportación a los resultados comprometidos con clientes y la participación en el crecimiento sostenible de Arena, para impulsar el desarrollo profesional de cada colaborador.

---

## 2. Entidades del modelo

### 2.1 Áreas (4)

| Clave | Nombre | Alias en documentos |
|-------|--------|---------------------|
| ID | Ingeniería de Datos | DE (Data Engineering) |
| CD | Ciencia de Datos | DS (Data Science) |
| PM | Product Manager | Producto |
| UXUI | UX/UI | UX UI |

### 2.2 Niveles de seniority (4)

| Clave | Nombre | Orden |
|-------|--------|-------|
| JR | Junior | 1 |
| MID | Mid | 2 |
| SNR | Senior | 3 |
| LEAD | Lead | 4 |

> **Nota:** el nivel *Trainee* existe en material histórico de ponderación pero queda **fuera del alcance** de este modelo y del sistema (decisión del 9-jun-2026).

Factores implícitos que diferencian los niveles (referencia conceptual, no se capturan en el sistema):

| Factor | Junior | Mid | Senior |
|--------|--------|-----|--------|
| Autonomía | Ejecuta | Gestiona problemas | Define problemas |
| Negocio | Features | Outcomes | Estrategia |
| Decisiones | Baja ambigüedad | Ambigüedad media | Alta ambigüedad |
| Stakeholders | Colabora | Negocia | Influye |
| Discovery | Ejecuta | Diseña | Prioriza |
| Impacto | Individual | Equipo | Organización |

### 2.3 Puestos (Área × Nivel = 16 combinaciones)

ID Jr, ID Mid, ID Snr, ID Lead, CD Jr, CD Mid, CD Snr, CD Lead, PM Jr, PM Mid, PM Snr, PM Lead, UX/UI Jr, UX/UI Mid, UX/UI Snr, UX/UI Lead.

Cada puesto tiene **un cuestionario (checklist) de Ownership propio** (16 cuestionarios precargados — ver Anexos A1–A4).

### 2.4 Roles del proceso

| Rol | Descripción |
|-----|-------------|
| **Evaluado (Colaborador)** | Cualquier miembro de Analítica con área y nivel asignados. Llena su checklist de Ownership. |
| **Líder de proyecto** | PM o Gerente del proyecto. Valida el checklist de Ownership de los miembros de su proyecto y llena la evaluación de Entrega de Valor del proyecto. Cada proyecto tiene exactamente un líder responsable. |
| **Lead de área** | Colaborador con nivel LEAD. Tiene visibilidad de todas las evaluaciones de su área. |
| **Director de Analítica** | Valida la evaluación de Entrega de Valor. Consume resultados. |
| **Talento y Cultura** | Comunica lineamientos, registra Impacto Arena (input manual), registra resultados formales, usa resultados para decisiones de talento. |

> La evaluación del propio Lead **no es parte de este modelo** (quién evalúa al Lead queda fuera de alcance). El Lead sí cuenta con checklist propio para autoevaluarse bajo el mismo flujo, pero la validación jerárquica de su evaluación no está definida en el modelo.

### 2.5 Proyectos

- Todo colaborador de Analítica está asignado a **al menos un proyecto** (no existe gente sin proyecto en este ecosistema).
- Un proyecto tiene: nombre, cliente, **líder de proyecto** (único responsable), equipo (miembros), y tipo de duración: **tiempo finito** (con fecha de entrega) o **servicio/iniciativa de tiempo indefinido**.
- Un colaborador puede estar en **varios proyectos simultáneamente** (los datos actuales contemplan hasta 3, pero el modelo no impone límite).

### 2.6 Periodos de evaluación

- **Obligatorio:** cada 6 meses (semestral). Primera ronda: junio 2026.
- **Opcional:** cada 3 meses, o como soporte para retroalimentaciones puntuales. Las rondas opcionales no sustituyen a la semestral.
- Toda evaluación pertenece a un **periodo**, que define ventana de inicio y cierre.

---

## 3. Ponderación por nivel de seniority

Pesos del promedio ponderado de la calificación final (suman 100% por nivel):

| Nivel | Ownership | Entrega de Valor | Impacto Arena |
|-------|-----------|------------------|---------------|
| **Jr** | 60% | 20% | 20% |
| **Mid** | 50% | 25% | 25% |
| **Snr** | 40% | 30% | 30% |
| **Lead** | 30% | 35% | 35% |

Principio: **a mayor seniority, más pesa el desempeño del proyecto y el impacto organizacional; a menor seniority, más pesa la ejecución individual.**

---

## 4. Pilar 1 — Ownership (evaluación individual)

### 4.1 Artefacto

**Checklist de Ownership:** listado de actividades, entregables, criterios de aceptación y frecuencia esperada, específico por **área y nivel** (16 variantes, ver Anexos A1–A4).

### 4.2 Escala por pregunta

Cada punto del checklist se califica con:

| Valor | Etiqueta | Definición |
|-------|----------|------------|
| 1 | No cumple | La actividad no se ejecutó o se ejecutó con deficiencias significativas que impactaron el proyecto o al equipo |
| 2 | Cumple parcial | Se ejecutó pero con omisiones, inconsistencias o calidad por debajo del estándar esperado para el nivel |
| 3 | Cumple | Se ejecutó de forma consistente y completa, cumpliendo el estándar esperado para el nivel |
| 4 | Excede | Se ejecutó por encima del estándar del nivel, con iniciativa, precisión o impacto adicional notable |
| N/A | No aplica | La actividad no aplicó en este período por razones justificadas (tipo de proyecto, fase, etc.) **No entra al promedio.** |

Para nivel **Lead** la escala tiene matices de redacción: 1 — No cumple (impacto negativo) / 2 — Cumple parcial (incompleto o tardío) / 3 — Cumple (consistente y proactivo) / 4 — Excede (impacto diferencial) / N/A. Numéricamente es idéntica.

### 4.3 Estructura de cada cuestionario

1. **Identificación:** nombre del evaluado, área, puesto, nombre del evaluador(es). *(En el sistema estos campos se derivan del usuario autenticado y del catálogo; no se capturan manualmente.)*
2. **Preguntas de escala (1–4 / N/A):** agrupadas por secciones temáticas. La cantidad varía por puesto (entre 20 y 39 preguntas calificables).
3. **Conclusión (texto libre):** **Fortalezas**, **Oportunidades**, **Comentarios** (opcional). Se redactan **en conjunto** durante la sesión de validación con el líder.
4. **Confirmación de envío:** "Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación" (Sí/No). Debe ser **Sí** para poder enviar.

### 4.4 Workflow del proceso de Ownership

```
[1] Talento comunica lineamientos, criterios y calendario del periodo
        │
[2] El colaborador consulta el checklist de su área/nivel y reúne evidencias
        │
[3] El colaborador llena el checklist (por cada proyecto en el que participó):
    califica cada punto 1–4 o N/A con base en evidencia → estado: BORRADOR
    (puede guardar y modificar; NO debe enviarse aún)
        │
[4] Sesión de validación con el evaluador (líder del proyecto):
    - revisan punto por punto
    - acuerdan la calificación definitiva de cada ítem
    - redactan en conjunto Fortalezas, Oportunidades y Comentarios
        │
[5] Confirmación "revisé con mi líder" = Sí → ENVÍO (Submit) → estado: ENVIADA
    Tras el envío la evaluación queda INMUTABLE para el evaluado
        │
[6] Registro del resultado: se calcula el promedio y queda visible en
    los resultados del colaborador → notificación por correo al evaluado
        │
[7] Retroalimentación al evaluado (lead ejecuta, líder de proyecto responsable)
    y seguimiento a acuerdos/mejoras derivadas
```

**Puntos clave del proceso (heredados del proceso actual en Forms/SharePoint):**
- El llenado inicia como captura del propio colaborador, pero la **calificación definitiva se acuerda en sesión con el líder**; conceptualmente es una evaluación validada, no una autoevaluación pura.
- Enviar antes de la sesión de validación es un error de proceso: una vez enviada no se puede modificar (en el sistema: bloquear edición tras envío; permitir reapertura solo por administrador/Talento).
- Confidencialidad: el resultado solo lo ven el evaluado, su evaluador/lead de área y Talento y Cultura.

### 4.5 Relación con proyectos (regla multi-proyecto)

- **Cada evaluación de Ownership está ligada a un proyecto y al líder de ese proyecto.**
- Si un colaborador participó en N proyectos durante el periodo, puede generar **N evaluaciones de Ownership** (una por proyecto, validada por el líder correspondiente).
- El **score de Ownership del periodo** = promedio simple de los scores de sus evaluaciones de Ownership enviadas en el periodo.

### 4.6 Fórmula de cálculo

Para una evaluación de Ownership:

```
score_evaluacion = SUM(respuestas numéricas 1–4) / COUNT(respuestas numéricas)
```

- **Las respuestas N/A se EXCLUYEN** del numerador y del denominador (regla de negocio confirmada; estaba implícita en el proceso original).
- Todas las preguntas pesan igual (promedio simple; las secciones no tienen peso propio).
- Resultado con 2 decimales (redondeo half-up).
- Rango posible: 1.00 – 4.00.

Score del pilar en el periodo:

```
score_ownership = AVG(score_evaluacion de cada proyecto del periodo)
```

### 4.7 Matriz RACI — Ownership

R = Ejecuta · A = Responsable principal · C = Consultado · I = Informado

| Actividad | Evaluado | Líder de proyecto | Leads | Director | Talento |
|-----------|----------|-------------------|-------|----------|---------|
| Comunicar lineamientos y criterios | I | I | I | I | **R/A** |
| Llenado del checklist | **R/A** | I | I | I | I |
| Revisión de evidencias y entregables | R | **R/A** | C | I | I |
| Calificación de cada punto | R | **R/A** | C | I | I |
| Validación de la evaluación | N/A | **R** | **A** | C/I | I |
| Retroalimentación al evaluado | I | **A** | **R** | I | I |
| Registro de resultados | I | **R/A** | I | I | I |
| Seguimiento a acuerdos/mejoras | **A** | R | R | I | C |
| Uso de resultados para decisiones de talento | I | C | C | **A** | **R** |

---

## 5. Pilar 2 — Entrega de Valor (evaluación del proyecto)

### 5.1 Artefacto

**Evaluación de proyecto:** califica la satisfacción del cliente, el cumplimiento de entregables y el cumplimiento en tiempo vs el plan acordado.

### 5.2 Reglas estructurales

- **Es la misma calificación para todos los miembros del equipo del proyecto** (se evalúa el proyecto, no a la persona).
- **Responsable:** Líder del Proyecto (PM o Gerente de Proyecto). **Valida:** el director correspondiente. *(Regla definitiva: responsable = líder de proyecto; el director valida.)*
- El evaluado **no tiene que hacer nada** en este pilar.
- Si un colaborador estuvo en más de un proyecto, su score del pilar = **promedio simple de las calificaciones de sus proyectos** del periodo.
- Frecuencia: obligatoria cada 6 meses.

### 5.3 Escala y criterios

**Escala oficial: 1 a 4** (decisión del 9-jun-2026; la versión histórica 0–4 queda descartada — los descriptores de los antiguos niveles 1 y 0 se fusionan en el nivel 1).

El score del proyecto = **promedio de los 3 criterios aplicables** (satisfacción + entregables + el criterio de tiempo que aplique; el criterio de tiempo no aplicable se marca N/A y **se excluye del promedio**).

**Criterio 1 — Satisfacción del cliente**

| Valor | Descripción |
|-------|-------------|
| 4 — Muy Alto | El cliente estuvo satisfecho durante todo el proyecto y es un sponsor de Arena |
| 3 — Alto | El cliente dio retroalimentación directa y se hicieron ajustes que corrigieron su percepción |
| 2 — Medio | El cliente dio retroalimentación en repetidas ocasiones y se logró ajustar correctamente |
| 1 — Bajo | El cliente dio retroalimentación en repetidas ocasiones y tuvo que escalar las oportunidades de mejora, o no quedó satisfecho con el trabajo, o se detuvo el proyecto |

**Criterio 2 — Cumplimiento de entregables**

| Valor | Descripción |
|-------|-------------|
| 4 — Muy Alto | Entregables cumplidos en tiempo, forma y calidad comprometida, sin retrabajos |
| 3 — Alto | Cumplidos en tiempo, forma y calidad, aunque con retrabajos menores por ajustes requeridos por el cliente |
| 2 — Medio | Cumplidos en tiempo, forma y calidad, aunque con retrabajos mayores por ajustes requeridos por el cliente |
| 1 — Bajo | Entregables cumplidos pero sin la calidad comprometida (el cliente los rechazó o expresó inconformidad en múltiples ocasiones), o no se logró cumplir con los entregables comprometidos |

**Criterio 3a — Cumplimiento en tiempo (proyectos con tiempo finito)**
*Aplica solo si el proyecto tiene fecha de entrega definida; si es servicio indefinido → N/A.*

| Valor | Descripción (retraso vs semanas planeadas en la versión acordada con el cliente al inicio) |
|-------|--------------------------------------------------------------------------------------------|
| 4 — Muy Alto | Retraso menor al 10% |
| 3 — Alto | Retraso entre 10% y 15% |
| 2 — Medio | Retraso entre 15% y 20% |
| 1 — Bajo | Retraso mayor al 20% |

**Criterio 3b — Cumplimiento en tiempo (servicios o iniciativas de tiempo indefinido)**
*Aplica solo si el proyecto es servicio continuo sin fecha de cierre; si tiene fecha de entrega → N/A.*

| Valor | Descripción (vs fechas planeadas con el cliente) |
|-------|---------------------------------------------------|
| 4 — Muy Alto | Entregas y actividades cumplidas consistentemente |
| 3 — Alto | La mayoría del tiempo se cumplen las entregas y actividades |
| 2 — Medio | Existen inconsistencias en el cumplimiento de las entregas |
| 1 — Bajo | Más del 50% de las entregas no se cumplieron, o consistentemente no se logran cumplir |

> Nota: las bandas de retraso del criterio 3a se ajustaron al fusionar los antiguos niveles 1 (20–25%) y 0 (>25%) en un solo nivel 1 (>20%).

### 5.4 Estructura del formulario (ver Anexo B)

1. Identificación: correos de **todos los evaluados** del proyecto, nombre del proyecto, nombre del evaluador(es). *(En el sistema: se selecciona el proyecto del catálogo y los evaluados se derivan del equipo del proyecto.)*
2. Criterio 4 (satisfacción), criterio 5 (entregables), criterios 6 y 7 (tiempo finito / indefinido, mutuamente excluyentes vía N/A).

### 5.5 Workflow

```
[1] Talento comunica criterios y calendario
        │
[2] Líder del proyecto recopila insumos (avance, entregables, feedback del cliente)
    — el evaluado aporta insumos (R), el líder es accountable
        │
[3] Líder del proyecto captura la evaluación del proyecto (3 criterios) → BORRADOR
        │
[4] Director correspondiente VALIDA la evaluación → VALIDADA
        │
[5] El score del proyecto se propaga automáticamente a todos los
    miembros del equipo del proyecto en el periodo
        │
[6] Si un colaborador tiene >1 proyecto: se promedian sus scores de proyecto
        │
[7] Registro formal de resultados (Talento)
```

### 5.6 Fórmulas

```
score_proyecto = ( satisfaccion + entregables + tiempo_aplicable ) / 3
score_entrega_valor(colaborador) = AVG(score_proyecto de cada proyecto del colaborador en el periodo)
```

Redondeo a 2 decimales. Rango: 1.00 – 4.00.

### 5.7 Matriz RACI — Entrega de Valor

| Actividad | Evaluado | Líder de proyecto | Leads | Director | Talento |
|-----------|----------|-------------------|-------|----------|---------|
| Comunicar criterios y calendario | I | I | I | I | **A/R** |
| Recopilar insumos del proyecto | R | **A** | C | I | I |
| Capturar calificación global (1–4) | N/A | **R** | N/A | **A** (valida) | N/A |
| Promediar calificaciones (>1 proyecto) | A | C | I | I | N/A *(en el sistema: automático)* |
| Registro formal de resultados | I | I | I | I | **A** |

---

## 6. Pilar 3 — Impacto Arena (evaluación organizacional)

### 6.1 Estado de definición

**`[PENDIENTE]` La mecánica interna de cálculo de Impacto Arena aún no está definida.** Para efectos del sistema, este pilar es un **input manual capturado por Talento y Cultura**: un valor de **1 a 4** (con hasta 2 decimales) por colaborador por periodo, con campo opcional de comentarios/desglose.

### 6.2 Marco conceptual (referencia del material original, no implementado como cálculo)

Talento y Cultura calculará el cumplimiento a partir de registros de asistencia y cursos, considerando factores como:

| Factor | Evidencia |
|--------|-----------|
| Asistencia a juntas semanales (Ciencia de Datos y Arena) | Listas de asistencia |
| Participación activa en Be Arenas | Listas de asistencia |
| Cumplimiento de gestión (solicitud de vacaciones, permisos) | Revisiones de Talento y Cultura |
| Cumplimiento de currículas de capacitación (marzo en adelante) | Reportes de capacitaciones |

La combinación de estos factores en una sola calificación 1–4 queda a criterio de Talento hasta que se formalice. El sistema solo almacena el resultado.

### 6.3 Matriz RACI — Impacto Arena

| Actividad | Evaluado | Líder de proyecto | Leads | Director | Talento |
|-----------|----------|-------------------|-------|----------|---------|
| Comunicar criterios y expectativas | I | I | I | I | **A** |
| Cumplir con los criterios | **A** | I | I | I | I |
| Consolidar información de cumplimiento | N/A | N/A | N/A | N/A | **A** |
| Calcular calificación individual (1–4) | N/A | N/A | N/A | N/A | **R/A** |
| Validación de la calificación | I | I | C | C | **A** |
| Registro formal del resultado | I | I | I | I | **R/A** |

---

## 7. Calificación final del periodo

### 7.1 Fórmula

```
calificacion_final = score_ownership      × peso_ownership(nivel)
                   + score_entrega_valor  × peso_entrega_valor(nivel)
                   + score_impacto_arena  × peso_impacto_arena(nivel)
```

Con los pesos de la sección 3. Redondeo a 2 decimales. Rango: 1.00 – 4.00.

**Ejemplo:** colaborador CD Mid con Ownership 3.40, Entrega de Valor 3.00, Impacto Arena 3.50:
`3.40×0.50 + 3.00×0.25 + 3.50×0.25 = 1.70 + 0.75 + 0.875 = 3.33`

### 7.2 Bandas de interpretación

*(Definidas el 9-jun-2026 para dar lectura cualitativa al promedio; alineadas a los anclajes de la escala.)*

| Rango | Interpretación |
|-------|----------------|
| 3.50 – 4.00 | Excede expectativas |
| 3.00 – 3.49 | Cumple |
| 2.00 – 2.99 | Cumple parcialmente |
| 1.00 – 1.99 | No cumple |

### 7.3 Condiciones de completitud

La calificación final de un colaborador en un periodo solo se considera **definitiva** cuando:
1. Tiene al menos 1 evaluación de Ownership **enviada** (una por cada proyecto del periodo).
2. Todos sus proyectos del periodo tienen evaluación de Entrega de Valor **validada** por el director.
3. Talento capturó su score de Impacto Arena.

Mientras falte un componente, el sistema puede mostrar una calificación **parcial/preliminar** claramente etiquetada.

### 7.4 Vista integral de resultados

Cada colaborador puede consultar en una sola vista: Calificación Final, Score Ownership, Score Entrega de Valor (con desglose por proyecto), Score Impacto Arena, Fortalezas, Oportunidades (y cursos del periodo, si aplica).

---

## 8. Reglas de negocio consolidadas (RN)

| ID | Regla |
|----|-------|
| RN-01 | Existen exactamente 4 áreas y 4 niveles de seniority; cada colaborador tiene exactamente un área y un nivel vigentes. |
| RN-02 | Cada combinación área×nivel tiene un checklist de Ownership propio; el colaborador solo puede responder el checklist de su puesto. |
| RN-03 | Las respuestas de escala valen 1, 2, 3, 4 o N/A. **Los N/A se excluyen de todos los promedios** (no cuentan como 0 ni en el denominador). |
| RN-04 | El score de una evaluación de Ownership es el promedio simple de sus respuestas numéricas, a 2 decimales. |
| RN-05 | Cada evaluación de Ownership está ligada a un proyecto y a su líder; un colaborador con N proyectos en el periodo genera hasta N evaluaciones de Ownership, y su score del pilar es el promedio simple de ellas. |
| RN-06 | Una evaluación de Ownership solo puede enviarse con la confirmación "revisé con mi líder" = Sí, y con Fortalezas y Oportunidades capturadas. Tras el envío es inmutable para el evaluado (solo Talento/admin puede reabrirla). |
| RN-07 | La evaluación de Entrega de Valor es por proyecto y por periodo: una sola por proyecto-periodo, capturada por el líder del proyecto y validada por el director. |
| RN-08 | El score de Entrega de Valor de un proyecto es el promedio de 3 criterios: satisfacción, entregables y el criterio de tiempo aplicable (finito o indefinido; exactamente uno aplica, el otro es N/A). |
| RN-09 | El score de Entrega de Valor del proyecto se asigna por igual a todos los miembros del equipo del proyecto; con varios proyectos, se promedian. |
| RN-10 | Toda la escala del modelo es 1–4 en los 3 pilares. No existe el valor 0. |
| RN-11 | Impacto Arena es un input manual de Talento (1–4, hasta 2 decimales) por colaborador-periodo. |
| RN-12 | Calificación final = promedio ponderado de los 3 pilares según el nivel del colaborador (tabla de la sección 3), a 2 decimales. |
| RN-13 | Periodicidad obligatoria semestral; pueden existir periodos opcionales trimestrales que no sustituyen al semestral. |
| RN-14 | El líder del proyecto valida el Ownership de los miembros de su proyecto; el lead de área tiene visibilidad de toda su área. |
| RN-15 | Confidencialidad: un colaborador solo ve sus propios resultados. Un Lead ve los de todos los colaboradores de su área. El líder de proyecto ve las evaluaciones que valida y las de Entrega de Valor de sus proyectos. Talento/admin ve todo. |
| RN-16 | Todo colaborador pertenece al menos a un proyecto; no existe el caso "sin proyecto". |
| RN-17 | La evaluación del Lead por parte de sus superiores está fuera del alcance del modelo. |
| RN-18 | El nivel Trainee está fuera del alcance del modelo y del sistema. |
| RN-19 | Ponderaciones vigentes: Jr 60/20/20, Mid 50/25/25, Snr 40/30/30, Lead 30/35/35 (Ownership/Entrega de Valor/Impacto Arena). |
| RN-20 | Bandas de interpretación de la calificación final: ≥3.50 Excede; 3.00–3.49 Cumple; 2.00–2.99 Cumple parcial; <2.00 No cumple. |

---

## 9. Permisos y visibilidad por rol (segregación de pantallas)

| Capacidad / Pantalla | Colaborador (Jr/Mid/Snr) | Lead de área | Líder de proyecto* | Talento / Admin | Superusuario |
|---|---|---|---|---|---|
| Login y perfil propio | ✔ | ✔ | ✔ | ✔ | ✔ |
| Llenar su checklist de Ownership (su área/nivel, por proyecto) | ✔ | ✔ (el suyo) | ✔ | — | ✔ |
| Ver sus propios resultados (todos los pilares) | ✔ | ✔ | ✔ | ✔ | ✔ |
| Ver evaluaciones/resultados de TODOS los colaboradores de su área | — | ✔ | — | ✔ | ✔ |
| Validar Ownership de miembros de sus proyectos (sesión + co-edición de fortalezas/oportunidades) | — | ✔ (si lidera proyectos) | ✔ | — | ✔ |
| Capturar Entrega de Valor de sus proyectos | — | ✔ (si lidera proyectos) | ✔ | — | ✔ |
| Validar Entrega de Valor (rol director) | — | — | — | ✔ (rol director) | ✔ |
| Capturar Impacto Arena (input manual) | — | — | — | ✔ | ✔ |
| Administrar catálogo de cuestionarios (preguntas, secciones, escalas) | — | — | — | ✔ | ✔ |
| Administrar usuarios, áreas, niveles, ponderaciones | — | — | — | ✔ | ✔ |
| Administrar proyectos y equipos | — | — | — | ✔ | ✔ |
| Administrar periodos (abrir/cerrar) | — | — | — | ✔ | ✔ |
| Reabrir evaluaciones enviadas | — | — | — | ✔ | ✔ |
| Dashboards globales / exportes | — | (su área) | (sus proyectos) | ✔ | ✔ |

\* "Líder de proyecto" no es un nivel: es una **relación** (usuario asignado como lead de un proyecto en el catálogo). Normalmente es un PM o un Lead, pero el permiso deriva de la asignación al proyecto, no del puesto. Importante: un líder de proyecto puede validar evaluaciones de personas de **otras áreas** (su equipo de proyecto es multidisciplinario).

---

## 10. Flujo de información y dependencias entre componentes

```
Catálogo de usuarios (área, nivel) ──┐
Catálogo de proyectos (lead, equipo) ─┤
Catálogo de cuestionarios (16) ───────┤
Catálogo de periodos ─────────────────┴──► EVALUACIÓN OWNERSHIP (colaborador×proyecto×periodo)
                                                  │ promedio sin N/A
                                                  ▼
                                          score_ownership (colaborador×periodo)
                                                  │
Proyecto×periodo ──► EVALUACIÓN ENTREGA DE VALOR ─┤
  (líder captura, director valida)                │ propagación a miembros + promedio
                                                  ▼
                                          score_entrega_valor (colaborador×periodo)
                                                  │
Talento ──► INPUT IMPACTO ARENA (manual) ─────────┤
                                                  ▼
                          CALIFICACIÓN FINAL = Σ (score_pilar × peso_nivel)
                                                  │
                              Vista de resultados + notificaciones + exportes
```

**Estados de una evaluación de Ownership:** `BORRADOR → ENVIADA` (con reapertura admin: `ENVIADA → BORRADOR`).
**Estados de una evaluación de Entrega de Valor:** `BORRADOR → EN_VALIDACION → VALIDADA` (rechazo del director regresa a `BORRADOR` con comentario).
**Estados de un periodo:** `PLANEADO → ABIERTO → CERRADO`. Al cerrar el periodo, todas las evaluaciones quedan de solo lectura.

**Dependencias temporales:**
1. No se puede crear una evaluación de Ownership sin: periodo ABIERTO + colaborador asignado al proyecto + cuestionario publicado para su área/nivel.
2. No se puede calcular la calificación final sin los 3 pilares completos (ver 7.3).
3. La Entrega de Valor requiere que el proyecto tenga líder y equipo definidos.

---

## 11. Catálogo seed de colaboradores

La lista oficial de colaboradores de Analítica 2026 (54 personas, dominio @arena-analytics.com) está en el **Anexo C**. El seed del sistema debe importarla. El área y nivel de cada colaborador **no están en la lista** y deberán asignarse vía administración `[PENDIENTE: mapeo persona→área/nivel]`.

---

## 12. Notificaciones del proceso (comportamiento heredado a replicar)

| Evento | Notificación |
|--------|--------------|
| Evaluación de Ownership enviada/registrada | Correo al evaluado con liga directa a su evaluación |
| Apertura de periodo | Comunicado de Talento con calendario y lineamientos |
| Resultado integral disponible | El colaborador puede consultar su vista integral |

---

## 13. Registro de decisiones de diseño (9 de junio de 2026)

| # | Tema | Decisión |
|---|------|----------|
| D-01 | Nivel Trainee | Descartado del modelo y del sistema |
| D-02 | Naturaleza del checklist | El colaborador captura; el líder valida y redactan comentarios en conjunto en sesión posterior. Se abandona el término "autoevaluación" |
| D-03 | N/A en promedios | Se excluyen de numerador y denominador. Regla formal (RN-03) |
| D-04 | Ponderaciones | Confirmadas: 60/20/20, 50/25/25, 40/30/30, 30/35/35 |
| D-05 | Escala Entrega de Valor | 1–4 (se elimina el 0; descriptores de 1 y 0 fusionados) |
| D-06 | Promedio Ownership | Promedio simple de ítems, omitiendo N/A |
| D-07 | Impacto Arena | Input manual de Talento, mecánica interna pendiente de definición |
| D-08 | Criterio de tiempo en EV | Exactamente uno aplica (finito o indefinido); el otro es N/A y se excluye; promedio de 3 elementos |
| D-09 | Gente sin proyecto | No existe ese caso en el ecosistema |
| D-10 | Evaluación del Lead | Fuera del alcance del modelo |
| D-11 | Responsable de EV | Líder del proyecto captura; director valida |
| D-12 | Bandas de interpretación | ≥3.50 Excede; 3.00–3.49 Cumple; 2.00–2.99 Cumple parcial; <2.00 No cumple |
| D-13 | Multi-proyecto | Una evaluación de Ownership por proyecto; promedios simples en ambos pilares |

---

# ANEXOS — Banco completo de cuestionarios (seed)

Los siguientes anexos contienen el texto íntegro y definitivo de los cuestionarios a precargar en el sistema. La numeración original de cada formulario se conserva como referencia; en el sistema, las preguntas 1–4 (identificación) se sustituyen por datos del usuario/proyecto, y las preguntas de conclusión/confirmación son campos estándar del flujo.


---

## Anexo A1 — Checklist Ownership: Ingeniería de Datos (ID)

# Checklist de Ownership — Ingeniería de Datos (ID)

> Evalúa cada actividad con base en evidencia concreta del período: entregables, sesiones, documentación o retroalimentación del cliente y del equipo.

**Escala de calificación:**
- **1 — No cumple:** La actividad no se ejecutó o se ejecutó con deficiencias significativas que impactaron el proyecto o al equipo.
- **2 — Cumple parcial:** La actividad se ejecutó pero con omisiones, inconsistencias o calidad por debajo del estándar esperado para el nivel.
- **3 — Cumple:** La actividad se ejecutó de forma consistente y completa, cumpliendo el estándar esperado para el nivel.
- **4 — Excede:** La actividad se ejecutó por encima del estándar del nivel, con iniciativa, precisión o impacto adicional notable.
- **N/A:** La actividad no aplicó en este período por razones justificadas (tipo de proyecto, fase, etc.).

---

## ID Jr

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: ID Jr / ID Mid / ID Snr / ID Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Notas de alcance** — Ejecutar proceso de discovery para identificar fuentes principales, el flujo E2E de los datos y los primeros pasos a tomar una vez que el proyecto arranca. Levantar dudas antes de empezar a desarrollar, no solo durante.

6. **Documento de alcance técnico** — Contribuir en la definición de qué se construye y qué no en el proyecto, documentando los componentes asignados a su nivel con precisión. No asumir que algo está en scope si no está explícitamente documentado.

7. **Checklist de requerimientos** — Completar el checklist de requerimientos técnicos y funcionales para los componentes bajo su responsabilidad, verificando que cada ítem tiene un estado claro (cumple / no cumple / pendiente) y escalando los pendientes críticos antes del inicio del desarrollo.

8. **Propuesta de conectividad** — Documentar los conectores asignados a su nivel: el medio de acceso a la fuente, la frecuencia de actualización y el método de carga (append, overwrite, delta). Levantar dudas sobre accesos o permisos antes de comenzar el desarrollo.

9. **Reporte de calidad de datos** — Ejecutar los checks de calidad de datos asignados a su nivel para las fuentes o desarrollos bajo su responsabilidad. Documentar los resultados y comunicar anomalías detectadas de forma inmediata.

10. **Reportes de pruebas** — Ejecutar los casos de prueba asignados a su nivel, documentando resultados esperados vs obtenidos y registrando issues o errores detectados. No declarar un componente como 'done' sin haber ejecutado, documentado y presentado sus pruebas.

11. **Reporte técnico de calidad de datos** — Ejecutar y compartir los reportes de calidad de datos de los componentes bajo su responsabilidad, documentando las reglas aplicadas, los resultados obtenidos y las excepciones encontradas.

12. **Scripts de validación** — Ejecutar los scripts de validación automática pre y post carga asignados a su nivel. Comunicar de inmediato cuando un script de validación falla o genera resultados inesperados.

13. **Esquema preliminar de tablas** — Construir el esquema preliminar de tablas para los componentes asignados con base en los comentarios y mockups del DE Sr/Mid/Lead, aplicando correctamente las convenciones de nombres, tipos de datos y claves definidas.

14. **Notas técnicas** — Registrar las decisiones técnicas, supuestos, trade-offs y dudas relevantes de los componentes bajo su responsabilidad durante todo el proyecto. Externalizar dudas al DE Mid/Sr antes de tomar decisiones técnicas por cuenta propia.

15. **Scripts, Notebooks y pipelines** — Implementar las tareas de desarrollo asignadas a su nivel siguiendo los estándares de calidad y versionado del proyecto (SOLID, naming conventions, modularidad). No entregar código sin haber ejecutado pruebas básicas.

16. **Checklist de ejecución** — Completar el checklist de ejecución para los componentes bajo su responsabilidad antes del despliegue, verificando que todos los ítems están marcados como completos y que no existen bloqueadores críticos sin resolver.

17. **Documentación de scripts** — Documentar el código desarrollado explicando propósito, inputs, outputs, dependencias y consideraciones de uso. La documentación es parte del entregable, no un paso opcional al final.

18. **Inventario de fuentes** — Recopilar la información básica de las fuentes de datos asignadas a su nivel: nombre, owner, frecuencia de actualización, formato y calidad estimada. Escalar cuando una fuente no tiene owner claro o cuando su accesibilidad es incierta.

19. **Diagrama de arquitectura** — Entender completamente la arquitectura del proyecto y sus componentes. Identificar la posición de los desarrollos bajo su responsabilidad dentro del flujo end-to-end y comunicar al DE Mid/Sr/Lead cuando detecta que algo en su implementación se desvía del diseño arquitectónico.

20. **Modelado de datos** — Documentar los campos y tipos de datos de las tablas asignadas correctamente, siguiendo las convenciones del proyecto. Verificar con el DE Mid/Sr/Lead antes de implementar si hay dudas sobre granularidad o relaciones.

21. **Diseño de pipelines** — Entender el diseño lógico del pipeline y documentar los pasos correspondientes a los componentes bajo su responsabilidad. Comunicar al DE Mid/Sr/Lead cuando la implementación requiere ajustes al diseño definido.

22. **Desarrollo de pipelines** — Implementar las tareas de desarrollo de pipelines asignadas a su nivel: ingestión de datos, transformaciones simples y cargas bajo supervisión del DE Mid/Sr/Lead. No entregar componentes sin haber ejecutado una prueba end-to-end básica.

23. **Scripts de validación y calidad de datos** — Ejecutar los scripts de validación técnica y de negocio asignados a su nivel, verificando completitud, unicidad y consistencia básica. Analizar los resultados y comunicar al DE Mid/Sr/Lead cualquier incumplimiento detectado.

24. **Pruebas técnicas y de integración** — Ejecutar las pruebas unitarias asignadas a su nivel para los componentes bajo su responsabilidad. Documentar los resultados y escalar los defectos encontrados al DE Mid/Sr/Lead con evidencia.

25. **Documentación técnica integral** — Documentar correctamente los componentes bajo su responsabilidad como parte del proceso de desarrollo, asegurando que la documentación está actualizada con el código final antes de considerarlo terminado.

26. **Rutinas de gestión — Daily** — Asistir al daily preparado, comunicando claramente el avance de sus componentes, bloqueos activos y dependencias. No llegar al daily a descubrir sus propios bloqueos: deben estar identificados y comunicados antes de la sesión.

27. **Rutinas de gestión — Sprint Planning** — Asistir al sprint planning preparado con una propuesta de sus actividades y estimaciones de tiempo para el sprint. No llegar al planning sin haber revisado el backlog y sin saber qué puede comprometer.

28. **Rutinas de gestión — Sprint Review** — Asistir al sprint review preparado para exponer el resultado de sus componentes, explicar qué completó y qué no, y recibir retroalimentación técnica sin ponerse a la defensiva.

29. **Coordinación con DS y PM** — Alinear con el equipo de Ciencia de Datos los requerimientos de datos y las interfaces de entrega antes de cada fase de desarrollo. No comenzar a desarrollar una exposición de datos sin haber validado el formato y la granularidad esperada con el equipo.

30. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

31. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

32. **Fortalezas**
33. **Oportunidades**
34. **Comentarios** *(opcional)*

---

**Confirmación de envío**

35. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## ID Mid

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: ID Jr / ID Mid / ID Snr / ID Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Notas de alcance** — Liderar el proceso de discovery identificando posibles bloqueos durante la implementación, dependencias entre fuentes y riesgos técnicos. Documentar supuestos críticos y escalar al DE Sr/Lead los que requieran decisión de arquitectura.

6. **Documento de alcance técnico** — Redactar el alcance técnico del proyecto, definiendo explícitamente qué se construye y qué queda fuera. Alinear el alcance con las notas de discovery y obtener el sign-off del equipo y del cliente antes de comenzar el desarrollo.

7. **Checklist de requerimientos** — Validar técnicamente los requerimientos del proyecto, identificando ambigüedades, conflictos entre requerimientos y riesgos de implementación. Asegurar que todos los requerimientos críticos tienen estado definido antes del inicio del desarrollo.

8. **Propuesta de conectividad** — Definir los métodos de carga, frecuencias y características técnicas de los conectores del proyecto. Evaluar opciones de conectividad considerando restricciones de acceso, seguridad y volumen de datos.

9. **Reporte de calidad de datos** — Ejecutar y analizar los resultados de los reportes de calidad de datos, identificar tendencias, priorizar las acciones de mejora y comunicar hallazgos al equipo con recomendaciones concretas.

10. **Reportes de pruebas** — Ejecutar y analizar los resultados de las pruebas del equipo, validar que los defectos detectados están correctamente clasificados y tomar la decisión de si un componente está listo para producción.

11. **Reporte técnico de calidad de datos** — Ejecutar y analizar los resultados de calidad, dar seguimiento al incremento de los indicadores entre períodos y asegurar que las recomendaciones del reporte anterior se implementaron.

12. **Scripts de validación** — Desarrollar los scripts de validación automática pre y post carga, asegurando que las fallas generan alertas o logs claros y que los scripts están integrados al flujo de ejecución.

13. **Esquema preliminar de tablas** — Revisar el esquema de tablas constantemente, dar retroalimentación al equipo sobre inconsistencias detectadas y asegurar que el esquema está alineado con el modelo lógico antes del inicio del desarrollo.

14. **Notas técnicas** — Concentrar las notas técnicas del equipo, aclarar las dudas levantadas por el equipo y el cliente y convertir las notas en tareas o metas claras en el backlog del proyecto.

15. **Scripts, Notebooks y pipelines** — Orquestar los pipelines del equipo, asegurando la correcta integración de los componentes del flujo completo. Identificar y corregir problemas de modularidad o reutilización antes del sprint review.

16. **Checklist de ejecución** — Revisar el checklist de ejecución del equipo, dar retroalimentación al equipo sobre ítems incompletos y asegurar que no existen bloqueadores críticos antes de aprobar el despliegue.

17. **Documentación de scripts** — Revisar la documentación del equipo y dar retroalimentación sobre completitud y claridad antes de considerarla como entregable. Documentar la integración de los pipelines orquestados.

18. **Inventario de fuentes** — Analizar la estructura, frecuencia, volumen y calidad de las fuentes de datos del proyecto. Identificar riesgos y limitaciones de cada fuente y documentarlos con propuestas de mitigación.

19. **Diagrama de arquitectura** — Entender la arquitectura definida para el proyecto y comunicarla con precisión al equipo y al cliente. Detectar desviaciones de implementación del equipo respecto al diseño durante el sprint, antes del roll-out.

20. **Modelado de datos** — Diseñar las tablas del proyecto y validar la granularidad correcta con el equipo. Asegurar que el modelo de datos es coherente con las métricas y entidades de negocio definidas.

21. **Diseño de pipelines** — Diseñar los pipelines estándar del proyecto: pasos, dependencias, manejo de errores, reintentos y ventanas de tiempo. Asegurar que el diseño es consistente con la arquitectura definida y aprobado antes del desarrollo.

22. **Desarrollo de pipelines** — Implementar pipelines completos: ingestión, transformaciones, cargas incrementales e historificación. Asegurar que los pipelines del desarrollo están correctamente integrados en el flujo completo.

23. **Scripts de validación y calidad de datos** — Desarrollar los scripts de validación técnica y de negocio del proyecto. Asegurar que los resultados son auditables y que las alertas son accionables por cualquier miembro del equipo.

24. **Pruebas técnicas y de integración** — Ejecutar las pruebas de integración del proyecto, verificando que los pipelines funcionan correctamente de forma conjunta. Asegurar que los casos críticos y los escenarios de error están cubiertos.

25. **Optimización de pipelines** — Analizar el desempeño de los pipelines e identificar oportunidades de optimización en tiempo de ejecución, consumo de recursos y costos. Implementar optimizaciones conocidas y documentar el impacto con métricas comparativas.

26. **Runbooks** — Actualizar y mantener los runbooks operativos del proyecto, asegurando que los procedimientos ante fallas son claros y utilizables por personal no desarrollador.

27. **Documentación técnica integral** — Mantener la documentación técnica del proyecto actualizada a lo largo del desarrollo. Revisar la documentación del equipo y asegurar que la documentación del proyecto está lista para auditoría o handover en cualquier momento.

28. **Informe de transición** — Ejecutar la transición formal del producto de datos a operación o al equipo receptor. Asegurar que el conocimiento técnico, los riesgos conocidos y las responsabilidades están claramente documentados y aceptados por el receptor.

29. **Rutinas de gestión — Daily** — Asistir al daily preparado, reportando el avance propio y el del equipo a su cargo. Identificar bloqueos del equipo antes de que impacten entregables y gestionarlos activamente.

30. **Rutinas de gestión — Sprint Planning** — Asistir al sprint planning preparado con propuesta de actividades propias y del equipo a su cargo, incluyendo estimaciones, definitions of completeness y dependencias inter-equipo.

31. **Rutinas de gestión — Sprint Review** — Asistir al sprint review exponiendo resultados propios, identificando qué se completó y qué no. Dar retroalimentación técnica honesta y documentada al equipo.

32. **Coordinación con DS y PM** — Alinear con el equipo de Ciencia de Datos los requerimientos de datos, interfaces y formatos de entrega antes de cada fase. Comunicar al PM cuando un cambio técnico en las fuentes impacta el plan de entrega.

33. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

34. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

35. **Fortalezas**
36. **Oportunidades**
37. **Comentarios** *(opcional)*

---

**Confirmación de envío**

38. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## ID Snr

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: ID Jr / ID Mid / ID Snr / ID Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Notas de alcance** — Liderar el discovery identificando fuentes críticas a nivel de negocio, diseñando la estrategia de implementación escalable y mapeando fuentes legacy y dependencias entre fuentes. Anticipar riesgos de implementación que no son visibles para el DE Mid.

6. **Esquemas de Bases de datos** — Realizar el diagrama entidad-relación de las tablas fuente y de las tablas destino, con campos tipificados, formatos y relaciones (PK/FK) claramente definidas. Asegurar que las reglas de negocio están correctamente interpretadas, modeladas y alineadas con la arquitectura.

7. **Matriz de trazabilidad** — Construir y mantener la matriz de trazabilidad que mapea las reglas de transformación entre fuentes y destinos. Compartirla con el equipo y explicar su funcionamiento para que el DE Mid y DE Jr puedan utilizarla como referencia durante el desarrollo.

8. **Documento de alcance técnico** — Definir los límites técnicos del proyecto con criterio, identificar riesgos de alcance y alinear el documento con todos los stakeholders técnicos y de negocio antes del inicio del desarrollo.

9. **Checklist de requerimientos** — Identificar riesgos técnicos en los requerimientos y asegurar que la alineación entre negocio y el equipo técnico es completa antes del inicio del desarrollo. Escalar al cliente los requerimientos que son técnicamente inviables tal como están definidos.

10. **Propuesta de conectividad** — Evaluar las opciones de conectividad considerando costos, performance, seguridad y escalabilidad. Aprobar la propuesta final y asegurar su alineación con la arquitectura definida.

11. **Reporte de calidad de datos** — Proponer las reglas de calidad del proyecto y definir el framework de data quality que el equipo implementará. Asegurar que el framework es adoptado consistentemente por el DE Mid y DE Jr.

12. **Reportes de pruebas** — Proponer las reglas de calidad y monitorear los resultados de las pruebas del equipo. Tomar la decisión final de liberar o no liberar a producción basado en la evidencia del reporte del DE Mid.

13. **Reporte técnico de calidad de datos** — Analizar los resultados de calidad del período, dar retroalimentación constante al equipo y asegurar que las métricas mejoran entre períodos. Escalar a Negocio cuando los problemas de calidad tienen impacto en los modelos del DS.

14. **Scripts de validación** — Optimizar y estandarizar los scripts de validación del proyecto. Definir las librerías comunes de validación que el equipo reutilizará en futuros desarrollos.

15. **Esquema preliminar de tablas** — Construir el mockup del esquema inicial, compartirlo con el equipo y dar seguimiento constante al cumplimiento de las convenciones durante el desarrollo. Realizar la revisión final del esquema antes del deployment.

16. **Notas técnicas** — Concentrar las notas técnicas del equipo, esclarecer las dudas levantadas y convertir las decisiones técnicas en tareas o metas claras en el backlog. Asegurar que ninguna decisión técnica relevante queda sin documentar.

17. **Scripts, Notebooks y pipelines** — Optimizar y escalar los desarrollos del equipo. Definir los patrones de desarrollo que el DE Mid y DE Jr seguirán para asegurar modularidad, reutilización y cumplimiento de estándares.

18. **Checklist de ejecución** — Revisar el cumplimiento del checklist de ejecución y dar retroalimentación al equipo sobre desviaciones detectadas. Aprobar el despliegue solo cuando todos los ítems están verificados.

19. **Documentación de scripts** — Revisar la documentación del equipo y dar retroalimentación sobre completitud y calidad técnica. Asegurar que la documentación del proyecto está lista para auditoría o handover en cualquier momento.

20. **Inventario de fuentes** — Evaluar la calidad, estabilidad y riesgos técnicos de las fuentes del proyecto. Identificar fuentes con historial de inestabilidad o problemas de calidad y proponer estrategias de mitigación.

21. **Diagrama de arquitectura** — Refinar el diseño de arquitectura para escalabilidad y operación en producción. Aprobar la arquitectura final y comunicarla al equipo con suficiente detalle para que el DE Mid pueda implementar sin ambigüedades.

22. **Modelado de datos** — Definir el modelo de datos completo y la granularidad correcta para las métricas del negocio. Validar la alineación del modelo con el negocio y con la arquitectura definida.

23. **Diseño de pipelines** — Validar el diseño de pipelines del DE Mid considerando fallos, escalabilidad y escenarios de error. Aprobar el diseño final antes del inicio del desarrollo.

24. **Desarrollo de pipelines** — Refactorizar, optimizar y asegurar la calidad de los pipelines del equipo. Definir los estándares de desarrollo que el DE Mid y DE Jr seguirán durante el proyecto.

25. **Scripts de validación y calidad de datos** — Diseñar las reglas de calidad robustas del proyecto y aprobar el enfoque y cobertura de los scripts del DE Mid. Asegurar que las reglas cubren los escenarios de negocio más críticos.

26. **Pruebas técnicas y de integración** — Diseñar la estrategia de testing del proyecto y aprobar los resultados finales antes del pase a producción. Asegurar que los casos críticos y los escenarios de error están cubiertos.

27. **Optimización de pipelines** — Optimizar el performance y los costos de los pipelines del proyecto. Validar el impacto técnico y financiero de las optimizaciones del DE Mid.

28. **Runbooks** — Diseñar los flujos de soporte y definir los SLAs y niveles de soporte del proyecto. Asegurar que los runbooks son suficientemente completos para que el equipo de operaciones del cliente pueda operar sin apoyo de Arena.

29. **Documentación técnica integral** — Validar la coherencia técnica de la documentación del proyecto y garantizar su completitud y calidad antes del cierre. Asegurar que la documentación es suficiente para una auditoría o handover sin apoyo del equipo.

30. **Informe de transición** — Asegurar que la transferencia de conocimiento técnico está completa y aprobar el cierre del proyecto. Garantizar que el equipo receptor puede operar sin apoyo de Arena.

31. **Rutinas de gestión — Daily** — Asistir al daily reportando avance propio en definición, coordinación y validación. Identificar y anticipar riesgos técnicos del equipo como principal responsable de la gestión de riesgos técnicos del proyecto.

32. **Rutinas de gestión — Sprint Planning** — Asistir al sprint planning liderando la definición de actividades técnicas del equipo. Hacer challenge de estimaciones no realistas y asegurar que todas las tareas tienen definition of completeness antes de comprometerse.

33. **Rutinas de gestión — Sprint Review** — Exponer resultados técnicos del equipo en el sprint review, identificar áreas de mejora propias y del equipo, y dar retroalimentación técnica profunda al DE Mid.

34. **Coordinación con DS y PM** — Liderar la alineación técnica con el equipo de Ciencia de Datos definiendo las interfaces de datos, formatos y granularidades que el pipeline proveerá. Comunicar al PM impactos técnicos que afecten el plan con suficiente anticipación para renegociar con el cliente.

35. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

36. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

37. **Fortalezas**
38. **Oportunidades**
39. **Comentarios** *(opcional)*

---

**Confirmación de envío**

40. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## ID Lead

> **Escala para nivel Lead:** 1 — No cumple (impacto negativo) / 2 — Cumple parcial (incompleto o tardío) / 3 — Cumple (consistente y proactivo) / 4 — Excede (impacto diferencial) / N/A

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: ID Jr / ID Mid / ID Snr / ID Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

### Aseguramiento de calidad técnica del equipo

5. Realizar seguimiento a los DE Sr/Mid de sus proyectos para evaluar el cumplimiento de sus checklists correspondientes. Documentar hallazgos y dar retro directa en sesión 1:1.

6. Asegurar que los proyectos a su cargo cumplen con las actividades de la Oficina de PMO y con los estándares de arquitectura de datos de Arena. Identificar brechas técnicas y escalarlas al director de Analítica cuando no puedan resolverse a nivel de proyecto.

7. Hacer equipo con los leads técnicos de DS, Producto y UX para asegurar que los proyectos cuentan con los diseños de integración de datos correctos y que no hay brechas entre lo que el pipeline entrega y lo que el DS necesita.

### Guía y soporte al equipo de proyecto

8. Asistir y participar activamente en los dailys al inicio del proyecto, en fases de entregables críticos y en el cierre. Evaluar en cada asistencia la preparación del equipo, el foco técnico y el cumplimiento de agenda y tiempos.

9. Asistir y participar activamente en los sprint planning y sprint review. Hacer challenge técnico de estimaciones de pipeline, diseños de arquitectura comprometidos y consistencia entre lo que se planea construir y la propuesta original.

10. Ayudar al equipo a mapear y entender todos los stakeholders técnicos y de negocio involucrados en el proyecto, incluyendo sus motivaciones, nivel de influencia y postura hacia las decisiones de arquitectura.

11. Identificar, validar el material técnico y participar en sesiones críticas con stakeholders senior del cliente o de tecnología del cliente que requieran el criterio del DE Lead. Asegurar que el equipo tiene clara la agenda y el objetivo técnico antes de construir el material.

12. Agendar y ejecutar one-on-ones con stakeholders técnicos senior del cliente (CTO, arquitectos, equipo de infraestructura) para alinear expectativas técnicas, anticipar restricciones de ambiente y construir una relación de confianza técnica.

13. Anticipar y coordinar la participación del director de Analítica en momentos críticos del proyecto (revisiones de arquitectura, escalamientos de cliente, decisiones de alcance técnico), comunicando con claridad el contexto y el tipo de apoyo requerido.

14. Crear y ejecutar un plan de transición, onboarding técnico, KT y seguimiento al staffing del proyecto al inicio, durante y al final, considerando riesgos de pérdida de conocimiento de arquitectura ante cambios de equipo.

### Guía y soporte al equipo interno

15. Asegurar que los proyectos a su cargo cumplen con las actividades de la Mesa de Talento, incluyendo evaluaciones de desempeño cerradas antes de que el equipo se reasigne a otros proyectos.

16. Monitorear el avance de los planes de capacitación técnica del equipo de Ingeniería en sus proyectos. Identificar quién no puede avanzar por carga de trabajo y escalar al director de Analítica con propuesta de solución.

17. Monitorear la ejecución y calidad de las sesiones de mentoring de los DE Sr/Mid en sus proyectos. Actuar sobre el mentoring que no está generando desarrollo real en el mentee.

18. Dar seguimiento a la planeación y anticipación de vacaciones y ausencias del equipo de DE en sus proyectos, gestionándolas como riesgo de continuidad de pipeline, no como trámite administrativo.

19. Ser el punto de referencia del equipo de DE para resolver dudas sobre procedimientos internos de Arena (PMO, Odoo, Mesa de Talento, vacaciones, etc.) sin necesidad de intermediación de RH o PMO.

20. Planear y ejecutar sesiones de aprendizaje técnico con el equipo de DE. Las sesiones deben desarrollar capacidades de arquitectura, ingeniería de datos o consultoría técnica que el equipo pueda aplicar en proyectos.

21. Identificar y gestionar la implementación de mejoras a las metodologías, estándares de arquitectura y herramientas del equipo de DE, en coordinación con los demás leads y el director de Analítica.

### Soporte comercial

22. Identificar oportunidades de expansión del trabajo de DE en los proyectos: nuevas fuentes de datos, modernización de arquitecturas legacy, automatización de procesos manuales del cliente o expansión de la cobertura del pipeline actual.

23. Dar soporte en la construcción y validación técnica de propuestas de ingeniería de datos: viabilidad de arquitectura, estimaciones de esfuerzo de pipeline, alcance técnico y dependencias con el cliente.

24. Dar soporte en el seguimiento a facturación y temas administrativos del proyecto cuando sea requerido por el director.

25. Coordinar y tener sesiones presenciales en las oficinas del cliente o de Arena para fortalecer la relación técnica y mantener una presencia activa de Arena con el equipo de tecnología del cliente.

### Cumplimiento de lineamientos de trabajo remoto

26. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

27. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

28. **Fortalezas**
29. **Oportunidades**
30. **Comentarios** *(opcional)*

---

**Confirmación de envío**

31. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---

## Anexo A2 — Checklist Ownership: Ciencia de Datos (CD)

# Checklist de Ownership — Ciencia de Datos (CD)

> Evalúa cada actividad con base en evidencia concreta del período: entregables, sesiones, documentación o retroalimentación del cliente y del equipo.

**Escala de calificación:**
- **1 — No cumple:** La actividad no se ejecutó o se ejecutó con deficiencias significativas que impactaron el proyecto o al equipo.
- **2 — Cumple parcial:** La actividad se ejecutó pero con omisiones, inconsistencias o calidad por debajo del estándar esperado para el nivel.
- **3 — Cumple:** La actividad se ejecutó de forma consistente y completa, cumpliendo el estándar esperado para el nivel.
- **4 — Excede:** La actividad se ejecutó por encima del estándar del nivel, con iniciativa, precisión o impacto adicional notable.
- **N/A:** La actividad no aplicó en este período por razones justificadas (tipo de proyecto, fase, etc.).

---

## CD Jr

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: CD Jr / CD Mid / CD Snr / CD Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Backlog de tareas** — Mantener un backlog de tareas de sus actividades, confirmando prioridades, expectativas de tiempo de entrega y dependencias (técnicas y operativas) de acuerdo con los estándares de la Oficina de PMO.

6. **Documentación del avance** — Actualizar y documentar el avance de sus tareas en la herramienta de seguimiento correspondiente y de acuerdo con los estándares de la Oficina de PMO. Incluir riesgos, dependencias y bloqueos activos.

7. **Documentación de los estándares de desarrollo y buenas prácticas** — Revisar, entender y aplicar los estándares de desarrollo y documentación vigentes para el proyecto desde el inicio del mismo.

8. **Diseño de arquitectura de datos** — Entender y documentar el diseño de arquitectura definido por el DS Sr/Lead y aplicarlo correctamente en sus desarrollos. Identificar cuando sus implementaciones se desvían del diseño acordado y comunicarlo de inmediato.

9. **Excelencia técnica de métodos estadísticos** — Implementar, ejecutar y darle seguimiento, con una base teórica sólida y siguiendo las buenas prácticas del trabajo estadístico, a las distintas pruebas (paramétricas o no), planes de muestreo, pruebas de hipótesis y modelación matemática que requiera el producto, validando cuidadosamente los supuestos empleados en cada caso.

10. **Funcionalidad óptima de código y excelencia técnica en programación** — Realizar, de manera óptima y de acuerdo con las pautas (técnicas y de infraestructura) establecidas en el proyecto, el código que ejecute la solución (o una parte de ella) asignada por el DS Mid, siguiendo las buenas prácticas y los más altos estándares de calidad en su programación.

11. **Documentación de reglas de negocio** — Entender las reglas de negocio definidas y validar que sus implementaciones las incorporan correctamente. Levantar dudas sobre la aplicación de una regla antes de codificarla.

12. **Rutinas de gestión y control interno 1** — Asistir al daily preparado, comunicando claramente el avance de sus actividades, bloqueos, dependencias y riesgos. No llegar al daily a descubrir sus propios bloqueos: deben estar identificados antes de la sesión.

13. **Rutinas de gestión y control interno 2** — Asistir al touchpoint o one-on-one interno con el DS Lead/Mid comunicando proactivamente los puntos más críticos de sus actividades, dudas técnicas y personales, y compromisos del período.

14. **Rutinas de gestión y control interno 3** — Asistir al sprint planning preparado, con una propuesta propia de sus actividades, estimaciones de tiempo, criterios de aceptación y dependencias relevantes para el sprint.

15. **Rutinas de gestión y control interno 4** — Asistir al sprint review y retro preparado, exponiendo los resultados de sus tareas, aprendizajes del sprint y áreas de mejora concretas. Recibir feedback sin ponerse a la defensiva.

16. **Checklist de validaciones** — Ejecutar y documentar las validaciones técnicas de cada entregable antes de considerarlo completo. No declarar una tarea como 'done' sin haber ejecutado el checklist correspondiente.

17. **Plan de deployment y roll-out** — Entender el plan de despliegue definido y ejecutar las actividades de deployment asignadas siguiendo los lineamientos del DS Sr/Lead. Comunicar cualquier incidente o desviación durante el roll-out de forma inmediata.

18. **Minuta de reuniones con Negocio** — Apoyar en el registro de acuerdos, definiciones y peticiones de Negocio (relacionadas con Ciencia de Datos) durante sesiones donde participe. Garantizar que los acuerdos relevantes para sus tareas están capturados correctamente.

19. **Checklist de documentación y revisiones de código** — Documentar el código desarrollado siguiendo las buenas prácticas definidas por Arena y los requerimientos de Negocio. La documentación es parte del entregable, no un paso opcional al final.

20. **Plan de KT y legacy** — Ejecutar las sesiones de KT asignadas a su nivel, garantizando que Negocio puede operar los desarrollos del DS Jr de forma autónoma después del cierre del proyecto.

21. **Resumen de herramientas y necesidades técnicas** — Comunicar proactivamente sus necesidades técnicas, de capacitación y accesos requeridos para ejecutar su trabajo en cada sprint. No esperar a que le pregunten si tiene todo lo que necesita.

22. **Preparación y participación en sesiones con Negocio** — Prepararse para cada sesión con Negocio anticipando preguntas técnicas que puedan surgir sobre los desarrollos bajo su responsabilidad. Llevar respuestas preparadas, no improvisar en sesión.

23. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

24. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams en tiempo y forma, dentro de las 24 horas hábiles de haberlos recibido.

---

**Conclusión** *(texto libre)*

25. **Fortalezas**
26. **Oportunidades**
27. **Comentarios** *(opcional)*

---

**Confirmación de envío**

28. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## CD Mid

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: CD Jr / CD Mid / CD Snr / CD Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Backlog de tareas** — Mantener un backlog de tareas de sus actividades, confirmando prioridades, expectativas de tiempo de entrega y dependencias (técnicas y operativas) de acuerdo con los estándares de la Oficina de PMO.

6. **Documentación del avance** — Actualizar y documentar el avance de sus tareas en la herramienta de seguimiento correspondiente y de acuerdo con los estándares de la Oficina de PMO. Incluir riesgos, dependencias y bloqueos activos.

7. **Documentación de los estándares de desarrollo y buenas prácticas** — Revisar, entender y aplicar los estándares de desarrollo y documentación vigentes para el proyecto desde el inicio del mismo.

8. **Diseño de arquitectura de datos** — Entender y documentar el diseño de arquitectura definido por el DS Sr/Lead y aplicarlo correctamente en sus desarrollos. Identificar cuando sus implementaciones se desvían del diseño acordado y comunicarlo de inmediato.

9. **Excelencia técnica de métodos estadísticos** — Implementar, ejecutar y darle seguimiento, con una base teórica sólida y siguiendo las buenas prácticas del trabajo estadístico, a las distintas pruebas (paramétricas o no), planes de muestreo, pruebas de hipótesis y modelación matemática que requiera el producto, validando cuidadosamente los supuestos empleados en cada caso.

10. **Funcionalidad óptima de código y excelencia técnica en programación** — Realizar, de manera óptima y de acuerdo con las pautas (técnicas y de infraestructura) establecidas en el proyecto, el código que ejecute la solución (o una parte de ella) asignada por el DS Mid, siguiendo las buenas prácticas y los más altos estándares de calidad en su programación.

11. **Documentación de reglas de negocio** — Entender las reglas de negocio definidas y validar que sus implementaciones las incorporan correctamente. Levantar dudas sobre la aplicación de una regla antes de codificarla.

12. **Rutinas de gestión y control interno 1** — Asistir al daily preparado, comunicando claramente el avance de sus actividades, bloqueos, dependencias y riesgos. No llegar al daily a descubrir sus propios bloqueos: deben estar identificados antes de la sesión.

13. **Rutinas de gestión y control interno 2** — Asistir al touchpoint o one-on-one interno con el DS Lead/Mid comunicando proactivamente los puntos más críticos de sus actividades, dudas técnicas y personales, y compromisos del período.

14. **Rutinas de gestión y control interno 3** — Asistir al sprint planning preparado, con una propuesta propia de sus actividades, estimaciones de tiempo, criterios de aceptación y dependencias relevantes para el sprint.

15. **Rutinas de gestión y control interno 4** — Asistir al sprint review y retro preparado, exponiendo los resultados de sus tareas, aprendizajes del sprint y áreas de mejora concretas. Recibir feedback sin ponerse a la defensiva.

16. **Rutinas de gestión y control interno 5** — Asistir al touchpoint semanal con los Leads de DE y Producto preparado, con updates de los proyectos que involucran a su equipo, bloqueos inter-equipo y compromisos. Representar al equipo de Ciencia con criterio propio.

17. **Rutinas de gestión y control interno 6** — Preparar y liderar el biweekly de datos con Negocio mostrando avances técnicos, supuestos estadísticos, reglas de negocio y benchmark entre modelos. Llevar respuestas preparadas a preguntas técnicas previsibles.

18. **Rutinas de gestión y control interno 7** — Coordinar y ejecutar las ceremonias de actualización al backlog, justificando adiciones y documentando reducciones con responsable, validador y, cuando aplique, responsable del pase a productivo.

19. **Checklist de validaciones** — Ejecutar y documentar las validaciones técnicas de cada entregable antes de considerarlo completo. No declarar una tarea como 'done' sin haber ejecutado el checklist correspondiente.

20. **Plan de deployment y roll-out** — Entender el plan de despliegue definido y ejecutar las actividades de deployment asignadas siguiendo los lineamientos del DS Sr/Lead. Comunicar cualquier incidente o desviación durante el roll-out de forma inmediata.

21. **Minuta de reuniones con Negocio** — Apoyar en el registro de acuerdos, definiciones y peticiones de Negocio (relacionadas con Ciencia de Datos) durante sesiones donde participe. Garantizar que los acuerdos relevantes para sus tareas están capturados correctamente.

22. **Checklist de documentación y revisiones de código** — Documentar el código desarrollado siguiendo las buenas prácticas definidas por Arena y los requerimientos de Negocio. La documentación es parte del entregable, no un paso opcional al final.

23. **Plan de KT y legacy** — Ejecutar las sesiones de KT asignadas a su nivel, garantizando que Negocio puede operar los desarrollos del DS Jr de forma autónoma después del cierre del proyecto.

24. **Resumen de herramientas y necesidades técnicas** — Comunicar proactivamente sus necesidades técnicas, de capacitación y accesos requeridos para ejecutar su trabajo en cada sprint. No esperar a que le pregunten si tiene todo lo que necesita.

25. **Preparación y participación en sesiones con Negocio** — Prepararse para cada sesión con Negocio anticipando preguntas técnicas que puedan surgir sobre los desarrollos bajo su responsabilidad. Llevar respuestas preparadas, no improvisar en sesión.

26. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

27. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams en tiempo y forma, dentro de las 24 horas hábiles de haberlos recibido.

---

**Conclusión** *(texto libre)*

28. **Fortalezas**
29. **Oportunidades**
30. **Comentarios** *(opcional)*

---

**Confirmación de envío**

31. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## CD Snr

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: CD Jr / CD Mid / CD Snr / CD Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Backlog de tareas** — Definir y mantener el backlog técnico del equipo de Ciencia, incluyendo deuda técnica, entrenamiento/reentrenamiento de modelos, métricas, sesgo, anomalías y validaciones. Asegurar que el backlog está priorizado de acuerdo con el valor al cliente y la viabilidad técnica, no solo con la urgencia operativa.

6. **Documentación del avance** — Coordinar con el DS Mid la distribución de tareas del sprint y asegurar que el plan refleja las fases de diseño y modelación con el nivel de detalle necesario. Detectar riesgos estructurales del sprint antes de que ocurran.

7. **Documentación de los estándares de desarrollo y buenas prácticas** — Definir, validar y asegurar la correcta aplicación de estándares de trabajo, desarrollo y buenas prácticas en todos los entregables del equipo de Ciencia. Resolver conflictos entre los estándares de Arena y los requerimientos de Negocio con criterio técnico documentado.

8. **Diseño de arquitectura de datos** — Diseñar, documentar y validar con DE y Producto la arquitectura de datos necesaria para el despliegue de soluciones en ambiente productivo. Comunicar explícitamente los componentes que no existen en el ecosistema de Negocio o que implican costos adicionales.

9. **Excelencia técnica de métodos estadísticos** — Diseñar, coordinar, implementar, ejecutar, evaluar y criticar, con bases teóricas sólidas y buenas prácticas del trabajo estadístico, todos los aspectos matemáticos o estadísticos (modelos, pruebas de hipótesis, pruebas, muestreo, etc.) que requiera el producto, validando cuidadosamente los supuestos que defina o elija en cada caso.

10. **Funcionalidad óptima de código y excelencia técnica en programación** — Diseñar, asignar y supervisar, apegado a las buenas prácticas y requerimientos (técnicos y de staff) establecidos en el proyecto, el pseudocódigo y los algoritmos que resuelven el problema de negocio. Dependiendo de la naturaleza del proyecto, le da seguimiento a la integración de pipelines, soluciones de GenAI, modelos de analítica avanzada y POC, cerciorándose de su correcto funcionamiento, mantenimiento, accesibilidad y escalabilidad.

11. **Documentación de reglas de negocio** — Definir y validar con Negocio y Producto las reglas de negocio dentro de los supuestos estadísticos del proyecto. Supervisar su correcta implementación en el pipeline y gestionar la deprecación de reglas que pierdan vigencia.

12. **Rutinas de gestión y control interno 1** — Asistir al daily reportando su avance en definición, coordinación y validación. Identificar y anticipar riesgos del sprint como principal responsable de la gestión de riesgos técnicos del equipo de Ciencia.

13. **Rutinas de gestión y control interno 2** — Asistir al touchpoint semanal con el DS Lead preparado con updates de proyectos, riesgos técnicos, plan de mentoring y compromisos del período. En ausencia del DS Lead, asumir la conducción del touchpoint.

14. **Rutinas de gestión y control interno 3** — Asistir al touchpoint con los Leads de DE y Producto representando al equipo de Ciencia con criterio propio. En ausencia del DS Lead, ser el vocero del equipo y documentar los acuerdos inter-equipo.

15. **Rutinas de gestión y control interno 4** — Liderar el sprint planning definiendo qué ejecutará, coordinará y validará durante el sprint. Hacer challenge de las actividades del equipo que no estén alineadas, no sean realistas o tengan definiciones incompletas.

16. **Rutinas de gestión y control interno 5** — Exponer su desempeño en el sprint review y retro, identificar áreas de mejora propias y del equipo, y proponer cambios concretos para el siguiente sprint. Dar retroalimentación técnica profunda al DS Mid.

17. **Rutinas de gestión y control interno 6** — Liderar el biweekly de datos con Negocio mostrando supuestos estadísticos, reglas de negocio, benchmark entre modelos y arquitectura del producto de datos. Validar supuestos con Negocio y documentar acuerdos.

18. **Rutinas de gestión y control interno 7** — Supervisar y coordinar las ceremonias de actualización al backlog, asegurando que cualquier redistribución de trabajo esté validada técnicamente y sea realista para el equipo disponible.

19. **Checklist de validaciones** — Definir los criterios de validación estadística del sprint, incluyendo horizontes de reentrenamiento, QA de modelos y arquitecturas de datos. Ser el árbitro final de la validez de un criterio de aceptación técnico.

20. **Plan de deployment y roll-out** — Diseñar el plan de despliegue y respuesta a contingencias del equipo de Ciencia. Asesorar al DS Mid y DS Jr sobre el plan de roll-back. Asegurarse de que el plan está alineado con los tiempos de Producto y Negocio.

21. **Minuta de reuniones con Negocio** — Liderar sesiones técnicas con Negocio y asegurarse de que los acuerdos de alto impacto técnico están correctamente documentados. Revisar y aprobar internamente las minutas del DS Mid antes de compartirlas con Negocio.

22. **Checklist de documentación y revisiones de código** — Definir los requisitos de documentación del proyecto según la expectativa de Negocio y las buenas prácticas de Arena. Hacer la revisión final de código y documentación antes del cierre del proyecto.

23. **Plan de KT y legacy** — Definir y supervisar el plan de KT y legacy. Asegurar que la solución es escalable, mantenible y operable por Negocio. Participar en las sesiones de KT críticas con Negocio.

24. **Resumen de herramientas y necesidades técnicas** — Anticipar y comunicar las necesidades técnicas del equipo de Ciencia a nivel de herramientas, licencias y capacidades. Supervisar el avance del plan de mentoring del DS Mid.

25. **Preparación y participación en sesiones con Negocio** — Preparar y liderar sesiones con Negocio anticipando preguntas de alto nivel técnico y estratégico sobre los modelos y la arquitectura. Proponer el enfoque correcto cuando Negocio plantea una solución técnicamente inviable o subóptima.

26. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

27. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams en tiempo y forma, dentro de las 24 horas hábiles de haberlos recibido.

---

**Conclusión** *(texto libre)*

28. **Fortalezas**
29. **Oportunidades**
30. **Comentarios** *(opcional)*

---

**Confirmación de envío**

31. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## CD Lead

> **Escala para nivel Lead:** 1 — No cumple (impacto negativo) / 2 — Cumple parcial (incompleto o tardío) / 3 — Cumple (consistente y proactivo) / 4 — Excede (impacto diferencial) / N/A

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: CD Jr / CD Mid / CD Snr / CD Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

### Aseguramiento de calidad técnica del equipo

5. Realizar seguimiento a los DS Sr/Mid de sus proyectos para evaluar el cumplimiento de sus checklists correspondientes. Documentar hallazgos y dar retro directa en sesión 1:1.

6. Asegurar que los proyectos a su cargo cumplen con las actividades de la Oficina de PMO y con los estándares técnicos de Arena. Identificar brechas y escalarlas al director de Analítica cuando no puedan resolverse a nivel de proyecto.

### Documentación de los estándares de desarrollo y buenas prácticas

7. Definir, validar y asegurar la correcta aplicación de estándares de trabajo, desarrollo y buenas prácticas en todos los entregables del equipo de Ciencia. Resolver conflictos entre los estándares de Arena y los requerimientos de Negocio con criterio técnico documentado.

### Guía y soporte al equipo de proyecto

8. Asistir y participar activamente en los dailys al inicio del proyecto, en fases de entregables críticos y en el cierre. Evaluar en cada asistencia la preparación del equipo, el foco y el cumplimiento de agenda y tiempos.

9. Asistir y participar activamente en los sprint planning y sprint review de los proyectos bajo su cargo. Hacer challenge técnico de estimaciones, definitions of completeness y alcance comprometido vs propuesta original.

10. Identificar, validar el material y participar en sesiones críticas con stakeholders senior del cliente que requieran apoyo del DS Lead. Asegurar que el equipo tiene clara la agenda, estructura y objetivo de la sesión antes de construir el material.

11. Ayudar al equipo a mapear, entender y gestionar a todos los stakeholders involucrados en el proyecto, incluyendo sus motivaciones, nivel de influencia y postura hacia el proyecto.

12. Agendar y ejecutar one-on-ones con stakeholders senior del cliente para alinear expectativas, detectar señales tempranas de insatisfacción y generar una relación de confianza y cercanía.

13. Anticipar y coordinar la participación del director de Analítica en momentos y sesiones críticas del proyecto, comunicando con claridad el contexto, la situación y el tipo de apoyo requerido.

14. Crear y ejecutar un plan de transición, onboarding, KT y seguimiento al staffing del proyecto al inicio, durante y al final, considerando riesgos de rotación y continuidad técnica.

### Guía y soporte al equipo interno

15. Asegurar que los proyectos a su cargo cumplen con las actividades correspondientes a la Mesa de Talento, incluyendo evaluaciones de desempeño y cierre de evaluaciones antes de que el equipo se mueva a otros proyectos.

16. Monitorear y dar seguimiento al avance de los planes de capacitación del equipo de Ciencia en sus proyectos. Identificar quién no ha podido avanzar por carga de trabajo y escalar al director de Analítica cuando sea necesario.

17. Monitorear la ejecución y calidad de las sesiones de mentoring de los DS Sr/Mid en sus proyectos. Identificar quién no está haciendo mentoring efectivo a su cargo y actuar sobre ello.

18. Dar seguimiento a la planeación y anticipación de los días de vacaciones y ausencias del equipo de Ciencia en sus proyectos para evitar riesgos en la ejecución de entregables críticos.

19. Ser el punto de referencia para resolver dudas de los procedimientos internos de Arena (PMO, Odoo, Mesa de Talento, vacaciones, etc.) para el equipo de Ciencia bajo su cargo.

20. Planear y ejecutar sesiones de aprendizaje técnico con el equipo de Ciencia. Diseñar sesiones que desarrollen habilidades técnicas o de consultoría del equipo, dejando al equipo con aprendizajes concretos y aplicables.

21. Identificar y gestionar la implementación de mejoras a las metodologías, estándares de trabajo y herramientas del equipo de Ciencia, en coordinación con el resto de los leads y el director de Analítica.

### Soporte comercial

22. Dar soporte comercial a través de la identificación de oportunidades de expansión, necesidades no cubiertas del cliente, evolución de soluciones actuales y sensibilización en temas de innovación en data science y analytics.

23. Dar soporte comercial a través de la construcción y validación técnica de propuestas en conjunto con otros leads y el director de Analítica.

24. Dar soporte comercial a través del seguimiento a facturación y temas administrativos del proyecto cuando sea requerido por el director.

25. Coordinar y tener sesiones presenciales en las oficinas del cliente o de Arena para desarrollar una relación más cercana y mantener una presencia activa de Arena con el cliente.

### Cumplimiento de lineamientos de trabajo remoto

26. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

27. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams en tiempo y forma, dentro de las 24 horas hábiles de haberlos recibido.

---

**Conclusión** *(texto libre)*

28. **Fortalezas**
29. **Oportunidades**
30. **Comentarios** *(opcional)*

---

**Confirmación de envío**

31. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---

## Anexo A3 — Checklist Ownership: Product Manager (PM)

# Checklist de Ownership — Product Manager (PM)

> Evalúa cada actividad con base en evidencia concreta del período: entregables, sesiones, documentación o retroalimentación del cliente y del equipo.

**Escala de calificación:**
- **1 — No cumple:** La actividad no se ejecutó o se ejecutó con deficiencias significativas que impactaron el proyecto o al equipo.
- **2 — Cumple parcial:** La actividad se ejecutó pero con omisiones, inconsistencias o calidad por debajo del estándar esperado para el nivel.
- **3 — Cumple:** La actividad se ejecutó de forma consistente y completa, cumpliendo el estándar esperado para el nivel.
- **4 — Excede:** La actividad se ejecutó por encima del estándar del nivel, con iniciativa, precisión o impacto adicional notable.
- **N/A:** La actividad no aplicó en este período por razones justificadas (tipo de proyecto, fase, etc.).

---

## PM Jr

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: PM Jr / PM Mid / PM Snr / PM Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

### Documentación del plan y del avance *(escala 1–4 / N/A)*

5. Mantener un plan de trabajo a nivel fase, actividad, entregable, responsable, día, semana. Identificando dependencias del cliente de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

6. Mantener un backlog o inventario con la lista de features o entregables ordenados por prioridad y validados con el equipo interno y el cliente en cada sesión de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

7. Documentar actividades completadas cada día y semana por cada uno de los miembros del equipo de Arena y del cliente de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

8. Generar reportes de avance semanales incluyendo fecha del reporte, número de semana, semáforo de status, done/inprogress/todo/blockers-riesgos, siguientes milestones, vista gráfica del plan de trabajo.

9. Documentar y enviar por escrito (correo + chat grupal + chat individual) el detalle de ajustes al plan, riesgos, retrasos y cambios al alcance en comparación con la propuesta inicial.

10. Validar, documentar y compartir al resto del equipo los estándares de trabajo, desarrollo y documentación requeridos por el cliente.

11. Actualizar indicadores de avance y resultado del proyecto (e.g. % de avance real vs plan, % de actividades completadas, indicadores de negocio como precisión, error, etc.) de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

12. Mantener una estructura de canal y archivos en Teams, donde todo el equipo trabaja sobre archivos guardados en esa estructura, ningún archivo del proyecto se encuentra en un drive personal y se alinea con las expectativas y necesidades de los clientes.

### Rutinas de gestión

13. Asegurar dailys recurrentes agendados.

14. Ejecutar weekly status reports con cliente técnico y de negocio.

15. Asegurar sprint plan agendados y documentados con minuta, pre-work y ajustes al plan.

16. Asegurar sprint review agendados y documentados con minuta, pre-work y ajustes al plan.

17. Asegurar sprint retrospective agendados y documentados con minuta, pre-work y ajustes al plan o esquema de trabajo.

18. Agendar refinamientos cada vez que exista un ajuste al backlog de actividades, al plan de trabajo o al alcance y entregables del proyecto o iniciativa.

### Cuestionamiento y validación de resultados

19. Contar con diseños de solución a nivel técnico. Revisados y validados por el PM para asegurar calidad y con signoff de lead técnico de Arena y lead técnico del cliente.

20. Contar con diseños de solución a nivel negocio y definiciones. Revisados y validados por el PM para asegurar calidad.

21. Generar presentaciones de revisión y validación de resultados y entregas con cliente técnico y de negocio.

### Preparación de reuniones y seguimiento con el cliente

22. Preparar reuniones internas y con el cliente que aseguren que todo el equipo de Arena está listo para llevar la sesión o participar en ella de forma exitosa y contundente.

23. Agendar sesiones one on one de retroalimentación para identificar la percepción de calidad y sugerencias de mejora del cliente.

24. Comunicar por mensaje individual o chat grupal avisando del avance, de los puntos críticos para asegurar que todos los stakeholders involucrados tienen la visibilidad del avance.

### Seguimiento a acuerdos y definiciones de las sesiones

25. Enviar pre-reads para sesiones internas y con clientes.

26. Documentar y enviar minutas con validaciones, definiciones, acuerdos y cambios de alcance o plan.

27. Documentar y enviar minutas con las mejoras y ajustes relevantes a realizar según los checkpoint y retro de cliente.

### Cumplimiento lineamientos de trabajo remoto

28. Asistir y mantenerse enfocado en las reuniones.

29. Responder correos y mensajes por Teams en tiempo y forma.

---

**Conclusión** *(texto libre)*

30. **Fortalezas**
31. **Oportunidades**
32. **Comentarios** *(opcional)*

---

**Confirmación de envío**

33. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## PM Mid

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: PM Jr / PM Mid / PM Snr / PM Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

### Documentación del plan y del avance *(escala 1–4 / N/A)*

5. Mantener un plan de trabajo a nivel fase, actividad, entregable, responsable, día, semana. Identificando dependencias del cliente de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

6. Mantener un backlog o inventario con la lista de features o entregables ordenados por prioridad y validados con el equipo interno y el cliente en cada sesión de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

7. Documentar actividades completadas cada día y semana por cada uno de los miembros del equipo de Arena y del cliente de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

8. Generar reportes de avance semanales incluyendo fecha del reporte, número de semana, semáforo de status, done/inprogress/todo/blockers-riesgos, siguientes milestones, vista gráfica del plan de trabajo.

9. Documentar y enviar por escrito (correo + chat grupal + chat individual) el detalle de ajustes al plan, riesgos, retrasos y cambios al alcance en comparación con la propuesta inicial.

10. Validar, documentar y compartir al resto del equipo los estándares de trabajo, desarrollo y documentación requeridos por el cliente.

11. Actualizar indicadores de avance y resultado del proyecto (e.g. % de avance real vs plan, % de actividades completadas, indicadores de negocio como precisión, error, etc.) de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

12. Mantener una estructura de canal y archivos en Teams, donde todo el equipo trabaja sobre archivos guardados en esa estructura, ningún archivo del proyecto se encuentra en un drive personal y se alinea con las expectativas y necesidades de los clientes.

### Rutinas de gestión

13. Asegurar dailys recurrentes agendados.

14. Ejecutar weekly status reports con cliente técnico y de negocio.

15. Asegurar sprint plan agendados y documentados con minuta, pre-work y ajustes al plan.

16. Asegurar sprint review agendados y documentados con minuta, pre-work y ajustes al plan.

17. Asegurar sprint retrospective agendados y documentados con minuta, pre-work y ajustes al plan o esquema de trabajo.

18. Agendar refinamientos cada vez que exista un ajuste al backlog de actividades, al plan de trabajo o al alcance y entregables del proyecto o iniciativa.

### Cuestionamiento y validación de resultados

19. Contar con diseños de solución a nivel técnico. Revisados y validados por el PM para asegurar calidad y con signoff de lead técnico de Arena y lead técnico del cliente.

20. Contar con diseños de solución a nivel negocio y definiciones. Revisados y validados por el PM para asegurar calidad.

21. Generar presentaciones de revisión y validación de resultados y entregas con cliente técnico y de negocio.

### Preparación de reuniones y seguimiento con el cliente

22. Preparar reuniones internas y con el cliente que aseguren que todo el equipo de Arena está listo para llevar la sesión o participar en ella de forma exitosa y contundente.

23. Agendar sesiones one on one de retroalimentación para identificar la percepción de calidad y sugerencias de mejora del cliente.

24. Comunicar por mensaje individual o chat grupal avisando del avance, de los puntos críticos para asegurar que todos los stakeholders involucrados tienen la visibilidad del avance.

### Seguimiento a acuerdos y definiciones de las sesiones

25. Enviar pre-reads para sesiones internas y con clientes.

26. Documentar y enviar minutas con validaciones, definiciones, acuerdos y cambios de alcance o plan.

27. Documentar y enviar minutas con las mejoras y ajustes relevantes a realizar según los checkpoint y retro de cliente.

### Análisis de impactos ante cambios

28. Analizar el impacto en fechas, dependencias y carga del equipo antes de ejecutar cambios en alcance o plan de trabajo.

### Clarificación de criterios de aceptación ambiguos

29. Detectar y resolver criterios incompletos o ambiguos comunicados por cliente o definidos en el alcance antes de la ejecución de los entregables relacionados.

### Detección temprana de desviaciones de calidad

30. Identificar desviaciones de calidad de forma recurrente durante la ejecución.

### Gestión consciente de dependencias

31. Identificar y destrabar dependencias que impactan la ejecución a través de un seguimiento y comunicación clara y puntual.

### Preparación para validaciones

32. Asegurar que entregables estén listos antes de sesiones con cliente.

### Traducción técnica de los elementos del proyecto al stakeholder

33. Aprovechar sesiones del proyecto para explicar aspectos técnicos de una forma clara a los stakeholders que no son técnicos, con el lenguaje y detalle que se adapta al stakeholder.

### Dominio de estrategias de comunicación con stakeholders

34. Identificar el orden, tipo de mensaje y momentos para comunicar con cada stakeholder las validaciones y puntos clave del proyecto.

### Cumplimiento lineamientos de trabajo remoto

35. Asistir y mantenerse enfocado en las reuniones.

36. Responder correos y mensajes por Teams en tiempo y forma.

---

**Conclusión** *(texto libre)*

37. **Fortalezas**
38. **Oportunidades**
39. **Comentarios** *(opcional)*

---

**Confirmación de envío**

40. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## PM Snr

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: PM Jr / PM Mid / PM Snr / PM Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

### Documentación del plan y del avance *(escala 1–4 / N/A)*

5. Mantener un plan de trabajo a nivel fase, actividad, entregable, responsable, día, semana. Identificando dependencias del cliente de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

6. Mantener un backlog o inventario con la lista de features o entregables ordenados por prioridad y validados con el equipo interno y el cliente en cada sesión de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

7. Documentar actividades completadas cada día y semana por cada uno de los miembros del equipo de Arena y del cliente de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

8. Generar reportes de avance semanales incluyendo fecha del reporte, número de semana, semáforo de status, done/inprogress/todo/blockers-riesgos, siguientes milestones, vista gráfica del plan de trabajo.

9. Documentar y enviar por escrito (correo + chat grupal + chat individual) el detalle de ajustes al plan, riesgos, retrasos y cambios al alcance en comparación con la propuesta inicial.

10. Validar, documentar y compartir al resto del equipo los estándares de trabajo, desarrollo y documentación requeridos por el cliente.

11. Actualizar indicadores de avance y resultado del proyecto (e.g. % de avance real vs plan, % de actividades completadas, indicadores de negocio como precisión, error, etc.) de acuerdo con los estándares de la Oficina de PMO de Arena y del cliente.

12. Mantener una estructura de canal y archivos en Teams, donde todo el equipo trabaja sobre archivos guardados en esa estructura, ningún archivo del proyecto se encuentra en un drive personal y se alinea con las expectativas y necesidades de los clientes.

### Rutinas de gestión

13. Asegurar dailys recurrentes agendados.

14. Ejecutar weekly status reports con cliente técnico y de negocio.

15. Asegurar sprint plan agendados y documentados con minuta, pre-work y ajustes al plan.

16. Asegurar sprint review agendados y documentados con minuta, pre-work y ajustes al plan.

17. Asegurar sprint retrospective agendados y documentados con minuta, pre-work y ajustes al plan o esquema de trabajo.

18. Agendar refinamientos cada vez que exista un ajuste al backlog de actividades, al plan de trabajo o al alcance y entregables del proyecto o iniciativa.

### Cuestionamiento y validación de resultados

19. Contar con diseños de solución a nivel técnico. Revisados y validados por el PM para asegurar calidad y con signoff de lead técnico de Arena y lead técnico del cliente.

20. Contar con diseños de solución a nivel negocio y definiciones. Revisados y validados por el PM para asegurar calidad.

21. Generar presentaciones de revisión y validación de resultados y entregas con cliente técnico y de negocio.

### Preparación de reuniones y seguimiento con el cliente

22. Preparar reuniones internas y con el cliente que aseguren que todo el equipo de Arena está listo para llevar la sesión o participar en ella de forma exitosa y contundente.

23. Agendar sesiones one on one de retroalimentación para identificar la percepción de calidad y sugerencias de mejora del cliente.

24. Comunicar por mensaje individual o chat grupal avisando del avance, de los puntos críticos para asegurar que todos los stakeholders involucrados tienen la visibilidad del avance.

### Seguimiento a acuerdos y definiciones de las sesiones

25. Enviar pre-reads para sesiones internas y con clientes.

26. Documentar y enviar minutas con validaciones, definiciones, acuerdos y cambios de alcance o plan.

27. Documentar y enviar minutas con las mejoras y ajustes relevantes a realizar según los checkpoint y retro de cliente.

### Competencias avanzadas de gestión *(escala 1–4 / N/A)*

28. **Análisis de impactos ante cambios** — Analizar el impacto en fechas, dependencias y carga del equipo antes de ejecutar cambios en alcance o plan de trabajo.

29. **Clarificación de criterios de aceptación ambiguos** — Detectar y resolver criterios incompletos o ambiguos comunicados por cliente o definidos en el alcance antes de la ejecución de los entregables relacionados.

30. **Detección temprana de desviaciones de calidad** — Identificar desviaciones de calidad de forma recurrente durante la ejecución.

31. **Gestión consciente de dependencias** — Identificar y destrabar dependencias que impactan la ejecución a través de un seguimiento y comunicación clara y puntual.

32. **Preparación para validaciones** — Asegurar que entregables estén listos antes de sesiones con cliente.

33. **Traducción técnica de los elementos del proyecto al stakeholder** — Aprovechar sesiones del proyecto para explicar aspectos técnicos de una forma clara a los stakeholders que no son técnicos, con el lenguaje y detalle que se adapta al stakeholder.

34. **Dominio de estrategias de comunicación con stakeholders** — Identificar el orden, tipo de mensaje y momentos para comunicar con cada stakeholder las validaciones y puntos clave del proyecto.

35. **Evaluación de impacto sistémico** — Evaluar impacto y sinergias en otras iniciativas, equipos o capacidades y comunicar a otros equipos para lograr una mejor ejecución y entrega.

36. **Definición y defensa de límites de alcance** — Establecer y sostener claramente el alcance del proyecto en los momentos donde haya negociaciones respecto a los entregables, equipo y tiempos del proyecto.

37. **Reencuadre de problemas del cliente** — Cuestionar el problema que el equipo interno o el cliente busca solucionar cuando las actividades no atacan la causa raíz.

38. **Intervención temprana en riesgos** — Anticipar, comunicar y actuar ante señales tempranas de riesgo involucrando a equipo interno de Arena y al cliente.

39. **Transferencia de criterio al equipo** — Elevar el nivel de decisión del equipo mediante coaching.

40. **Posicionamiento como asesor de confianza con stakeholder** — Desarrollar una relación de confianza, cercanía y apoyo con los stakeholders clave a través de los one on ones del proyecto.

41. **Autonomía en la gestión y ejecución del proyecto** — Ejecutar y entregar el proyecto durante períodos largos sin requerir apoyo o presencia constante del equipo directivo, manteniendo tiempo, calidad y confianza.

### Cumplimiento lineamientos de trabajo remoto

42. Asistir y mantenerse enfocado en las reuniones.

43. Responder correos y mensajes por Teams en tiempo y forma.

---

**Conclusión** *(texto libre)*

44. **Fortalezas**
45. **Oportunidades**
46. **Comentarios** *(opcional)*

---

**Confirmación de envío**

47. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## PM Lead

> **Escala para nivel Lead:** 1 — No cumple (impacto negativo) / 2 — Cumple parcial (incompleto o tardío) / 3 — Cumple (consistente y proactivo) / 4 — Excede (impacto diferencial) / N/A

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: PM Jr / PM Mid / PM Snr / PM Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

### Aseguramiento de gestión de proyectos

5. Realizar seguimiento a los PMs con los que trabaja en el proyecto para evaluar el cumplimiento del checklist correspondiente y definir ajustes.

6. Asegurar que los proyectos a su cargo cumplen con las actividades correspondientes a la Oficina de PMO.

7. Identificar y hacer equipo con leads técnicos para asegurar que el proyecto cuenta con las bases y diseños técnicos requeridos.

### Guía y soporte al equipo de proyecto

8. Asistir y participar activamente a los dailys al inicio del proyecto, en fases de entregables críticos y en el cierre.

9. Asistir y participar activamente a los planning y review del proyecto.

10. Asegurar y revisar la alineación recurrente del trabajo del equipo vs el alcance de la propuesta.

11. Identificar, validar el material y preparación y participar en sesiones críticas donde asistirán stakeholders senior del cliente que requieran apoyo del lead.

12. Ayudar al equipo a mapear y entender a todos los stakeholders involucrados.

13. Agendar one on ones con stakeholders senior del proyecto para alinear expectativas y generar una relación de confianza y cercanía.

14. Anticipar participación de directores en momentos y sesiones críticas, dando claridad de la comunicación o influencia requerida de su parte.

15. Crear y ejecutar un plan de transición, onboarding, KTs y seguimiento al staffing del proyecto al inicio, durante y al final.

### Guía y soporte al equipo interno

16. Asegurar que los proyectos a su cargo cumplen con las actividades correspondientes a la Mesa de Talento.

17. Monitorear el avance de los planes de capacitación del equipo de Producto en sus proyectos.

18. Monitorear la ejecución y calidad de las sesiones de mentoring de los equipos de producto en sus proyectos.

19. Dar seguimiento a la planeación y anticipación de los días de vacaciones y ausencias del equipo en sus proyectos para evitar riesgos en la ejecución.

20. Dar seguimiento a resolver directamente dudas de los procedimientos internos de Arena (e.g. PMO, Odoo, Mesa de Talento, Vacaciones, etc.).

21. Planear y ejecutar sesiones de aprendizaje con el equipo de PMs.

22. Asegurar el mantenimiento del directorio de KO, accesos internos Arena y otros clientes (bajas, altas, cambios de reporte).

23. Identificar y gestionar la implementación de mejoras a las metodologías, estándares de trabajo y herramientas en coordinación con el resto de los leads y del equipo de Arena.

### Soporte comercial

24. Dar soporte comercial a través de la identificación de oportunidades, necesidades, evolución de soluciones actuales y sensibilización en temas de innovación para el cliente.

25. Dar soporte comercial a través de la construcción y validación de propuestas en conjunto con otros leads y el director.

26. Dar soporte comercial a través del seguimiento a facturación y temas administrativos en caso de ser requerido.

27. Coordinar y tener sesiones presenciales en las oficinas del cliente o de Arena para desarrollar una relación más cercana y mantener una presencia activa.

### Cumplimiento lineamientos de trabajo remoto

28. Asistir y mantenerse enfocado en las reuniones.

29. Responder correos y mensajes por Teams en tiempo y forma.

---

**Conclusión** *(texto libre)*

30. **Fortalezas**
31. **Oportunidades**
32. **Comentarios** *(opcional)*

---

**Confirmación de envío**

33. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---

## Anexo A4 — Checklist Ownership: UX/UI

# Checklist de Ownership — UX/UI

> Evalúa cada actividad con base en evidencia concreta del período: entregables, sesiones, documentación o retroalimentación del cliente y del equipo.

**Escala de calificación:**
- **1 — No cumple:** La actividad no se ejecutó o se ejecutó con deficiencias significativas que impactaron el proyecto o al equipo.
- **2 — Cumple parcial:** La actividad se ejecutó pero con omisiones, inconsistencias o calidad por debajo del estándar esperado para el nivel.
- **3 — Cumple:** La actividad se ejecutó de forma consistente y completa, cumpliendo el estándar esperado para el nivel.
- **4 — Excede:** La actividad se ejecutó por encima del estándar del nivel, con iniciativa, precisión o impacto adicional notable.
- **N/A:** La actividad no aplicó en este período por razones justificadas (tipo de proyecto, fase, etc.).

---

## UX/UI Jr

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: UX UI Jr / UX UI Mid / UX UI Snr / UX UI Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Diseño UI alineado a Design System** — Construir pantallas respetando los componentes, tokens y patrones del Design System del proyecto. Si no existe Design System definido, usar el de Figma de Arena como referencia base y documentar cualquier excepción.

6. **Diseño de flujos asignados** — Diseñar los flujos específicos asignados, entregando un user flow completo que incluya todos los estados de la pantalla (normal, vacío, error, loading) y los edge cases identificados. No entregar pantallas sueltas sin flujo.

7. **Documentación de estados y edge cases** — Documentar explícitamente todos los estados de cada pantalla diseñada: estado vacío, estado de error, estado de carga, estado de éxito y edge cases identificados. No asumir que el equipo de desarrollo puede inferir los estados no diseñados.

8. **Preparación de handoff a desarrollo** — Preparar los archivos de Figma para entrega a desarrollo: nombrar capas correctamente, agrupar componentes, especificar espaciados, tipografías, colores con tokens y anotar reglas de interacción que no son evidentes visualmente.

9. **Documentación del trabajo de diseño** — Documentar en la herramienta de seguimiento del proyecto (Figma, Planner u otra definida) las tareas ejecutadas, el estado de cada pantalla o flujo y el avance del sprint. Actualizar el registro antes del daily, no en el review.

10. **Pruebas de usabilidad básicas** — Ejecutar pruebas de usabilidad básicas bajo el protocolo definido por el Mid o Sr del proyecto, o por el propio Jr si trabaja solo: mostrar el prototipo a al menos 3 usuarios o stakeholders relevantes, documentar observaciones y comunicar hallazgos al equipo antes del handoff a desarrollo.

11. **Documentación del plan y avance** — Mantener actualizada la estructura de archivos del proyecto en Teams/SharePoint: todos los archivos de trabajo en el canal del proyecto, ningún archivo en un drive personal. Actualizar los indicadores de avance definidos para el proyecto (% avance, actividades completadas) de forma semanal.

12. **Rutinas de gestión — Daily** — Asistir al daily preparado: saber qué avanzó desde el día anterior, qué hará hoy y qué le impide avanzar. Comunicar bloqueos antes de que impacten un entregable del sprint.

13. **Rutinas de gestión — Sprint Planning** — Asistir al sprint planning sabiendo qué puede comprometer para el sprint: revisar el backlog antes de la sesión, tener propuesta de actividades propias y sus estimaciones, y salir de la sesión con claridad total de sus entregables, criterios de aceptación y dependencias.

14. **Rutinas de gestión — Sprint Review** — Asistir al sprint review preparado para exponer los entregables del sprint: qué completó, qué no completó y por qué. Recibir retroalimentación técnica y de diseño con apertura y documentar los acuerdos de mejora.

15. **Rutinas de gestión — Sprint Retrospectiva** — Participar activamente en la retrospectiva: expresar lo que funcionó bien, lo que no funcionó y proponer al menos un ajuste concreto al proceso de trabajo del equipo.

16. **Rutinas de gestión — Refinamiento de backlog** — Asistir al refinamiento preparado para aclarar dudas sobre las actividades del backlog antes de que entren al planning. Identificar y comunicar ambigüedades en criterios de aceptación antes de comprometerse a ejecutarlos.

17. **Cuestionamiento y validación de resultados** — Preparar y presentar los diseños para revisión y validación con el cliente o stakeholders. Documentar el feedback recibido, los retrabajos solicitados y la percepción del cliente tras cada sesión de revisión.

18. **Preparación de reuniones** — Preparar cada reunión con cliente usando el Formato de Preparación de Reuniones del proyecto: definir objetivo, agenda, material de soporte, posibles preguntas del cliente y acciones críticas a lograr. Completarlo al menos 24 horas antes de la sesión.

19. **Seguimiento a acuerdos — Pre-reads y minutas** — Enviar pre-reads con el material de la sesión al menos 24 horas antes de cada reunión con cliente. Documentar y enviar minutas con validaciones, acuerdos y siguientes pasos dentro de las 24 horas posteriores a cada sesión.

20. **Comunicación de avance con stakeholders** — Comunicar el avance del proyecto a los stakeholders relevantes mediante mensajes directos o en chat grupal 2-3 veces por semana, sin esperar a las sesiones formales para dar visibilidad del progreso.

21. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

22. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

23. **Fortalezas**
24. **Oportunidades**
25. **Comentarios** *(opcional)*

---

**Confirmación de envío**

26. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## UX/UI Mid

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: UX UI Jr / UX UI Mid / UX UI Snr / UX UI Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Definición del problema de experiencia** — Documentar el problema real que se está resolviendo desde la perspectiva del usuario y del negocio antes de abrir Figma. Formular el problema como hipótesis falsable con una métrica asociada. No aceptar como punto de partida 'necesitamos rediseñar X' sin cuestionarlo.

6. **Investigación y validación de supuestos** — Identificar los supuestos críticos que sostienen la hipótesis de diseño antes de desarrollar pantallas en alta fidelidad. Validarlos con evidencia mínima viable (entrevistas, datos existentes, tests rápidos). Documentar qué se sabe, qué se supone y qué se desconoce.

7. **Diseño de flujo y arquitectura de decisión** — Diseñar el journey completo del usuario incluyendo todos los estados, edge cases y microdecisiones críticas. No diseñar pantallas en aislamiento: cada pantalla existe dentro de un flujo que el Mid define de forma explícita.

8. **Diseño UI con rigor sistémico** — Construir la interfaz visual alineada al Design System, principios cognitivos básicos y accesibilidad mínima (WCAG AA). Justificar funcionalmente las decisiones estéticas. Si no hay Design System definido, proponer los patrones base que el equipo seguirá.

9. **Validación de prototipo antes de desarrollo** — Validar el prototipo con al menos 3 usuarios o stakeholders relevantes antes del handoff a desarrollo. Documentar hallazgos, incorporar ajustes y comunicar al equipo qué se validó y qué decisiones se tomaron a partir de la validación.

10. **Handoff estratégico a desarrollo** — Preparar la transferencia del diseño a desarrollo con especificaciones completas: estados, microcopy, reglas de interacción, criterios de aceptación medibles en el backlog. El Mid es responsable de que desarrollo pueda implementar sin ambigüedades.

11. **Medición post-release** — Analizar el impacto de los diseños entregados en las métricas definidas al inicio de la iniciativa. Documentar el aprendizaje y tomar una decisión explícita: iterar, escalar o descartar.

12. **Documentación del proyecto** — Mantener la estructura de archivos del proyecto en Teams/SharePoint actualizada y accesible: todos los archivos de trabajo en el canal del proyecto, indicadores de avance actualizados semanalmente, ningún archivo en drives personales.

13. **Rutinas de gestión — Daily** — Facilitar o participar activamente en el daily asegurando que la sesión dura entre 15 y 20 minutos, que cada participante reporta avance real con bloqueos identificados y que los bloqueos críticos se gestionan antes de que impacten el sprint. Si el Mid opera solo, reporta su avance al PM o stakeholder correspondiente.

14. **Rutinas de gestión — Sprint Planning** — Liderar o participar activamente en el sprint planning: proponer actividades y estimaciones propias, asegurar que todas las tareas tienen criterio de aceptación claro antes de comprometerse, y validar que el plan es ejecutable dentro del sprint.

15. **Rutinas de gestión — Sprint Review** — Exponer los resultados del sprint al equipo y al cliente con honestidad: qué se completó, qué no se completó y por qué. Dar retroalimentación técnica de diseño al equipo si hay niveles Junior. Documentar los acuerdos de mejora.

16. **Rutinas de gestión — Sprint Retrospectiva** — Facilitar o participar activamente en la retrospectiva con aportaciones concretas sobre el proceso de trabajo. Asegurar que los acuerdos de mejora se implementan en el siguiente sprint.

17. **Rutinas de gestión — Refinamiento de backlog** — Facilitar o participar en el refinamiento para aclarar criterios de aceptación ambiguos, identificar dependencias y priorizar el backlog antes del planning. No comprometerse a actividades sin criterio de aceptación claro.

18. **Cuestionamiento y validación de resultados** — Generar y presentar los diseños de solución (a nivel técnico y de negocio) con el nivel de detalle suficiente para obtener un sign-off explícito del cliente. Documentar los retrabajos solicitados y la percepción del cliente en cada sesión.

19. **Preparación de reuniones** — Preparar cada reunión con cliente usando el Formato de Preparación de Reuniones: objetivo, agenda, material de soporte, preguntas anticipadas y acciones críticas a lograr. Completarlo al menos 24 horas antes.

20. **Sesiones 1:1 de retroalimentación con cliente** — Agendar y ejecutar sesiones one-on-one con el cliente para identificar su percepción de calidad, expectativas no explícitas y sugerencias de mejora. Documentar el feedback y comunicarlo al equipo.

21. **Seguimiento a acuerdos — Pre-reads y minutas** — Enviar pre-reads con el material de la sesión al menos 24 horas antes de cada reunión con cliente. Documentar y enviar minutas con validaciones, acuerdos y siguientes pasos dentro de las 24 horas posteriores a cada sesión.

22. **Comunicación de avance con stakeholders** — Mantener informados a todos los stakeholders relevantes sobre el avance del proyecto mediante mensajes directos o en chat grupal 2-3 veces por semana, sin esperar las sesiones formales.

23. **Análisis de impactos ante cambios** — Evaluar el impacto en fechas, dependencias y carga del equipo antes de aceptar o ejecutar cambios en el alcance o plan de trabajo. Documentar el análisis y comunicarlo al cliente y al equipo directivo de Arena antes de comprometerse.

24. **Gestión de dependencias** — Identificar y gestionar activamente las dependencias que impactan la ejecución del sprint: con desarrollo, con el cliente, con otros equipos de Arena. Comunicar bloqueos por dependencias antes de que afecten un entregable.

25. **Traducción técnica a stakeholders** — Explicar aspectos técnicos de UX de forma comprensible para stakeholders no técnicos, adaptando el lenguaje y nivel de detalle al perfil del interlocutor en cada sesión.

26. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

27. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

28. **Fortalezas**
29. **Oportunidades**
30. **Comentarios** *(opcional)*

---

**Confirmación de envío**

31. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## UX/UI Snr

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: UX UI Jr / UX UI Mid / UX UI Snr / UX UI Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Definición estratégica del problema de experiencia** — Definir el problema estratégico de experiencia antes de cualquier actividad de diseño: conectar el objetivo de negocio con el comportamiento actual del usuario, la brecha deseada y el impacto económico estimado. Priorizar el problema frente a otras iniciativas con criterio explícito.

6. **Identificación y validación de supuestos críticos** — Identificar, clasificar por riesgo y validar con evidencia los supuestos que sostienen la hipótesis de diseño. Definir el método de validación adecuado al contexto del proyecto (entrevistas, datos cuantitativos, tests rápidos, shadowing). Documentar qué se sabe y qué se asume con distinción explícita.

7. **Arquitectura de decisión y flujo completo** — Diseñar el sistema de decisiones del usuario: user flow end-to-end, mapa de estados, microdecisiones críticas, puntos de abandono potencial y reglas de negocio con implicación de experiencia. El Sr define el flujo completo aunque opere solo.

8. **Diseño de interfaz con rigor sistémico** — Construir o supervisar la construcción visual de la interfaz con alineación al Design System, criterios cognitivos, accesibilidad WCAG AA y consistencia cross-product. Definir los patrones de diseño que el equipo seguirá. Justificar funcionalmente todas las decisiones estéticas.

9. **Validación de prototipo antes de desarrollo** — Diseñar el protocolo de validación, ejecutar o supervisar las pruebas con usuarios y sintetizar los aprendizajes en insights accionables. El Sr valida comprensión, confianza, claridad, fluidez de tarea y fricción emocional, no solo si 'se ve bien'.

10. **Handoff estratégico y criterios de aceptación** — Convertir el diseño en especificación ejecutable: definir estados, microcopy, reglas de interacción, animaciones y criterios de aceptación medibles en el backlog. El Sr es responsable de que desarrollo no tenga que suponer nada.

11. **Medición post-release y aprendizaje** — Analizar el impacto de los diseños en los KPIs definidos al inicio. Sintetizar cambios en comportamiento, feedback cualitativo e impacto sistémico en otros flows. Tomar una decisión documentada: iterar, escalar o descartar.

12. **Documentación del proyecto** — Garantizar que la estructura de archivos del proyecto en Teams/SharePoint está actualizada, accesible y organizada en todo momento. Si hay Jr o Mid en el equipo, establecer el estándar de organización y revisarlo periódicamente.

13. **Rutinas de gestión — Daily** — Asistir o facilitar el daily con criterio de calidad de ejecución: verificar que el equipo reporta avance real, que los bloqueos se gestionan antes de impactar el sprint y que la sesión dura entre 15 y 20 minutos. Si opera solo, reporta avance al PM o stakeholder.

14. **Rutinas de gestión — Sprint Planning** — Liderar el sprint planning con criterio técnico de UX: desafiar estimaciones irreales, asegurar que todas las tareas tienen definición de terminado clara y que el plan es ejecutable dados los supuestos del proyecto.

15. **Rutinas de gestión — Sprint Review** — Exponer los resultados técnicos del sprint con criterio estratégico: qué se completó, qué impacto tiene en el KPI definido y qué se aprendió. Dar retroalimentación técnica profunda al Mid y Jr si los hay.

16. **Rutinas de gestión — Sprint Retrospectiva** — Facilitar o participar en la retrospectiva identificando los patrones de proceso que generan retrabajo recurrente y proponiendo cambios sistémicos, no solo ajustes puntuales.

17. **Rutinas de gestión — Refinamiento de backlog** — Liderar el refinamiento con criterio técnico de UX: identificar actividades mal definidas, proponer criterios de aceptación técnicamente correctos y priorizar con criterio de impacto en el problema original.

18. **Cuestionamiento y validación de resultados** — Presentar los diseños de solución con el nivel de detalle estratégico suficiente para generar decisiones informadas del cliente, no solo aprobación visual. Obtener sign-off explícito y documentado antes de pasar a desarrollo.

19. **Preparación de reuniones** — Preparar y liderar la preparación de reuniones críticas usando el Formato de Preparación de Reuniones: definir el objetivo estratégico, la estructura de la sesión, las preguntas clave para el cliente y los posibles escenarios de respuesta.

20. **Sesiones 1:1 de retroalimentación con cliente** — Agendar y ejecutar sesiones one-on-one con stakeholders clave del cliente para detectar señales tempranas de insatisfacción, alinear expectativas estratégicas y construir una relación de confianza que va más allá del proyecto.

21. **Seguimiento a acuerdos — Pre-reads y minutas** — Asegurar que todas las sesiones con cliente tienen pre-read 24 horas antes y minuta dentro de las 24 horas posteriores. Si hay Jr o Mid en el equipo, el Sr establece el estándar de calidad y revisa antes de enviar.

22. **Comunicación de avance con stakeholders** — Mantener informados a todos los stakeholders relevantes 2-3 veces por semana mediante mensajes directos o en chat grupal. Comunicar proactivamente desviaciones o riesgos antes de que el cliente los descubra.

23. **Análisis de impactos ante cambios** — Evaluar el impacto estratégico de los cambios de alcance en fechas, dependencias, calidad del diseño y relación con el cliente. Comunicar el análisis al cliente y al equipo directivo de Arena antes de comprometerse a cualquier cambio.

24. **Definición y defensa de límites de alcance** — Establecer y defender el alcance del proyecto en negociaciones sobre entregables, equipo y tiempos. Documentar los acuerdos de alcance y comunicar al equipo directivo los intentos de scope creep.

25. **Reencuadre de problemas del cliente** — Cuestionar el problema que el cliente o el equipo busca resolver cuando las actividades propuestas no atacan la causa raíz. Proponer un reencuadre con argumentos de impacto y alinear al cliente en el nuevo enfoque antes de ejecutar.

26. **Intervención temprana en riesgos** — Anticipar, comunicar y actuar ante señales tempranas de riesgo de proyecto (técnicos, de relación con el cliente, de alcance, de calidad) involucrando al equipo de Arena y al cliente según la naturaleza del riesgo.

27. **Transferencia de criterio al equipo** — Desarrollar el criterio técnico de diseño del Mid y Jr mediante coaching en contexto: retroalimentación técnica en sesiones de diseño, preguntas que desarrollan el razonamiento y espacios para que el equipo proponga soluciones antes de que el Sr las proponga.

28. **Posicionamiento como asesor de confianza con el cliente** — Desarrollar una relación de confianza y cercanía con los stakeholders clave del cliente que vaya más allá del entregable del sprint. Identificar necesidades del cliente más allá del proyecto actual y comunicar oportunidades al equipo directivo de Arena.

29. **Autonomía en la gestión del proyecto** — Gestionar y entregar el proyecto durante períodos largos sin necesitar apoyo o presencia constante del equipo directivo, manteniendo tiempo, calidad y confianza del cliente.

30. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

31. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

32. **Fortalezas**
33. **Oportunidades**
34. **Comentarios** *(opcional)*

---

**Confirmación de envío**

35. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## UX/UI Lead

> **Escala para nivel Lead:** 1 — No cumple (impacto negativo) / 2 — Cumple parcial (incompleto o tardío) / 3 — Cumple (consistente y proactivo) / 4 — Excede (impacto diferencial) / N/A

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: UX UI Jr / UX UI Mid / UX UI Snr / UX UI Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

### Aseguramiento de gestión de proyectos

5. Realizar seguimiento a los PMs con los que trabaja en el proyecto para evaluar el cumplimiento del checklist correspondiente y definir ajustes.

6. Asegurar que los proyectos a su cargo cumplen con las actividades correspondientes a la Oficina de PMO.

7. Identificar y hacer equipo con leads técnicos para asegurar que el proyecto cuenta con las bases y diseños técnicos requeridos.

### Guía y soporte al equipo de proyecto

8. Asistir y participar activamente a los dailys al inicio del proyecto, en fases de entregables críticos y en el cierre.

9. Asistir y participar activamente a los planning y review del proyecto.

10. Asegurar y revisar la alineación recurrente del trabajo del equipo vs el alcance de la propuesta.

11. Identificar, validar el material y preparación y participar en sesiones críticas donde asistirán stakeholders senior del cliente que requieran apoyo del lead.

12. Ayudar al equipo a mapear y entender a todos los stakeholders involucrados.

13. Agendar one on ones con stakeholders senior del proyecto para alinear expectativas y generar una relación de confianza y cercanía.

14. Anticipar participación de directores en momentos y sesiones críticas, dando claridad de la comunicación o influencia requerida de su parte.

15. Crear y ejecutar un plan de transición, onboarding, KTs y seguimiento al staffing del proyecto al inicio, durante y al final.

### Guía y soporte al equipo interno

16. Asegurar que los proyectos a su cargo cumplen con las actividades correspondientes a la Mesa de Talento.

17. Monitorear el avance de los planes de capacitación del equipo de Producto en sus proyectos.

18. Monitorear la ejecución y calidad de las sesiones de mentoring de los equipos de producto en sus proyectos.

19. Dar seguimiento a la planeación y anticipación de los días de vacaciones y ausencias del equipo en sus proyectos para evitar riesgos en la ejecución.

20. Dar seguimiento a resolver directamente dudas de los procedimientos internos de Arena (e.g. PMO, Odoo, Mesa de Talento, Vacaciones, etc.).

21. Planear y ejecutar sesiones de aprendizaje con el equipo de PMs.

22. Asegurar el mantenimiento del directorio de KO, accesos internos Arena y otros clientes (bajas, altas, cambios de reporte).

23. Identificar y gestionar la implementación de mejoras a las metodologías, estándares de trabajo y herramientas en coordinación con el resto de los leads y del equipo de Arena.

### Soporte comercial

24. Dar soporte comercial a través de la identificación de oportunidades, necesidades, evolución de soluciones actuales y sensibilización en temas de innovación para el cliente.

25. Dar soporte comercial a través de la construcción y validación de propuestas en conjunto con otros leads y el director.

26. Dar soporte comercial a través del seguimiento a facturación y temas administrativos en caso de ser requerido.

27. Coordinar y tener sesiones presenciales en las oficinas del cliente o de Arena para desarrollar una relación más cercana y mantener una presencia activa.

### Cumplimiento de lineamientos de trabajo remoto

28. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

29. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

30. **Fortalezas**
31. **Oportunidades**
32. **Comentarios** *(opcional)*

---

**Confirmación de envío**

33. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---

## Anexo B — Cuestionario Entrega de Valor (texto original; aplicar escala 1–4 según sección 5.3)

# Evaluación de Proyecto — Entrega de Valor

> Este formulario evalúa la participación del equipo en un proyecto específico. Deberás evaluar su contribución con base en evidencia observable.
>
> **Importante:** Todos los colaboradores involucrados en el mismo proyecto serán evaluados bajo los mismos criterios y sobre el mismo contexto de entrega.

---

## Identificación

1. **Correo de todos los evaluados** *(separados por comas y sin espacios)*
2. **Nombre del Proyecto**
3. **Nombre del evaluador(es)** *(texto libre)*

---

## Criterios de evaluación del proyecto

### 4. Satisfacción del cliente

Evalúa qué tan satisfecho quedó el cliente con el trabajo entregado en este proyecto.

| Calificación | Descripción |
|---|---|
| **4 — Muy Alto** | Cliente satisfecho todo el proyecto; es sponsor de Arena |
| **3 — Alto** | Dio retroalimentación directa; se hicieron ajustes que corrigieron su percepción |
| **2 — Medio** | Dio retroalimentación en repetidas ocasiones; se logró ajustar |
| **1 — Bajo** | Dio retroalimentación repetida y se tuvieron que escalar oportunidades de mejora |
| **0 — Muy Bajo** | Cliente no quedó satisfecho o se paró el proyecto |

---

### 5. Cumplimiento de entregables

Evalúa si se entregó lo comprometido con la calidad esperada para el proyecto.

| Calificación | Descripción |
|---|---|
| **4 — Muy Alto** | Entregables cumplidos en tiempo, forma y calidad sin retrabajos |
| **3 — Alto** | Cumplidos en tiempo, forma y calidad con retrabajos menores por ajustes del cliente |
| **2 — Medio** | Cumplidos en tiempo, forma y calidad con retrabajos mayores por ajustes del cliente |
| **1 — Bajo** | Cumplidos pero sin calidad comprometida; cliente expresó inconformidad múltiples veces |
| **0 — Muy Bajo** | No se cumplió en tiempo, forma ni calidad comprometida |

---

### 6. Cumplimiento en tiempo — Proyectos con tiempo finito

*Aplica únicamente si el proyecto tiene una fecha de entrega definida. Si el proyecto es de servicio indefinido, selecciona N/A.*

| Calificación | Descripción |
|---|---|
| **4 — Muy Alto** | Retraso menor al 10% vs semanas planeadas |
| **3 — Alto** | Retraso entre 10% y 15% vs semanas planeadas |
| **2 — Medio** | Retraso entre 15% y 20% vs semanas planeadas |
| **1 — Bajo** | Retraso entre 20% y 25% vs semanas planeadas |
| **0 — Muy Bajo** | Retraso mayor al 25% vs semanas planeadas |
| **N/A** | El proyecto es de servicio indefinido |

---

### 7. Cumplimiento en tiempo — Servicios o iniciativas con tiempo indefinido

*Aplica únicamente si el proyecto es un servicio continuo sin fecha de cierre definida. Si el proyecto tiene fecha de entrega, selecciona N/A.*

| Calificación | Descripción |
|---|---|
| **4 — Muy Alto** | Entregas y actividades cumplidas consistentemente vs fechas planeadas |
| **3 — Alto** | La mayoría del tiempo se cumplen entregas y actividades vs fechas planeadas |
| **2 — Medio** | Inconsistencias en el cumplimiento de entregas vs fechas planeadas |
| **1 — Bajo** | Más del 50% de entregas no cumplidas vs fechas planeadas |
| **0 — Muy Bajo** | Consistentemente no se logran cumplir entregas vs fechas planeadas |
| **N/A** | El proyecto tiene fecha de entrega definida |

---

## Anexo C — Lista de colaboradores Analítica 2026 (seed de usuarios)

## HC Total Nov 2024-2026
| NOMBRE COMPLETO | Correo |
| --- | --- |
| RAMIRO ABAD ARELLANO CARMONA | abad.arellano@arena-analytics.com |
| ABRAHAM MARTÍNEZ RAMIREZ | abraham.martinez@arena-analytics.com |
| ADRIÁN LANDAVERDE NAVA | adrian@arena-analytics.com |
| ADRIÁN PÉREZ ÁNGELES | adrian.perez@arena-analytics.com |
| ALDO ALEJANDRO GALLEGOS RUIZ | aldo.gallegos@arena-analytics.com |
| JESÚS ALEJANDRO OLIVARES PADILLA | alejandro.olivares@arena-analytics.com |
| ANDREA GUADALUPE PLASCENCIA RODRÍGUEZ | andrea.plascencia@arena-analytics.com |
| JOSÉ ANTONIO PEDRAZA RANGEL | jose.pedraza@arena-analytics.com |
| CARLOS ALBERTO RUIZ  ESTAÑÓN | carlos.ruiz@arena-analytics.com |
| CARLOS ALFONSO BARRÓN RIVERA | alfonso.barron@arena-analytics.com |
| DANTE OCTAVIO GODINEZ ALDANA | dante.godinez@arena-analytics.com |
| DAVID PASTOR MARTÍNEZ ULLOA | dpastor@arena-analytics.com |
| DIANA ITZEL VAZQUEZ SANTIAGO | divazquez@arena-analytics.com |
| EDUARDO ALAIN ESPINOZA DE LA CRUZ | eduardo.espinoza@arena-analytics.com |
| RAUL EDUARDO AYALA SOTO | eduardo.ayala@arena-analytics.com |
| EDWARD IGNACIO GÓMEZ RUIZ | edward.gomez@arena-analytics.com |
| ELÍAS ABRAHAM GARCÍA MENDOZA | elias.garcia@arena-analytics.com |
| EMILIO OLMOS SÁNCHEZ | emilio.olmos@arena-analytics.com |
| ERICK LÓPEZ CRUZ | erick.lopez@arena-analytics.com |
| FEDERICO LAGOS GUIZAR | flagos@arena-analytics.com |
| FELIPE DE JESÚS ZETINA SALGADO | felipe.zetina@arena-analytics.com |
| FRANCISCO MANUEL BARRIOS PANIAGUA | fbarrios@arena-analytics.com |
| ERIKA GABRIELA TOSTADO MILLAN | gabriela.tostado@arena-analytics.com |
| JOSE GERARDO ESPINOZA JIMENEZ | gerardo@arena-analytics.com |
| HECTOR RANGEL CASTRO | hector@arena-analytics.com |
| ILSE HERNÁNDEZ MINUTTI | ilse.hernandez@arena-analytics.com |
| IÑAKI FERNÁNDEZ FISCAL | inaki.fernandez@arena-analytics.com |
| JAVIER MARTÍNEZ CARRANZA | javier.martinez@arena-analytics.com |
| JORGE ANTONIO VARGAS RAMOS | jorge.vargas@arena-analytics.com |
| JOSE ROBLES NORIEGA | jrobles@arena-analytics.com |
| JUAN DANIEL GRANADOS ROMO | juan.granados@arena-analytics.com |
| JUAN LUIS VELÁZQUEZ MORALES | juan.velazquez@arena-analytics.com |
| JUAN PABLO MONTOYA GUZMÁN | juan.montoya@arena-analytics.com |
| KAREEM GALVÁN DELGADILLO | kareem.galvan@arena-analytics.com |
| LORENA MONSERRAT CAMPUZANO SÁNCHEZ | lorena.campuzano@arena-analytics.com |
| LORENZO LLAGUNO | lorenzo@arena-analytics.com |
| LOURDES MARTINEZ MARTINEZ | lourdes.martinez@arena-analytics.com |
| LUIS ADRIÁN LARA GARCÍA | luis.lara@arena-analytics.com |
| LUIS ANTONIO FLORES CASTRO | luis.flores@arena-analytics.com |
| LUIS JESUS BECERRIL VILLASEÑOR | luis@arena-analytics.com |
| LUZ MARÍA GURROLA RAMOS | lmgurrola@arena-analytics.com |
| MARCO ANTONIO ARISTEO GARCÍA | marco.aristeo@arena-analytics.com |
| MARÍA MAGDALENA CASTRO SAM | maria.castro@arena-analytics.com |
| MARIANA CONTRERAS MENDEZ | mariana.contreras@arena-analytics.com |
| MAX BURKLE GOYA | mburkle@arena-analytics.com |
| MICHAEL STEVEN DELGADO | mdelgado@arena-analytics.com |
| MIGUEL ANGEL AGUILAR CAMPA | angel.aguilar@arena-analytics.com |
| OSCAR ANDRÉS MANCHA | omancha@arena-analytics.com |
| RODOLFO NAVARRETE PEREZ | rodolfo@arena-analytics.com |
| RODRIGO CASIANO MORALES | rodrigo.casiano@arena-analytics.com |
| RUBÉN ALEJANDRO RUIZ GÓMEZ | alejandro.ruiz@arena-analytics.com |
| SAMUEL AGUILAR RAMIREZ | samuel.aguilar@arena-analytics.com |
| SEBASTIÁN JIMÉNEZ JIMÉNEZ | sebastian.jimenez@arena-analytics.com |