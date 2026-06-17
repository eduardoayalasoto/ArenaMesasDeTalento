# Checklist de Progreso — Webapp de Evaluaciones Arena

> Documento vivo. Se actualiza conforme avanza la implementación del `Plan_Desarrollo_Webapp_Evaluaciones.md`.
> Estado: ⬜ pendiente · 🟡 en curso · ✅ hecho · ⚠️ con nota
> Última actualización: 2026-06-17 · **Desplegado en Vercel + Neon** · Ver `CONTEXTO_Sistema.md` para el panorama completo.

## Convenciones del proyecto (recordatorio permanente)
- **Idioma:** sistema 100% en español (etiquetas, mensajes, correos, validaciones). Código (modelos, variables) en inglés.
- **Stack:** Django 6.0.6 · Python 3.14 · htmx · Alpine.js 3 · Tailwind v4.
- **BD:** SQLite en local, Postgres gestionado (`DATABASE_URL`) en prod.
- **Skills obligatorias:** UX UI Pro Max (toda pantalla), feature-dev (cada feature), code simplifier (cierre de módulo), Vercel (deploy).
- Reglas de negocio referenciadas por ID (RN-xx) del `KB_Modelo_Desempeno_2026.md`.

---

## Estado por fase

### Fase 0 — Fundaciones ✅
- ✅ Proyecto Django (`config/`, `manage.py`)
- ✅ `settings.py` por entorno (es-mx, MX TZ, Postgres/SQLite, whitenoise, simple-history, correo, seguridad prod)
- ✅ Dependencias instaladas en `.venv`
- ✅ `accounts.User` custom (email como username) + manager + roles derivados (is_lead/is_talento/is_director)
- ✅ `core/views.py` (errores 403/404/500 en español) + `core/context_processors.py` (navegación por rol, marca activo)
- ✅ `urls.py` por app (accounts completo; catalog/questionnaires/evaluations como stubs por fase)
- ✅ Layout base (`base.html`) + Tailwind v4 (browser) + Alpine + htmx + sistema de iconos SVG + toasts + sidebar/topbar
- ✅ Páginas de error personalizadas en español (standalone)
- ✅ `requirements.txt` / `.env.example` / `.gitignore`
- ✅ Migraciones iniciales + smoke test (login 200, home redirige, tableros 200, 404 ok)
- ⬜ Conexión a Vercel (deploy preview) — **requiere cuenta/credenciales del usuario**

### Fase 1 — Identidad y catálogos 🟡
- ✅ Modelos `catalog` (Area, SeniorityLevel, PillarWeight, EvaluationPeriod, Project, ProjectMembership)
- ✅ Login / logout / reset de contraseña (vistas + plantillas en español)
- ✅ `admin.py` de accounts y catalog (soporte del superusuario)
- ✅ `seed_superuser` + `seed_catalogs` (4 áreas, 4 niveles, ponderaciones RN-19, periodo 2026-S1 ABIERTO) + `seed_users` (53 colaboradores) + `seed_all`
- ✅ **Pantalla de Talento para asignar área/nivel/rol** (masiva, con búsqueda) — selects mejorados (appearance-none + chevron Lucide); **bug crítico corregido**: el POST ahora omite usuarios no visibles para evitar borrar sus datos con filtro activo.
- ✅ **Reset de contraseña individual** desde `/cuenta/usuarios/`: botón "Resetear" por fila, POST htmx, restablece a `Arena2026!` + activa `must_change_password`.
- ✅ Cierre/apertura de periodos (pantalla propia de Talento)
- ⬜ Pantallas propias para áreas/niveles/ponderaciones/proyectos (hoy vía Django admin)

