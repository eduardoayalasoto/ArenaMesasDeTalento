# Contexto del Sistema — Mesa de Talento (Arena Analytics)

> Documento de referencia rápida para retomar el proyecto sin leer todo el código.
> Última actualización: 2026-06-11.

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
- **catalog:** `Area` (ID/CD/PM/UXUI), `SeniorityLevel` (JR/MID/SNR/LEAD), `PillarWeight` (pesos por nivel, suman 1.00), `EvaluationPeriod` (PLANEADO/ABIERTO/CERRADO), `Project` (lead, duration_type FINITO/INDEFINIDO), `ProjectMembership`.
- **questionnaires:** `QuestionnaireTemplate` (kind OWNERSHIP/VALUE_DELIVERY, area, level, version, status BORRADOR/PUBLICADO/ARCHIVADO; solo 1 PUBLICADO por kind/area/level) → `Section` → `Question` (SCALE/TEXT_LONG) → `ScaleOption`.
- **evaluations:**
  - `OwnershipEvaluation` (user×project×period, `template`, `validator`=evaluador elegido, `status` BORRADOR→ENVIADA(=cerrada), strengths/opportunities/comments, score) → `OwnershipAnswer` (value 1–4 o is_na).
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
- **Ownership:** el colaborador inicia su evaluación y **elige evaluador** (cualquiera de Arena) → captura respuestas (autosave, promedio en vivo). El **evaluador** entra a *Validación de Ownership*, complementa **Fortalezas/Oportunidades/Comentarios** y hace **Guardar y cerrar** (modal de confirmación) → queda **inmutable** y se calcula el score. El evaluado puede cambiar de evaluador solo mientras esté abierta. Vistas **Ver** y **Editar** separadas.
- **Entrega de Valor:** el **líder del proyecto** captura (criterio de tiempo según FINITO/INDEFINIDO) → **Director** valida o regresa con comentario → recalcula finales del equipo.
- **Impacto Arena:** **Talento** captura en tabla masiva → recalcula finales.
- **Calificación final:** `FinalScore` materializado; se recalcula al validar EV / guardar Impacto / abrir resultados.

## 7. Capa de servicios (`apps/core/services/`)
`scoring.py` (promedios, ponderación, bandas) · `permissions.py` (visibilidad/capacidades) · `ownership_flow.py` (crear/cerrar) · `value_delivery_flow.py` · `final_flow.py` (recálculo materializado) · `questionnaire_editor.py` (versionado). **Toda la lógica vive aquí, no en vistas/plantillas.** 40 pruebas en `apps/core/tests/`.

## 8. Pantallas por rol (URLs)
- **Todos:** `/` Mi tablero (= informe de resultados), `/cuenta/perfil/` (foto + contraseña, en tabs), `/ayuda/` (tabs por rol + “El modelo”). Campana = pendientes.
- **Colaborador:** `/evaluaciones/ownership/` (lista) → iniciar (elige evaluador) → editar/ver.
- **Evaluador:** `/evaluaciones/ownership/validacion/` (solo si tiene validaciones asignadas).
- **Líder:** `/evaluaciones/entrega-valor/` (captura).
- **Director:** `/evaluaciones/entrega-valor/validar/`, `/mesa-talento/`.
- **Talento (admin):** Impacto Arena (`/evaluaciones/impacto-arena/`), Avance (`/avance-periodo/`), **Mesa de Talento** (`/mesa-talento/`, con buscador/paginación; “Ver” abre informe en nueva pestaña), **Usuarios** (`/cuenta/usuarios/` lista+asignación; `/cuenta/usuarios/nuevo/` alta), **Proyectos** (`/catalogo/proyectos/` + alta/edición + equipo), **Periodos** (`/catalogo/periodos/` + `/catalogo/periodos/nuevo/`), **Cuestionarios** (`/cuestionarios/admin/` editar/versionar).

## 9. Seed y comandos (`manage.py`)
- `seed_all` = `seed_superuser` + `seed_catalogs` + `seed_users` + `seed_questionnaires` (+ `seed_demo` con `--demo`).
- `import_csv_users` — crea/actualiza usuarios desde `docs/Modelos/usuarios.csv` (deduce área/nivel del puesto, fija contraseña, `must_change_password=False`).
- `require_password_change --all [--temp-password X] [--clear]` — switch de cambio de contraseña forzado.
- `send_pending_reminders [--dry-run]` — correos de pendientes (agendable).

## 10. Despliegue (producción)
- **Repo:** github.com/eduardoayalasoto/ArenaMesasDeTalento (push → auto-deploy en Vercel).
- **Vercel:** entrypoint `api/wsgi.py` (builder Django, zero-config; **sin `vercel.json`**). Estáticos por WhiteNoise (`WHITENOISE_USE_FINDERS`, sin `collectstatic`).
- **BD:** Neon Postgres. La app lee `DATABASE_URL` (o cae a `POSTGRES_URL` si es inválida). Ya migrada y sembrada.
- **Variables en Vercel** (ver `docs/Deploy_Vercel.md` y `.env.vercel`): `DATABASE_URL` (pooled), `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS=.vercel.app`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://*.vercel.app`.
- **Migrar contra prod (local):** exportar `DATABASE_URL` (unpooled de Neon) y `manage.py migrate`.

## 11. Peculiaridades del entorno (no obvias)
- **No hay Node/npm.** Tailwind se compila con `tailwindcss.exe` (standalone). `build_css.ps1` borra `static/css` antes de compilar (bug EEXIST en OneDrive). El `<link>` del CSS lleva `?v={{ asset_version }}` (mtime) para cache-busting.
- **Consola Windows = cp1252:** evitar glifos no-latin en salidas; correr con `PYTHONIOENCODING=utf-8`.
- **Plantillas no recargan en caliente** → reiniciar runserver tras editar templates.
- **Fuentes:** Lato (cuerpo) + Ubuntu (títulos, clase `font-display`). Tema **azul marino** (token `arena`).
- **Foto:** obligatoria (middleware `PhotoRequiredMiddleware` redirige a perfil); se procesa a círculo 400×400; sin foto → icono Lucide.

## 12. Estado actual
- **Fases 0–6 funcionales**; desplegado en Vercel+Neon. 57 usuarios reales (todos `Arena2026!`, sin cambio forzado), 2 directores (Héctor, Óscar), 17 cuestionarios/419 preguntas, periodo 2026-S1 ABIERTO.
- **Pendiente/opcional:** asignar proyectos/equipos reales; compilar Tailwind en el build de Vercel (hoy se versiona el CSS compilado); recordatorios agendados (Cron); endurecimiento final (Fase 7).
