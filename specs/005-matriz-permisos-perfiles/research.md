# Research: Matriz de permisos por perfiles (005)

El as-is ruta por ruta está en `research-permisos-actuales.md`. Aquí van las decisiones de diseño.

## R1. Dónde vive el catálogo de permisos

- **Decision**: el **catálogo es código**: un registro declarativo en `apps/access/registry.py` con una entrada por permiso (`clave`, módulo, pantalla, acción, alcances permitidos, rutas que protege y estado activa/pendiente). Los **perfiles y concesiones son datos** en BD y referencian la clave del permiso como texto validado contra el registro.
- **Rationale**: el catálogo describe qué pantallas existen, y eso cambia solo cuando cambia el código. Si viviera en BD habría que sincronizarlo en cada despliegue. Los perfiles, en cambio, los edita Talento sin desplegar.
- **Alternatives**: `django.contrib.auth.Permission`/`Group`. No tiene alcance (propio/área/todos), está ligado a modelos y no a pantallas, y su UI es el admin de Django. Se descarta.

## R2. Alcance jerárquico

- **Decision**: los alcances son ordinales y cada uno **incluye a los menores**: `NINGUNO < PROPIO < ASIGNADO < AREA < TODOS`.
  - **ASIGNADO** incluye lo propio y los registros donde la persona tiene relación vigente (evaluador, responsable, validador, aprobador de la etapa, receptor).
  - **AREA** incluye lo anterior y lo de las personas de su área.
- **Rationale**: un Lead con alcance AREA que además es evaluador de alguien de otra área debe poder abrir esa evaluación. Con alcances excluyentes habría que conceder dos cosas. Así cada permiso tiene un solo valor por celda, que es lo que pidió la UI.
- Cada permiso declara qué alcances admite. Ej.: "Impacto Arena · editar" solo admite NINGUNO/TODOS.

## R3. Un perfil por usuario (Clarification P1)

- **Decision**: FK `User.profile` → `Profile` (PROTECT; no se puede borrar un perfil con usuarios). El superusuario ignora el perfil y lo puede todo. Sin perfil, se aplica el perfil `colaborador` (falla cerrado).

## R4. Evaluación eficiente

- **Decision**: `access.services.scope(user, key)` lee un dict `{clave: alcance}` cacheado **por request** en `request.user._access_grants`, cargado con 1 consulta (grants del perfil). Encima de ella: `has(user, key, at_least="PROPIO")` y `scope_qs(user, key, qs, owner_field, area_field, assigned_q)` para filtrar listados.
- **Rationale**: el menú, la campana y la vista consultan decenas de permisos por request. Con el caché son O(1) y una sola consulta.
- Los cambios aplican en el siguiente request (FR-008) porque el caché vive en el request, no en la sesión.

## R5. Aplicación en vistas y cobertura (FR-003/FR-014)

- **Decision**: decorador `@requires("clave", at_least=...)` en **cada vista**. Marca la función con `view._access_key`, responde 403 con la plantilla de error en español y fija `request.access_scope` para filtrar.
  - Las vistas con varias acciones (p. ej. un POST con `action=approve|return`) verifican el permiso específico dentro, con `access.require(user, key, obj)`.
- **Prueba de cobertura** (`apps/core/tests/test_access_coverage.py`):
  - (a) recorre **todas** las rutas resueltas por el URLconf, salvo una lista de exentas explícita (login, logout, recuperación de contraseña, cambio de contraseña, Mi perfil, foto de usuario, ayuda, admin, media), y exige que cada vista tenga `_access_key` y que esa clave exista en el registro;
  - (b) exige que cada permiso del registro con estado activo proteja al menos una ruta, o esté marcado como `kind="assignable"` o `kind="inline"`.
- Esto deja listo al futuro agente auditor: la prueba es su verificación base.

## R6. Reglas de flujo que NO son permisos

- **Decision**: siguen en los servicios, como condición adicional a la matriz:
  - inmutabilidad de periodos Cerrados (spec 002);
  - "nadie se aprueba a sí mismo";
  - "solo el evaluado gestiona sus evaluadores";
  - "cerrar antes de pedir otro curso" y duplicados por liga.
- `permissions.py` queda como **fachada**: sus funciones (`visible_users`, `can_view_evaluation`, `can_capture_value_delivery`…) conservan la firma, pero internamente consultan la matriz más la relación. Así los ~40 puntos que las llaman no cambian.

## R7. Paridad "deber ser" (Clarification P2) y reporte previo

- **Decision**: la matriz semilla está en `seed-matrix.md` (revisada por el usuario) y se aplica con una migración de datos. Hay una sola definición de administrador: Talento + superusuario. Desaparece `permissions._is_admin` con Director.
- **Reporte FR-011b**: comando `manage.py access_report`. Para cada usuario compara la decisión **legacy**, que se conserva congelada en `apps/access/legacy.py` para este fin y luego se borra, contra la nueva, sobre cada clave de la matriz. Lista lo que se gana y lo que se pierde, más el uso histórico conocido, como las Entregas de Valor capturadas por Directores que no eran responsables.
- **Batería de paridad**: prueba parametrizada perfil × permiso que compara `legacy` contra `access` y exige que **toda** diferencia esté en `EXPECTED_CHANGES` (la lista de FR-011a). Corre sin HTTP: rápida, sin cientos de requests a Neon.

## R8. Perfil independiente del nivel (Clarification P3)

- **Decision**: `User.is_lead` deja de usarse para **permisos**; sigue existiendo para cuestionarios y ponderaciones.
- La capacidad "es Lead" para flujos que hoy lo usan pasa a ser "tiene el permiso X con alcance AREA". Por ejemplo, los aprobadores Lead de Arena Learn salen de `learn.approve_lead` ≥ AREA dentro del área.
- **Migración**: perfil sugerido = `talento` si rol TALENTO, `director` si rol DIRECTOR, `lead` si nivel LEAD, y si no, `colaborador`.

## R9. Asignables

- **Decision**: permisos `kind="assignable"` con alcance NINGUNO/TODOS (`assign.ownership_evaluator`, `assign.project_role`, `assign.feedback_responsable`, `assign.direct_lead`, `assign.area_director`, `assign.learn_approver`).
  - Los selectores filtran con `access.assignable_users(key)`.
  - Las asignaciones vigentes que quedan "fuera de perfil" se listan en el resumen de Perfiles (FR-021); nunca se borran.

## R10. UI de la matriz

- **Decision**: pantalla `Catálogos → Perfiles y permisos` (`/catalogo/perfiles/`).
  - Lista de perfiles con conteo de usuarios.
  - Editor de matriz: tabla agrupada por módulo, filas de pantalla, columnas de acción y un `<select>` de alcance por celda, limitado a los alcances permitidos.
  - Se guarda con un POST de formulario, validado en servicio, con bitácora y toast.
  - htmx para guardar por módulo sin recargar.
- Asignación: columna "Perfil" en Usuarios (mismo patrón que "Lead directo", respetando el fix de filtro) y en el alta de usuario.
- Acceso efectivo: `/catalogo/perfiles/acceso/<user_pk>/`.

## R11. Ponderaciones

- **Decision**: se registra `catalog.weights` con estado **pendiente**: aparece en la matriz deshabilitada y la prueba de cobertura la exime de tener ruta. Se elimina del menú el enlace roto a `catalog:weight_admin`. Construir la pantalla queda fuera de alcance.