### Fase 2 — Motor de cuestionarios ✅
- ✅ Fixtures YAML (ID, CD, PM, UXUI)
- ✅ Modelos `questionnaires` (Template, Section, Question, ScaleOption) + versionado (constraint 1 PUBLICADO por kind/area/level)
- ✅ `seed_questionnaires` → **17 plantillas (16 Ownership + 1 Entrega de Valor), 419 preguntas**, escala RN-03
- ✅ **Editor administrable de Talento**: listar, ver, editar/agregar/eliminar/reordenar preguntas, nota de escala; **versionado** (publicar archiva la anterior; duplicar crea borrador) — `questionnaire_editor.py` con 2 tests. Publicados = solo lectura (protege resultados históricos).
- ✅ Render genérico del template (pantalla del checklist de Ownership)
- ⬜ Reordenamiento drag-and-drop (hoy con botones ↑/↓) y edición de descriptores de escala (mejora futura)

### Fase 3 — Flujo Ownership ✅ (funcional E2E)
- ✅ Modelos `OwnershipEvaluation` / `OwnershipAnswer` (+ migraciones)
- ✅ `ownership_evaluation_score` / `ownership_pillar_score` (RN-03/04/05) **con tests**
- ✅ Pantalla de llenado (1 sola página, secciones, **autosave por ítem vía JSON**, progreso fijo, **promedio en vivo**) — patrón elegido según UX UI (no wizard de pasos)
- ✅ Envío con candado RN-06 (confirmación + Fortalezas + Oportunidades), inmutabilidad post-envío (403), reapertura admin (servicio)
- ✅ Cola de validación — **evaluadores múltiples** (primario + secundarios): modelo `OwnershipEvaluator` (migración `0002`); el colaborador gestiona la lista mientras esté abierta; cualquier evaluador puede complementar y cerrar; badges Primario/Secundario en UI. Correos de confirmación eliminados.
- ✅ **Sync de template al cambiar área/nivel:** al entrar a una evaluación BORRADOR, `sync_evaluation_template` detecta desajuste con el área/nivel actual, actualiza el template y borra respuestas previas (con aviso al usuario).
- ⬜ Vista lado a lado / co-edición del líder (ajuste fino, mejora futura)

### Fase 4 — Entrega de Valor ✅ (funcional E2E)
- ✅ Modelo + scoring (RN-08/09) **con tests**
- ✅ Captura del líder (criterio de tiempo condicionado al tipo de proyecto) + envío a validación
- ✅ Cola del director: validar / rechazar con comentario → **propaga recálculo a los miembros (RN-09)**

### Fase 5 — Impacto Arena + Calificación final ✅ (funcional E2E)
- ✅ Modelos `ArenaImpactScore` + `FinalScore`
- ✅ `final_score` ponderado por nivel (RN-12/19) + bandas (RN-20) + `is_complete` **con tests**
- ✅ Captura masiva de Talento (tabla editable, guardado en lote) + recálculo del final
- ✅ Vista integral "Mis resultados" (calificación, banda, pilares con peso por nivel)
- ⬜ Recálculo por señal automática (hoy: al validar EV / guardar Arena / abrir resultados)

### Capa de servicios (`core/services/`) ✅
- ✅ `scoring.py` (18 tests) · `permissions.py` (13 tests) · `ownership_flow.py` (add/remove/set_primary_evaluator + sync_evaluation_template) · `final_flow.py` (2 tests) · `value_delivery_flow.py`
- ✅ **Suite total: 168 pruebas en verde** (11 nuevas de evaluadores múltiples); `manage.py check` sin incidencias; smoke E2E de los 3 pilares OK

### Pendiente (no construido aún)
- Pantallas admin propias de Talento (áreas/niveles/usuarios/proyectos/periodos/ponderaciones) — hoy vía Django admin.
- Editor visual de cuestionarios (CRUD + drag-and-drop) — hoy editable vía Django admin.
- Vista "Mi área" del Lead, dashboard de avance de Talento, exportes CSV/XLSX, cierre de periodo (Fase 6).
- Deploy a Vercel + compilación de Tailwind (Fase 7) — **requiere credenciales del usuario**.

### Fase 6 — Dashboards, reportes y cierre ✅ (núcleo)
- ✅ Vista "Mi área" (Lead/Talento/Director) con filtro por nivel, filtrado a nivel queryset (RN-14/15)
- ✅ Dashboard de avance de Talento (% Ownership enviadas, % EV validadas, % finales completas)
- ✅ Exporte **CSV** de calificaciones por ámbito de rol (BOM UTF-8 para Excel)
- ✅ Cierre/apertura de periodos (RN-13): al cerrar, la captura queda en solo lectura
- ✅ Tablero de inicio con datos reales
- ⬜ Exporte XLSX y breakdown por área más rico (mejora futura)

