# CLAUDE.md — arena-talento (Mesa de Talento de Arena Analytics)

**Este proyecto es independiente.** El `CLAUDE.md` de la carpeta padre (`ArenaOS/`) describe
**ArenaOps** (apps projects/tasks/meetings, roles manager/backoffice, `apps/<app>/services.py`) y
**no aplica aquí**, salvo sus reglas genéricas (htmx sobre `fetch`, Django Forms, `transaction.atomic`,
Lucide, sin emojis).

## Documentos que mandan (en este orden)
0. `.specify/memory/constitution.md` — principios I–VII (permisos, servicios, integridad de
   evaluaciones, diseño único con arena-crm, pruebas, datos de producción, idioma).
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
- **Menú = datos**: `apps/core/navigation.py` (6 categorías: Inicio · Arena Learn · Mesa de Talento ·
  Organización · Modelo de evaluación · Administración). Ninguna condición de menú en plantillas.
- Django Forms para todo POST; `transaction.atomic` al escribir 2+ modelos;
  `select_related`/`prefetch_related` en listados.
- **Pruebas compactas por escenario** (pytest contra Neon, `--reuse-db`, nunca en paralelo); usuarios
  de prueba con `password=None`. No cambiar la infraestructura de pruebas a SQLite.
  Local: `.\.venv\Scripts\python.exe scripts/pytest_changed.py [extra]` (tests modificados +
  guardas, ≤ 3 min). La **suite completa la corre CI** (`.github/workflows/tests.yml`, Postgres local
  del runner) en cada push a `main`: revisar que quede en verde (`gh run list`).

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

## Harness del agente
- Hooks (`.claude/settings.json`): `codegraph prompt-hook` (contexto), `design_kit_reminder.py`
  (aviso al editar plantillas/CSS) y **`stop_checks.py` (Stop, bloquea una vez)**: componente
  compartido distinto de arena-crm, CSS compilado más viejo que las plantillas, o `models.py` sin
  migración. Mismo script en arena-crm.
- Componentes **idénticos en ambos repos**: `templates/components/_nav_menu.html` y
  `_breadcrumb.html` (solo cambia la URL de inicio); `test_shared_components.py` lo verifica.

## Agentes y skills del proyecto
`.claude/agents/frontend-web-engineer.md` (implementa frontend), `frontend-auditor.md` (audita,
CUMPLE/NO CUMPLE), `django-backend-engineer.md` (backend); skills `daisyui`, `design-system`,
`django-architecture`, `django-patterns`, speckit. Hook `design_kit_reminder.py` al editar plantillas/CSS.

## Organigrama: Área → Posición → Nivel (opcional) — nov 2026
- **Vocabulario de la UI ≠ código:** «Área» = `catalog.Department` (Analítica, Consultoría; tiene Director); «Posición»
  = `catalog.Area` (Ingeniero de Datos, Analista, Gerente…; `User.area`); «Nivel» = `SeniorityLevel`, **opcional**;
  `catalog.Position` = combinación posición × nivel (nombre visible + ponderación de pilares; `level` nullable).
- «Lead / Gerente» y «Director» son marcas de la ficha (`User.is_lead_flag`, `is_director_flag`); `is_lead` ya no
  deriva del nivel. Los permisos siguen viniendo del perfil (spec 005).
- Cuestionario de Ownership ↔ persona por **coincidencia exacta** posición + nivel (`ownership_flow.resolve_ownership_template`).
- Preguntas: competencia (título) + bloque del catálogo (skills) + nivel de dominio objetivo N1–N4 + «pondera».
  Ponderación automática con enteros que suman 100 (`ownership_weights.auto_distribute`); la matriz de competencias
  se carga con `import_competency_matrix` (simula por defecto) y la migración de Consultoría fue `restructure_org`.
- **Todo texto visible dice «ponderación», nunca «peso»** (excepto tamaño de archivo y moneda).
- Pantallas de administración: búsqueda en vivo (htmx), filas de texto, «Ver y editar» en drawer, borrado con `_confirm`
  y bitácora (`UserAuditLog`, `CatalogAuditLog`). Patrón en `templates/catalog/org_list.html` y `accounts/user_admin.html`.
- **Botones de CRUD (regla dura):** Ver/Editar/Eliminar = solo ícono con tooltip, mismo tamaño
  (`components/_row_action.html`, `components/_confirm.html`); crear = «+ Nuevo/Nueva …» (`components/_create_button.html`).
  Detalle en `DESIGN_SYSTEM.md` §6.
- **Categorías de pregunta** = solo las 4 familias de la matriz (Persona, Proyecto, Cliente, Metodología y técnica) +
  «General»; `consolidate_categories` reclasifica por el título de la competencia. **Ponderación de pilares**: el catálogo
  siempre se edita; `FinalScore` guarda la ponderación aplicada y los periodos cerrados la conservan.
- **Seguridad HTTP:** `SecurityHeadersMiddleware` (CSP, Permissions-Policy, CORP) + HSTS 2 años, Referrer-Policy y
  X-Frame-Options en `settings`; la CSP conserva `unsafe-inline/unsafe-eval` por Alpine y `on*`/`hx-on` (para A+ estricta: build CSP de
  Alpine y nonces). **Editor de cuestionarios:** en modo automático (`ownership_weights.is_automatic`) editar preguntas recalcula el
  reparto solo; en manual avisa qué falta. Área «Desarrollo» (Director Héctor Rangel) con Gerente y Desarrollador·Snr.
- **360 al owner (spec 010, en producción):** informativa, NO alimenta ninguna calificación. `Project.three_sixty_enabled`; cuestionario tipo
  `THREE_SIXTY` (sección = dimensión con `Section.weight_pct`); `ThreeSixtyResponse/Answer` guardan `respondent` (POC) pero ninguna vista lo
  muestra; servicio `apps/core/services/three_sixty.py`; pantalla «Evaluaciones 360». Carga: `import_competency_matrix <xlsx> --360`.
- **Centro de ayuda contextual (spec 011):** botón `circle-help` en la barra (junto a la campana). `apps/core/services/help_center.py`
  decide las pestañas por permisos y relaciones y trae datos reales (ponderación de la persona, su cuestionario, evaluadores, organigrama);
  Talento ve solo guías de catálogos con el diagrama del organigrama. Al agregar una función nueva, agrega su guía en `templates/help/`.
- Pendiente: ponderación por proyecto de cada persona (ver memoria `talento-org-restructure`).
