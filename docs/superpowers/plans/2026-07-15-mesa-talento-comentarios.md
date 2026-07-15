# Mesa de Talento — campo Comentarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar un tercer campo libre "Mesa de Talento — Comentarios" a `TalentSessionNote`, editable solo por Talento con autosave y de solo lectura para Director, siguiendo exactamente el patrón ya existente de `fortalezas`/`oportunidades`.

**Architecture:** Un `TextField` nuevo en `TalentSessionNote` + una migración; una rama nueva en el `if/elif` de `talent_note_autosave` para guardarlo; un tercer bloque de UI en `talent_person.html` (editable con Alpine autosave para Talento, solo lectura para Director), ubicado después de Oportunidades y antes de Escenarios.

**Tech Stack:** Django 6, pytest + pytest-django, Alpine.js (autosave debounced), Tailwind (clases `card`, `input`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-15-mesa-talento-comentarios-design.md`.
- El campo se llama `comentarios` en el modelo (no confundir con `comentarios_adicionales`, que pertenece a la sesión de retroalimentación y no se toca).
- Mismos permisos que `fortalezas`/`oportunidades`: guardar requiere `request.user.is_admin` (Talento o superusuario); Director ve solo lectura.
- Ubicación en la UI: después del bloque de Oportunidades, antes del bloque de Escenarios (ambas ramas: editable y solo lectura).
- Ícono Lucide: `message-square`.
- Correr pruebas con `PYTHONIOENCODING=utf-8` y `pytest --reuse-db` (ver `docs/superpowers/specs/2026-07-15-mesa-talento-comentarios-design.md` y memoria de entorno: Neon vía `DATABASE_URL`, usar `--reuse-db`).
- Al terminar todas las tareas y con pruebas en verde: `git push origin main` y aplicar la migración a Neon producción (flujo de entrega automático del proyecto), sin pedir confirmación adicional.

---

### Task 1: Campo `comentarios` en el modelo + migración

**Files:**
- Modify: `apps/evaluations/models.py:266` (después de la línea de `oportunidades`)
- Create: `apps/evaluations/migrations/0010_talentsessionnote_comentarios_and_more.py` (generada con `makemigrations`, no escrita a mano)
- Test: `apps/core/tests/test_talent_session_note_comentarios.py`

**Interfaces:**
- Consumes: nada nuevo (usa `TalentSessionNote` y fixtures compartidas `period`, `collaborator` de `apps/core/tests/conftest.py`).
- Produces: `TalentSessionNote.comentarios` (`TextField`, `blank=True`, default `""`), consumido por Task 2 (vista) y Task 3 (template).

- [ ] **Step 1: Escribir la prueba que falla**

```python
"""TalentSessionNote debe tener un campo `comentarios` de Mesa de Talento, separado
de `comentarios_adicionales` (que pertenece a la sesión de retroalimentación)."""

import pytest

from apps.evaluations.models import TalentSessionNote


@pytest.mark.django_db
def test_comentarios_default_vacio(collaborator, period):
    note = TalentSessionNote.objects.create(user=collaborator, period=period)
    assert note.comentarios == ""


@pytest.mark.django_db
def test_comentarios_se_guarda_y_no_se_confunde_con_comentarios_adicionales(collaborator, period):
    note = TalentSessionNote.objects.create(
        user=collaborator, period=period,
        comentarios="Comentario general de la sesión de Mesa.",
        comentarios_adicionales="Comentario de la sesión de retroalimentación.",
    )
    note.refresh_from_db()
    assert note.comentarios == "Comentario general de la sesión de Mesa."
    assert note.comentarios_adicionales == "Comentario de la sesión de retroalimentación."
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `$env:PYTHONIOENCODING='utf-8'; pytest apps/core/tests/test_talent_session_note_comentarios.py -v --reuse-db`
Expected: FAIL — `TypeError` o `AttributeError` porque `comentarios` no existe todavía en `TalentSessionNote`.

- [ ] **Step 3: Agregar el campo al modelo**

En `apps/evaluations/models.py`, dentro de `TalentSessionNote`, justo después de la línea `oportunidades = models.TextField("oportunidades Mesa de Talento", blank=True)` (línea 266):

```python
    comentarios = models.TextField("comentarios Mesa de Talento", blank=True)
```

- [ ] **Step 4: Generar la migración**

Run: `$env:PYTHONIOENCODING='utf-8'; python manage.py makemigrations evaluations`
Expected: crea `apps/evaluations/migrations/0010_talentsessionnote_comentarios_and_more.py` (el nombre exacto lo decide Django; incluye el campo nuevo en `TalentSessionNote` y su espejo en `HistoricalTalentSessionNote`).

- [ ] **Step 5: Correr la prueba y confirmar que pasa**

Run: `$env:PYTHONIOENCODING='utf-8'; pytest apps/core/tests/test_talent_session_note_comentarios.py -v --reuse-db`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add apps/evaluations/models.py apps/evaluations/migrations/0010_talentsessionnote_comentarios_and_more.py apps/core/tests/test_talent_session_note_comentarios.py
git commit -m "feat(evaluations): agrega campo comentarios a TalentSessionNote"
```

---

### Task 2: Guardar `comentarios` vía `talent_note_autosave`

**Files:**
- Modify: `apps/dashboards/views.py:674-683` (rama `if/elif` de `field` dentro de `talent_note_autosave`)
- Test: `apps/core/tests/test_talent_note_comentarios_autosave.py`

**Interfaces:**
- Consumes: `TalentSessionNote.comentarios` (Task 1), vista existente `talent_note_autosave` (`apps/dashboards/views.py:655`, URL `dashboards:talent_note_autosave`, requiere JSON `{"field": ..., "value": ...}`).
- Produces: nada nuevo para otras tareas; Task 3 solo necesita saber que el POST con `field="comentarios"` guarda en `note.comentarios`.

- [ ] **Step 1: Escribir la prueba que falla**

```python
"""Autosave de Mesa de Talento debe aceptar field='comentarios', con los mismos
permisos que 'fortalezas'/'oportunidades' (solo Talento/superusuario)."""

import json

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.evaluations.models import TalentSessionNote

User = get_user_model()


@pytest.fixture
def talento_user(db):
    u = User.objects.create_user(
        email="talento-comentarios@arena-analytics.com", password="x",
        full_name="Talento Comentarios", role=User.Role.TALENTO,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.fixture
def director_user(db):
    u = User.objects.create_user(
        email="director-comentarios@arena-analytics.com", password="x",
        full_name="Director Comentarios", role=User.Role.DIRECTOR,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.mark.django_db
def test_talento_guarda_comentarios(client, talento_user, collaborator, period):
    client.force_login(talento_user)
    resp = client.post(
        reverse("dashboards:talent_note_autosave", kwargs={"pk": collaborator.pk}),
        data=json.dumps({"field": "comentarios", "value": "Buen desempeño general."}),
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    note = TalentSessionNote.objects.get(user=collaborator, period=period)
    assert note.comentarios == "Buen desempeño general."


@pytest.mark.django_db
def test_director_no_puede_guardar_comentarios(client, director_user, collaborator, period):
    client.force_login(director_user)
    resp = client.post(
        reverse("dashboards:talent_note_autosave", kwargs={"pk": collaborator.pk}),
        data=json.dumps({"field": "comentarios", "value": "Intento no permitido."}),
        content_type="application/json",
    )
    assert resp.status_code == 403
    assert not TalentSessionNote.objects.filter(user=collaborator, period=period).exists()
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `$env:PYTHONIOENCODING='utf-8'; pytest apps/core/tests/test_talent_note_comentarios_autosave.py -v --reuse-db`
Expected: FAIL en `test_talento_guarda_comentarios` — la vista responde `{"ok": false, "error": "Campo inválido."}` (400) porque `field == "comentarios"` no está contemplado.

- [ ] **Step 3: Agregar la rama en la vista**

En `apps/dashboards/views.py`, dentro de `talent_note_autosave`, agregar el `elif` antes del `else` final (después de la rama de `oportunidades`, línea ~681):

```python
    elif field == "comentarios":
        note.comentarios = value
        note.save(update_fields=["comentarios", "updated_at"])
```

- [ ] **Step 4: Correr la prueba y confirmar que pasa**

Run: `$env:PYTHONIOENCODING='utf-8'; pytest apps/core/tests/test_talent_note_comentarios_autosave.py -v --reuse-db`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add apps/dashboards/views.py apps/core/tests/test_talent_note_comentarios_autosave.py
git commit -m "feat(dashboards): autosave del campo comentarios en Mesa de Talento"
```

---

### Task 3: UI en `talent_person.html` (editable + solo lectura)

**Files:**
- Modify: `templates/dashboards/talent_person.html:58-75` (insertar bloque nuevo justo después del bloque de Oportunidades, antes del comentario `{# Escenarios #}`)
- Modify: `templates/dashboards/talent_person.html:122` (agregar `comentarios: null` al estado de Alpine)
- Modify: `templates/dashboards/talent_person.html:150-157` (insertar bloque solo lectura después de Oportunidades, antes de Escenarios)
- Test: `apps/core/tests/test_talent_person_comentarios_ui.py`

**Interfaces:**
- Consumes: `note.comentarios` (Task 1), endpoint `dashboards:talent_note_autosave` con `field="comentarios"` (Task 2), variable de contexto `note` ya presente en `talent_person` (vista en `apps/dashboards/views.py:577` construye `ctx` con `note` — confirmar que ya existe antes de escribir la prueba; si no, es un bug preexistente fuera de alcance de esta tarea).

- [ ] **Step 1: Escribir la prueba que falla**

```python
"""La ficha de Mesa de Talento debe mostrar el bloque 'Mesa de Talento — Comentarios',
editable para Talento y de solo lectura para Director."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.evaluations.models import TalentSessionNote

User = get_user_model()


@pytest.fixture
def talento_ui(db):
    u = User.objects.create_user(
        email="talento-ui-comentarios@arena-analytics.com", password="x",
        full_name="Talento UI", role=User.Role.TALENTO,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.fixture
def director_ui(db):
    u = User.objects.create_user(
        email="director-ui-comentarios@arena-analytics.com", password="x",
        full_name="Director UI", role=User.Role.DIRECTOR,
    )
    u.photo_data = b"fake-photo"
    u.photo_mime = "image/jpeg"
    u.save(update_fields=["photo_data", "photo_mime"])
    return u


@pytest.mark.django_db
def test_talento_ve_textarea_editable_de_comentarios(
    client, talento_ui, collaborator, project_finite, period, ownership_template
):
    from apps.evaluations.models import OwnershipEvaluation
    OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period, template=ownership_template,
    )
    TalentSessionNote.objects.create(
        user=collaborator, period=period, comentarios="Va bien encaminado.",
    )
    client.force_login(talento_ui)
    resp = client.get(reverse("dashboards:talent_person", kwargs={"pk": collaborator.pk}))
    html = resp.content.decode("utf-8")
    assert resp.status_code == 200
    assert "Mesa de Talento — Comentarios" in html
    assert 'name="comentarios"' in html
    assert "Va bien encaminado." in html


@pytest.mark.django_db
def test_director_ve_comentarios_solo_lectura(
    client, director_ui, collaborator, project_finite, period, ownership_template
):
    from apps.evaluations.models import OwnershipEvaluation
    OwnershipEvaluation.objects.create(
        user=collaborator, project=project_finite, period=period, template=ownership_template,
    )
    TalentSessionNote.objects.create(
        user=collaborator, period=period, comentarios="Comentario visible para Director.",
    )
    client.force_login(director_ui)
    resp = client.get(reverse("dashboards:talent_person", kwargs={"pk": collaborator.pk}))
    html = resp.content.decode("utf-8")
    assert resp.status_code == 200
    assert "Mesa de Talento — Comentarios" in html
    assert 'name="comentarios"' not in html
    assert "Comentario visible para Director." in html
```

- [ ] **Step 2: Correr la prueba y confirmar que falla**

Run: `$env:PYTHONIOENCODING='utf-8'; pytest apps/core/tests/test_talent_person_comentarios_ui.py -v --reuse-db`
Expected: FAIL — no aparece "Mesa de Talento — Comentarios" en el HTML todavía.

- [ ] **Step 3: Insertar el bloque editable**

En `templates/dashboards/talent_person.html`, después del `</div>` que cierra el bloque de Oportunidades (línea 74) y antes del comentario `{# Escenarios #}` (línea 76):

```html
    {# Comentarios #}
    <div class="card p-5">
      <label class="block text-sm font-semibold text-slate-700 mb-2">
        <span class="flex items-center gap-1.5">
          <i data-lucide="message-square" class="w-4 h-4 text-arena-600"></i>
          Mesa de Talento — Comentarios
          <span x-show="state.comentarios === 'saving'" class="text-xs text-slate-400 font-normal ml-2">Guardando…</span>
          <span x-show="state.comentarios === 'saved'" x-cloak class="text-xs text-emerald-600 font-normal ml-2 flex items-center gap-1">
            <i data-lucide="check" class="w-3 h-3"></i> Guardado
          </span>
        </span>
      </label>
      <textarea name="comentarios" rows="4"
        class="input w-full resize-y"
        placeholder="Comentarios generales de la sesión de Mesa de Talento…"
        @input.debounce.800ms="save('comentarios', $el.value)">{{ note.comentarios }}</textarea>
    </div>
```

- [ ] **Step 4: Agregar `comentarios` al estado de Alpine**

En la misma plantilla, cambiar (línea 122):

```html
        state: { fortalezas: null, oportunidades: null },
```

por:

```html
        state: { fortalezas: null, oportunidades: null, comentarios: null },
```

- [ ] **Step 5: Insertar el bloque de solo lectura**

Después del `</div>` que cierra el bloque de solo lectura de Oportunidades (línea 157) y antes del bloque de Escenarios (`<div class="card p-5">` que empieza en la línea 158):

```html
    <div class="card p-5">
      <h4 class="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <i data-lucide="message-square" class="w-4 h-4 text-arena-600"></i> Mesa de Talento — Comentarios
      </h4>
      <p class="text-slate-800 whitespace-pre-line leading-relaxed">{{ note.comentarios|default:"Sin información." }}</p>
    </div>
```

- [ ] **Step 6: Correr la prueba y confirmar que pasa**

Run: `$env:PYTHONIOENCODING='utf-8'; pytest apps/core/tests/test_talent_person_comentarios_ui.py -v --reuse-db`
Expected: PASS (2 tests).

- [ ] **Step 7: Reiniciar `runserver` si estaba corriendo y verificar visualmente**

Las plantillas no recargan en caliente en este proyecto. Si hay un `runserver` activo, reiniciarlo y abrir `/mesa-talento/persona/<pk>/` como Talento y como Director para confirmar visualmente el bloque nuevo en la posición correcta (después de Oportunidades, antes de Escenarios) y que el autosave funciona (indicador "Guardando…" → "Guardado").

- [ ] **Step 8: Commit**

```bash
git add templates/dashboards/talent_person.html apps/core/tests/test_talent_person_comentarios_ui.py
git commit -m "feat(dashboards): agrega bloque Comentarios a la ficha de Mesa de Talento"
```

---

### Task 4: Suite completa + entrega (commit, push, migración Neon)

**Files:** ninguno nuevo — solo verificación y entrega.

**Interfaces:** N/A (tarea de cierre).

- [ ] **Step 1: Correr toda la suite de pruebas**

Run: `$env:PYTHONIOENCODING='utf-8'; pytest --reuse-db -q`
Expected: todas las pruebas pasan (las 3 nuevas suites + las ~40+ existentes), sin regresiones.

- [ ] **Step 2: Verificar que no quedan cambios sin commitear**

Run: `git status`
Expected: working tree limpio (todo ya commiteado en las Tasks 1–3).

- [ ] **Step 3: Push a `main`**

```bash
git push origin main
```

Expected: dispara auto-deploy en Vercel.

- [ ] **Step 4: Aplicar la migración a Neon producción**

Cargar `DATABASE_URL` con la URL **unpooled** de Neon (ver `docs/neon.md`) sin imprimir el secreto, y correr:

```bash
python manage.py migrate evaluations
```

Expected: aplica `0010_talentsessionnote_comentarios_and_more` (y cualquier migración pendiente previa) contra Neon, sin errores.
