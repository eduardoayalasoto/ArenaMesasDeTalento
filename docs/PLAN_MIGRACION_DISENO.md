# Plan de migración del frontend de Mesa de Talento al sistema de diseño de Arena (arena-crm)

**Fecha:** 2026-10-07 · **Estado:** propuesta para aprobación · **Referencia:** `../arena-crm/DESIGN_SYSTEM.md` (ley vigente en arena-crm, daisyUI 5 desde 2026-09-22).

## 1. Diagnóstico

### Mesa de Talento hoy
| Aspecto | Estado |
|---|---|
| Plantillas | 93 HTML. **Sin biblioteca de componentes**: solo 10 parciales sueltos (`partials/`) |
| CSS | `static/src/input.css` artesanal de 56 líneas: `.btn-*`, `.card`, `.input`, `.label`, `.badge` y `.nav-link` hechos con `@apply` |
| Botones / modales | 176 botones armados a mano con clases. Hay **5 modales copiados** (el patrón de `ownership_fill.html`) y diálogos con `confirm()` |
| Tema | Navy `#1e3a5f`, Lato + Ubuntu. **Sin dark mode** ni tokens semánticos |
| Iconos | `partials/icon.html` es una lista blanca de ~60 `elif`; se mezcla con `<i data-lucide>` directo. Usa `lucide.createIcons()` global |
| Menú | `context_processors.navigation`: hasta **20 entradas** en una sola lista plana. Talento ve **~14 ítems de primer nivel más 6 en "Catálogos"**, sin agrupación por intención. Cada spec nueva agrega ítems |
| Agentes / skills de diseño | Ninguno. Solo hay skills de speckit. Además, el `CLAUDE.md` del folder padre (ArenaOps) se carga aquí con reglas que no aplican |
| Calidad visual | No hay revisión ni lint de plantillas. Hay 6 `style=` inline |

### Qué tiene arena-crm y conviene adoptar
- **daisyUI 5.7.43 vendorizado**, que funciona con `tailwindcss.exe` standalone **sin Node** (probado): `@plugin` con ruta local al `.mjs`. **Ojo:** el specifier `"daisyui/theme"` no resuelve; hay que usar la ruta relativa.
- **Temas**: `arena` (claro, de marca) y `business` (oscuro), con **tokens semánticos** (`bg-base-100`, `text-base-content/60`, `bg-primary`). Prohíbe hex sueltos.
- **Biblioteca `templates/components/`** con API `{% include … with %}`: `_button`, `_icon_button`, `_form_field` (con `forms.field_classes()`), `_modal` (`<dialog>` nativo más `modals.js`), `_confirm`, `_table`, `_badge`, `_breadcrumb`, `_empty_state`, `_toast_container`, `_spinner` y `_avatar`. Más un **showcase** en `/dev/components/`.
- **JS mínimo y robusto**:
  - `icons.js`: `renderIcons(root)` incremental. **Prohíbe `createIcons()` global** por un bug de ciclo infinito con Alpine.
  - `modals.js`, `theme_toggle.js` y `htmx_csrf.js`.
  - Toasts por `HX-Trigger: {"toast": {...}}`.
- **Gobierno de diseño con IA**:
  - Agente `frontend-web-engineer`, que implementa invocando las skills `daisyui`, `frontend-design` y `ui-ux-pro-max`.
  - Agente `frontend-auditor`, que da un veredicto CUMPLE / NO CUMPLE.
  - Hook `design_kit_reminder.py`: un PreToolUse que recuerda el sistema al editar plantillas o CSS.
  - Skill oficial `daisyui` fijada en `skills-lock.json`.

### Qué NO copiar de arena-crm
- **El navbar con hamburguesa.** Tiene las rutas hardcodeadas en la plantilla, no filtra por permisos, marca el estado activo solo en 4 ítems y tiene HTML inválido (`<div>` dentro de `<ul>`). Talento necesita lo contrario: **menú como datos**, filtrado por la matriz de permisos (spec 005).
- **El bug de `_table.html`**: la paginación hace swap del `closest table` y deja el `<nav>` fuera, y el sort pierde la página y los filtros.
- **El `style=` inline de `_avatar.html`.**
- **El modo oscuro dual** (`.dark` + `data-theme`): Talento no tiene legado `dark:`, así que basta `data-theme`.
- **La escala tipográfica `text-sm` = 11 px**, que en el CRM ya generó quejas de legibilidad.
- **El E2E con puppeteer/Node**: choca con la regla "sin Node" de este entorno.
- **Los documentos contradictorios**: la constitución del CRM cita Flowbite, y el `DESIGN_KIT.md` de ArenaOS pide CDN.