### UX transversal — Guías, validaciones y consultas ✅
- ✅ Panel de instrucciones reutilizable (`info_panel`) en validación, Impacto Arena, usuarios, captura de EV, listas
- ✅ Validación **en vivo** del envío de Ownership (errores junto al campo: Fortalezas/Oportunidades/confirmación; aviso de preguntas pendientes)
- ✅ Pantalla de **consulta de persona** (drill-down desde "Mi área" → resultados + evaluaciones, con permiso por visibilidad)
- ✅ Estados vacíos y mensajes guía en todas las pantallas; banners de proceso (no enviar antes de validar, etc.)

### Fase 7 — Endurecimiento y despliegue ✅ (desplegado)
- ✅ Auditoría `simple-history` + tests de permisos + smoke E2E
- ✅ **Desplegado en Vercel** (entrypoint `api/wsgi.py`, builder Django, sin `vercel.json`) + **Neon Postgres** (migrado y sembrado)
- ✅ Repo en GitHub: `eduardoayalasoto/ArenaMesasDeTalento` (push → auto-deploy)
- ✅ Estáticos locales (Tailwind compilado, Lucide/Alpine/htmx vendorizados) + cache-busting; perf (lucide defer)
- ✅ Variables de entorno documentadas (`.env.vercel`, `docs/Deploy_Vercel.md`)
- ✅ Ayuda por rol en la app (`/ayuda/`) — sustituye al manual
- ⬜ Compilar Tailwind en el build de Vercel (hoy se versiona el CSS ya compilado) — opcional
- ⬜ Recordatorios agendados (Cron) — comando listo, falta agendar

---

## Bitácora (orden cronológico)

### 2026-06-10
- Recap del estado heredado (09-jun): plan + KB + scaffold parcial + modelos `catalog` + fixtures YAML.
- Detectado bloqueante: `AUTH_USER_MODEL=accounts.User` sin modelo; `urls.py` de apps y `core.views`/`core.context_processors` referenciados pero inexistentes → el proyecto no levantaba.
- **Fase 0 cerrada:** `accounts.User` custom + manager; `core` (errores en español + navegación por rol); urls por app; layout base con Tailwind v4 (browser CDN — sin Node), Alpine, htmx, iconos SVG, sidebar/topbar/toasts/estados vacíos; login + reset de contraseña; páginas de error. Migraciones y smoke test OK.
- **Fase 1 (catálogos/seed):** `seed_superuser` + `seed_catalogs` (4 áreas, 4 niveles, ponderaciones, periodo 2026-S1 ABIERTO) + `seed_users` (53 colaboradores reales) + `seed_all`. Admin de Django como soporte.
- **Fase 2 (datos):** modelos de cuestionarios + `seed_questionnaires` → 17 plantillas / 419 preguntas.
- **Núcleo verificado (TDD):** modelos de `evaluations` (5 modelos); `core/services/scoring.py` (18 tests) y `permissions.py` (13 tests). **31 pruebas en verde.**
- **Decisiones técnicas:** Tailwind se sirve por CDN de navegador en dev (no hay Node en el entorno); en prod se compila con el CLI standalone (Fase 7). Salida de consola en ASCII por cp1252 de Windows; correr management/pytest con `PYTHONIOENCODING=utf-8`.
- **Sesión 2 (mismo día):** se construyeron y verificaron E2E los flujos completos:
  - Ownership: lista por proyecto → llenado de una página con autosave por ítem y promedio en vivo → envío con candado RN-06 → inmutabilidad → correo → cola del líder. (Patrón de pantalla: **una página con secciones**, no wizard de pasos, por recomendación de UX UI.)
  - Entrega de Valor: captura del líder (criterio de tiempo según tipo de proyecto) → cola del director (validar/rechazar) → recálculo del equipo.
  - Impacto Arena: captura masiva de Talento → recálculo.
  - Calificación final materializada + vista "Mis resultados" (banda + pilares).
  - Servicios `ownership_flow`, `value_delivery_flow`, `final_flow` añadidos. **39 pruebas en verde** + smoke E2E de los 3 pilares (final 2.92 “Cumple parcial” para un MID, verificado a mano).
