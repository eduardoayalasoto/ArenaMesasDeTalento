# Research: Checklists de Ownership versión 2027

## D1 — Dónde guardar los campos del checklist

- **Decision**: 6 `TextField(blank=True)` en `Question`: `acceptance_criteria`, `deliverable`, `deliverable_format`, `frequency`, `level_expectation`, `guidance`.
- **Rationale**: son atributos 1:1 del reactivo, se leen junto con él (0 consultas extra) y la migración es aditiva (no toca v1). `simple_history` no está en `Question`, así que no hay tabla histórica que migrar.
- **Alternatives**: concatenarlos en `text` (ilegible, no editable por campo); modelo `QuestionDetail` 1:1 (consulta extra sin beneficio); JSONField (no editable con Django Forms sin código extra).

## D2 — Importación en dos pasos (xlsx → YAML → BD)

- **Decision**: `scripts/checklists_2027_to_yaml.py` convierte los libros a `fixtures/questionnaires/2027/<AREA>.yaml` (versionado en git y revisable); el comando `import_questionnaire_version` carga el YAML.
- **Rationale**: mismo patrón que `seed_questionnaires` (fixtures YAML); el diff en git es la evidencia de revisión; el runtime no depende de openpyxl ni de la carpeta `docs/`.
- **Alternatives**: comando que lee el xlsx directo (sin artefacto revisable; los subtemas curados quedarían enterrados en código de producción).

## D3 — Títulos

- **Decision**, en orden: (a) si una v1 de cualquier puesto tiene el mismo texto (≥ 0.95) con título «Categoría — Subtema», se conserva; (b) si la hoja trae Categoría: «Categoría — Actividad»; (c) si la Actividad se repite en la hoja: «Actividad — Subtema» con subtema curado (tabla `SUBTOPICS` del script); (d) la Actividad. El script falla si queda un título repetido o un subtema sin curar.
- **Rationale**: en PM, CD Lead y rutinas de CD la "Actividad" del Excel es en realidad una categoría (se repite hasta 8 veces). La convención «Categoría — Subtema» ya la usan UX/UI Lead e ID en la v1; el usuario pidió conservar esos títulos y ser consistente con el sistema.
- **Resultado**: 16/16 cuestionarios con títulos únicos; conteos idénticos a las hojas (21, 24, 24, 24 · 29, 32, 34, 25 · 25, 32, 39, 25 · 18, 23, 27, 25).

## D4 — Secciones

- **Decision**: una sola sección "Checklist de Ownership" por cuestionario (igual que la v1).
- **Rationale**: el editor no permite crear/renombrar/reordenar secciones (auditoría #11), la numeración del formulario se reinicia por sección (#13) y PM/UX Lead intercalan categorías (agrupar alteraría el orden del Excel). El prefijo de categoría en el título conserva la información.
- **Alternatives**: secciones por categoría (rechazada por lo anterior; queda como mejora futura junto con un editor de secciones).

## D5 — Resincronización segura (FR-001)

- **Decision**: `sync_evaluation_template(evaluation)` solo actúa si: no está enviada, **nunca fue enviada** (`evaluation.history.filter(status="ENVIADA").exists()` es falso; `reopen` borra `submitted_at`, por eso se usa el historial), `period.status == ABIERTO`, y `template.area_id/level_id` difieren de `user.area_id/level_id`. Envuelta en `transaction.atomic`. La vista la llama solo con `editing=True` y si el usuario puede editar respuestas.
- **Rationale**: hoy compara IDs de template, así que publicar v2 dispararía el borrado de respuestas en S1 (PM Snr: 39 + 11 respuestas), incluso desde la vista de solo lectura de un director.
- **Alternatives**: no resincronizar nunca (perdería el caso legítimo de cambio de puesto en S2).

## D6 — Idempotencia de la carga

- **Decision**: llave (`OWNERSHIP`, área, nivel, `version`). Si existe y algún reactivo tiene respuestas → se rechaza ese puesto (`CommandError` con detalle, sin tocar nada). Si existe sin respuestas → se reconstruyen sección, reactivos y escala. Con `--publish` se llama a `publish_template`. Borradores de versión mayor sin respuestas se archivan (CD Jr v3: copia de prueba de v1 con 2 reactivos invertidos; CD Jr v2 actual es copia idéntica de v1 y se reconstruye).
- **Rationale**: `OwnershipAnswer.question` es `PROTECT` (auditoría #5); 2026-S2 no tiene evaluaciones aún, así que la carga de hoy es segura y repetible hasta que existan respuestas.

## D7 — Escala y nota de escala

- **Decision**: se copian de la v1 publicada del mismo puesto (`ScaleOption` a nivel template + `scale_note`).
- **Rationale**: los Excel usan la misma escala 1–4; mantiene descriptores vigentes (RN-03).

## D8 — Publicación

- **Decision**: `publish_template` valida (≥ 1 reactivo SCALE, títulos únicos, escala presente) y archiva el publicado anterior con `save()` por instancia (queda en `HistoricalRecords`). Lanza `ValidationError` con mensaje en español; la vista lo muestra como `messages.error`.
- **Rationale**: auditoría #8.

## D9 — Siembra

- **Decision**: `seed_questionnaires` omite un puesto si existe una versión > 1; `seed_all` llama después a `import_questionnaire_version --dir fixtures/questionnaires/2027 --target-version 2 --publish`.
- **Rationale**: auditoría #6 (re-ejecutar la siembra violaba `unique_published_template`).

## D10 — Presentación

- **Decision**: parcial `templates/partials/_checklist_details.html` (desplegable daisyUI `collapse` con Alpine `open`) usado en `ownership_fill.html` y en la vista de solo lectura del editor; textos con `whitespace-pre-line`. Badge: `PUBLICADO` → success; `BORRADOR` y `ARCHIVADO` quedan neutros (el parcial es compartido con evaluaciones, cuyo BORRADOR ya es neutro). Ajustes de la auditoría de frontend: etiqueta visible en el alta, `aria-expanded`/`aria-controls`, texto del disparador en `base-content/80` (contraste) y objetivo táctil de 44 px en móvil.
- **Rationale**: único punto que renderiza reactivos (auditoría #13); regla de Alpine solo para estado local de UI.

## D12 — Opción del comando

- **Decision**: `--target-version` (no `--version`, que Django reserva). La carga de los 16 puestos es **todo o nada** en una transacción; `--dry-run` la revierte.
- **Hallazgo**: detectado en la simulación contra producción; se agregó prueba del comando (`call_command`).

## D11 — Orden de despliegue (analyze F1)

- **Decision**: migrar Neon → push y esperar el deploy → importar y publicar.
- **Rationale**: la migración es aditiva (el código viejo la tolera); publicar v2 con el código viejo activo reabriría el riesgo de borrado de respuestas que corrige US1.

## Revisión de contenido (criterio del equipo técnico)

Criterios para publicar cada v2: (1) mismo número de reactivos que la hoja; (2) títulos únicos; (3) 100 % con descripción y criterio de aceptación (salvo celdas vacías en el Excel); (4) sin texto de respaldo ni leyendas de escala importadas; (5) escala y nota copiadas de la v1. Resultado en `reporte-revision.md`.
