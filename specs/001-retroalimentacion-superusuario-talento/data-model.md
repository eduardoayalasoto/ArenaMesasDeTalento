# Data Model: Reapertura de retroalimentación y vista de superusuario para Talento

No hay migración de base de datos en esta feature: reutiliza el esquema ya
existente de `TalentSessionNote` / `FeedbackResponsible`
(`apps/evaluations/models.py`). Este documento describe las entidades tal como
ya existen y el único elemento nuevo (un campo calculado en el view-model de la
tarjeta, no en la base de datos).

## Entidad existente: `TalentSessionNote`

Campos relevantes a esta feature (sin cambios):

| Campo | Tipo | Notas |
|---|---|---|
| `user` | FK → `User` | Persona que recibe la retroalimentación |
| `period` | FK → `EvaluationPeriod` | Periodo de evaluación |
| `feedback_agreed` | `BooleanField` (default `False`) | `True` = cerrada/acordada |
| `feedback_agreed_at` | `DateTimeField` (nullable) | Cuándo se cerró (o se reabrió: se limpia a `None`) |
| `feedback_agreed_by` | FK → `User` (nullable, `PROTECT`) | Quién la cerró (se limpia a `None` al reabrir) |
| `objetivo_desarrollo_1/2/3`, `expectativas_profesionales`, `expectativas_personales`, `comentarios_adicionales` | `TextField` | Contenido de la sesión; determinan `has_feedback_session` |
| `history` | `HistoricalRecords` (simple_history) | Auditoría automática de cada cambio de estos campos, incluida la reapertura |

### Estados derivados (sin campo `status` propio)

```text
Sin iniciar   →  has_feedback_session == False  y  feedback_agreed == False
Con avance    →  has_feedback_session == True   y  feedback_agreed == False
Cerrada       →  feedback_agreed == True
```

### Transición nueva cubierta por esta feature

```text
Cerrada  --reopen (autorizado)-->  Con avance | Sin iniciar
           (feedback_agreed=False, feedback_agreed_at=None, feedback_agreed_by=None;
            el contenido de texto no se toca, así que el estado resultante depende
            de si ya tenía contenido capturado — igual que hoy en el detalle)
```

No cambia el modelo de datos: la transición ya existe (rama `action == "reopen"`
en `feedback_session_detail`); lo que cambia es (a) desde dónde se puede
disparar (también desde la tarjeta) y (b) quién puede dispararla (también el
responsable asignado, no solo `is_admin`) — ver `research.md`, Decisión 1.

**Nota de auditoría (FR-004/SC-004)**: al reabrir, `feedback_agreed_by` y
`feedback_agreed_at` se limpian a `None` — los campos *vigentes* de la nota
deliberadamente no guardan a la vez "quién cerró" y "quién reabrió" (reflejan
solo el estado actual). El rastro de ambos eventos vive en el historial de
auditoría (`HistoricalRecords` / `simple_history`, ya activo vía
`simple_history.middleware.HistoryRequestMiddleware` en `config/settings.py`),
que registra `history_user`/`history_date` en cada `save()` — incluido el que
cierra y el que reabre. FR-004 se satisface por este mecanismo ya existente,
no por los campos actuales de `TalentSessionNote`; no se requiere ningún campo
nuevo (`reopened_by`/`reopened_at`), pero sí una prueba que lo confirme (ver
`tasks.md`, tarea de auditoría en Foundational).

## Entidad existente: `FeedbackResponsible`

Sin cambios. Sigue determinando, junto con `User.is_admin`, el resultado de
`permissions.can_edit_feedback_session(viewer, note)`:

```text
can_edit_feedback_session(viewer, note) =
    viewer.is_admin
    OR note.responsables.filter(user_id=viewer.pk).exists()
```

Esta es, sin cambios de firma ni de lógica, la función que pasa a gobernar
también el permiso de reabrir (antes gobernaba solo guardar/cerrar/ver-edición).

## Elemento nuevo (view-model, no persistido): `can_reopen` en la tarjeta

`_feedback_card()` (apps/dashboards/views.py:921) hoy arma un dict
`{note, target, final, projects, givers, viewer_role}` para cada tarjeta del
listado. Se agrega una clave:

| Campo nuevo | Tipo | Cómo se calcula |
|---|---|---|
| `can_reopen` | `bool` | `permissions.can_edit_feedback_session(request.user, note)` — calculado por el llamador (`feedback_session_list`) y pasado a `_feedback_card()`, no derivado del `viewer_role` |

No se persiste en base de datos: vive solo en el contexto de render de
`feedback_session_list` / `_feedback_session_card.html`.

## Elemento nuevo (view-model): sección `all_cards` en `feedback_session_list`

| Campo nuevo en el contexto | Tipo | Contenido |
|---|---|---|
| `all_cards` | `list[dict]` | Solo poblada si `request.user.is_admin`. Tarjetas (mismo shape que las demás) de toda `TalentSessionNote` del periodo activo cuyo `pk` no esté ya en `primary_cards`/`secondary_cards`/`own_cards`. `viewer_role="Talento"` en cada una. |

`viewer_role="Talento"` es un valor nuevo para ese campo (antes solo
`"Principal"`/`"Secundario"`/`"Receptor"`); el template de la tarjeta ya cae en
su rama `{% else %}` genérica para el badge y para el título de la sección de
responsables, así que no requiere una rama nueva — ver `research.md`, Decisión 3.
