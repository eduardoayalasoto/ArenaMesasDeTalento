# Implementation Plan: Matriz de permisos por perfiles

**Branch**: `005-matriz-permisos-perfiles` | **Date**: 2026-10-07 | **Spec**: [spec.md](./spec.md)

## Summary

Los permisos fijos por rol pasan a ser datos. Un **registro declarativo** en código cataloga cada pantalla y acción (≈50 claves que cubren las ~95 rutas). Los **perfiles** son datos editables por Talento y conceden a cada clave un alcance jerárquico: — / Propio / Asignado / Área / Todos.

Cada usuario tiene **un** perfil, independiente de su nivel. El decorador `@requires` protege cada vista. `permissions.py` queda como fachada que consulta la matriz más la relación, así que sus llamadores no cambian. El menú, la campana y los botones se derivan de la matriz.

Una prueba de cobertura falla si una ruta no está mapeada. Una batería de paridad compara la regla anterior contra la matriz semilla "deber ser", y toda diferencia debe estar listada como cambio esperado. El comando `access_report` avisa a Talento qué cambia para cada persona antes de activar.

## Technical Context

**Language/Version**: Python 3.14 / 3.12 (Vercel), Django 6.0

**Primary Dependencies**: Django; htmx, Alpine y Lucide (vendorizados). Sin dependencias nuevas.

**Storage**: Postgres (Neon). Migraciones: `access` 0001 + 0002 (semilla), `accounts` (User.profile).

**Testing**: pytest contra `test_neondb --reuse-db`, con pruebas compactas por escenario. La cobertura y la paridad corren sin HTTP: son rápidas y no hacen cientos de requests a Neon.

**Target Platform**: Vercel + Neon.

**Project Type**: monolito Django server-rendered.

**Performance Goals**: 1 consulta adicional por request (las concesiones del perfil), cacheada en el request.

**Constraints**:
- Se despliega con un periodo Abierto: la activación no puede romper la operación.
- Falla cerrado.
- El superusuario siempre tiene acceso total.

**Scale/Scope**: ~95 rutas en 6 apps, ≈50 permisos, 5 perfiles semilla, 62 usuarios.

## Constitution Check

No hay constitución ratificada. Convenciones del repo:
- La lógica va en `apps/core/services/`; aquí se usa `apps/access/services.py`, igual que `learning` usa `learning_flow`.
- El filtrado se hace a nivel queryset.
- No se usa CDN.
- La UI está en español.

✅ Sin violaciones. La app nueva se justifica en Complexity Tracking.

## Project Structure

```text
apps/access/                       # NUEVA
├── registry.py                    # PermissionDef + PERMISSIONS (catálogo) + EXEMPT_ROUTES
├── seed.py                        # SEED_MATRIX (deber ser) + suggested_profile(user)
├── legacy.py                      # reglas anteriores congeladas (solo para paridad/reporte; se borra después)
├── models.py                      # Profile, ProfileGrant, AccessAuditLog
├── services.py                    # scope(), has(), require(), scope_qs(), assignable_users(),
│                                  # set_grant(), assign_profile(), effective_access(), guardias FR-007
├── decorators.py                  # @requires(key, at_least)
├── context.py                     # helpers para menú/plantillas ({% can 'clave' %})
├── templatetags/access_tags.py
├── views.py / urls.py / forms.py  # /catalogo/perfiles/ (lista, matriz, acceso efectivo)
├── management/commands/access_report.py
└── migrations/0001_initial.py, 0002_seed_profiles.py
apps/accounts/models.py            # + User.profile; views user_admin/user_create: selector de perfil
apps/core/services/permissions.py  # fachada → access (una sola definición de admin)
apps/core/services/learning_flow.py# aprobadores por permiso (learn.approve.*), is_course_approver por matriz
apps/core/context_processors.py    # menú y campana derivados de la matriz; quitar weight_admin roto
apps/*/views.py                    # @requires en cada vista (≈95)
templates/access/*.html            # profiles_list, matrix, effective_access
templates/**                       # botones condicionados con {% can %}
apps/core/tests/test_access.py, test_access_coverage.py, test_access_parity.py
```

## Fases

1. **Fundación**: modelos, registro, servicios, decorador, semilla, migraciones y prueba de cobertura (falla hasta completar la fase 2).
2. **Aplicación**: `@requires` en todas las vistas, fachada `permissions.py`, Arena Learn por permiso, menú y campana.
3. **UI**: matriz, selector en Usuarios y acceso efectivo.
4. **Paridad y reporte**: `legacy.py`, batería de paridad, `access_report`.
5. **Entrega**: reporte a Talento, migraciones a Neon y push.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| App nueva `apps/access` | El dominio de autorización es transversal a todas las apps | Meterlo en `core` mezclaría modelos con servicios genéricos; `auth.Group` no tiene alcance ni pantallas |
| `legacy.py` temporal | Es la única forma de demostrar la paridad y generar el reporte FR-011b | Comparar a mano ~95 rutas × 5 perfiles es propenso a error; se borra tras la activación |
