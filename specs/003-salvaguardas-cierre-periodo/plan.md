# Implementation Plan: Salvaguardas de UX y completitud de datos para el cierre/apertura de Periodos de Evaluación

**Branch**: `003-salvaguardas-cierre-periodo` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-salvaguardas-cierre-periodo/spec.md`

## Summary

Tres mejoras de interfaz sobre el motor de ciclo de vida ya construido en
`002-ciclo-vida-periodos` (sin tocar la lógica de negocio existente de
`period_lifecycle.py`, solo agregándole una función nueva de solo lectura):

1. Confirmación explícita (`confirm()` de navegador, mismo patrón que
   "Eliminar periodo") antes de Abrir o Cerrar un periodo en
   `apps/catalog/views.py::period_admin` / `templates/catalog/period_admin.html`.
2. El texto de esa confirmación de cierre incluye un resumen de actividad
   pendiente (Ownership sin enviar, Entrega de Valor sin validar,
   calificaciones incompletas), calculado con una función nueva y
   compartida en `apps/core/services/period_lifecycle.py` para no duplicar
   las consultas que ya hace `apps/dashboards/views.py::period_progress`.
3. Campo de texto "motivo" (obligatorio solo cuando aplica la excepción de
   corrección de un periodo Cerrado) en las pantallas de Ownership y Entrega
   de Valor, replicando el patrón ya implementado en
   `templates/dashboards/feedback_session_detail.html`. La acción
   "Reiniciar" de Ownership se oculta sobre un periodo Cerrado (FR-011a): no
   se le agrega motivo, se bloquea directamente.

   **Hallazgo de investigación que amplía el alcance necesario de (3)**:
   `ownership_list`, `ownership_validation` y `value_delivery_list` solo
   operan sobre el periodo Abierto vigente, y `value_delivery_capture`
   siempre resuelve `require_open_period()` en cada solicitud — ninguna
   permite navegar a un periodo Cerrado específico. Sin extenderlas con el
   mismo patrón `?periodo=<id>` que ya usan `feedback_session_list` y
   `talent_person` (002), el campo de motivo de (3) sería inalcanzable por
   navegación normal. Se extrae el helper de resolución de periodo
   (duplicado hoy en `apps/dashboards/views.py`) a
   `period_lifecycle.resolve_requested_period(request)` para reutilizarlo
   también en `apps/evaluations/views.py`, en vez de duplicarlo una vez más.

## Technical Context

**Language/Version**: Python (venv del repo), Django 6.0.7

**Primary Dependencies**: Django (server-rendered, sin DRF/API); reutiliza
`apps/core/services/period_lifecycle.py` y `permissions.py` ya existentes de
`002-ciclo-vida-periodos`

**Storage**: Sin cambios de esquema — no hay migraciones en esta feature (es
puramente de interfaz sobre datos y funciones ya existentes)

**Testing**: `pytest` + `pytest-django`; se extiende
`apps/core/tests/test_period_lifecycle.py` (mismo archivo que ya cubre 002,
por cohesión temática) con los casos nuevos de esta feature

**Target Platform**: Aplicación web Django ya desplegada

**Project Type**: Web application monolítica Django (server-rendered)

**Performance Goals**: N/A — mismo volumen bajo que 002; el resumen de
actividad pendiente son a lo más 3 `COUNT()` adicionales, solo al renderizar
la fila del periodo Abierto en `/catalogo/periodos/`

**Constraints**: El cálculo de actividad pendiente hoy vive inline dentro de
`apps.dashboards.views.period_progress`, pero `apps.catalog` (donde vive la
confirmación de cierre) no depende de `apps.dashboards` ni debería empezar a
hacerlo. Se extrae a una función nueva en `apps/core/services/period_lifecycle.py`
(ya es la capa de servicios de la que ambas apps —`catalog` y las vistas de
`evaluations`/`dashboards`— dependen), y `period_progress` se refactoriza para
usarla también, eliminando la duplicación en vez de crearla.

**Scale/Scope**: `apps.catalog` (vista `period_admin`, template `period_admin.html`),
`apps.core.services` (2 funciones nuevas en `period_lifecycle.py`:
`pending_activity_counts` y `resolve_requested_period`), `apps.dashboards`
(`period_progress` y `_resolve_period` pasan a reusar las funciones nuevas,
sin cambio de comportamiento visible), `apps.evaluations` (vistas de listado
y captura de Ownership/Entrega de Valor extendidas con `?periodo=`, más el
input de motivo en sus templates)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` sigue siendo la plantilla sin llenar — no
hay principios ratificados, no hay gates que evaluar. No se detectan
violaciones porque no hay contra qué comparar.