## 2. Objetivo

Que Mesa de Talento y arena-crm se vean y se construyan igual:
- el mismo tema, tokens, componentes, JS y reglas;
- el mismo agente para implementar y auditar.

Además, Talento debe tener un **menú escalable**: agrupado por intención, derivado de la matriz de permisos y con buscador de pantallas. Todo esto **sin romper la operación** (hay un periodo abierto) y migrando módulo por módulo.

## 3. Arquitectura destino

### 3.1 Pipeline de CSS
- `static/vendor/daisyui/5.7.43/{daisyui.mjs, daisyui-theme.mjs}` y `static/vendor/VERSIONS.md`.
- `static/src/input.css` reescrito sobre el modelo de `arena-crm/styles/tailwind_input.css`:
  - `@plugin` daisyUI (ruta local) con los temas `arena` y `business --prefersdark`;
  - `@theme` con fuentes, escala tipográfica, sombras y transiciones;
  - `@layer base` con foco y `scrollbar-gutter`.
- `build_css.ps1` se conserva: mismo binario y mismo borrado previo por el bug EEXIST de OneDrive. Solo se agrega `scripts/vendor_daisyui.ps1`, el equivalente PowerShell de `vendor_daisyui.sh`.
- El CSS compilado sigue versionado: Vercel no compila.

### 3.2 Componentes (`templates/components/`)
**Se portan** del CRM, corrigiendo los bugs anteriores:
- `_button`, `_icon_button`, `_form_field`, `_modal`, `_confirm`, `_table` (con la paginación arreglada), `_badge`, `_breadcrumb`, `_empty_state`, `_toast_container`, `_spinner`, `_avatar` (sin `style=`).

**Se crean**, porque Talento los usa mucho y el CRM no los tiene:
- `_tabs` (perfil, ayuda, retroalimentación);
- `_stat` (tarjetas de KPI de los tableros);
- `_page_header` (título, descripción y acciones, presente en casi todas las pantallas);
- `_filters` (barras de filtros con GET);
- `_star_rating` (Arena Learn).

**Se agrega** `/dev/componentes/`, el showcase (solo con DEBUG o con el permiso `access.manage`), para que el agente y las personas vean la referencia viva.

### 3.3 Navegación (resuelve "el menú se sale de control")
- **Registro de menú en Python** (`apps/core/navigation.py`), con el mismo patrón que el registro de permisos. Cada ítem se declara como datos: `label, url_name, icon, section, permission_key(s), also_active, badge_fn`. La visibilidad sale **solo** de la matriz (spec 005). Ya no hay condiciones sueltas en el context processor.
- **Secciones por intención.** En lugar de una lista plana, el menú se agrupa así:

| Sección | Ítems |
|---|---|
| **Inicio** | Mi tablero |
| **Mi desarrollo** | Mis evaluaciones · Mi retroalimentación · Arena Learn |
| **Pendientes** (bandejas con contador) | Validar Ownership · Capturar Entrega de Valor · Validar Entrega de Valor · Aprobar cursos |
| **Comité de Talento** | Mi área · Mesa de Talento · Escenario Actual · Avance del periodo · Impacto Arena |
| **Administración** | Usuarios · Perfiles y permisos · Proyectos · Periodos · Áreas · Escenarios · Cuestionarios |

- **Layout**: `drawer` de daisyUI, fijo en escritorio (`lg:drawer-open`) y deslizable en móvil.
  - Secciones plegables, con la sección activa abierta automáticamente.
  - Estado activo correcto en todos los niveles.
  - Contadores de pendientes en los ítems de "Pendientes".
- **Buscador de pantallas (Ctrl/⌘ + K)**: una lista filtrable que se alimenta del mismo registro, así que solo muestra lo que la persona puede abrir. Con eso, el tamaño del menú deja de ser un problema de usabilidad.
- **Prueba de cobertura del menú**: todo ítem debe apuntar a una ruta con permiso registrado, y no puede haber ítems con condiciones fuera del registro.

### 3.4 Tema e identidad (requiere decisión, ver §6)
**Recomendación:** adoptar el tema `arena` del CRM y el dark mode `business` para que ArenaOS se vea como una sola suite, conservando una escala tipográfica legible (base 14, sm 12–13).

