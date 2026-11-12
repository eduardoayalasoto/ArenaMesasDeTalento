# Research: Ownership ponderado por categorías

Hallazgos de la auditoría contra el código (2026-11-12) y decisiones de diseño. No quedan `NEEDS CLARIFICATION`.

## Hallazgos de la auditoría

- **A1. `Question.weight` no se usa en el cálculo.** `scoring.ownership_evaluation_score` promedia todas las respuestas numéricas sin ponderar; `questionnaire_editor.duplicate_as_new_version` solo copia el valor. Hoy vale 1.00 en todos los reactivos.
- **A2. Solo los cuestionarios en BORRADOR se editan.** `template_edit` rechaza ediciones si no es borrador; para cambiar uno publicado se duplica como versión nueva. Por eso los pesos solo se editan en borradores y los cuestionarios publicados quedan inmutables (principio III).
- **A3. La importación exige una v1 previa.** `questionnaire_import.import_version` copia escala y nota de la v1 y el comando exige `--target-version ≥ 2`. CONS no tiene v1, así que la importación debe aceptar escala propia en el YAML y permitir la versión 1.
- **A4. `Section` ya agrupa visualmente** (el formulario recorre `sections → questions`). La categoría es otra dimensión; para CONS se crea una sección por categoría para que la pantalla agrupe igual.
- **A5. El score vive materializado** en `OwnershipEvaluation.score` al cerrar; el informe lee ese valor. El promedio en vivo (`_progress`) usa la misma función de cálculo, así que cambiar la función cubre el autoguardado, el cierre y la reapertura.
- **A6. El nivel se muestra en ~24 lugares** (`user.level.name` en perfil, tablas, Mi área, etc.), y hay filtros por nivel (`level.code`) que deben seguir usando los niveles globales.
- **A7. El proyecto no tiene evaluador sugerido.** El colaborador elige evaluador en `ownership_start` (principal y secundarios); el Lead lo hace en `ownership_lead_start`.
- **A8. Los cuestionarios de Entrega de Valor** comparten el modelo (`kind=VALUE_DELIVERY`, sin área ni nivel) y no deben exigir categorías.
- **A9. Los permisos** se declaran en `apps/access/registry.py` y hay una prueba de cobertura; toda vista nueva necesita clave, fila en `seed.py` y `legacy.py`.

## Decisiones

### D1. Peso de pregunta: campo nuevo `weight_pct`, el campo `weight` queda sin uso
- **Decision**: agregar `Question.weight_pct` (decimal, 1 decimal, **nulo = partes iguales**) y dejar `Question.weight` intacto y sin leer (se retira en un spec posterior).
- **Rationale**: reinterpretar `weight` obligaría a reescribir datos de producción y rompe la garantía de «idéntico a hoy»; con nulo = partes iguales el cálculo reproduce exactamente el promedio simple sin redondear repartos (evita el 33.4/33.3/33.3 que cambiaría resultados).
- **Alternatives**: reutilizar `weight` con migración de datos (riesgo de regresión y de redondeo); pesos relativos sin sumar 100 (contradice la petición de validar 100%).

### D2. Categorías: catálogo global + peso por cuestionario
- **Decision**: `Category` (código, nombre, orden, activa) común a todas las áreas; `TemplateCategory` (cuestionario, categoría, `weight_pct`) con único por par; `Question.category` nulo solo para preguntas de texto.
- **Rationale**: permite comparar «cuánto saca por categoría» entre áreas y cambiar pesos por puesto sin tocar el catálogo; las categorías son datos administrables (se pueden sustituir por C1–C10 en una versión futura).
- **Alternatives**: categoría como texto libre en la pregunta (no comparable, sin catálogo); categorías por área (impide la comparación común).