*Re-chequeo post-diseño (tras Fase 1)*: sin cambios — la única decisión de
diseño (extraer `pending_activity_counts` a `period_lifecycle.py` en vez de
duplicar o crear una dependencia `catalog → dashboards`) sigue el mismo
principio de facto que ya aplicó 002 (capa de services compartida), sin
introducir nada nuevo que evaluar.

## Project Structure

### Documentation (this feature)

```text
specs/003-salvaguardas-cierre-periodo/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No se genera `contracts/`: sin API externa, son vistas Django server-rendered
internas y una función de servicio, cubiertas por tests de vista/unitarios.

### Source Code (repository root)

```text
apps/
├── catalog/
│   ├── views.py                   # period_admin: arma el texto de confirmación
│   │                              #   (nombre de periodo, siguiente contiguo, conteos pendientes)
│   │                              #   y lo pasa al contexto por fila
│   └── (sin cambios de modelo/migraciones)
│
├── core/
│   └── services/
│       └── period_lifecycle.py    # NUEVAS: pending_activity_counts(period) y
│                                   #   resolve_requested_period(request) — ambas de
│                                   #   solo lectura, sin efectos secundarios
│
├── dashboards/
│   └── views.py                   # period_progress usa pending_activity_counts;
│                                   #   _resolve_period se vuelve un alias/uso directo
│                                   #   de resolve_requested_period (sin duplicar lógica)
│
└── evaluations/
    ├── views.py                    # ownership_list/ownership_validation/value_delivery_list/
    │                              #   value_delivery_capture: usan resolve_requested_period
    │                              #   en vez de forzar siempre el periodo Abierto;
    │                              #   value_delivery_capture solo CREA una VD nueva si el
    │                              #   periodo resuelto es el Abierto (nunca sobre uno Cerrado);
    │                              #   ownership_autosave lee `reason` del payload JSON;
    │                              #   _render_ownership calcula can_correct_closed y ajusta
    │                              #   can_reset (FR-011a); value_delivery_review añade motivo
    │                              #   a validar/rechazar/comentar (protege el POST-por-pk
    │                              #   existente, aunque su queue no liste periodos Cerrados)
    └── (sin cambios de modelo)

templates/
├── catalog/
│   └── period_admin.html          # onclick="return confirm(...)" en los botones Abrir/Cerrar
├── evaluations/
│   ├── ownership_list.html         # selector de periodo (?periodo=) para Talento
│   ├── ownership_validation.html   # ídem
│   ├── value_delivery_list.html    # ídem
│   ├── ownership_fill.html        # input "motivo" (Alpine, junto a guardar/reabrir);
│   │                               #   bloque de "Reiniciar" oculto si periodo Cerrado
│   ├── value_delivery_capture.html # input "motivo" condicional
│   └── value_delivery_review.html  # input "motivo" condicional en validar/rechazar/comentar
```

**Structure Decision**: Todo el trabajo se distribuye entre las apps ya
existentes; el único código nuevo no-UI es una función de solo lectura en
`period_lifecycle.py`. No se crea ninguna app, modelo, migración o ruta
nueva.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No aplica — no hay constitution ratificada ni violaciones que justificar.
