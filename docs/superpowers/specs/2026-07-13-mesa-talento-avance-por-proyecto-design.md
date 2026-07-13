# Mesa de Talento — avance de evaluación por proyecto

Fecha: 2026-07-13

## Contexto

`mesa-talento/` (`dashboards:talent_table`) es hoy una lista plana de todos
los colaboradores activos con filtros por **área**, **nivel** y búsqueda por
nombre, más 4 tarjetas de estadísticas globales del periodo. No hay forma de
ver el trabajo agrupado por **equipo (= proyecto)** ni de saber, de un
vistazo, a quiénes de cada equipo ya "pasó" el comité por la Mesa.

Talento necesita usar esta pantalla como herramienta de control durante la
sesión de Mesa de Talento: saber qué equipo está evaluando, cuánto lleva de
avance por equipo, y filtrar con un clic a los integrantes de ese equipo.

## Objetivo

1. Agregar un **estado explícito** por colaborador-periodo: "Listo en Mesa de
   Talento", que Talento marca a mano cuando el comité terminó de trabajar a
   esa persona. Este único estado cubre lo que antes se pensaba como dos
   cosas ("revisada" y "seleccionada para retroalimentación").
2. Agregar sobre la lista una **tabla compacta de avance por proyecto**:
   por cada proyecto activo, cuántos integrantes del equipo ya están listos,
   cuántos pendientes y el porcentaje de avance.
3. Hacer que cada fila de esa tabla **filtre la lista** de abajo a solo los
   integrantes de ese equipo (filtro exclusivo).

## Qué NO cambia

- El resto de `talent_table` (tarjetas de stats, paginación, comportamiento
  sin filtro de proyecto) se mantiene igual.
- Impacto Arena, Entrega de Valor, Ownership y la retroalimentación no se
  tocan. El avance por proyecto NO mide esos insumos: mide únicamente el
  trabajo del comité (el check "Listo en Mesa").

## Modelo de datos

Se agregan tres campos a `TalentSessionNote` (una por `user`+`period`, ya
existe), siguiendo el patrón de `feedback_agreed*`:

- `mesa_ready` — `BooleanField(default=False)`. El check "Listo en Mesa de
  Talento".
- `mesa_ready_at` — `DateTimeField(null=True, blank=True)`.
- `mesa_ready_by` — `FK(AUTH_USER_MODEL, on_delete=PROTECT, null=True,
  blank=True, related_name="mesa_ready_notes")`.

Migración correspondiente. Los campos quedan cubiertos por `HistoricalRecords`
(`HistoricalTalentSessionNote`) automáticamente.

"Listo" es independiente de `feedback_agreed` (retro acordada con el
colaborador): son dos cosas distintas y ambas conviven.

## Definición de "equipo" de un proyecto

Para un `Project` activo, su equipo es la **unión, sin duplicados**, de:

- los `user` de `ProjectMembership` de ese proyecto, y
- el `owner` del proyecto (lead).

`responsable` y `validador` **no** cuentan (suelen ser externos al equipo).
Si el `owner` ya es miembro, se cuenta una sola vez.

## Cálculo del avance por proyecto

Para cada `Project` con `is_active=True` que tenga **≥1 integrante**:

- `total` = número de integrantes del equipo (según definición anterior).
- `listos` = integrantes cuya `TalentSessionNote` del periodo abierto tiene
  `mesa_ready=True`.
- `pendientes` = `total − listos`.
- `pct` = `round(listos / total * 100)` (0 si `total == 0`, aunque esos
  proyectos no aparecen).

Se resuelve sin N+1: un query de memberships (`select_related` proyecto/usuario),
el conjunto de owners de proyectos activos, y un set de `user_id` con
`mesa_ready=True` en el periodo. El cálculo se arma en memoria a partir de esos
tres conjuntos.

Una persona en varios proyectos **cuenta como integrante en cada uno**, y su
estado listo/pendiente se refleja en el avance de todos ellos.

Proyectos activos sin integrantes no aparecen en la tabla.

## Orden de la tabla de avance

Por `pct` **ascendente** (equipos más atrasados primero), con `project.name`
ascendente como desempate. Así el comité ve primero dónde falta trabajo.

