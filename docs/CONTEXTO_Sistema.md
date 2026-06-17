# Contexto del Sistema — Mesa de Talento (Arena Analytics)

> Documento de referencia rápida para retomar el proyecto sin leer todo el código.
> Última actualización: 2026-06-17.

## 1. Qué es
Webapp interna del **Modelo de Desempeño Analítica 2026**. Cada colaborador se evalúa por **3 pilares** (escala 1–4): **Ownership**, **Entrega de Valor** e **Impacto Arena**. La **calificación final** es el promedio **ponderado por nivel** de los 3 pilares. Reglas de negocio en `docs/KB_Modelo_Desempeno_2026.md` (RN-xx).

## 2. Stack y cómo correr
- **Django 6** + Python (local 3.14 / Vercel 3.12). UI: plantillas Django + **Tailwind v4** (CSS compilado), **Alpine.js**, **htmx**, **Lucide** (iconos). Todo **vendorizado en `static/vendor/`** (sin CDN).
- **BD:** SQLite en local · **Postgres (Neon)** en producción.
- **Correr local:**
  ```powershell
  $env:PYTHONIOENCODING='utf-8'
  .\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
  ```
  - Login local: `admin@arena-analytics.com` / `Arena2026!`.
  - **Las plantillas NO se recargan en caliente** en este entorno → reinicia el server tras editar templates.
- **Compilar CSS** (tras editar plantillas/`static/src/input.css`): `.\build_css.ps1` (usa `tailwindcss.exe`; borra `static/css` antes por un bug EEXIST en Windows/OneDrive).
- **Pruebas:** `.\.venv\Scripts\python.exe -m pytest` (40 en verde).

## 3. Estructura (apps)
```
config/            settings, urls, wsgi (DJANGO_SETTINGS_MODULE=config.settings)
api/wsgi.py        entrypoint de Vercel (get_wsgi_application directo)
apps/
  accounts/        User custom (email), perfil, alta/admin de usuarios
  catalog/         Area, SeniorityLevel, PillarWeight, EvaluationPeriod, Project, ProjectMembership + pantallas
  questionnaires/  Template, Section, Question, ScaleOption + editor/versionado
  evaluations/     OwnershipEvaluation, OwnershipAnswer, ValueDeliveryEvaluation, ArenaImpactScore, FinalScore + flujos
  dashboards/      tablero (=resultados), Mi área, Mesa de Talento, avance, exportes, ayuda
  core/            services/ (lógica), middleware, context_processors, management/commands (seed*), text, templatetags
templates/         base.html + partials/ + por app
static/            src/input.css, css/app.css (compilado), vendor/ (lucide/alpine/htmx), img/ (logo, favicon)
fixtures/          questionnaires/*.yaml, users.yaml
docs/              KB, plan, progreso, este contexto, Deploy_Vercel, usuarios.csv
```

## 4. Modelo de datos (resumen)
- **User** (`accounts`): `email` (login), `full_name`, `area`→Area, `level`→SeniorityLevel, `role` (COLABORADOR/TALENTO/DIRECTOR), `photo` (obligatoria, se recorta a 400×400), `must_change_password`. Propiedades derivadas: `is_lead` (level.code==LEAD), `is_talento`, `is_director`, `is_admin` (superuser o talento), `leads_projects`.
- **catalog:** `Area` (ID/CD/PM/UXUI), `SeniorityLevel` (JR/MID/SNR/LEAD), `PillarWeight` (pesos por nivel, suman 1.00), `EvaluationPeriod` (PLANEADO/ABIERTO/CERRADO), `Project` (lead, responsable FK, kickoff, target_close, status ON_TRACK/DELAYED, duration_type FINITO/INDEFINIDO), `ProjectMembership`. Editables desde la pantalla de proyecto en Talento.
- **questionnaires:** `QuestionnaireTemplate` (kind OWNERSHIP/VALUE_DELIVERY, area, level, version, status BORRADOR/PUBLICADO/ARCHIVADO; solo 1 PUBLICADO por kind/area/level) → `Section` → `Question` (SCALE/TEXT_LONG) → `ScaleOption`.
- **evaluations:**
  - `OwnershipEvaluation` (user×project×period, `template`, `status` BORRADOR→ENVIADA(=cerrada), strengths/opportunities/comments, score) → `OwnershipAnswer` (value 1–4 o is_na). Los evaluadores ya **no** son un FK directo: se gestionan vía `OwnershipEvaluator` (ver abajo).
  - `OwnershipEvaluator` (migración `0002`): relación N:N entre evaluación y usuarios evaluadores. Campos: `evaluation`, `user`, `is_primary` (bool), `added_at`. Cualquier evaluador —primario o secundario— tiene los mismos permisos: editar respuestas, complementar Fortalezas/Oportunidades y cerrar. El colaborador gestiona la lista mientras la evaluación esté abierta.
  - `ValueDeliveryEvaluation` (project×period, evaluator/validated_by, status BORRADOR→EN_VALIDACION→VALIDADA, criterios, score).
  - `ArenaImpactScore` (user×period, score, notes, captured_by).
  - `FinalScore` (materializado: pilares, final_score, band, is_complete).