- **Pendiente:** Fase 6 (Mi área del Lead, dashboard de avance de Talento, exportes, cierre de periodo), editor visual de cuestionarios y pantallas admin propias de Talento (hoy vía Django admin), y **deploy a Vercel (requiere credenciales del usuario)**.

### 2026-06-11
- **Desplegado a producción:** Vercel (entrypoint `api/wsgi.py`) + **Neon Postgres**. Repo en GitHub `eduardoayalasoto/ArenaMesasDeTalento`. Resueltos: entrypoint Django, parseo de `requirements.txt`, `DATABASE_URL` inválido (fallback a `POSTGRES_URL`), `connect_timeout`. Neon migrado y sembrado.
- **Usuarios reales:** import desde `docs/Modelos/usuarios.csv` (`import_csv_users`); deducción de área/nivel por puesto. Quitada la gente de Tecnología (salvo Óscar = Director). **2 directores** (Héctor, Óscar). UX→MID. Todos con `Arena2026!` y **sin cambio forzado**. 57 usuarios.
- **Pantallas de alta propias de Talento:** crear **usuario** (`/cuenta/usuarios/nuevo/`) y **periodo** (`/catalogo/periodos/nuevo/`). (Proyectos ya tenían alta.)
- **UX/branding:** tema **azul marino**; fuentes **Lato + Ubuntu**; **Lucide** en todo; logo de Arena en nav y login; favicon **user-star** blanco; toasts arriba-derecha; perfil con tabs (foto + contraseña, nombre editable); informe estilo slide; comentario de Impacto Arena al final; login rediseñado (sin ícono/“Arena Analytics”, logo grande).
- **Mejoras de error handling/UX:** modal de confirmación al cerrar Ownership, anti-doble-envío, buscador+paginación en Mesa de Talento, recordatorios por correo (comando), logging + Sentry opcional, switch de cambio de contraseña forzado.
- Creado **`docs/CONTEXTO_Sistema.md`** (referencia rápida del sistema).
- **Fix foto en BD:** la foto se guarda en `User.photo_data` (BinaryField) y se sirve en `/cuenta/foto/<id>/`, porque el FS de Vercel es de solo lectura (resuelto el 500 al subir foto/guardar contraseña).
- **Docs reorganizados:** índice `docs/README.md`; deduplicación de deploy (CONTEXTO apunta a `Deploy_Vercel.md`).

### 2026-06-12
- **BD limpiada:** eliminados proyectos, membresías y evaluaciones existentes; conservados usuarios, periodos, catálogos y cuestionarios.
- **Modelo `Project` ampliado** (`0002_historicalproject_kickoff_and_more`): añadidos `responsable` (FK User, PROTECT, null/blank), `kickoff` (DateField), `target_close` (DateField), `status` (ON_TRACK/DELAYED). Migración aplicada a Neon. Editables en la pantalla de edición de proyecto; `ProjectForm` y template actualizados. Tests: `test_project_extra_fields.py` (3 pruebas).
- **Comandos `import_projects` + `import_memberships`** (`apps/core/management/commands/`): leen `docs/Modelos/Quien evalua a quien Analítica 1er S 2026.xlsx` (openpyxl). Idempotentes, soportan `--dry-run`. Servicio `apps/core/services/imports.py` con `normalize_name`, `build_user_index`, `resolve_user`, `resolve_or_create_user`, `to_date`. Tests: `test_imports_helpers.py` (11 pruebas), `test_import_commands.py` (7 pruebas).
- **Importación real a Neon:** 3 usuarios nuevos creados (cpalacio@, crodriguez@, arturo.carranza@); **17 proyectos** y **71 membresías** importados. Corrección post-import: 3 proyectos sin responsable resueltos manualmente (Oscar Nafarrate — nombre corto en el xlsx no empató).
- **Corrección de membresías (`import_memberships` v2):** el comando inicial leía la hoja `Proyectos` con fill-down, lo que atribuía evaluadores y leads como integrantes del equipo. Reescrito para leer la hoja **`HC Total`**: cada fila es una persona, las columnas `Proyecto N` determinan el equipo (columnas `Evaluador N` se ignoran). Agrega **sincronización bidireccional**: crea faltantes y elimina membresías en BD que ya no están en el xlsx. Matching por correo (strip para tolerar `\xa0`/espacios). Aplicado a Neon: **29 membresías incorrectas eliminadas**; quedaron 71 correctas.
- **Suite de pruebas:** 66 en verde.

