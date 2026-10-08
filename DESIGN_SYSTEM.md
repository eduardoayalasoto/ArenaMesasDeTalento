# DESIGN_SYSTEM.md — arena-talento

**Ley para todo cambio visual.** arena-talento comparte el sistema de diseño de **arena-crm**
(`../arena-crm/DESIGN_SYSTEM.md`, daisyUI 5 desde 2026-09-22): mismo stack, tema, tipografía,
componentes y reglas. **Decisión (2026-10-08): ambos sistemas se ven EXACTAMENTE igual.** Shell,
navbar, login, tema, escala tipográfica, modo oscuro, vendors y componentes son copia literal del
CRM; las únicas diferencias son la palabra «talento» (naranja) y el contenido del menú. Este
archivo fija solo eso; donde no diga nada, aplica el documento de arena-crm. Plan y estado de la migración:
`docs/PLAN_MIGRACION_DISENO.md`.

## 1. Stack (sin CDN, sin Node)
Tailwind v4 (`tailwindcss.exe` standalone, `.\build_css.ps1`) + **daisyUI 5.7.43** vendorizado
(`static/vendor/daisyui/5.7.43/*.mjs`, `@plugin` con ruta relativa) + htmx + Alpine (solo estado
local de UI) + Lucide. Entrada: `static/src/input.css`; salida versionada: `static/css/app.css`.

## 2. Tema y color
- Tema **`arena`** (copia fiel del de arena-crm): `data-theme="arena"` en `<html>`.
- **Solo tokens semánticos** en código nuevo: `bg-base-100/200/300`, `text-base-content(/60)`,
  `bg-neutral`/`text-neutral-content` (navy `#242D51`), `btn-primary`, `badge-success`, etc.
  Prohibidos hex sueltos y la escala legada `arena-*` (solo vive en plantillas aún no migradas).
- **Acento de producto: naranja «talento»** — `talento-300 #FFB45A` → `talento-600 #F2711C`
  (degradado). **Solo en la marca.** Todo lo demás (estado activo del menú = `bg-secondary/15
  text-secondary`, contadores = `badge-error`) es idéntico al CRM.
- Modo oscuro (`business`) **activo**, con el mismo toggle del menú de usuario que el CRM
  (`static/js/theme_toggle.js`, clave `arena_talento_theme`). Las plantillas legadas aún no
  migradas pueden verse imperfectas en oscuro hasta su fase 3.

## 3. Tipografía
Una sola familia: **Quicksand** self-hosted (`static/fonts/`) y **la misma escala del CRM**
(`text-sm` = 11 px, `text-base` = 14 px…), copiada literal en `static/src/input.css`.

## 4. Marca
Lockup **«arenatalento»**: `{% include "components/_brand_mark.html" %}` — ícono de Arena +
«arena» (`primary-100`) + «talento» en degradado naranja, Quicksand 700. Sobre fondo oscuro
(navbar, panel de login). Nunca recrear el logo a mano.

## 5. Navegación
**Navbar superior** portado de arena-crm (`templates/_navbar.html`), sin sidebar:
- Hamburguesa → `dropdown` → `menu` con categorías plegables en acordeón: **Inicio · Arena Learn ·
  Mesa de Talento · Administración**. Mesa de Talento usa subtítulos (Mi evaluación · Por validar ·
  Comité, con `menu-title`). Igual que el CRM: una categoría abierta a la vez, sin auto-expandir;
  ítem activo `bg-secondary/15 text-secondary`; contenedor `max-w-6xl`.
- **El menú es datos**: `apps/core/navigation.py`. Cada ítem declara su permiso de la matriz
  (spec 005) y, si aplica, una regla de relación. Agregar una pantalla al menú =
  agregar un `NavItem` ahí; **nunca** condiciones de menú en plantillas.
- Sin buscador Ctrl+K ni contadores en el menú (el CRM no los tiene). Campana de pendientes con
  `indicator` y menú de usuario (modo oscuro · Mi perfil · Centro de ayuda · Cerrar sesión por
  POST). Diferencias inevitables: avatar con la foto real (`{% nice_avatar %}`) y Cerrar sesión
  por POST.
- **Pantallas de acceso** (login, restablecer y cambiar contraseña): pantalla partida del login del
  CRM en `accounts/_auth_card.html`; cada pantalla solo llena `{% block card %}`.

## 6. Componentes
Biblioteca en `templates/components/` con API `{% include … with … %}` (portada del CRM en la
fase 2: `_button`, `_icon_button`, `_form_field`, `_modal`, `_confirm`, `_table`, `_badge`,
`_breadcrumb`, `_empty_state`, `_toast_container`, `_spinner`, `_avatar`, más `_tabs`, `_stat`,
`_page_header`, `_filters`, `_star_rating`). Antes de escribir markup, busca el componente.

## 7. Reglas duras (heredadas del CRM)
- Íconos: **solo `window.renderIcons(raíz)`** (`static/js/icons.js`); prohibido
  `lucide.createIcons()` global (ciclo infinito con Alpine).
- Diálogos = modal (`<dialog>`); prohibidos `alert()/confirm()/prompt()` en código nuevo.
- Prohibido `style=` inline, emojis como íconos y CSS nuevo fuera de `static/src/input.css`.
- htmx para interacción con el servidor (la vista devuelve un parcial HTML); Alpine solo para
  estado local; nunca `fetch` dentro de Alpine.
- Accesibilidad AA: `aria-label` en botones de solo ícono, foco visible, contraste en ambos temas.
- Permisos en plantillas: `{% load access_tags %}` y `request.user|can:"clave"`.

## 8. Capa legada `ui-*` (temporal)
Las clases artesanales previas se renombraron a `ui-btn-*`, `ui-card`, `ui-input`, `ui-label`,
`ui-badge`, `ui-nav-link` (mismo aspecto). **Prohibidas en código nuevo.** Cada módulo migrado
deja de usarlas; se eliminan en la fase 4. Script del renombre: `scripts/rename_legacy_classes.py`.

## 9. Verificación (sin Node)
Pruebas de vista pytest compactas + revisión en navegador (1440 px y 390 px) cuando el cambio sea
visual; `.\build_css.ps1` tras tocar clases. El agente `frontend-auditor` emite CUMPLE / NO CUMPLE.