## 5. Roles, permisos y reglas clave
- **Roles:** Colaborador, Talento (admin), Director. **Lead** se deriva del nivel (LEAD). **Evaluador** se deriva de ser `validator` de alguna evaluación (no del liderazgo).
- **Visibilidad** (`core/services/permissions.py`): colaborador → solo él; lead → su área; Talento/Director/superuser → todos. Filtrado a nivel queryset.
- **Escala** (RN-03): 1 No cumple · 2 Cumple parcial · 3 Cumple · 4 Excede · N/A (se excluye del promedio).
- **Ponderación por nivel** (RN-19): JR 60/20/20 · MID 50/25/25 · SNR 40/30/30 · LEAD 30/35/35 (Ownership/EV/Impacto).
- **Bandas** (RN-20): ≥3.50 Excede · 3.00–3.49 Cumple · 2.00–2.99 Cumple parcial · <2.00 No cumple.

## 6. Flujos principales
- **Ownership:** el colaborador inicia su evaluación y **elige evaluador** (cualquiera de Arena) → captura respuestas (autosave, promedio en vivo). El **evaluador** entra a *Validación de Ownership*, complementa **Fortalezas/Oportunidades/Comentarios** y hace **Guardar y cerrar** (modal de confirmación) → queda **inmutable** y se calcula el score. El evaluado puede cambiar de evaluador solo mientras esté abierta. Vistas **Ver** y **Editar** separadas. **Reapertura (RN-06):** solo Talento/admin puede **Reabrir** una evaluación cerrada (botón con modal en la vista) → vuelve a borrador y recalcula la final.
- **Entrega de Valor:** el **líder del proyecto** captura (criterio de tiempo según FINITO/INDEFINIDO) → **Director** valida o regresa con comentario → recalcula finales del equipo.
- **Impacto Arena:** **Talento** captura en tabla con **autoguardado por campo** (carga los datos de la BD; guarda calificación/nota al salir del campo; indicador por fila) → recalcula finales. Mismo patrón que el autosave de Ownership.
- **Calificación final:** `FinalScore` materializado; se recalcula al validar EV / guardar Impacto / abrir resultados.

## 7. Capa de servicios (`apps/core/services/`)
`scoring.py` (promedios, ponderación, bandas) · `permissions.py` (visibilidad/capacidades) · `ownership_flow.py` (crear/cerrar; `add_evaluator`/`remove_evaluator`/`set_primary_evaluator`; `sync_evaluation_template` — detecta desajuste área/nivel y actualiza el template en evaluaciones BORRADOR) · `value_delivery_flow.py` · `final_flow.py` (recálculo materializado) · `questionnaire_editor.py` (versionado). **Toda la lógica vive aquí, no en vistas/plantillas.** 168 pruebas en `apps/core/tests/`.

## 8. Pantallas por rol (URLs)
- **Todos:** `/` Mi tablero (= informe de resultados), `/cuenta/perfil/` (foto + contraseña, en tabs), `/ayuda/` (tabs por rol + “El modelo”). Campana = pendientes.
- **Colaborador:** `/evaluaciones/ownership/` (lista) → iniciar (elige evaluador) → editar/ver.
- **Evaluador:** `/evaluaciones/ownership/validacion/` (solo si tiene validaciones asignadas).
- **Líder:** `/evaluaciones/entrega-valor/` (captura).
- **Director:** `/evaluaciones/entrega-valor/validar/`, `/mesa-talento/`.
- **Talento (admin):** Impacto Arena (`/evaluaciones/impacto-arena/`, autoguardado), **reabrir** evaluaciones de Ownership cerradas (botón en la vista), Avance (`/avance-periodo/`), **Mesa de Talento** (`/mesa-talento/`, con buscador/paginación; “Ver” abre informe en nueva pestaña), **Usuarios** (`/cuenta/usuarios/` lista+asignación masiva con búsqueda; botón **”Resetear”** por fila para restablecer contraseña a `Arena2026!` vía htmx sin recargar, activa `must_change_password`; POST `/cuenta/usuarios/<pk>/reset-password/`; `/cuenta/usuarios/nuevo/` alta), **Proyectos** (`/catalogo/proyectos/` + alta/edición + equipo), **Periodos** (`/catalogo/periodos/` + `/catalogo/periodos/nuevo/`), **Cuestionarios** (`/cuestionarios/admin/` editar/versionar).

