# CLAUDE.md — arena-talento (Mesa de Talento de Arena Analytics)

**Este proyecto es independiente.** El `CLAUDE.md` de la carpeta padre (`ArenaOS/`) describe
**ArenaOps** (apps projects/tasks/meetings, roles manager/backoffice, `apps/<app>/services.py`) y
**no aplica aquí**, salvo sus reglas genéricas (htmx sobre `fetch`, Django Forms, `transaction.atomic`,
Lucide, sin emojis).

## Documentos que mandan (en este orden)
1. `DESIGN_SYSTEM.md` — **ley para todo cambio visual** (daisyUI 5, tema `arena`, componentes, navbar).
2. `docs/CONTEXTO_Sistema.md` — panorama del sistema (apps, modelos, flujos, URLs, despliegue).
3. `docs/PLAN_MIGRACION_DISENO.md` — migración del frontend al sistema de arena-crm (por fases).
4. `docs/KB_Modelo_Desempeno_2026.md` — reglas de negocio RN-xx.
5. `specs/NNN-*/` — specs de speckit (spec → plan → tasks).

## Reglas de código
- **Lógica de negocio en `apps/core/services/<dominio>.py`**, nunca en views ni plantillas.
- **Permisos = matriz de perfiles (spec 005).** Toda view lleva `@login_required` + `@requires("clave")`
  (`apps/access/decorators.py`) y su clave existe en `apps/access/registry.py` con la ruta listada,
  más su fila en `apps/access/seed.py` y `apps/access/legacy.py`. Nunca decidir por rol
  (`is_admin`, `is_director`, `is_lead`): usar `apps.access.services.has/scope` o la fachada
  `apps/core/services/permissions.py`. `is_lead` solo define el TIPO de evaluación.
  `apps/core/tests/test_access_coverage.py` debe quedar en verde.
- **Menú = datos**: `apps/core/navigation.py` (4 categorías: Inicio · Arena Learn · Mesa de Talento ·
  Administración). Ninguna condición de menú en plantillas.
- Django Forms para todo POST; `transaction.atomic` al escribir 2+ modelos;
  `select_related`/`prefetch_related` en listados.
- **Pruebas compactas por escenario** (pytest contra Neon, `--reuse-db`, nunca en paralelo); usuarios
  de prueba con `password=None`. No cambiar la infraestructura de pruebas a SQLite.

## Entorno
- Windows + OneDrive, **sin Node**. CSS: `.\build_css.ps1` (tailwindcss.exe v4 standalone +
  daisyUI vendorizado en `static/vendor/daisyui/`). El CSS compilado se versiona.
- Python: `.\.venv\Scripts\python.exe` (la `.venv` se creó en otra ruta: usar `python -m pytest`).
- Consola cp1252: `PYTHONIOENCODING=utf-8`.
- Producción: Vercel (push a `main` = deploy, https://arena-mesasdetalento.vercel.app) + Neon
  Postgres; **Vercel no corre migraciones**: aplicarlas con la URL unpooled de `docs/neon.md`
  antes del push.
- **BD compartida por esquemas (desde 2026-10-08):** Neon `db-arena`/`neondb` aloja varios sistemas,
  uno por esquema. Esta app vive en **`"talento-app"`** (NO en `public`, que queda vacío);
  arena-crm vive en `"crm-app"` — nunca tocar ese esquema desde aquí. `config/settings.py` fija
  `options=-c search_path="talento-app",public` y usa el host DIRECTO de Neon (el pooler ignora
  `options`); `DB_SCHEMA` lo controla (vacío = comportamiento anterior). `pg_dump`/migraciones
  siempre por la conexión directa.
- Favicon: `static/img/favicon.svg` = `sprout` de Lucide sobre el degradado naranja de "talento"
  (`talento-300` #FFB45A → `talento-600` #F2711C).
- UI y textos en español (México); código en inglés.

## Agentes y skills del proyecto
`.claude/agents/frontend-web-engineer.md` (implementa frontend), `frontend-auditor.md` (audita,
CUMPLE/NO CUMPLE), `django-backend-engineer.md` (backend); skills `daisyui`, `design-system`,
`django-architecture`, `django-patterns`, speckit. Hook `design_kit_reminder.py` al editar plantillas/CSS.
