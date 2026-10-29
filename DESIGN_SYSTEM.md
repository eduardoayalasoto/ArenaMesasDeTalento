# DESIGN_SYSTEM.md — arena-talento

**Ley para todo cambio visual.** arena-talento comparte el sistema de diseño de **arena-crm**
(`../arena-crm/DESIGN_SYSTEM.md`, daisyUI 5 desde 2026-09-22): mismo stack, tema, tipografía,
componentes y reglas. **Decisión (2026-10-08, reafirmada 2026-10-28): ambos sistemas se ven
EXACTAMENTE igual.** Shell, navbar, login, tema (paleta oficial de Arena), escala tipográfica, modo
oscuro, vendors y componentes son los mismos; las únicas diferencias son el acento de la marca
(«talento» naranja / «crm» teal), el contenido del menú y la URL de inicio. **Archivos idénticos en
ambos repos** (cambiar uno = cambiar el otro): `components/_nav_menu.html` y
`components/_breadcrumb.html` (este último solo difiere en la URL de inicio). Este
archivo fija solo eso; donde no diga nada, aplica el documento de arena-crm. Plan y estado de la migración:
`docs/PLAN_MIGRACION_DISENO.md`.

## 1. Stack (sin CDN, sin Node)
Tailwind v4 (`tailwindcss.exe` standalone, `.\build_css.ps1`) + **daisyUI 5.7.43** vendorizado
(`static/vendor/daisyui/5.7.43/*.mjs`, `@plugin` con ruta relativa) + htmx + Alpine (solo estado
local de UI) + Lucide. Entrada: `static/src/input.css`; salida versionada: `static/css/app.css`.

## 2. Tema y color
- Tema **`arena`**: `data-theme="arena"` en `<html>`. **Colores = paleta oficial de Arena**
  (`../arena-os/DESIGN_KIT.md` §1, desde 2026-10-28; el verde menta anterior daba ~2:1 de
  contraste). Mismos valores en arena-crm:

  | Token | Claro (`arena`) | Uso |
  |---|---|---|
  | `primary` | morado `#804971` (texto blanco, 6.75:1) | botones, ligas, foco de campos, ítem activo del menú, paneles informativos |
  | `secondary` | navy `#3A4263` (texto blanco) | nivel actual del breadcrumb, selección en selectores, avatar |
  | `accent` | teal `#6AB6A1` | acentos puntuales |
  | `neutral` | navy `#242D51` | navbar y menú desplegable |
  | `success` / `info` / `warning` / `error` | `#08875D` / `#3274A3` / `#F3B843` / `#E02D3C` | estados (siempre con ícono o texto) |

  Oscuro (`business`): `primary` `#D984CE` con texto `#1D2433`. **Nunca** usar `text-secondary` /
  `text-primary` sobre `bg-neutral` (navy sobre navy): sobre el navbar los textos van en
  `text-neutral-content(/70–/85)` y el activo como píldora `bg-primary text-primary-content`.
  Atenuados mínimos para AA: `text-base-content/75` sobre blanco, `text-neutral-content/70` sobre navy.
- **Solo tokens semánticos** en código nuevo: `bg-base-100/200/300`, `text-base-content(/60)`,
  `bg-neutral`/`text-neutral-content` (navy `#242D51`), `btn-primary`, `badge-success`, etc.
  Prohibidos hex sueltos y la paleta cruda de Tailwind (`slate-*`, `gray-*`, `emerald-*`…): el
  navy legado `arena-*` ya no existe (se migró a `primary` el 2026-10-08).
- **Acento de producto: naranja «talento»** — `talento-300 #FFB45A` → `talento-600 #F2711C`
  (degradado). **Solo en la marca** (en arena-crm el acento de marca es el teal de «crm»; es lo
único verde de ese sistema). Contadores = `badge-error`.
- Modo oscuro (`business`) disponible con el mismo toggle del menú de usuario que el CRM
  (`static/js/theme_toggle.js`, clave `arena_talento_theme`). **Por defecto SIEMPRE claro**
  (2026-10-08): no se hereda la preferencia del sistema operativo; el oscuro solo si la persona
  lo activa. Igual en arena-crm.

## 3. Tipografía
Una sola familia: **Quicksand** self-hosted (`static/fonts/`) y **la misma escala del CRM**
(`text-sm` = 11 px, `text-base` = 14 px…), copiada literal en `static/src/input.css`.

## 4. Marca
Lockup **«arenatalento»**: `{% include "components/_brand_mark.html" %}` — ícono de Arena +
«arena» (`primary-100`) + «talento» en degradado naranja, Quicksand 700. Sobre fondo oscuro
(navbar, panel de login). Nunca recrear el logo a mano.

## 5. Navegación
**Navbar superior** (`templates/_navbar.html`), sin sidebar; contenedor `max-w-6xl`.

### 5.1 Menú — componente `components/_nav_menu.html` (idéntico en arena-crm)
- Hamburguesa → `dropdown` (`bg-neutral`, `w-72`) → `{% include "components/_nav_menu.html" with
  on_navigate="menuOpen = false" menu_class="p-0" %}`.
