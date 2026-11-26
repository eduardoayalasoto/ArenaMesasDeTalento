# Spec 010 — Evaluación 360 al owner del proyecto (informativa, POC)

**Estado:** implementado y desplegado (fases 1–4, 2026-11-26; sin recordatorios por correo: aún no hay servicio de correo) · **Fuente de contenido:** hoja
«03 · 360 al Gerente» de la *Matriz de Competencias y Pesos por Puesto v1.1* (10 dimensiones × 3 preguntas,
escala 1–4).

## 1. Contexto y decisiones del usuario (2026-11-26)
1. La 360 **no cuenta para ninguna calificación**: ni Ownership, ni Entrega de Valor, ni Impacto Arena, ni la
   calificación final. Es **informativa**, pero tiene un **índice** (p. ej. «3.4 de 4») con su banda de lectura.
2. Se califica **al owner del proyecto** (`Project.owner`), **solo en proyectos que lo activen** con un **check
   en el proyecto**. Responden **todas las personas involucradas** en ese proyecto.
3. El cuestionario se crea **con el mismo editor** de hoy; al crearlo se elige el **tipo**: *Ownership* (pide
   posición y nivel) o *360* (no pide nada: se asigna a todo el equipo del proyecto).
4. El owner ve **un score por proyecto**, **en vivo**. **En pantalla nunca se muestra quién respondió qué**
   (ni al owner, ni a Talento, ni a Dirección).
5. **POC — se guarda todo:** la base **sí conserva** quién escribió cada respuesta y comentario (más fechas y
   duración), aunque la interfaz no lo muestre, para poder decidir después, sin pedirle a nadie que responda otra
   vez, si Talento/Dirección podrán ver la autoría.
6. **Sin mínimo de respuestas.** Empresa chica: un proyecto con 2 personas es normal y se asume que el owner puede
   deducir quién dijo qué. El score se muestra siempre: con una sola respuesta es **la calificación directa**; con
   varias, **el promedio**. El énfasis está en que **todos completen** su respuesta.
7. Superficies: pantalla «Evaluaciones 360» (arriba lo que me toca responder, abajo lo que mi equipo dijo de mí,
   como «Validar Ownership») y un bloque en **Mesa de Talento** (score + enlace) cuando la persona es owner de un
   proyecto con la 360 activa.

## 2. Glosario
- **Evaluado**: el owner del proyecto. **Respondiente**: miembro del proyecto con membresía vigente en el periodo,
  distinto del evaluado. **Dimensión**: una sección del cuestionario 360 (3 preguntas) con su ponderación (las de
  la hoja: 8 × 12.5 % y 2 × 0 %). **Índice 360**: promedio de dimensiones ponderado, escala 1–4.

## 3. Privacidad (POC)
- La **interfaz** nunca muestra autor, hora ni orden de llegada; los comentarios salen **sin autor y en orden
  aleatorio estable** (no cronológico).
- La **base** guarda `respondent` en cada respuesta (§5). Es un dato **interno** que solo el servicio de resultados
  y los comandos de soporte pueden leer; ninguna vista, API ni exporte lo entrega.
- **Honestidad del texto al responder:** la pantalla dice «Quien evalúas **no verá** quién respondió qué» y **no**
  promete que «nadie» pueda saberlo (la persona sí queda registrada). Antes de pasar a producción real,
  Talento valida el aviso de privacidad con ese texto.
- Si más adelante se decide mostrar autoría a Talento/Dirección, es un cambio de permisos y pantalla, **sin
  migrar datos** (ya existen).

## 4. Alcance

### 4.1 Cuestionario tipo 360 (editor existente)
- `QuestionnaireTemplate.Kind.THREE_SIXTY`; sin `area` ni `level`. Una sola versión **vigente** (publicar archiva
  la anterior, igual que hoy). Al crear (`+ Nuevo cuestionario`): **Tipo** = Ownership | Entrega de Valor | 360;
  si es Ownership pide Área › Posición › Nivel; si es 360, no pide nada.