### D3. Fórmula y redondeo
- **Decision**: score de categoría = promedio ponderado sin redondear; score del cuestionario = Σ (score_categoría × peso_categoría) con renormalización cuando una categoría queda sin calificar; **un solo** redondeo final a 2 decimales (mitad hacia arriba) como hoy. En el desglose por categoría se redondea cada categoría solo para mostrarla.
- **Rationale**: con una categoría «General» y pesos nulos, la fórmula es `Σvalores/n` cuantizado una vez: idéntico al código actual. Redondear por etapas generaría diferencias de centésimas.
- **Alternatives**: redondear cada categoría antes de ponderar (diferencias contra la matriz de Consultoría).

### D4. Compatibilidad sin configuración
- **Decision**: si un cuestionario no tiene filas `TemplateCategory` (p. ej. creado por código antiguo), el cálculo lo trata como una sola categoría al 100%; la publicación del editor **sí** exige configuración completa. `seed_questionnaires` y la duplicación crean/copian «General».
- **Rationale**: robustez durante el despliegue (migrar → desplegar) y para fixtures de pruebas existentes.

### D5. Validación de pesos: décimas enteras y tres capas
- **Decision**: pesos manejados como enteros en décimas (0–1000) para sumar sin errores de coma flotante. Capas: (1) pantalla en vivo con Alpine (total, aviso «Suma actual X% — debe llegar a 100%», botón Guardar/Publicar deshabilitado), (2) Django Form + servicio `ownership_weights.validate_*` al guardar, (3) `validate_for_publish` e importación llaman al mismo servicio.
- **Rationale**: cumple la petición explícita de no dejar guardar pesos que no sumen 100% y evita decimales largos; un solo servicio evita que la regla diverja.
- **Alternatives**: validar solo en servidor (no cumple «visual»); permitir guardar parcial y bloquear solo publicar (el solicitante pidió que se valide al modificar).

### D6. Reparto en partes iguales
- **Decision**: método del mayor residuo sobre décimas: 3 categorías → 33.4 / 33.3 / 33.3; el sobrante va a las primeras por orden. Mismo algoritmo para el botón de la pantalla y para normalizar los pesos de la matriz al importar.
- **Rationale**: suma exacta 100.0 con un decimal.

### D7. Puestos: tabla `Position` + nombre con caché corta
- **Decision**: `catalog.Position(area, level, name, is_active)`, único por (área, nivel); servicio `positions.position_name(area_id, level_id)` con caché de proceso de 60 s invalidada al guardar; filtro de plantilla `puesto` para mostrar el nombre; los selectores por `level.code` siguen usando niveles globales. Siembra: una fila por área × nivel existente con el nombre del nivel (Analítica) y los nombres propios de CONS.
- **Rationale**: evita N+1 al listar usuarios y no cambia FK ni los permisos o ponderaciones por nivel.
- **Alternatives**: nombre de puesto en el usuario (duplica datos); relación 1:1 a una tabla de puestos globales (rompe `PillarWeight` por nivel).

### D8. Importación con escala propia y versión 1
- **Decision**: ampliar el YAML con `categories` (código, nombre, peso), `scale` opcional y por pregunta `category` y `weight`; si el puesto no tiene v1 y el YAML trae escala, se crea la v1 sin copiar. Una sección por categoría cuando hay más de una categoría; si solo hay una, una sección como hoy. El script `scripts/matriz_consultoria_to_yaml.py` genera el YAML desde el xlsx con las mismas reglas de redondeo y valida sumas. Idempotente y con rechazo si hay respuestas.
- **Rationale**: reutiliza el pipeline de la spec 007 (xlsx → YAML → importación) y deja el resultado revisable en git.

### D9. Mapeo de la matriz a categorías y pesos
- **Decision**: categoría = mapeo por «Bloque del catálogo» definido en la spec (FR-022); peso de categoría = suma de los pesos de sus competencias, normalizado a 100.0 con mayor residuo; peso de pregunta = peso de la competencia ÷ suma de su categoría, normalizado igual (las competencias de peso 0 quedan en 0.0; «Apego a los valores» en 0.0). Resultado esperado de categorías: Analista 13.6/22.7/18.2/45.5; Consultor 30.2/20.9/14.0/34.9; Consultor Sr 32.7/18.2/21.8/27.3; Gerente 32.3/16.1/19.3/32.3.
- **Rationale**: reproduce la matriz exacta salvo el redondeo (≤ 0.1 punto).
- **Verificación**: prueba que calcula el score de un conjunto de respuestas con la matriz original (pesos sin redondear) y con el modelo cargado, y exige diferencia ≤ 0.01.