### 2026-06-16
- **Ownership multi-evaluador:** reemplazado el campo `validator` (FK único) por el modelo `OwnershipEvaluator` (evaluation, user, is_primary, added_at). Migración `0002` con data migration de `validator` → `OwnershipEvaluator`. Servicios: `add_evaluator`, `remove_evaluator`, `set_primary_evaluator`. El colaborador gestiona la lista desde `ownership_fill` mientras la evaluación esté abierta. Cola de validación unificada para primario y secundario (mismos permisos). UI: badges Primario/Secundario, formularios add/remove inline. Correos de confirmación eliminados. 11 pruebas nuevas → **168 en verde**.
- **Sync de template Ownership:** si el área/nivel del colaborador cambiaron después de crear la evaluación (BORRADOR), `sync_evaluation_template` detecta el desajuste al entrar a la vista, actualiza el template y borra respuestas previas (que pertenecían al template anterior). El usuario ve un aviso explicativo y el cuestionario correcto. Solo aplica a borradores.

### 2026-06-17
- **Bug crítico en user_admin corregido:** al guardar con un filtro activo (ej. buscar "alain"), el POST solo contenía los campos del usuario visible, pero el loop iteraba todos los usuarios y asignaba `area=None`/`level=None` a los demás. Fix: el loop ahora hace `continue` para usuarios cuyo campo `area-{id}` no está en el POST. Como consecuencia, también se restauraron los datos de 57 usuarios con `import_csv_users --skip-password` (nuevo flag que actualiza solo área/nivel/rol sin resetear contraseñas ni fotos).
- **Reset de contraseña individual desde Usuarios:** endpoint `POST /cuenta/usuarios/<pk>/reset-password/` (solo Talento/admin) que restablece la contraseña a `Arena2026!` y activa `must_change_password=True`. Responde como fragment htmx: reemplaza el botón con un badge verde "Reseteada" sin recargar la página. Agrega confirmación (`hx-confirm`) antes de ejecutar.
- **UX de `/cuenta/usuarios/`:** selects con `appearance-none` + ícono `chevron-down` de Lucide (elimina la flecha nativa del navegador); etiquetas vacías descriptivas ("— Sin área —"); hover en filas.

### 2026-06-11 (durante pruebas con Talento)
- **Reapertura de Ownership (RN-06):** botón **"Reabrir"** (con modal) en la evaluación cerrada, visible solo para Talento/admin → `ENVIADA→BORRADOR` y **recálculo de la final**. Vistas `ownership_reopen` + URL `ownership/<pk>/reabrir/`; el servicio `reopen_ownership_evaluation` ahora recalcula. Antes el texto de ayuda prometía algo sin botón.
- **Impacto Arena con autoguardado:** la tabla **trae datos de la BD** y guarda **cada campo al instante** (calificación + notas), con indicador por fila *Guardando/Guardado/Revisa* y recálculo de la final por persona. Endpoint `arena_impact_autosave` + URL; validación 1–4 en servidor; ahora **sí se puede limpiar un campo** y capturar por sesiones sin perder nada (elimina el riesgo de "lote" reportado).
- **Pruebas:** +5 (recálculo al reabrir; autosave guarda/recalcula, rechaza fuera de rango, bloquea no-admin, render de la tabla). **45 en verde.**
- **Snapshot:** `backups/snapshot_2026-06-11_post-altas.json` (62 usuarios, 967 objetos) tras altas nuevas de Talento.
