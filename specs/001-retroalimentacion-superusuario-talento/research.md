# Research: Reapertura de retroalimentación y vista de superusuario para Talento

No queda ningún `NEEDS CLARIFICATION` en el Technical Context del plan — el
Technical Context se llenó completo a partir del código ya existente (Django
6.0.6 / Python 3.14, `apps.dashboards` + `apps.evaluations` + `apps.core.services.permissions`,
`pytest-django`), y las dos ambigüedades de producto ya se resolvieron en
`/speckit-clarify` (ver `## Clarifications` en `spec.md`). Este documento cubre
las decisiones de diseño necesarias para pasar de la spec a un plan concreto,
que no estaban explícitas en el spec por ser detalles de implementación.

## Decisión 1 — Quién puede reabrir: reutilizar `can_edit_feedback_session`

**Decision**: El chequeo de permiso para la acción `reopen` deja de ser
`request.user.is_admin` (código actual en `feedback_session_detail`,
`apps/dashboards/views.py:1018`) y pasa a ser
`permissions.can_edit_feedback_session(request.user, note)` — la misma función
ya usada para autorizar `save`/`agree` y para decidir si el detalle es editable.

**Rationale**: `can_edit_feedback_session` (apps/core/services/permissions.py:75-77)
ya define exactamente el conjunto de personas autorizadas que la spec pide para
reabrir: `viewer.is_admin or note.responsables.filter(user_id=viewer.pk).exists()`
— es decir, responsable asignado (principal o secundario) o superusuario de
Talento. No hace falta una función nueva ni un criterio distinto: reabrir pasa a
tener el mismo alcance de permiso que cerrar/editar, tal como se resolvió en
`/speckit-clarify`.

**Alternatives considered**:
- Crear una función nueva `can_reopen_feedback_session` idéntica a
  `can_edit_feedback_session` — rechazada por duplicar lógica sin aportar nada;
  si el alcance de permisos diverge en el futuro, se puede separar entonces.
- Mantener `is_admin` para reabrir y agregar un permiso aparte solo para el
  responsable — rechazada porque contradice la respuesta de `/speckit-clarify`
  (el responsable debe tener el mismo alcance que ya tiene para cerrar).

## Decisión 2 — Botón "Reabrir" en la tarjeta sin salir del listado

**Decision**: El formulario de "Reabrir" en `_feedback_session_card.html`
apunta al mismo endpoint que ya usa el detalle
(`dashboards:feedback_session_detail`, POST con `action=reopen`), agregando un
campo oculto `next` con la URL del listado
(`{% url 'dashboards:feedback_session_list' %}`). La vista `feedback_session_detail`,
en la rama `action == "reopen"`, redirige a `request.POST.get("next")` si viene
presente y es una ruta interna válida, y si no, conserva su comportamiento
actual (`redirect("dashboards:feedback_session_detail", pk=target.pk)`).

**Rationale**: Evita crear una vista/URL nueva solo para esta variante de la
misma mutación (menor superficie, reutiliza el permiso y el registro de
auditoría ya implementados una sola vez). El botón "Reabrir" que ya existe hoy
dentro del detalle sigue funcionando igual (no manda `next`, conserva su
redirect). Satisface el criterio de aceptación "sin necesitar entrar al
detalle" / "sin salir de esa pantalla": tras el POST, quien reabrió desde la
tarjeta vuelve a ver el listado (recargado, con la tarjeta ya en estado
editable), no el detalle.

**Alternatives considered**:
- Vista/URL nueva dedicada `feedback_session_reopen` solo para la tarjeta —
  rechazada por duplicar el chequeo de permiso y el bloque de auditoría que ya
  existen en `feedback_session_detail`.
- Reabrir vía fetch/HTMX sin recargar la página y actualizar la tarjeta in-place
  — es una mejora de UX válida a futuro, pero no la pide la spec (que solo exige
  no tener que *entrar al detalle*, no exige que no haya recarga de página) y
  añade complejidad de frontend fuera de alcance de esta iteración.

## Decisión 3 — Cómo se arma la 4ª sección "Todas" para el superusuario de Talento

**Decision**: `feedback_session_list` agrega una cuarta lista de tarjetas,
`all_cards`, poblada **solo cuando `request.user.is_admin`**, con las
`TalentSessionNote` del periodo activo que **no** aparecen ya en
`primary_cards`, `secondary_cards` u `own_cards` (deduplicadas por `note.pk`).
El `viewer_role` de esas tarjetas usa una nueva etiqueta ("Talento") distinta de
"Principal"/"Secundario"/"Receptor".

**Rationale**: Evita mostrar la misma retroalimentación duplicada dos veces
(una en su sección personal y otra en "Todas") cuando el propio superusuario de
Talento también es responsable o receptor de esa nota — el union de las 4
secciones ya cubre el 100% de las retroalimentaciones del periodo (cumple
FR-005/SC-002) sin ruido visual.

**Alternatives considered**:
- Que "Todas" muestre literalmente todas las notas del periodo sin excluir las
  que ya aparecen arriba — rechazada por duplicar tarjetas para el caso (poco
  frecuente pero real) de que Talento sea además responsable/receptor de
  alguna.
- Reemplazar las 3 secciones personales por una sola tabla/lista para
  superusuarios — rechazada: se pierde la distinción "doy / asisto / recibo"
  que sigue siendo información útil incluso para Talento, y es un cambio de UX
  más invasivo que lo que pide la spec.

## Decisión 4 — El template de la tarjeta necesita el flag de permiso, no solo el rol

**Decision**: `_feedback_card()` (apps/dashboards/views.py:921) recibe y agrega
al diccionario de la tarjeta un nuevo campo `can_reopen: bool`, calculado en el
llamador como `permissions.can_edit_feedback_session(request.user, note)` — el
template ya no infiere el permiso a partir de `viewer_role` (que es solo una
etiqueta de UI, no una fuente de autorización).

**Rationale**: `viewer_role` ("Principal"/"Secundario"/"Receptor"/"Talento") es
una etiqueta puramente visual; el permiso real de reabrir depende de
`can_edit_feedback_session`, que ya contempla superusuario y responsable
asignado de forma unificada. Calcularlo una sola vez en la vista (en vez de
reimplementar la regla en el template) evita divergencia entre lo que el
template muestra y lo que la vista efectivamente autoriza.

**Alternatives considered**:
- Inferir el permiso en el template a partir de `viewer_role in ('Principal',
  'Secundario') or request.user.is_admin` — rechazada: duplica en Django
  Template Language una regla que ya vive en `permissions.py`, con riesgo de
  que diverjan si la regla cambia ahí.
