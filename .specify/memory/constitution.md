<!--
Sync Impact Report
- Version: (plantilla vacía) → 1.0.0 (ratificación inicial, 2026-10-28)
- Principios añadidos: I–VII (todos nuevos; antes el archivo era la plantilla de Spec Kit sin llenar)
- Secciones añadidas: Entorno y Despliegue, Flujo de Trabajo, Governance
- Fuentes: CLAUDE.md, DESIGN_SYSTEM.md, docs/CONTEXTO_Sistema.md, memoria del proyecto y
  decisiones de las specs 001–007. No contradice ninguno: los codifica.
- Plantillas: plan-template.md usa "Constitution Check" genérico → compatible sin cambios.
-->

# Arena Talento Constitution

Mesa de Talento de Arena Analytics (evaluación de desempeño, Arena Learn). Este documento es la
fuente de principios que `/speckit-plan` y `/speckit-analyze` verifican. Ante un conflicto,
gana este documento; luego `CLAUDE.md`, luego `DESIGN_SYSTEM.md`.

## Core Principles

### I. Permisos = Matriz de Perfiles (NON-NEGOTIABLE)
- Toda vista lleva `@login_required` + `@requires("clave")` (`apps/access/decorators.py`); la clave
  existe en `apps/access/registry.py` con su ruta, más su fila en `apps/access/seed.py` y
  `apps/access/legacy.py`.
- **Nunca** decidir por rol (`is_admin`, `is_director`, `is_lead`): usar `apps.access.services.has/scope`
  o la fachada `apps/core/services/permissions.py`. `is_lead` solo define el TIPO de evaluación.
- `apps/core/tests/test_access_coverage.py` en verde es condición de entrega.
- Fail-closed: sin perfil o sin permiso, se niega; jamás se defaultea a privilegiado.
**Por qué**: la spec 005 sustituyó reglas por rol dispersas por una matriz auditable; cualquier
atajo por rol reabre accesos que Talento ya cerró.

### II. Lógica en Servicios, Vistas Delgadas
- Reglas de negocio en `apps/core/services/<dominio>.py`; nunca en vistas ni plantillas.
- Vista = validar entrada (Django Forms para todo POST) → llamar servicio → renderizar.
- `transaction.atomic` en toda escritura a 2+ modelos; `select_related`/`prefetch_related` en listados.

### III. Integridad de las Evaluaciones (NON-NEGOTIABLE)
- Una evaluación queda ligada a la versión de cuestionario con la que se creó; publicar una versión
  nueva **nunca** mueve ni borra respuestas existentes (spec 007, FR-001).
- Los periodos cerrados congelan datos; corregirlos exige el permiso de corrección y un motivo
  (specs 002/003).
- Los cuestionarios son datos versionados (Borrador → Publicado → Archivado; uno publicado por
  puesto) y se cargan con importaciones idempotentes y revisables (YAML versionado en git).
- Un proyecto cerrado sale de "iniciar evaluación" pero su histórico sigue consultable.

### IV. Sistema de Diseño Único con arena-crm
- `DESIGN_SYSTEM.md` es ley para todo cambio visual: daisyUI 5 + tema `arena` (paleta oficial de
  Arena), tokens semánticos, Lucide, Quicksand, contraste AA en ambos temas.
- Menú = datos (`apps/core/navigation.py`); breadcrumb automático en todas las pantallas.
- `components/_nav_menu.html` y `components/_breadcrumb.html` son el mismo archivo que en
  arena-crm (la prueba de paridad lo verifica).
- htmx para interacción con el servidor; Alpine solo estado local; sin `fetch` en Alpine; diálogos
  = modal; sin emojis, `style=` inline ni `alert()/confirm()` en código nuevo.

### V. Pruebas con Cada Cambio
- pytest + datos mínimos; **pruebas compactas por escenario** (pocas funciones que encadenan un
  flujo); usuarios de prueba con `password=None`.
- Local: Postgres de pruebas en Neon (`--reuse-db`, nunca en paralelo), solo los archivos del
  cambio; **una corrida ≤ 3 min**. La suite completa la corre CI en Postgres local en cada push.
- No cambiar la infraestructura de pruebas a SQLite.

### VI. Datos de Producción con Cuidado
- Toda migración es aditiva o tiene plan; se aplica a Neon (URL unpooled) **antes** del push
  (Vercel no corre migraciones). Un cambio que depende de código nuevo se publica en orden
  migrar → desplegar → mover datos.
- Cambios de datos: simulación (`--dry-run` o transacción revertida) antes de la ejecución real,
  conteos antes/después y registro en la spec o en `docs/CONTEXTO_Sistema.md`.
- Esquema propio `"talento-app"` en la BD compartida; nunca tocar `"crm-app"`.
- Credenciales nunca en el repo ni en documentos versionados.

### VII. Español de México, Código en Inglés
UI, textos, mensajes y documentación en español (México), con acentos; identificadores de código
en inglés.

## Entorno y Despliegue
Windows + OneDrive, sin Node. CSS con `.\build_css.ps1` (Tailwind v4 standalone + daisyUI
vendorizado); el CSS compilado se versiona. Producción: Vercel (push a `main` = deploy) + Neon.
CI (GitHub Actions, `.github/workflows/tests.yml`) corre la suite completa en cada push.

## Flujo de Trabajo
- Features no triviales con Spec Kit: specify → (auditoría adversarial contra el código) → plan →
  tasks → analyze → implement. Si `analyze` encuentra algo real, se corrige en tasks/research y se
  continúa; los hallazgos quedan en la spec.
- Entrega: pruebas del cambio en verde → commit → push → verificación del deploy.
- Cambios de UI pasan por el agente `frontend-auditor` (CUMPLE / NO CUMPLE) antes del commit.

## Governance
Esta constitución prevalece sobre otras prácticas. Enmiendas: editar este archivo con su Sync
Impact Report, subir la versión (MAJOR = principio eliminado o redefinido; MINOR = principio o
sección nueva; PATCH = redacción) y reflejar el cambio en `CLAUDE.md` si afecta reglas de código.
Todo plan incluye un "Constitution Check" contra los principios I–VII.

**Version**: 1.0.0 | **Ratified**: 2026-10-28 | **Last Amended**: 2026-10-28
