# Importación de proyectos/equipos y edición de proyecto — Diseño

**Fecha:** 2026-06-12
**Autor:** Eduardo Ayala (con Claude Code)
**Estado:** aprobado para plan

## Contexto

La BD de Neon se limpió (proyectos, membresías y evaluaciones borradas; usuarios,
periodos, catálogos y cuestionarios conservados). Hay que recargar los proyectos del
1er semestre 2026 y sus equipos desde
`docs/Modelos/Quien evalua a quien Analítica 1er S 2026.xlsx`, y enriquecer el modelo
`Project` con propiedades que el negocio maneja pero el sistema aún no tiene.

### Fuente de datos (xlsx, 3 hojas)

- **`HC Total Nov 2024-2026`** — 1 fila por colaborador: Nombre completo, Nombre corto,
  Correo, Área, Puesto, Cliente, y pares Proyecto N / Evaluador N (hasta 4). El
  "Evaluador N" coincide con el Owner del proyecto. Sirve como mapa Nombre corto → Correo.
- **`Proyectos`** — `Employee | Project | Min of Start | Max of End`. Fuente de membresías
  con fechas (más completa que HC Total). Tiene filas con Employee en blanco (relleno hacia
  abajo desde Héctor Rangel Castro y Oscar Nafarrate).
- **`Proyectos Dueños`** — catálogo de 17 proyectos: ID(P#), Nombre, Cliente, Owner,
  Responsable, Kick-off, Target Cierre, Status, Descripción (Descripción viene vacía).

## Decisiones (acordadas con el usuario)

1. **Campos nuevos en `Project`**: Responsable, Kick-off, Target Cierre, Status.
   - **No** se agrega código externo `P#` (idempotencia por nombre) ni Descripción.
2. **Owners faltantes** (no existen como usuario): se **crean** como usuarios.
3. **`duration_type`** (no viene en Excel): Claude propone, usuario valida (tabla abajo).
4. **Miembro no-usuario** `Arturo Carranza Lucio`: se **crea** como usuario.
5. **Evaluador**: NO se persiste como campo aparte (coincide con `lead`/Owner).
6. **Fechas**: son a nivel proyecto (kickoff/target_close). Las fechas por miembro de la
   hoja `Proyectos` se cargan en `ProjectMembership.start/end` de forma silenciosa (el modelo
   ya tiene los campos), pero **sin UI** ni edición por miembro.

## Cambios de esquema

Migración que agrega a `apps/catalog/models.py::Project`:

| Campo | Tipo | Notas |
|---|---|---|
| `responsable` | `FK(User, on_delete=PROTECT, null=True, blank=True, related_name="responsible_projects")` | persona responsable, distinta del `lead` |
| `kickoff` | `DateField(null=True, blank=True)` | fecha de arranque |
| `target_close` | `DateField(null=True, blank=True)` | cierre objetivo |
| `status` | `CharField(choices=Status, default=ON_TRACK)` | `ON_TRACK` / `DELAYED` |

`Project` ya tiene `HistoricalRecords()`; la migración de historial se genera junto.
Todos opcionales para no romper datos/lógica existentes. `lead` sigue mapeando al **Owner**.

## Usuarios nuevos a crear (3)

Rol COLABORADOR, sin área/nivel, contraseña por defecto (`Arena2026!`),
`must_change_password=False`, idempotente por correo. Correos por convención:

| Persona | Correo |
|---|---|
| Carolina Palacio | carolina.palacio@arena-analytics.com |
| Carlos Alejandro Rodríguez Ochoa | carlos.rodriguez@arena-analytics.com |
| Arturo Carranza Lucio | arturo.carranza@arena-analytics.com |

## Clasificación FINITO / INDEFINIDO (validada)

| Proyecto | duration_type |
|---|---|
| MSI | FINITO |
| Share Forecast LATAM / Apollo 2.0 | INDEFINIDO |
| Data Ops / MPM | INDEFINIDO |
| GenAI | FINITO |
| AI Latam Office Program Manager | INDEFINIDO |
| OBPPC | INDEFINIDO |
| Weather | FINITO |
| Migración 360 a 720 | FINITO |
| CCL Engineering Cell | INDEFINIDO |
| Hypercare Migración 360 a 720 | FINITO |
| Business Terms Harmonization & SSOT | FINITO |
| Rodin | INDEFINIDO |
| Urrea Bolsa de Horas | INDEFINIDO |
| Coppel Portal (Sistema de Gestión de Categorías) | FINITO |
| NSR PM & Comm | FINITO |
| Prime Partners Support | INDEFINIDO |
| C&CL Report | FINITO |

## Componentes

### 1. `import_projects` (management command)
- Patrón `import_csv_users`: idempotente, `--dry-run`, lee el xlsx (openpyxl, import perezoso
  → dependencia solo local, no afecta deploy).
- Lee `Proyectos Dueños`. Por cada fila:
  - Resuelve/crea `lead` (Owner) y `responsable` por nombre → usuario (mapa por nombre
    normalizado contra `full_name`; crea los 3 usuarios faltantes según corresponda).
  - `get_or_create(name=...)` y actualiza `client, lead, responsable, kickoff, target_close,
    status, duration_type`.
- Reporta creados/actualizados y cualquier nombre no resuelto.

### 2. `import_memberships` (management command)
- Lee `Proyectos`. Aplica relleno hacia abajo del Employee en blanco.
- Empareja Employee → usuario: mapa Nombre corto→Correo de `HC Total`, respaldo por
  `full_name` normalizado.
- `ProjectMembership.get_or_create(project, user)`, set `start`/`end` desde la hoja.
- Idempotente; reporta filas omitidas / no emparejadas.

### 3. Edición de proyecto (UI ya existente, a extender)
- `apps/catalog/forms.py::ProjectForm`: agregar `responsable, kickoff, target_close, status`
  a `fields` con widgets/estilos del patrón actual (DateInput type=date, Select con `input`).
  `responsable` queryset = usuarios activos, `empty_label` opcional.
- `templates/catalog/project_form.html`: renderizar los 4 campos nuevos en el panel "Datos
  del proyecto". El panel "Equipo" (agregar/quitar) se mantiene **sin cambios**.
- `views.project_edit` ya guarda vía `ProjectForm.save()` y gestiona el equipo — sin cambios.

## Matriz de emparejamiento de nombres (normalización)

Normalizar: minúsculas, sin acentos, espacios colapsados. Resolver en este orden:
1. Mapa Nombre corto (HC Total) → Correo → `User`.
2. `full_name` normalizado contiene/igual al nombre del Excel.
3. Si no resuelve y es Owner/Responsable/miembro de la lista de "crear": crear usuario.
4. Si no resuelve y no está en la lista: **omitir y reportar** (no crear silenciosamente).

## Verificación

- Correr ambos comandos con `--dry-run` primero contra Neon (`DATABASE_URL` unpooled).
- Post-import: 17 proyectos, 65 usuarios (62 + 3), conteo de membresías; listar no-emparejados.
- Editar un proyecto en la UI y confirmar que los 4 campos persisten.

## Fuera de alcance

- Código externo `P#`, Descripción de proyecto.
- Edición de fechas por miembro en la UI.
- Re-modelado del evaluador (sigue siendo `lead`).