## 9. Seed y comandos (`manage.py`)
- `seed_all` = `seed_superuser` + `seed_catalogs` + `seed_users` + `seed_questionnaires` (+ `seed_demo` con `--demo`).
- `import_csv_users [--skip-password]` — crea/actualiza usuarios desde `docs/Modelos/usuarios.csv` (deduce área/nivel del puesto, fija contraseña, `must_change_password=False`). Con `--skip-password`, actualiza solo área/nivel/rol sin tocar contraseñas ni fotos de usuarios existentes (útil para restaurar datos).
- `import_projects [--path xlsx] [--dry-run]` — lee hoja **'Proyectos Dueños'** del xlsx de Talento; idempotente por nombre; crea/actualiza lead, responsable, kickoff, target_close, status, duration_type. Crea usuarios faltantes (3 predefinidos en `imports.py`).
- `import_memberships [--path xlsx] [--dry-run]` — lee hoja **'HC Total'** del xlsx; **cada fila = una persona**, columnas `Proyecto N` = sus proyectos (columnas `Evaluador N` se ignoran). Sincroniza: crea membresías faltantes **y elimina** las que ya no están en el xlsx. Idempotente. La clave de matching es el correo (strip para tolerar espacios/`\xa0`).
- `require_password_change --all [--temp-password X] [--clear]` — switch de cambio de contraseña forzado.
- `send_pending_reminders [--dry-run]` — correos de pendientes (agendable).

## 10. Despliegue (producción)
Desplegado en **Vercel** (entrypoint `api/wsgi.py`, builder Django, sin `vercel.json`) + **Neon Postgres**. Repo `github.com/eduardoayalasoto/ArenaMesasDeTalento` (push a `main` → auto‑deploy). Estáticos por WhiteNoise (`WHITENOISE_USE_FINDERS`, sin `collectstatic`). La app lee `DATABASE_URL` (o cae a `POSTGRES_URL`).

➡️ **Variables de entorno, migraciones y respaldos/restauración: ver `Deploy_Vercel.md`** (y `.env.vercel`). No se duplican aquí para evitar inconsistencias.

## 11. Peculiaridades del entorno (no obvias)
- **No hay Node/npm.** Tailwind se compila con `tailwindcss.exe` (standalone). `build_css.ps1` borra `static/css` antes de compilar (bug EEXIST en OneDrive). El `<link>` del CSS lleva `?v={{ asset_version }}` (mtime) para cache-busting.
- **Consola Windows = cp1252:** evitar glifos no-latin en salidas; correr con `PYTHONIOENCODING=utf-8`.
- **Plantillas no recargan en caliente** → reiniciar runserver tras editar templates.
- **Fuentes:** Lato (cuerpo) + Ubuntu (títulos, clase `font-display`). Tema **azul marino** (token `arena`).
- **Foto:** obligatoria (middleware `PhotoRequiredMiddleware`); se procesa a 400×400 y se **guarda en la BD** (`User.photo_data`, porque el FS de Vercel es de solo lectura), servida en `/cuenta/foto/<id>/`; sin foto → icono Lucide.

## 12. Estado actual
- **Fases 0–7 funcionales y desplegadas** (Vercel + Neon). **65 usuarios reales** (todos `Arena2026!`, sin cambio forzado; 3 altas el 2026-06-12: cpalacio@, crodriguez@, arturo.carranza@), 2 directores (Héctor, Óscar), 17 cuestionarios/419 preguntas, periodo 2026-S1 ABIERTO. En **pruebas con Talento**.
- **17 proyectos y 71 membresías** importados y sincronizados desde `docs/Modelos/Quien evalua a quien Analítica 1er S 2026.xlsx` (2026-06-12). Modelo `Project` ampliado con responsable, kickoff, target_close, status (editables en la pantalla de proyecto). Fuente canónica de membresías: hoja **'HC Total'** del xlsx (columnas `Proyecto N`).
- **Ownership multi-evaluador (2026-06-16):** modelo `OwnershipEvaluator` (migración `0002`); el colaborador puede agregar evaluadores primario y secundarios. Correos eliminados. 168 pruebas en verde.
- **Sync de template Ownership (2026-06-16):** si el colaborador cambió de área/nivel después de iniciar su evaluación en BORRADOR, al entrar se detecta el desajuste, se actualiza el template y se limpian respuestas previas (aviso visible). Solo aplica a borradores.
- **Bug crítico corregido (2026-06-17):** la vista masiva de usuarios (`/cuenta/usuarios/`) borraba área y nivel de todos los usuarios si se guardaba con un filtro activo (porque el loop del POST cubría todos los usuarios, no solo los visibles). Fix: el loop ahora omite usuarios cuyo campo no llegó en el POST.
- **Reset de contraseña desde Usuarios (2026-06-17):** botón "Resetear" por fila en `/cuenta/usuarios/`; restablece a `Arena2026!` y activa `must_change_password`; responde como fragment htmx (sin recarga).
- **Pendiente/opcional:** compilar Tailwind en el build de Vercel (hoy se versiona el CSS); recordatorios agendados (Cron); migrar fotos a almacenamiento de objetos si crecen mucho (hoy en BD).
