# Data Model: Matriz de permisos por perfiles (005)

App nueva: `apps/access`.

## Registro (código, `apps/access/registry.py`)

```
PermissionDef(
  key: str            # "learn.approve.direction"
  module: str         # "Arena Learn"
  screen: str         # "Aprobar cursos — etapa Dirección"
  action: str         # ver | crear | editar | borrar | aprobar | exportar | asignable | otra
  scopes: tuple       # alcances admitidos, p. ej. (NINGUNO, AREA, TODOS)
  routes: tuple       # url names que protege (vacío para kind assignable/inline)
  kind: str           # "screen" | "inline" (acción dentro de una vista) | "assignable"
  status: str         # "active" | "pending" (p. ej. weights.manage)
)
```

`Scope` es un IntEnum: `NINGUNO=0, PROPIO=10, ASIGNADO=20, AREA=30, TODOS=40`. Cada alcance incluye a los menores.

## Modelos (BD)

### `Profile`
- `slug` (unique), `name`, `description`.
- `is_system`: True solo para `superusuario`. No se edita ni se asigna desde la UI.
- `created_at`, `updated_at`.

### `ProfileGrant`
- `profile` FK (CASCADE), `permission_key` (CharField 80), `scope` (PositiveSmallInteger).
- `unique_together (profile, permission_key)`.
- Validación: la clave debe existir en el registro y el alcance debe estar entre los que admite.
- Si un perfil no tiene concesión para una clave, el alcance es NINGUNO (falla cerrado).

### `User.profile` (cambio en `accounts.User`)
- FK → `Profile`, null, `on_delete=PROTECT`, `related_name="users"`.
- Si es null, se aplica el perfil `colaborador`.

### `AccessAuditLog` (inmutable)
- `actor` FK, `created_at`.
- `kind`: GRANT_CHANGED | PROFILE_CREATED | PROFILE_RENAMED | PROFILE_DELETED | PROFILE_ASSIGNED.
- `profile` FK null, `permission_key`, `old_value`, `new_value`, `target_user` FK null, `comment`.

## Migraciones

1. `access.0001_initial`: crea Profile, ProfileGrant y AccessAuditLog.
2. `accounts.00xx_user_profile`: agrega el campo `User.profile`.
3. `access.0002_seed_profiles`: migración de datos. Crea los perfiles y concesiones de `seed-matrix.md` (fuente: `apps/access/seed.py::SEED_MATRIX`) y asigna el perfil sugerido a cada usuario no superusuario según R8. Es idempotente.

## Reglas

- Hay que conservar siempre al menos un usuario activo, no superusuario, con `access.manage` = TODOS, o el superusuario (FR-007).
- No se puede borrar un perfil con usuarios ni un perfil de sistema.
- Cada cambio de concesión o de asignación genera una entrada en `AccessAuditLog`.