- Estructura **idéntica** a la actual: Escala (1–4 con N/A), Secciones y preguntas. En 360 la **sección es la
  dimensión** y lleva `Section.weight_pct` (solo 360; Σ = 100.0; admite 0 % «se califica, no pesa»). **No** usa
  Categorías (no contamina el catálogo de Ownership). Las preguntas de una dimensión pesan igual entre sí. Bloque
  del catálogo y nivel objetivo se conservan como referencia. Arrastrar y soltar, publicar y versionado funcionan
  igual; «ponderación automática» = partes iguales entre las dimensiones con peso > 0.
- Carga inicial desde la hoja 03 con un comando de importación (`import_competency_matrix --360`), simulación por
  defecto, como el de Ownership.

### 4.2 Activación por proyecto
- `Project.three_sixty_enabled` (bool, default **No**). Check «Activar evaluación 360 al owner» en la pantalla del
  proyecto (permiso `projects.edit`). Texto: quién la responde, que es informativa y que el owner no verá quién
  respondió qué.
- Requisitos: ninguno extra (todo proyecto tiene owner); responden las membresías vigentes distintas del owner.
- Apagarla **conserva** lo ya respondido; deja de pedirse y de mostrarse; Talento/Dirección siguen viendo el
  histórico.

### 4.3 Ciclo (por periodo)
1. Con el periodo **Abierto** y el check activo, cada respondiente ve el pendiente en «Evaluaciones 360» y en la
   campana.
2. Contesta las 30 preguntas (autoguardado como borrador), con **un comentario general** opcional; la escala es 1–4 (sin N/A, como la hoja). **Enviar** exige todas contestadas (o N/A) y confirmación («no podrás cambiarla»).
3. El owner ve su **score por proyecto en vivo**, desde la **primera** respuesta (calificación directa con una,
   promedio con varias), sin conteos ni nombres. Talento y Dirección ven además **cuántos de cuántos** han
   respondido y **quién falta** (para dar seguimiento y recordatorios), nunca el contenido ligado a una persona.
4. Al **cerrar el periodo** todo queda de solo lectura; los borradores sin enviar no cuentan.
5. Una respuesta por persona, proyecto y periodo; en varios proyectos con 360 activa, una por proyecto.

### 4.4 Cálculo (informativo)
- Promedio por dimensión (ignora N/A) → Índice = Σ promedio_dimensión × peso_dimensión (las de 0 % se muestran y no
  suman). Escala 1–4; 1 decimal en pantalla. Banda con `scoring.interpretation_band` (Excede ≥ 3.50 · Cumple ≥ 3.00 ·
  Cumple parcial ≥ 2.00 · No cumple). Con una sola respuesta, el índice es esa calificación.
- **No se escribe** en `FinalScore` ni en ninguna tabla de calificación. Servicio nuevo
  `apps/core/services/three_sixty.py`; `scoring.py` no cambia.

### 4.5 Pantallas
- **«Evaluaciones 360»** (Mesa de Talento › *Mi evaluación*; badge con pendientes). Dos bloques, como
  «Validar Ownership»:
  - **Por responder:** proyectos del periodo donde soy respondiente y no he enviado («Responder» / «Continuar
    borrador»; las enviadas aparecen como «Enviada» sin detalle).
  - **Mi liderazgo:** por cada proyecto donde soy owner con 360 activa: índice, banda, desglose por dimensión
    (barras 1–4) y comentarios sin autor.
- **Responder 360:** una sola pantalla con una sección por dimensión (plegables), escala visible, progreso,
  autoguardado y el aviso de privacidad del §3.
- **Resultado de un proyecto (Talento/Dirección):** igual que el del owner + avance (X de Y) + quién falta.
- **Mesa de Talento › persona:** en el bloque de cada proyecto donde es owner con 360 activa: «Tu equipo lo calificó
  con **3.4 / 4 · Cumple**» + enlace «Ver detalle 360» (según permisos).

