# Quickstart: validar Reapertura de retroalimentación y vista de superusuario

Guía de validación manual/automatizada de extremo a extremo, una vez
implementadas las tareas de `tasks.md`. No repite el modelo de datos
(`data-model.md`) ni las decisiones de diseño (`research.md`).

## Prerrequisitos

- Entorno local funcionando: `./.venv/Scripts/python.exe manage.py runserver`
  (o el flujo que uses habitualmente para levantar el proyecto).
- Un periodo de evaluación **abierto** (`EvaluationPeriod.Status.ABIERTO`).
- Al menos:
  - Un usuario con `role=TALENTO` (superusuario de Talento) — p. ej. reutiliza
    el fixture `talento` de `apps/core/tests/conftest.py`.
  - Un usuario Lead/responsable normal (sin `is_admin`).
  - Una `TalentSessionNote` del periodo abierto con un `FeedbackResponsible`
    asignado a ese Lead (principal).
  - Una segunda `TalentSessionNote` del mismo periodo **sin ningún**
    `FeedbackResponsible` asignado (nota huérfana) — para probar la Historia 2.

## Validación automatizada (pytest)

```bash
./.venv/Scripts/python.exe -m pytest apps/core/tests/test_feedback_session.py -v
./.venv/Scripts/python.exe -m pytest apps/core/tests/test_period_progress_pending_people.py -v
```

Resultado esperado tras implementar `tasks.md`:

- `test_solo_talento_puede_reabrir` (existente) queda **actualizado** para
  reflejar que el responsable asignado también puede reabrir — ya no debe
  llamarse "solo Talento puede reabrir" si el nombre del test se conserva sin
  actualizar, revisar que el nombre y el cuerpo del test sigan describiendo el
  comportamiento correctamente.
- Nuevos tests (ver `tasks.md`) verifican: reabrir desde la tarjeta (POST a
  `feedback_session_detail` con `action=reopen` y `next` apuntando al listado),
  que un tercero sin asignación ni `is_admin` sigue recibiendo 403, y que
  `feedback_session_list` incluye `all_cards` solo para `is_admin` y sin
  duplicar tarjetas ya presentes en `primary_cards`/`secondary_cards`/`own_cards`.

## Validación manual — Historia 1 (reabrir desde la tarjeta)

1. Como el Lead/responsable normal, entra a `/retroalimentacion/` y abre la
   retroalimentación asignada; ciérrala con "Marcar como acordado" (`action=agree`).
2. Vuelve a `/retroalimentacion/`: la tarjeta debe mostrar el badge
   "Acordada · cerrada" **y** un botón "Reabrir" visible ahí mismo (sin entrar
   al detalle) — porque ese mismo Lead sigue siendo su responsable asignado.
3. Presiona "Reabrir" en la tarjeta: la página debe permanecer en el listado
   (no navegar al detalle), y la tarjeta debe reflejar el estado anterior
   ("Con avance" o "Sin iniciar" según el contenido ya capturado).
4. Repite el cierre; esta vez inicia sesión como un usuario que **no** es
   responsable de esa nota ni tiene `role=TALENTO`/superusuario — confirma que
   no ve ningún botón "Reabrir" en ninguna tarjeta suya, y que un POST directo
   a la URL de reabrir devuelve 403.

## Validación manual — Historia 2 (vista de superusuario)

1. Crea o ubica una `TalentSessionNote` del periodo abierto donde el usuario
   Talento **no** es responsable asignado ni receptor.
2. Inicia sesión como ese usuario Talento y entra a `/retroalimentacion/`:
   debe aparecer una sección adicional (p. ej. "Todas") con esa nota, mostrando
   su estado real y sin estar duplicada si además apareciera en alguna de las
   otras tres secciones.
3. Desde esa tarjeta o su detalle, confirma que Talento puede: ver, editar,
   cerrar el acuerdo (desde el detalle) y reabrir (desde la tarjeta o el
   detalle) esa retroalimentación ajena.
4. Inicia sesión como Director (sin `is_admin`) y confirma que **no** ve esa
   sección ampliada — su listado sigue mostrando solo sus propias tarjetas.

## Criterio de éxito

Si los 4 pasos manuales de cada historia se comportan como se describe y la
suite de pytest pasa en verde, la feature cumple SC-001 a SC-004 de `spec.md`.