## Filtro por proyecto (exclusivo)

- Parámetro nuevo `?proyecto=<project_id>`.
- Cuando viene `proyecto`:
  - La lista muestra **solo** los integrantes de ese equipo.
  - Se **ignoran** `area`, `nivel` y `q` (el comité ve el equipo completo, sin
    recortar). Los inputs de esos filtros se ocultan mientras hay un proyecto
    seleccionado.
  - Se muestra un chip "Equipo: NOMBRE ✕" que enlaza de vuelta a la vista sin
    filtro (todos los colaboradores).
  - La fila del proyecto activo se resalta en la tabla de avance.
- Sin `proyecto`: la pantalla se comporta como hoy (todos los colaboradores,
  con filtros de área/nivel/búsqueda combinables).
- La tabla de avance por proyecto muestra **siempre todos** los proyectos,
  independientemente de los filtros aplicados (no se recalcula por
  área/nivel/búsqueda).

## UI

### Tabla de avance por proyecto (nueva)

Bloque compacto entre las tarjetas de stats y los filtros/lista. Columnas:

| Proyecto | Total | Listos | Pendientes | % avance |

- `% avance` como número + barra de progreso (patrón visual existente del
  proyecto, Tailwind).
- Cada fila es un enlace a `?proyecto=<id>`.
- Fila del proyecto seleccionado resaltada.
- Si no hay proyectos con equipo, el bloque no se muestra (o muestra un
  vacío discreto).

### Lista de colaboradores

- Nuevo badge de estado por fila: **"Listo en Mesa"** (verde) / **"Pendiente"**
  (neutro), leyendo `mesa_ready` de la nota del periodo.
- Se **conserva** la columna de Banda / calificación final existente; el badge
  de "Listo" es información adicional, no la reemplaza.

### Ficha de la persona (`talent_person`)

- Nuevo control **"Marcar como listo en Mesa"** (toggle HTMX, mismo patrón que
  `talent_scenario_toggle`), ubicado junto a la nota/escenarios.
- Muestra quién marcó y cuándo (`mesa_ready_by`, `mesa_ready_at`) cuando está
  activo.
- Es el **único** lugar donde se marca/desmarca el estado.

## Permisos

- Ver `talent_table` y `talent_person`: `is_admin` (Talento) o `is_director`,
  como hoy.
- Marcar/desmarcar `mesa_ready`: **solo `is_admin`**, igual que
  `talent_note_autosave` / `talent_scenario_toggle`. Un `is_director` que
  intente el POST recibe 403.
- Nueva ruta para el toggle:
  `mesa-talento/persona/<int:pk>/listo/` → `views.talent_mesa_ready_toggle`.

## Casos borde

- Colaboradores **sin proyecto**: no aparecen en ninguna fila de la tabla de
  avance, pero siguen visibles en la lista general (sin filtro de proyecto).
- Sin periodo abierto: la tabla de avance no se muestra (no hay notas del
  periodo); la lista se comporta como hoy.
- `proyecto` inválido o inactivo en la query: se ignora (equivale a sin
  filtro) o 404 controlado; el spec toma **ignorar y mostrar todos** para no
  romper enlaces viejos.
- Nota inexistente para un integrante: cuenta como **pendiente**
  (`mesa_ready` efectivamente `False`).

## Pruebas

- **Equipo**: unión miembros + owner, sin duplicar cuando el owner es miembro.
- **Avance**: `total`/`listos`/`pendientes`/`pct` correctos, con una persona
  en 2 proyectos reflejada en ambos.
- **Filtro exclusivo**: `?proyecto=<id>` devuelve solo el equipo; ignora
  `area`/`nivel`/`q` presentes en la misma URL.
- **Orden**: proyectos ordenados por `pct` ascendente.
- **Toggle**: `is_admin` puede marcar/desmarcar y setea `mesa_ready_at` /
  `mesa_ready_by`; `is_director` recibe 403.
- **Badge**: la lista refleja `mesa_ready` (Listo vs Pendiente).
- **Sin periodo**: no rompe; sin tabla de avance.
