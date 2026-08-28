# Implementation Plan: Reapertura de retroalimentación y vista de superusuario para Talento

**Branch**: `001-retroalimentacion-superusuario-talento` | **Date**: 2026-08-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-retroalimentacion-superusuario-talento/spec.md`

## Summary

Dos cambios sobre el dominio ya existente de retroalimentación de Mesa de Talento
(`TalentSessionNote` / `FeedbackResponsible`, app `apps.dashboards` + `apps.evaluations`):

1. Exponer el control "Reabrir" (que ya existe hoy, pero solo dentro de
   `feedback_session_detail`) también directamente en la tarjeta del listado
   (`_feedback_session_card.html`), y ampliar quién puede usarlo: hoy solo
   `request.user.is_admin`; pasa a ser cualquiera para quien
   `permissions.can_edit_feedback_session(viewer, note)` sea verdadero (responsable
   asignado —principal o secundario— o superusuario de Talento), el mismo criterio
   que ya rige para cerrar y editar.
2. Ampliar `feedback_session_list` para que, cuando el viewer sea superusuario de
   Talento (`request.user.is_admin`), se agregue una cuarta sección con **todas**
   las `TalentSessionNote` del periodo activo (sin filtrar por responsable/receptor),
   con las mismas acciones que ya tiene el detalle.

No se agrega ningún endpoint público ni API — es una feature 100% interna a las
vistas Django server-rendered que ya existen.

## Technical Context

**Language/Version**: Python 3.14 (venv del repo), Django 6.0.6

**Primary Dependencies**: Django (server-rendered, sin DRF/API), `django-simple-history` (auditoría vía `HistoricalRecords`, ya presente en `TalentSessionNote`), Tailwind (clases utilitarias en templates, sin build step propio)

**Storage**: PostgreSQL en producción/preview (`psycopg`), SQLite en desarrollo/tests — mismo modelo `TalentSessionNote`/`FeedbackResponsible` ya existente, sin cambios de esquema

**Testing**: `pytest` + `pytest-django` (suite ya existente en `apps/core/tests/`, en particular `test_feedback_session.py`)

**Target Platform**: Aplicación web Django desplegada (no aplica mobile/desktop)

**Project Type**: Web application monolítica Django (server-rendered templates, sin frontend separado)

**Performance Goals**: N/A — herramienta interna de bajo volumen (decenas/cientos de registros por periodo); no hay metas de throughput específicas

**Constraints**: Ninguna restricción técnica nueva; reutiliza permisos y modelo existentes sin migración de base de datos

**Scale/Scope**: Cambio acotado a 2 vistas (`feedback_session_list`, `feedback_session_detail`) y 2 templates (`_feedback_session_card.html`, `feedback_session_list.html`) dentro de `apps/dashboards`; sin nuevas apps ni modelos

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` sigue siendo la plantilla sin llenar (placeholders
`[PRINCIPLE_N_NAME]` sin resolver) — no hay principios de proyecto ratificados
todavía, por lo tanto no hay gates que evaluar. No se detectan violaciones porque
no hay contra qué comparar. Recomendación (no bloqueante): correr
`/speckit-constitution` en algún momento para fijar principios explícitos del
proyecto (p. ej. "reusar `permissions.py` como única fuente de verdad de
autorización", ya seguido de facto por este plan).

*Re-chequeo post-diseño (tras Fase 1)*: sin cambios — `research.md` y
`data-model.md` no introducen ninguna dependencia, servicio externo o patrón
que requiera evaluarse contra principios (no hay ninguno ratificado). Gate
sigue pasando trivialmente.

## Project Structure

### Documentation (this feature)

```text
specs/001-retroalimentacion-superusuario-talento/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

No se genera `contracts/`: esta feature no expone ni consume ninguna API/contrato
externo — son vistas Django server-rendered internas, cubiertas por tests de vista
(`pytest-django` + `Client`), no por contratos de API.

### Source Code (repository root)

```text
apps/
├── evaluations/
│   └── models.py                 # TalentSessionNote, FeedbackResponsible (sin cambios de esquema)
├── core/
│   ├── services/
│   │   └── permissions.py        # can_edit_feedback_session / can_view_feedback_session (reutilizadas, sin cambios de firma)
│   └── tests/
│       └── test_feedback_session.py   # tests existentes a extender/actualizar
└── dashboards/
    ├── views.py                  # feedback_session_list, feedback_session_detail, _feedback_card (a modificar)
    └── urls.py                   # sin cambios (mismas rutas: retroalimentacion/, retroalimentacion/<pk>/)

templates/dashboards/
├── _feedback_session_card.html   # agregar botón "Reabrir" condicional
├── feedback_session_list.html    # agregar 4ª sección "Todas" para is_admin
└── feedback_session_detail.html  # sin cambios de fondo (ya tiene reabrir; solo cambia la condición de permiso subyacente)
```

**Structure Decision**: Todo el trabajo vive dentro de la app `apps.dashboards` ya
existente (vistas + templates) más el módulo compartido `apps.core.services.permissions`;
no se crea ninguna app, modelo o ruta nueva. Es una extensión de una feature
existente, no una feature aislada con estructura propia.

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

No aplica — no hay constitution ratificada ni violaciones que justificar.
