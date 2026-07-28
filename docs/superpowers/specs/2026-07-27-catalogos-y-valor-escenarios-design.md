# Diseño — Folder "Catálogos" en el sidebar + valor invertido en Escenarios

Fecha: 2026-07-27

## 1. Contexto

El sidebar de Talento acumula cada vez más pantallas administrativas sueltas
(`apps/core/context_processors.py::navigation()`), lo que lo hace largo y
difícil de escanear. Por separado, el catálogo de Escenarios
(`apps.catalog.models.ScenarioOption`) usado en la Mesa de Talento
(`TalentSessionNote.scenario_actual/scenario_s1/scenario_s2`, M2M por
colaborador × periodo) tiene un campo `order` que hoy solo controla el orden
de despliegue en la pantalla admin, pero semánticamente el escenario "mejor"
(Promoción de puesto) tiene el número más bajo (1) y el "peor" (Desempeño no
satisfactorio) el más alto (5) — lo contrario de lo que se necesita si se
quiere usar ese valor como ranking (mayor = mejor) en reportes futuros de
Mesa de Talento.

## 2. Alcance

Dos cambios independientes, agrupados en un solo spec por ser pequeños y
tocar el mismo módulo (`apps.catalog`) en el mismo periodo de trabajo:

- **A.** Agrupar en el sidebar los catálogos administrables de Talento bajo
  un folder colapsable "Catálogos".
- **B.** Invertir el valor semántico de `ScenarioOption.order` y renumerar
  los nombres para que coincidan.

## 3. A — Folder "Catálogos"

### Qué entra

Solo los 5 catálogos administrables puros, todos hoy visibles únicamente
para `user.is_admin` (Talento):

- Cuestionarios (`questionnaires:admin_list`)
- Usuarios (`accounts:user_admin`)
- Escenarios (`catalog:scenario_admin`)
- Periodos (`catalog:period_admin`)
- Ponderaciones (`catalog:weight_admin`)

**Quedan fuera** (sin cambios, sueltos arriba del folder):
- Impacto Arena, Avance del periodo — son pantallas de captura/reporte, no
  catálogos.
- Proyectos — es un catálogo, pero lo ven también Leads y Directores
  (`can_edit_project`), no es exclusivo de Talento; meterlo en un folder
  etiquetado "solo Talento" sería inconsistente con quién lo puede ver.

### Comportamiento

- Colapsable, **cerrado por defecto**.
- Se **auto-expande** si el usuario está parado en una pantalla de adentro
  del folder (igual patrón que `active` ya usa para resaltar el link
  actual).
- Ícono nuevo para el folder (`catalog` → lucide `database`, agregado a
  `templates/partials/icon.html`) distinto del ícono `folder` que ya usa
  Proyectos.

### Implementación

- `apps/core/context_processors.py::navigation()`: generalizar el closure
  `add()` para aceptar un parámetro opcional `target` (lista destino,
  default `items`). Construir una lista `catalog_children` acumulando los 5
  items con `target=catalog_children` en vez de `items`. Si
  `catalog_children` no está vacía, append a `items` un solo entry:
  `{"type": "group", "label": "Catálogos", "icon": "catalog",
  "children": catalog_children, "active": any(c["active"] for c in
  catalog_children)}`.
- `templates/partials/_navlist.html`: en el `{% for item in nav_items %}`,
  ramificar por `item.type == "group"` — un `<div x-data="{open: ...}">`
  con botón toggle (label + chevron) y un contenedor `x-show="open"` con
  los links hijos indentados; el resto del loop sigue el markup actual de
  link simple.
- No se usa ningún plugin de Alpine adicional (el proyecto solo vendoriza
  Alpine core, sin `x-collapse`); el toggle es un `x-show` simple.
- Sin cambios de permisos: la visibilidad de cada item hijo la sigue
  decidiendo `navigation()` exactamente igual que hoy (el folder es
  puramente de presentación).

## 4. B — Valor invertido en Escenarios

### Decisión

Se reutiliza `ScenarioOption.order` como el valor semántico (no se agrega
un campo nuevo). Los 5 registros existentes:

| Nombre actual | order actual | Nombre nuevo | order nuevo |
|---|---|---|---|
| 1. Promoción de puesto | 1 | 5. Promoción de puesto | 5 |
| 2. Acting del puesto superior | 2 | 4. Acting del puesto superior | 4 |
| 3. Mismo puesto, buen desempeño | 3 | 3. Mismo puesto, buen desempeño | 3 |
| 4. Desempeño con áreas de oportunidad | 4 | 2. Desempeño con áreas de oportunidad | 2 |
| 5. Desempeño no satisfactorio | 5 | 1. Desempeño no satisfactorio | 1 |

Regla general para la migración de datos: `new_order = 6 - old_order`;
`new_name` reemplaza el prefijo `"{old_order}. "` por `"{new_order}. "`.

`Meta.ordering` de `ScenarioOption` cambia de `["order"]` a `["-order"]`
para que la pantalla admin (`catalog:scenario_admin`) siga mostrando
Promoción de puesto arriba y Desempeño no satisfactorio abajo — igual look
visual que hoy, aunque el valor interno ya sea el inverso.

### Implementación

Una sola migración Django (`apps/catalog/migrations/0008_...py`):
- `AlterModelOptions` sobre `ScenarioOption` (`ordering: ["-order"]`).
- `RunPython` con función `forwards` que recorre los 5 `ScenarioOption`
  existentes por nombre (match tolerante al prefijo actual) y aplica la
  tabla de arriba; función `reverse` simétrica (reaplica la tabla al
  revés) para que la migración sea reversible.
- Si no existen las 5 filas esperadas (entorno limpio/test), la función no
  hace nada (no falla) — es una migración de datos "best effort" sobre
  datos ya sembrados manualmente en producción, no un seed.

### Fuera de alcance

- No se toca la estructura de `TalentSessionNote` ni las vistas de Mesa de
  Talento — la relación ya existe (M2M) y no cambia.
- No se construye todavía ningún reporte/cálculo que consuma el nuevo
  valor de ranking; el spec solo deja el dato correcto en la base para que
  un futuro reporte lo use.

## 5. Riesgos / notas

- Migración de datos por nombre: si alguien ya editó manualmente los
  nombres de estos 5 escenarios en producción (quitando el prefijo
  numérico), el matching por nombre podría no encontrar la fila — se
  decide no fallar la migración en ese caso, solo se deja tal cual (riesgo
  aceptado, es un catálogo pequeño y administrado por Talento que puede
  corregirse a mano desde la pantalla admin si hiciera falta).
- Aplica a Neon manualmente después del merge, como toda migración en este
  proyecto (Vercel no corre migraciones).