### 4.6 Permisos (matriz de perfiles, spec 005)
Claves nuevas, con ruta registrada, fila en `seed.py` y `legacy.py`:
| Clave | Alcance | Quién |
|---|---|---|
| `three_sixty.respond` | propio | todo el que tenga membresía |
| `three_sixty.results.own` | propio | el owner (ve solo lo suyo) |
| `three_sixty.results.view` | área / todos | Dirección (su área), Talento (todos) |
Activar el check: `projects.edit`. Editor del cuestionario 360: `questionnaires.manage`.

## 5. Modelo de datos (resumen)
- `Project.three_sixty_enabled: bool`.
- `QuestionnaireTemplate.kind += THREE_SIXTY`; `Section.weight_pct: Decimal(4,1) null` (solo 360).
- `ThreeSixtyResponse(project, period, template, evaluee, respondent, status BORRADOR|ENVIADA, started_at,
  submitted_at, duration_seconds)` — única por (project, period, respondent); con `HistoricalRecords`.
- `ThreeSixtyAnswer(response, question, value 1–4, answered_at)`; el comentario general vive en `ThreeSixtyResponse.comment`.
- `evaluee` queda fijo al enviar (si el owner cambia a mitad de periodo, lo enviado sigue con quien era).
- Ownership, Entrega de Valor y `FinalScore` **sin cambios**.

## 6. Casos límite
- Cambia el owner a mitad de periodo: el nuevo empieza de cero; Talento ve ambos.
- Miembro entra/sale del proyecto: responde si su membresía vigente toca el periodo abierto.
- Proyecto cerrado o fuera del periodo: no se pide. Owner que no es miembro: se permite (es el evaluado).
- Plantilla nueva a mitad de periodo: lo enviado conserva su versión; los borradores se migran a la nueva (se
  pierde lo contestado de preguntas eliminadas, con aviso).
- Talento/Dirección que también son miembros: responden como cualquiera.

## 7. Fuera de alcance
- Ponderación en la calificación final; 360 a quien no sea owner; 360 entre pares; exportes por persona;
  reapertura de respuestas enviadas; mostrar autoría en pantalla (decisión diferida, ver §3).

## 8. Criterios de aceptación
1. Ninguna vista ni plantilla muestra autor de una respuesta o comentario; la base sí lo guarda (pruebas de ambos).
2. El owner ve score desde la primera respuesta (directo con una, promedio con varias) y no ve conteos ni nombres.
3. Talento/Dirección ven X de Y y quién falta; los recordatorios llegan solo a quien no ha enviado.
4. El check apagado: nadie ve pendientes; el histórico sigue para Talento/Dirección.
5. La 360 no altera `FinalScore` (prueba con y sin respuestas).
6. El editor crea el tipo 360 sin pedir posición/nivel; el de Ownership sigue pidiéndolos.
7. Importar la hoja 03 deja 10 dimensiones, 30 preguntas, pesos 8×12.5 + 2×0, Σ = 100.
8. Pruebas de permisos (`test_access_coverage`), de ciclo (borrador, enviar, cerrar periodo) y de cálculo contra la hoja.

## 9. Fases
1. **Modelo + editor tipo 360 + importación** de la hoja 03.
2. **Check en proyecto + Responder** (borrador → envío).
3. **Evaluaciones 360** (por responder / mi liderazgo) + cálculo.
4. **Mesa de Talento + menú/badge + recordatorios** (`send_pending_reminders`) + vista Talento/Dirección.

## 10. Decisiones finales
- **Comentarios:** solo uno general por respuesta. **Recordatorios por correo:** fuera de alcance (sin servicio de correo);
  el seguimiento es la pantalla «Evaluaciones 360» (Talento/Dirección ven quién falta) y el contador del menú.