### D10. Desglose por categoría calculado, no congelado
- **Decision**: función pura `scoring.ownership_category_breakdown(evaluation)` devuelve filas (categoría, peso, score, calificadas, total); la vista de evaluación y el autoguardado lo muestran; el pilar del informe promedia por categoría las evaluaciones enviadas (mismo criterio que el total).
- **Rationale**: los cuestionarios publicados no cambian, así que recalcular es estable y evita otra columna; cuando exista una sola categoría el desglose se oculta.

### D11. Evaluador sugerido
- **Decision**: `Project.suggested_evaluator` (FK opcional a usuario, `SET_NULL`) en el formulario de proyecto; `ownership_start` preselecciona sugerido → owner → responsable, excluyendo al propio colaborador. El Lead (sin proyecto) no cambia.

### D12. Verificación de no regresión en producción
- **Decision**: comando `verify_ownership_scores [--period X] [--fix-report]` que recalcula con el modelo nuevo el score de **todas** las evaluaciones con respuestas y lo compara con el guardado, imprimiendo conteos y diferencias; se corre antes y después de migrar (simulación) y en una prueba con datos sintéticos.
- **Rationale**: cumple el principio VI (conteos antes/después y simulación) y respalda SC-001.

### D13. Seguridad de datos y permisos
- **Decision**: claves nuevas `catalog.positions.manage` y `catalog.categories.manage` (ON_OFF, como los demás catálogos) con fila en seed y legacy; las acciones de pesos en el editor usan `questionnaires.manage`.
- **Rationale**: principio I; ninguna comprobación por rol.

## Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| El cálculo nuevo cambia un score existente por redondeo o por preguntas de texto | Un solo redondeo final (D3); tests de equivalencia; `verify_ownership_scores` sobre producción antes de desplegar |
| Despliegue con código que espera categorías antes de migrar | Orden migrar → desplegar (VI); fallback sin configuración (D4) |
| Mostrar el puesto en 24 lugares a mano omite alguno | Lista de lugares en tasks + prueba que compila plantillas; los restantes siguen mostrando el nivel global sin romper nada |
| La matriz tiene VOBO pendiente | La importación se corre en borrador en Neon (sin publicar) y se publica cuando Dirección dé el VOBO |
| Editar pesos de una categoría deja el cuestionario temporalmente inválido | La pantalla edita todos los pesos del grupo en un solo envío validado; publicar exige validez total |

## Verificación en local (2026-11-12)

- **Migraciones sobre datos existentes** (SQLite de desarrollo, aparte de producción): se sembraron catálogos, 17 cuestionarios (v1 + Entrega de Valor) y se importaron los 16 de 2027; al revertir y volver a aplicar `questionnaires 0004` quedaron **5 categorías, 32 vínculos «General» al 100%, 0 preguntas de escala de Ownership sin categoría y 0 preguntas de Entrega de Valor con categoría**. `verify_ownership_scores`: 0 diferencias (sin evaluaciones en esa base).
- **Generador de la matriz**: pesos de categoría idénticos a la tabla de FR-023; desviación máxima por competencia 0.031 pp (Consultor); 72 competencias (16 / 18 / 19 / 19).
- **Equivalencia con la matriz original** (prueba `test_cons_score_matches_the_original_matrix`): con respuestas completas, diferencia ≤ 0.011 en los cuatro puestos. Con N/A el modelo redistribuye dentro de la categoría (la matriz no tiene N/A porque las competencias que no aplican no existen en el puesto).
- **Pendiente en producción** (requiere confirmación): `verify_ownership_scores` en Neon antes y después de migrar (conteos), y carga de CONS.