### 3.5 Gobierno con IA (portado del CRM y adaptado)
- **`arena-talento/CLAUDE.md`, propio.** Declara que el proyecto es independiente del `CLAUDE.md` de ArenaOps y enlaza a `DESIGN_SYSTEM.md`, la spec 005 y la convención `apps/core/services/`.
- **`DESIGN_SYSTEM.md`.** Es la ley de diseño de Talento: el contenido del CRM más las secciones propias de navegación y permisos.
- **`.claude/skills/daisyui/`** y `skills-lock.json`, la skill oficial fijada.
- **`.claude/agents/frontend-web-engineer.md`** y **`frontend-auditor.md`**, adaptados. El auditor verifica además que cada pantalla nueva use `@requires` y que sus acciones respeten la matriz. Es el primer paso del **agente auditor de permisos** pendiente.
- **`.claude/hooks/design_kit_reminder.py`**, que recuerda `DESIGN_SYSTEM.md` al editar plantillas o CSS.
- **Lint de plantillas en pytest** (rápido, sin Node). Falla si una plantilla nueva o migrada tiene:
  - `style=`, emojis, `confirm()` o `alert()`;
  - hex sueltos en clases;
  - `lucide.createIcons()`;
  - botones o modales armados fuera de `components/`.

## 4. Estrategia de migración sin "big bang"

**El riesgo principal es que las clases choquen.** daisyUI define `.btn-primary`, `.card`, `.input`, `.label` y `.badge`, los mismos nombres que usa hoy `input.css`. Activar daisyUI sin preparación cambiaría de golpe las 93 plantillas.

**Solución en dos pasos:**
1. **Renombre mecánico, sin cambio visual.** Las clases propias pasan a `ui-btn-primary`, `ui-card`, `ui-input`, `ui-label`, `ui-badge` y `ui-nav-link` en `input.css` y en las 93 plantillas, con un script de reemplazo probado y una verificación visual de 5 pantallas.
2. **Activar daisyUI.** Conviven: lo no migrado usa `ui-*` y lo migrado usa componentes y daisyUI. Cada módulo migrado borra su uso de `ui-*`. Al final, `ui-*` desaparece.

## 5. Fases

| Fase | Entregable | Riesgo | Esfuerzo |
|---|---|---|---|
| **0. Fundación** | `CLAUDE.md` y `DESIGN_SYSTEM.md` propios, skill daisyui, agentes, hook, `vendor_daisyui.ps1`, renombre a `ui-*`, daisyUI activo con tema `arena`, JS base (`icons.js`, `modals.js`, `theme_toggle.js`), `static_v`, lint de plantillas en modo informe | Bajo: sin cambio visual | 1–2 días |
| **1. Shell y navegación** | `base.html` sobre `drawer`, registro de menú con secciones, buscador Ctrl+K, topbar (campana y usuario con toggle de tema), toasts nuevos | Medio: todos lo ven | 2–3 días |
| **2. Componentes** | Los 12 portados más los 5 nuevos, showcase, `field_classes()`, prueba de cada componente | Bajo | 2 días |
| **3. Migración por módulo** | En este orden, de más nuevo a más crítico: **Perfiles y permisos → Arena Learn → Catálogos → Retroalimentación → Mesa de Talento y Escenario Actual → Evaluaciones (Ownership y Entrega de Valor) → Tableros y ayuda**. Cada módulo sale con el auditor en CUMPLE y su lint activo en modo estricto | Medio, acotado por módulo | 1–2 días por módulo (~10 días) |
| **4. Cierre** | Borrar `ui-*` y `partials/icon.html`, lint estricto global, dark mode verificado, revisión de accesibilidad AA y a 375 px | Bajo | 1 día |

**Total estimado:** 3–4 semanas de trabajo efectivo, desplegable al terminar cada fase. Evaluaciones y Mesa de Talento, que se usan durante el periodo, se migran al final y fuera de las ventanas de captura.

## 6. Decisiones que necesito del usuario

1. **Identidad visual.**
   - **A (recomendada):** tema `arena` del CRM (navy `#242D51` y Quicksand), para una sola suite.
   - **B:** conservar el navy `#1e3a5f` y Lato/Ubuntu de Talento sobre daisyUI.
2. **Navegación.**
   - **A (recomendada):** sidebar `drawer` con secciones y buscador Ctrl+K.
   - **B:** el navbar con hamburguesa del CRM.
3. **Dark mode desde la fase 1.** Recomendado: sí, porque con tokens semánticos cuesta poco.
4. **¿Arranco con la fase 0** como spec 006 (specify → plan → tasks), con el mismo flujo de las specs anteriores?
