# Implementation Plan: Ciclo de vida y continuidad de Periodos de Evaluación

**Branch**: `002-ciclo-vida-periodos` | **Date**: 2026-09-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-ciclo-vida-periodos/spec.md`

## Summary

Refuerza el ciclo de vida de `catalog.EvaluationPeriod` (ya existe con `status`
PLANEADO/ABIERTO/CERRADO, pero hoy sin ninguna validación de transición ni de
continuidad) para garantizar tres invariantes de negocio: (1) a lo más un
periodo Abierto en todo el sistema, (2) continuidad sin huecos/traslapes entre
periodos hacia adelante, y (3) inmutabilidad de los registros de un periodo
Cerrado, con una excepción auditada para Talento/superusuario. El cierre de un
periodo abre automáticamente, en la misma transacción, el siguiente periodo
Planeado contiguo.

El refuerzo aplica a los 6 modelos que hoy tienen FK uno-a-uno a
`EvaluationPeriod`: `OwnershipEvaluation`, `ValueDeliveryEvaluation`,
`ArenaImpactScore`, `FinalScore`, `TalentSessionNote` (nota + acuerdo de
sesión, mismo registro) y `MesaProjectReview`. No se crea ninguna app nueva;
se extiende `apps.catalog` (modelo `EvaluationPeriod` + vistas/forms de
administración) y se agrega un módulo de orquestación
`apps/core/services/period_lifecycle.py`, siguiendo el mismo patrón que ya
usan `ownership_flow.py`, `value_delivery_flow.py` y `final_flow.py`.

## Technical Context

**Language/Version**: Python (venv del repo), Django 6.0.7

**Primary Dependencies**: Django (server-rendered, sin DRF/API), `django-simple-history` (auditoría vía `HistoricalRecords`, ya presente en 5 de los 6 modelos afectados; falta en `FinalScore`)

**Storage**: PostgreSQL en producción/preview (`psycopg`), SQLite en desarrollo/tests — requiere migraciones nuevas en `apps.catalog` (constraint de unicidad de periodo Abierto) y en `apps.evaluations` (agregar `history` a `FinalScore`)

**Testing**: `pytest` + `pytest-django` (suite ya existente en `apps/core/tests/`; se extiende con pruebas nuevas para el ciclo de vida de periodos)

**Target Platform**: Aplicación web Django desplegada (no aplica mobile/desktop)

**Project Type**: Web application monolítica Django (server-rendered templates, sin frontend separado)

**Performance Goals**: N/A — herramienta interna de bajo volumen (decenas de periodos en la vida del sistema, cientos/miles de registros por periodo); no hay metas de throughput específicas

**Constraints**: La validación de continuidad (FR-003) debe comportarse igual en SQLite (tests/dev) y PostgreSQL (prod/preview) — descarta mecanismos exclusivos de Postgres como `EXCLUDE USING gist` sobre rangos de fecha; se resuelve a nivel de aplicación (`clean()`), como ya hace el proyecto para otras reglas de negocio (`ValueDeliveryEvaluation.clean()`, `ScaleOption.clean()`)

**Scale/Scope**: `apps.catalog` (modelo `EvaluationPeriod`, `PeriodForm`, vistas `period_create`/`period_edit`), `apps.evaluations` (6 modelos + puntos de entrada de creación/edición en `views.py` y en los services `ownership_flow.py`/`value_delivery_flow.py`), `apps.dashboards` (vistas de consulta histórica y reportes agregados), `apps.core.services` (extender `permissions.py`, nuevo `period_lifecycle.py`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` sigue siendo la plantilla sin llenar
(placeholders `[PRINCIPLE_N_NAME]` sin resolver) — no hay principios de
proyecto ratificados todavía, por lo tanto no hay gates que evaluar. No se
detectan violaciones porque no hay contra qué comparar.

*Re-chequeo post-diseño (tras Fase 1)*: sin cambios — `research.md` y
`data-model.md` reutilizan patrones ya existentes en el código (constraint
parcial, `clean()` de modelo, capa de services) sin introducir dependencias
externas nuevas ni arquitectura ajena al proyecto. Gate sigue pasando
trivialmente.

## Project Structure

### Documentation (this feature)

```text
specs/002-ciclo-vida-periodos/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── checklists/
│   └── requirements.md
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No se genera `contracts/`: esta feature no expone ni consume ninguna API/contrato
externo — son vistas Django server-rendered internas y un módulo de services,
cubiertos por tests de modelo/vista (`pytest-django`), no por contratos de API.

### Source Code (repository root)

```text
apps/
├── catalog/
│   ├── models.py                 # EvaluationPeriod: UniqueConstraint (status=ABIERTO) + clean() de continuidad
│   │                              #   e inmutabilidad de fechas/tipo fuera de estatus Planeado
│   ├── admin.py                   # EvaluationPeriodAdmin: status/start_date/end_date -> readonly_fields
│   │                              #   (evita bypassear period_lifecycle desde el admin de Django)
│   ├── forms.py                  # PeriodForm: ya llama full_clean() vía ModelForm, sin cambios de forma
│   ├── views.py                  # period_create/period_edit: usar period_lifecycle en vez de guardar status directo;
│   │                              #   nuevas vistas period_open/period_close (abre el siguiente automáticamente)
│   ├── urls.py                   # nuevas rutas periodos/<int:pk>/abrir/ y periodos/<int:pk>/cerrar/
│   └── migrations/                # nueva migración: constraint unique_open_period
│
├── evaluations/
│   ├── models.py                  # FinalScore: agregar `history = HistoricalRecords()`
│   ├── views.py                   # value_delivery_capture, ownership_*, arena_impact_*: usar period_lifecycle
│   │                              #   para bloquear creación sin periodo Abierto (FR-009) y edición de periodo Cerrado (FR-006)
│   └── migrations/                # nueva migración: historicalfinalscore
│
├── dashboards/
│   └── views.py                   # feedback_session_list/detail, period_progress, talent_person:
│                                   #   extender a consulta histórica de periodos Cerrados (FR-007/FR-015/FR-017)
│
└── core/
    ├── services/
    │   ├── period_lifecycle.py    # NUEVO: open/close/validar continuidad/assert_record_editable
    │   ├── permissions.py         # extender con is_period_correction_allowed(user) (Talento/superusuario)
    │   ├── ownership_flow.py      # usar period_lifecycle.assert_record_editable antes de guardar
    │   └── value_delivery_flow.py # ídem
    └── tests/
        └── test_period_lifecycle.py  # NUEVO: cobertura de las 5 historias de usuario de spec.md
```

**Structure Decision**: Todo el trabajo se distribuye entre las apps ya
existentes (`catalog`, `evaluations`, `dashboards`, `core.services`); no se
crea ninguna app nueva. El único módulo nuevo es
`apps/core/services/period_lifecycle.py`, que sigue el mismo patrón de
capa de orquestación que ya usan `ownership_flow.py`, `value_delivery_flow.py`
y `final_flow.py` (lógica de negocio fuera de las vistas, vistas delgadas que
llaman al service).

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No aplica — no hay constitution ratificada ni violaciones que justificar.