- daisyUI `menu` multinivel: **Categoría** (`<details>`, ícono Lucide) › **grupo** opcional
  (`menu-title`, p. ej. Mi evaluación · Por validar · Comité en Mesa de Talento) › **ítem** (ícono
  Lucide). La categoría `inicio` se pinta como accesos directos, sin desplegable.
- **Al abrir, la categoría de la pantalla actual ya está desplegada** (`nav_active_category`) y el
  ítem actual es la píldora morada `menu-active bg-primary text-primary-content` con
  `aria-current="page"`; la categoría activa lleva un punto morado (+ texto `sr-only`).
  Acordeón: una categoría abierta a la vez (Alpine, estado local).
- **El menú es datos**: `apps/core/navigation.py` (`NavCategory` / `NavItem` con `icon`, `group`,
  permiso de la matriz de la spec 005, regla de relación opcional y `also_active` = subpantallas
  que marcan ese ítem). Agregar una pantalla al menú = agregar un `NavItem`; una subpantalla
  nueva = agregar su ruta a `also_active`. **Nunca** condiciones de menú en plantillas.

### 5.2 Breadcrumb — componente `components/_breadcrumb.html` (mismo archivo que arena-crm)
- **En TODAS las pantallas, automático**: `templates/base.html` lo pinta con `nav_breadcrumb`, que
  `build_nav` deriva del mismo registro del menú:
  - pantalla del menú → Inicio › Categoría › **Ítem**
  - subpantalla (`also_active`) → Inicio › Categoría › Ítem (liga) › **título de la página**
    (`page_title`, sin sufijos « · Arena Learn» / prefijo «Mesa de Talento · »)
  - pantalla fuera del menú → Inicio › **título de la página**
  - no repite la categoría en «Inicio» ni cuando se llama igual que su ítem.
- Personalizar: la vista pasa `breadcrumb_trail` (lista de `{"label","url","icon"}`) y/o
  `breadcrumb_current`, o la plantilla redefine `{% block breadcrumb %}`.
- Estilo discreto: `text-sm`, `text-base-content/75`, íconos Lucide `w-3.5`, casa (`house`) como
  inicio, niveles sin liga (categorías) como texto, actual en `text-secondary` con `aria-current`.
- **Prohibido** escribir migas a mano o enlaces «← Volver» que repitan la miga. Solo se conserva un
  «Volver» cuando regresa a un estado que la miga no tiene (p. ej. `?periodo=` o la lista de origen
  de una evaluación a la que se llega desde varias pantallas).
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

Clases canónicas (las mismas del CRM, sin equivalente legado):
- **Card**: `bg-base-100 border border-base-300 rounded-2xl shadow-sm` (la `shadow-sm` es la
  única adición sobre el CRM, aprobada 2026-10-08).
- **Botones**: `btn btn-primary` · `btn btn-outline btn-primary` (secundario) · `btn btn-ghost` ·
  `btn btn-error` · `btn btn-sm btn-soft btn-primary` (acción ligera en tablas).
- **Tamaño de botones (2026-10-13)**: todo botón del encabezado de una página o de su tarjeta
  principal usa el tamaño normal (`btn`, sin `btn-sm`), igual que «Exportar Excel» del dashboard,
  aunque sea ghost o abra una confirmación (`_confirm.html` con `trigger_size="md"`). `btn-sm` solo
  va en filas de tabla, tarjetas de listado, avisos en línea y barras densas.
- **Formularios**: `input w-full` · `select w-full` · `textarea w-full` · `file-input w-full`;
  label `fieldset-legend` (o el componente `_form_field`).
- **Badges**: `badge` + `badge-soft badge-{success|warning|error|info}` (o `_badge`).

## 7. Reglas duras (heredadas del CRM)
- Íconos: **solo `window.renderIcons(raíz)`** (`static/js/icons.js`); prohibido
  `lucide.createIcons()` global (ciclo infinito con Alpine).
- Diálogos = modal (`<dialog>`); prohibidos `alert()/confirm()/prompt()` en código nuevo.
- Prohibido `style=` inline, emojis como íconos y CSS nuevo fuera de `static/src/input.css`.
- htmx para interacción con el servidor (la vista devuelve un parcial HTML); Alpine solo para
  estado local; nunca `fetch` dentro de Alpine.
- Accesibilidad AA: `aria-label` en botones de solo ícono, foco visible, contraste ≥ 4.5:1 en ambos
  temas (ver tabla de §2; medir al introducir un color o una opacidad nueva).
- Permisos en plantillas: `{% load access_tags %}` y `request.user|can:"clave"`.

## 8. Capa legada `ui-*` (eliminada)
Retirada el 2026-10-08 (fases 3-4): las 553 clases `ui-*` y la paleta cruda se migraron a
daisyUI y tokens con `scripts/migrate_to_daisyui.py`. `ui-*` ya no existe en `input.css`.

## 9. Verificación (sin Node)
Pruebas de vista pytest compactas + revisión en navegador (1440 px y 390 px) cuando el cambio sea
visual; `.\build_css.ps1` tras tocar clases. El agente `frontend-auditor` emite CUMPLE / NO CUMPLE.
