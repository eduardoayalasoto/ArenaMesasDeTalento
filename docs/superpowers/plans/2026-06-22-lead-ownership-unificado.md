# Lead Ownership Unificado — Plan de Implementación

> **Para agentes:** Usar superpowers:executing-plans para ejecutar tarea a tarea.

**Goal:** Reemplazar las evaluaciones de Ownership por-proyecto para usuarios con nivel LEAD por una única evaluación transversal por periodo, mostrando sus proyectos de forma informativa.

**Architecture:** Se hace `OwnershipEvaluation.project` nullable (NULL = evaluación de Lead). Dos UniqueConstraints parciales reemplazan al actual. La capa de servicios y scoring no cambia. Las vistas se bifurcan en `is_lead`. Los dashboards adaptan `build_results` para entregar la estructura correcta según el nivel.

**Tech Stack:** Django 6, pytest-django, Tailwind v4, Alpine.js, htmx, Postgres (Neon prod) / SQLite (test).

## Global Constraints

- Todo texto UI en español; código en inglés.
- `$env:PYTHONIOENCODING='utf-8'` antes de todo comando Python/pytest.
- Pytest: `.\.venv\Scripts\python.exe -m pytest <path> -v`
- Manage: `.\.venv\Scripts\python.exe manage.py <cmd>`
- Sin Node; no tocar `static/css/` ni correr Tailwind (el CSS compilado está versionado).
- Plantillas no recargan en caliente → reiniciar `runserver` tras editar templates.
- Commits con PowerShell here-string; sin comillas dobles dentro del mensaje.
- Spec de referencia: `docs/superpowers/specs/2026-06-22-lead-ownership-unificado-design.md`

---

## Archivos que cambian

| Acción | Archivo |
|---|---|
| Modify | `apps/evaluations/models.py` |
| Create | `apps/evaluations/migrations/0003_ownership_project_nullable.py` (vía makemigrations) |
| Modify | `apps/core/services/ownership_flow.py` |
| Modify | `apps/evaluations/urls.py` |
| Modify | `apps/evaluations/views.py` |
| Modify | `templates/evaluations/ownership_list.html` |
| Modify | `templates/evaluations/ownership_start.html` |
| Modify | `templates/evaluations/ownership_fill.html` |
| Modify | `templates/evaluations/ownership_validation.html` |
| Modify | `apps/dashboards/views.py` |
| Modify | `templates/dashboards/_results_body.html` |
| Modify | `templates/dashboards/talent_table.html` |
| Modify | `apps/core/tests/conftest.py` |
| Create | `apps/core/tests/test_lead_ownership.py` |

---

## Task 1: Migración — `project` nullable + constraints parciales

**Files:**
- Modify: `apps/evaluations/models.py`
- Create: `apps/evaluations/migrations/0003_ownership_project_nullable.py` (vía makemigrations)

**Interfaces:**
- Produces: `OwnershipEvaluation.project` acepta `None`; constraints `unique_ownership_eval` (project IS NOT NULL) y `unique_lead_ownership_eval` (project IS NULL).

- [ ] **Step 1: Modificar el campo `project` y los constraints en `models.py`**

En `apps/evaluations/models.py`, reemplaza el campo `project` y el bloque `constraints` de `OwnershipEvaluation`:

```python
# Campo project — reemplaza la definición existente:
project = models.ForeignKey(
    "catalog.Project", on_delete=models.PROTECT,
    related_name="ownership_evaluations", verbose_name="proyecto",
    null=True, blank=True,
)
```

```python
# Bloque constraints dentro de class Meta — reemplaza el existente:
constraints = [
    models.UniqueConstraint(
        fields=["user", "project", "period"],
        condition=models.Q(project__isnull=False),
        name="unique_ownership_eval",
    ),
    models.UniqueConstraint(
        fields=["user", "period"],
        condition=models.Q(project__isnull=True),
        name="unique_lead_ownership_eval",
    ),
]
```

- [ ] **Step 2: Generar la migración**

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe manage.py makemigrations evaluations --name ownership_project_nullable
```

Esperado: `Migrations for 'evaluations': apps/evaluations/migrations/0003_ownership_project_nullable.py`

- [ ] **Step 3: Aplicar la migración localmente**

```powershell
.\.venv\Scripts\python.exe manage.py migrate evaluations
```

Esperado: `Applying evaluations.0003_ownership_project_nullable... OK`

- [ ] **Step 4: Verificar con `manage.py check`**

```powershell
.\.venv\Scripts\python.exe manage.py check
```

Esperado: `System check identified no issues (0 silenced).`

- [ ] **Step 5: Commit**

```powershell
git add apps/evaluations/models.py apps/evaluations/migrations/0003_ownership_project_nullable.py
git commit -m @'
feat(evaluations): project nullable en OwnershipEvaluation + constraints parciales para Lead

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
'@
```

---

## Task 2: Servicio — `get_or_create_ownership_evaluation` bifurcado

**Files:**
- Modify: `apps/core/services/ownership_flow.py:26-55`

**Interfaces:**
- Consumes: `OwnershipEvaluation` con `project` nullable (Task 1).
- Produces: `get_or_create_ownership_evaluation(user, period, project=None, evaluator=None)` — firma con `project` como keyword con default `None` y reordenada (`period` antes de `project`).

- [ ] **Step 1: Reemplazar la función en `ownership_flow.py`**

Reemplaza la función completa `get_or_create_ownership_evaluation` (líneas 26–55):

```python
def get_or_create_ownership_evaluation(user, period, project=None, evaluator=None):
    """Obtiene o crea la evaluación para el usuario y periodo dados.

    Para Leads: project=None crea una evaluación transversal (sin proyecto).
    Para colaboradores normales: project es el proyecto específico.
    Devuelve (evaluation, error). error es None si todo bien.
    """
    from apps.evaluations.models import OwnershipEvaluation, OwnershipEvaluator

    if project is None:
        existing = OwnershipEvaluation.objects.filter(
            user=user, project__isnull=True, period=period
        ).first()
    else:
        existing = OwnershipEvaluation.objects.filter(
            user=user, project=project, period=period
        ).first()
    if existing:
        return existing, None

    template = resolve_ownership_template(user)
    if template is None:
        return None, (
            "Aún no podemos abrir tu evaluación: tu área y nivel deben estar asignados "
            "por Talento y debe existir un cuestionario publicado para tu puesto."
        )

    evaluation = OwnershipEvaluation.objects.create(
        user=user, project=project, period=period, template=template,
    )
    if evaluator:
        OwnershipEvaluator.objects.create(
            evaluation=evaluation, user=evaluator, is_primary=True,
        )
    return evaluation, None
```

**Importante:** también busca y actualiza la llamada en `apps/evaluations/views.py` (función `ownership_start`, línea ~103) para usar la nueva firma:

```python
# Antes:
evaluation, error = ownership_flow.get_or_create_ownership_evaluation(
    request.user, membership.project, period, evaluator=evaluator
)
# Después:
evaluation, error = ownership_flow.get_or_create_ownership_evaluation(
    request.user, period, project=membership.project, evaluator=evaluator
)
```

- [ ] **Step 2: Verificar que las pruebas existentes siguen en verde**

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_ownership_flow.py -v
```

Esperado: todas PASSED.

- [ ] **Step 3: Commit**

```powershell
git add apps/core/services/ownership_flow.py apps/evaluations/views.py
git commit -m @'
refactor(ownership): get_or_create acepta project=None para evaluacion de Lead

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
'@
```

---

## Task 3: URLs y vistas de evaluaciones

**Files:**
- Modify: `apps/evaluations/urls.py`
- Modify: `apps/evaluations/views.py`

**Interfaces:**
- Consumes: `get_or_create_ownership_evaluation(user, period, project=None, evaluator)` (Task 2).
- Produces: URL `evaluations:ownership_lead_start`; vista `ownership_lead_start`; `ownership_list` bifurcada; `_render_ownership` con `lead_projects` y `page_title` correctos; mensajes sin crash en `ownership_save` y `ownership_reopen`.

- [ ] **Step 1: Agregar la URL en `urls.py`**

En `apps/evaluations/urls.py`, añade la nueva URL **antes** de los patrones `<int:pk>`:

```python
# Justo después de:
path("ownership/iniciar/<int:project_id>/", views.ownership_start, name="ownership_start"),
# Agrega:
path("ownership/lead/iniciar/", views.ownership_lead_start, name="ownership_lead_start"),
```

- [ ] **Step 2: Reemplazar `ownership_list` en `views.py`**

Reemplaza la función `ownership_list` completa:

```python
@login_required
def ownership_list(request):
    """Para Leads: una tarjeta transversal. Para el resto: una tarjeta por proyecto."""
    period = _open_period()

    if request.user.is_lead:
        lead_eval = None
        answered = total = 0
        lead_projects = []
        if period:
            lead_eval = OwnershipEvaluation.objects.filter(
                user=request.user, project__isnull=True, period=period
            ).first()
            if lead_eval:
                answered, total, _ = _progress(lead_eval)
            lead_projects = list(
                request.user.memberships.select_related("project")
                .filter(project__is_active=True).order_by("project__name")
            )
        return render(request, "evaluations/ownership_list.html", {
            "page_title": "Mis evaluaciones",
            "period": period,
            "is_lead": True,
            "lead_eval": lead_eval,
            "lead_projects": lead_projects,
            "answered": answered,
            "total": total,
        })

    cards = []
    if period:
        memberships = request.user.memberships.select_related("project").filter(
            project__is_active=True
        )
        evals = {
            e.project_id: e
            for e in OwnershipEvaluation.objects.filter(user=request.user, period=period)
        }
        for m in memberships:
            ev = evals.get(m.project_id)
            answered = total = 0
            if ev:
                answered, total, _ = _progress(ev)
            cards.append({"project": m.project, "evaluation": ev,
                          "answered": answered, "total": total})
    return render(request, "evaluations/ownership_list.html", {
        "page_title": "Mis evaluaciones",
        "period": period,
        "is_lead": False,
        "cards": cards,
    })
```

- [ ] **Step 3: Agregar la nueva vista `ownership_lead_start`**

Agrega esta función en `views.py` justo después de la función `ownership_start`:

```python
@login_required
def ownership_lead_start(request):
    """Lead elige su evaluador para la evaluación unificada (sin proyecto específico)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    if not request.user.is_lead:
        messages.error(request, "Esta pantalla es solo para colaboradores con nivel Lead.")
        return redirect("evaluations:ownership_list")

    period = _open_period()
    if not period:
        messages.error(request, "No hay un periodo abierto en este momento.")
        return redirect("evaluations:ownership_list")

    existing = OwnershipEvaluation.objects.filter(
        user=request.user, project__isnull=True, period=period
    ).first()
    if existing:
        return redirect("evaluations:ownership_edit", pk=existing.pk)

    if request.method == "POST":
        evaluator = User.objects.filter(
            pk=request.POST.get("evaluator"), is_active=True
        ).exclude(pk=request.user.pk).first()
        if not evaluator:
            messages.error(request, "Elige un evaluador principal válido para continuar.")
        else:
            evaluation, error = ownership_flow.get_or_create_ownership_evaluation(
                request.user, period, project=None, evaluator=evaluator
            )
            if error:
                messages.error(request, error)
                return redirect("evaluations:ownership_list")

            secondary_ids = request.POST.getlist("secondary_evaluators")
            for sid in secondary_ids:
                secondary = User.objects.filter(
                    pk=sid, is_active=True
                ).exclude(pk=request.user.pk).exclude(pk=evaluator.pk).first()
                if secondary:
                    ownership_flow.add_evaluator(evaluation, secondary, is_primary=False)

            messages.success(request, f"Asignaste a {evaluator.full_name} como evaluador principal.")
            return redirect("evaluations:ownership_edit", pk=evaluation.pk)

    evaluators = (
        User.objects.filter(is_active=True).exclude(pk=request.user.pk).order_by("full_name")
    )
    return render(request, "evaluations/ownership_start.html", {
        "page_title": "Elegir evaluador",
        "project": None,
        "evaluators": evaluators,
    })
```

- [ ] **Step 4: Corregir `_render_ownership`**

Reemplaza la función `_render_ownership` completa:

```python
def _render_ownership(request, pk, *, editing):
    evaluation = get_object_or_404(
        OwnershipEvaluation.objects.select_related("template", "project", "user"), pk=pk
    )
    if not permissions.can_view_evaluation(request.user, evaluation):
        return render(request, "errors/403.html", {
            "titulo": "No puedes ver esta evaluación",
            "mensaje": "Esta evaluación pertenece a otra persona o área.",
        }, status=403)

    if ownership_flow.sync_evaluation_template(evaluation):
        messages.info(
            request,
            "Tu área o nivel cambiaron; tu cuestionario se actualizó al correspondiente. "
            "Las respuestas anteriores fueron eliminadas.",
        )
        return redirect(request.path)

    can_edit_answers = _can_edit_answers(request.user, evaluation)
    can_complement = _can_complement(request.user, evaluation)
    is_owner = evaluation.user_id == request.user.pk
    can_manage_evaluators = editing and is_owner and not evaluation.is_submitted

    all_users = None
    if can_manage_evaluators:
        from django.contrib.auth import get_user_model
        all_users = (
            get_user_model().objects.filter(is_active=True)
            .exclude(pk=request.user.pk).order_by("full_name")
        )

    ev_records = (
        evaluation.evaluators.select_related("user")
        .order_by("-is_primary", "added_at")
    )

    answers = {a.question_id: a for a in evaluation.answers.all()}
    sections = evaluation.template.sections.prefetch_related(
        Prefetch("questions", queryset=Question.objects.order_by("order"))
    ).order_by("order")
    scale = list(evaluation.template.scale_options.order_by("order"))
    answered, total, average = _progress(evaluation)

    lead_projects = None
    if evaluation.project is None:
        lead_projects = list(
            evaluation.user.memberships.select_related("project")
            .filter(project__is_active=True).order_by("project__name")
        )

    page_title = evaluation.project.name if evaluation.project else "Todos mis proyectos"

    return render(request, "evaluations/ownership_fill.html", {
        "page_title": page_title,
        "evaluation": evaluation,
        "sections": sections,
        "answers": answers,
        "scale": scale,
        "answered": answered,
        "total": total,
        "average": average,
        "is_owner": is_owner,
        "editing": editing,
        "answers_editable": editing and can_edit_answers,
        "can_complement": editing and can_complement,
        "can_manage_evaluators": can_manage_evaluators,
        "all_users": all_users,
        "ev_records": ev_records,
        "can_edit_link": (can_edit_answers or can_complement),
        "can_reopen": evaluation.is_submitted and request.user.is_admin,
        "lead_projects": lead_projects,
    })
```

- [ ] **Step 5: Corregir mensajes con `project.name` en `ownership_save`**

Busca en `ownership_save` el bloque `if request.POST.get("action") == "save_close":` y reemplaza el `messages.success`:

```python
# Antes:
messages.success(
    request,
    f"Cerraste la evaluación de {evaluation.user.full_name} "
    f"({evaluation.project.name}). Calificación: {evaluation.score}.",
)
# Después:
project_label = evaluation.project.name if evaluation.project else "todos sus proyectos"
messages.success(
    request,
    f"Cerraste la evaluación de {evaluation.user.full_name} "
    f"({project_label}). Calificación: {evaluation.score}.",
)
```

- [ ] **Step 6: Corregir mensaje en `ownership_reopen`**

```python
# Antes:
messages.success(
    request,
    f"Reabriste la evaluación de {evaluation.user.full_name} "
    f"({evaluation.project.name}). Ahora puede editarse de nuevo.",
)
# Después:
project_label = evaluation.project.name if evaluation.project else "todos sus proyectos"
messages.success(
    request,
    f"Reabriste la evaluación de {evaluation.user.full_name} "
    f"({project_label}). Ahora puede editarse de nuevo.",
)
```

- [ ] **Step 7: Corregir ordering en `ownership_validation`**

```python
# Antes:
.order_by("evaluation__project__name", "evaluation__user__full_name")
# Después:
.order_by("evaluation__user__full_name")
```

- [ ] **Step 8: Verificar que el servidor levanta sin errores**

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe manage.py check
```

Esperado: `System check identified no issues (0 silenced).`

- [ ] **Step 9: Commit**

```powershell
git add apps/evaluations/urls.py apps/evaluations/views.py
git commit -m @'
feat(evaluations): vistas ownership bifurcadas para Lead + ownership_lead_start

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
'@
```

---

## Task 4: Templates de evaluaciones

**Files:**
- Modify: `templates/evaluations/ownership_list.html`
- Modify: `templates/evaluations/ownership_start.html`
- Modify: `templates/evaluations/ownership_fill.html`
- Modify: `templates/evaluations/ownership_validation.html`

**Interfaces:**
- Consumes: contexto de Task 3 (`is_lead`, `lead_eval`, `lead_projects`, `page_title`, `project`).

- [ ] **Step 1: Reemplazar `ownership_list.html` completo**

```html
{% extends "base.html" %}
{% block content %}
  <div class="mb-6">
    <h2 class="text-xl font-semibold text-slate-900">Mis evaluaciones de Ownership</h2>
    {% if period %}
      <p class="text-slate-600">Periodo <span class="font-medium">{{ period.name }}</span>.
        {% if is_lead %}Una evaluación transversal para todos tus proyectos.
        {% else %}Una evaluación por proyecto.{% endif %}
      </p>
    {% endif %}
  </div>

  <div class="rounded-lg bg-arena-50 border border-arena-100 px-4 py-3 mb-6 text-sm text-arena-800">
    Captura tus respuestas y revísalas en tu sesión con tu evaluador; tu evaluador las cierra cuando estén listas.
  </div>

  {% if not period %}
    {% include "partials/empty_state.html" with icon="calendar" title="No hay un periodo abierto" message="Tus evaluaciones se habilitarán cuando Talento abra el periodo." %}

  {% elif is_lead %}
    <!-- Tarjeta única para Leads -->
    {% if not lead_projects %}
      {% include "partials/empty_state.html" with icon="folder" title="Aún no tienes proyectos asignados" message="Cuando Talento te asigne a proyectos, verás aquí tu evaluación de Ownership." %}
    {% else %}
      <div class="card p-5 max-w-xl">
        <div class="flex items-start justify-between gap-3 mb-4">
          <div>
            <h3 class="font-semibold text-slate-900">Ownership · Todos tus proyectos</h3>
            <p class="text-sm text-slate-500 mt-0.5">Evaluación única que refleja tu rol de liderazgo transversal.</p>
          </div>
          {% if lead_eval %}
            {% include "partials/status_badge.html" with status=lead_eval.status label=lead_eval.get_status_display %}
          {% else %}
            <span class="badge bg-slate-100 text-slate-500">Sin iniciar</span>
          {% endif %}
        </div>

        <!-- Chips de proyectos -->
        <div class="flex flex-wrap gap-1.5 mb-4">
          {% for m in lead_projects %}
            <span class="inline-flex items-center gap-1 text-xs bg-arena-50 text-arena-700 border border-arena-100 rounded-full px-2.5 py-1">
              {% include "partials/icon.html" with name="folder" cls="w-3 h-3" %}
              {{ m.project.name }}{% if m.project.client %} · {{ m.project.client }}{% endif %}
            </span>
          {% endfor %}
        </div>

        {% if lead_eval and total %}
          <div class="mb-4">
            <div class="flex items-center justify-between text-sm text-slate-600 mb-1">
              <span>{{ answered }}/{{ total }} respondidas</span>
              {% if lead_eval.score %}<span class="font-semibold text-slate-900 tabular-nums">{{ lead_eval.score }}</span>{% endif %}
            </div>
            <div class="h-2 rounded-full bg-slate-100 overflow-hidden">
              <div class="h-full bg-arena-500" style="width: {% widthratio answered total 100 %}%"></div>
            </div>
          </div>
        {% endif %}

        <div class="pt-4 border-t border-slate-100">
          {% if lead_eval and lead_eval.is_submitted %}
            <a href="{% url 'evaluations:ownership_view' pk=lead_eval.pk %}" class="btn-secondary w-full">Ver evaluación cerrada</a>
          {% elif lead_eval %}
            <a href="{% url 'evaluations:ownership_edit' pk=lead_eval.pk %}" class="btn-primary w-full">Continuar</a>
          {% else %}
            <a href="{% url 'evaluations:ownership_lead_start' %}" class="btn-primary w-full">Comenzar evaluación</a>
          {% endif %}
        </div>
      </div>
    {% endif %}

  {% else %}
    <!-- Tarjetas por proyecto (colaboradores normales) -->
    {% if not cards %}
      {% include "partials/empty_state.html" with icon="folder" title="Aún no tienes proyectos asignados" message="Cuando Talento te asigne a un proyecto en este periodo, verás aquí tu evaluación de Ownership." %}
    {% else %}
      <div class="grid gap-4 sm:grid-cols-2">
        {% for card in cards %}
          <div class="card p-5 flex flex-col">
            <div class="flex items-start justify-between gap-3">
              <div>
                <h3 class="font-semibold text-slate-900">{{ card.project.name }}</h3>
                {% if card.project.client %}<p class="text-sm text-slate-500">{{ card.project.client }}</p>{% endif %}
              </div>
              {% if card.evaluation %}
                {% include "partials/status_badge.html" with status=card.evaluation.status label=card.evaluation.get_status_display %}
              {% else %}
                <span class="badge bg-slate-100 text-slate-500">Sin iniciar</span>
              {% endif %}
            </div>

            {% if card.evaluation %}
              <div class="mt-4">
                <div class="flex items-center justify-between text-sm text-slate-600 mb-1">
                  <span>{{ card.answered }}/{{ card.total }} respondidas</span>
                  {% if card.evaluation.score %}<span class="font-semibold text-slate-900 tabular-nums">{{ card.evaluation.score }}</span>{% endif %}
                </div>
                <div class="h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div class="h-full bg-arena-500" style="width: {% widthratio card.answered card.total 100 %}%"></div>
                </div>
              </div>
            {% endif %}

            <div class="mt-5 pt-4 border-t border-slate-100">
              {% if card.evaluation and card.evaluation.is_submitted %}
                <a href="{% url 'evaluations:ownership_view' pk=card.evaluation.pk %}" class="btn-secondary w-full">Ver evaluación cerrada</a>
              {% elif card.evaluation %}
                <a href="{% url 'evaluations:ownership_edit' pk=card.evaluation.pk %}" class="btn-primary w-full">Continuar</a>
              {% else %}
                <a href="{% url 'evaluations:ownership_start' project_id=card.project.pk %}" class="btn-primary w-full">Comenzar evaluación</a>
              {% endif %}
            </div>
          </div>
        {% endfor %}
      </div>
    {% endif %}
  {% endif %}
{% endblock %}
```

- [ ] **Step 2: Modificar `ownership_start.html` — subtítulo condicional**

Reemplaza la línea:
```html
<p class="text-slate-600 mb-5">Proyecto: <span class="font-medium text-slate-900">{{ project.name }}</span></p>
```
Por:
```html
<p class="text-slate-600 mb-5">
  {% if project %}Proyecto: <span class="font-medium text-slate-900">{{ project.name }}</span>
  {% else %}<span class="font-medium text-slate-900">Todos tus proyectos</span> · evaluación de liderazgo transversal{% endif %}
</p>
```

- [ ] **Step 3: Modificar `ownership_fill.html` — título + card de proyectos Lead**

**3a.** Reemplaza la línea del título (L16):
```html
<h2 class="text-xl font-semibold text-slate-900">{{ evaluation.project.name }}</h2>
```
Por:
```html
<h2 class="text-xl font-semibold text-slate-900">
  {% if evaluation.project %}{{ evaluation.project.name }}{% else %}Todos mis proyectos{% endif %}
</h2>
```

**3b.** Inserta el card informativo de proyectos Lead **inmediatamente antes** del comentario `<!-- Barra de progreso fija -->`:

```html
{% if lead_projects %}
<div class="card p-4 mb-6 bg-arena-50 border border-arena-100">
  <p class="text-xs font-semibold text-arena-700 uppercase tracking-wide mb-2 flex items-center gap-1.5">
    {% include "partials/icon.html" with name="folder" cls="w-3.5 h-3.5" %}
    Proyectos en los que participas — referencia para esta evaluación
  </p>
  <div class="flex flex-wrap gap-1.5">
    {% for m in lead_projects %}
      <span class="inline-flex items-center gap-1 text-xs bg-white text-arena-800 border border-arena-200 rounded-full px-2.5 py-1">
        {{ m.project.name }}{% if m.project.client %} · {{ m.project.client }}{% endif %}
      </span>
    {% endfor %}
  </div>
</div>
{% endif %}
```

- [ ] **Step 4: Modificar `ownership_validation.html` — proyecto null-safe**

Reemplaza la línea del nombre de proyecto (dentro del `{% for rec in ev_records %}`):
```html
<p class="text-sm text-slate-500 truncate">{{ ev.project.name }}</p>
```
Por:
```html
<p class="text-sm text-slate-500 truncate">
  {% if ev.project %}{{ ev.project.name }}{% else %}Todos sus proyectos{% endif %}
</p>
```

- [ ] **Step 5: Commit**

```powershell
git add templates/evaluations/
git commit -m @'
feat(templates): ownership_list Lead card + start/fill/validation null-safe

Co-Authored-By: Claude Sonnet 4.6 <noreply@anonymic.com>
'@
```

---

## Task 5: Dashboard — vistas y templates

**Files:**
- Modify: `apps/dashboards/views.py`
- Modify: `templates/dashboards/_results_body.html`
- Modify: `templates/dashboards/talent_table.html`

**Interfaces:**
- Consumes: `OwnershipEvaluation` con `project` nullable (Task 1).
- Produces: `build_results` retorna `lead_eval` (None para no-Leads); `talent_table` incluye `lead_projects` por fila; `_results_body.html` muestra proyectos de membresía para Leads + feedback null-safe.

- [ ] **Step 1: Agregar import de `ProjectMembership` en `dashboards/views.py`**

Busca la línea:
```python
from apps.catalog.models import EvaluationPeriod, SeniorityLevel
```
Reemplázala por:
```python
from apps.catalog.models import Area, EvaluationPeriod, ProjectMembership, SeniorityLevel
```

(Nota: `Area` ya se importa dentro de `talent_table` con un import local; muévelo aquí y elimina el import local más adelante.)

- [ ] **Step 2: Reemplazar `build_results` completo en `dashboards/views.py`**

```python
def build_results(subject, period):
    """Arma el contexto del informe de resultados de una persona.

    Para Leads: projects viene de membresías (no de evals de Ownership) y
    lead_eval es la OwnershipEvaluation con project=None.
    Para el resto: comportamiento original.
    """
    final = final_flow.recompute_final_score(subject, period)
    weight = getattr(subject.level, "weight", None)

    from apps.evaluations.models import ArenaImpactScore
    impact = ArenaImpactScore.objects.filter(user=subject, period=period).first()
    arena_notes = impact.notes if impact and impact.notes else ""

    if subject.is_lead:
        lead_eval = (
            OwnershipEvaluation.objects.filter(
                user=subject, project__isnull=True, period=period
            ).first()
        )
        member_projects = list(
            subject.memberships.select_related("project")
            .filter(project__is_active=True).order_by("project__name")
        )
        vd_by_project = {
            vd.project_id: vd.score
            for vd in ValueDeliveryEvaluation.objects.filter(
                period=period,
                project__in=[m.project_id for m in member_projects],
                status=ValueDeliveryEvaluation.Status.VALIDADA,
            )
        }
        projects = [
            {
                "evaluation": None,
                "project": m.project,
                "ownership_score": None,
                "vd_score": vd_by_project.get(m.project_id),
                "closed": None,
                "is_lead_project": True,
            }
            for m in member_projects
        ]
        feedback = [lead_eval] if lead_eval and lead_eval.is_submitted else []
        return {
            "final": final, "weight": weight, "projects": projects,
            "feedback": feedback, "arena_notes": arena_notes,
            "lead_eval": lead_eval,
        }

    # Colaborador normal
    evals = list(
        OwnershipEvaluation.objects.filter(user=subject, period=period)
        .select_related("project").order_by("project__name")
    )
    vd_by_project = {
        vd.project_id: vd.score
        for vd in ValueDeliveryEvaluation.objects.filter(
            period=period, project__in=[e.project_id for e in evals],
            status=ValueDeliveryEvaluation.Status.VALIDADA,
        )
    }
    projects = [
        {
            "evaluation": e,
            "project": e.project,
            "ownership_score": e.score,
            "vd_score": vd_by_project.get(e.project_id),
            "closed": e.is_submitted,
            "is_lead_project": False,
        }
        for e in evals
    ]
    feedback = [e for e in evals if e.is_submitted]
    return {
        "final": final, "weight": weight, "projects": projects,
        "feedback": feedback, "arena_notes": arena_notes,
        "lead_eval": None,
    }
```

- [ ] **Step 3: Agregar `lead_projects` por fila en `talent_table`**

Dentro de `talent_table`, justo antes de construir `rows`, agrega:

```python
lead_projects_by_user = {}
for u in page.object_list:
    if u.is_lead:
        lead_projects_by_user[u.id] = list(
            ProjectMembership.objects.filter(user=u, project__is_active=True)
            .order_by("project__name")
            .values_list("project__name", flat=True)
        )
```

Luego actualiza la construcción de `rows` para incluir `lead_projects`:

```python
rows = [
    {
        "user": u,
        "final": finals_all.get(u.id),
        "evaluators": evaluators_by_user.get(u.id, []),
        "lead_projects": lead_projects_by_user.get(u.id),
    }
    for u in page.object_list
]
```

Elimina también el import local `from apps.catalog.models import Area, SeniorityLevel` que está al final de la vista `talent_table` (ya está en el import global).

- [ ] **Step 4: Corregir `_results_body.html` — Estado Lead + feedback null-safe**

**4a.** En la columna "Estado" de la tabla de proyectos, reemplaza:
```html
<td class="px-5 py-3">
  {% if row.closed %}<span class="badge bg-emerald-50 text-emerald-700">Cerrada</span>
  {% else %}<span class="badge bg-slate-100 text-slate-600">Abierta</span>{% endif %}
</td>
```
Por:
```html
<td class="px-5 py-3">
  {% if row.is_lead_project %}<span class="text-slate-400">—</span>
  {% elif row.closed %}<span class="badge bg-emerald-50 text-emerald-700">Cerrada</span>
  {% else %}<span class="badge bg-slate-100 text-slate-600">Abierta</span>{% endif %}
</td>
```

**4b.** En la columna "Ver" (detail_links), guarda el acceso a `row.evaluation.pk`:
```html
{% if detail_links %}
<td class="px-5 py-3 text-right">
  {% if row.evaluation %}
    <a href="{% url 'evaluations:ownership_view' pk=row.evaluation.pk %}" target="_blank" rel="noopener" class="inline-flex items-center gap-1 text-xs font-medium text-arena-600 hover:text-arena-700">Ver {% include "partials/icon.html" with name="external" cls="w-3.5 h-3.5" %}</a>
  {% endif %}
</td>
{% endif %}
```

**4c.** En la sección de feedback (sección `{% for ev in feedback %}`), reemplaza el título:
```html
<h3 class="font-semibold text-slate-900">Retroalimentación · {{ ev.project.name }}</h3>
```
Por:
```html
<h3 class="font-semibold text-slate-900">
  Retroalimentación{% if ev.project %} · {{ ev.project.name }}{% endif %}
</h3>
```

- [ ] **Step 5: Modificar `talent_table.html` — tooltip de proyectos para Leads**

Reemplaza la celda de "Proyectos":
```html
<td class="px-3 py-3 text-center tabular-nums hidden sm:table-cell">{{ row.user.num_projects }}</td>
```
Por:
```html
<td class="px-3 py-3 text-center tabular-nums hidden sm:table-cell">
  {% if row.lead_projects %}
    <span class="relative inline-block" x-data="{ open: false }" @mouseenter="open=true" @mouseleave="open=false">
      <span class="underline decoration-dotted decoration-slate-400 cursor-help tabular-nums">{{ row.user.num_projects }}</span>
      <div x-show="open" x-cloak
           class="absolute z-10 left-1/2 -translate-x-1/2 bottom-full mb-2 bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-left min-w-52 max-w-xs">
        <p class="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">Proyectos</p>
        {% for name in row.lead_projects %}
          <p class="text-xs text-slate-700 truncate">{{ name }}</p>
        {% endfor %}
      </div>
    </span>
  {% else %}
    {{ row.user.num_projects }}
  {% endif %}
</td>
```

- [ ] **Step 6: Verificar `manage.py check`**

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe manage.py check
```

Esperado: `System check identified no issues (0 silenced).`

- [ ] **Step 7: Commit**

```powershell
git add apps/dashboards/views.py templates/dashboards/_results_body.html templates/dashboards/talent_table.html
git commit -m @'
feat(dashboards): build_results bifurcado para Lead + proyectos en talent_table

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
'@
```

---

## Task 6: Fixtures nuevas y pruebas

**Files:**
- Modify: `apps/core/tests/conftest.py`
- Create: `apps/core/tests/test_lead_ownership.py`

**Interfaces:**
- Consumes: `get_or_create_ownership_evaluation(user, period, project=None)` (Task 2); constraints de Task 1.
- Produces: 8 pruebas nuevas en verde.

- [ ] **Step 1: Agregar fixtures en `conftest.py`**

Al final del archivo, agrega:

```python
@pytest.fixture
def level_lead(db):
    lvl = SeniorityLevel.objects.create(code="LEAD", name="Lead", order=4)
    PillarWeight.objects.create(
        level=lvl, w_ownership=Decimal("0.30"),
        w_value_delivery=Decimal("0.35"), w_arena_impact=Decimal("0.35"),
    )
    return lvl


@pytest.fixture
def lead_collab(db, area, level_lead):
    return User.objects.create_user(
        email="marco.aristeo@arena-analytics.com", password="x",
        full_name="Marco Aristeo",
        area=area, level=level_lead,
    )


@pytest.fixture
def ownership_template_lead(db, area, level_lead):
    tpl = QuestionnaireTemplate.objects.create(
        kind=QuestionnaireTemplate.Kind.OWNERSHIP, area=area, level=level_lead,
        version=1, status=QuestionnaireTemplate.Status.PUBLICADO,
    )
    section = Section.objects.create(template=tpl, title="Checklist Lead", order=1)
    for i in range(1, 4):
        Question.objects.create(section=section, order=i, title=f"LP{i}", qtype="SCALE")
    return tpl
```

- [ ] **Step 2: Ejecutar las pruebas existentes para confirmar que las fixtures no rompen nada**

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m pytest apps/core/tests/ -v --ignore=apps/core/tests/test_lead_ownership.py
```

Esperado: todas PASSED (168 pruebas).

- [ ] **Step 3: Crear `test_lead_ownership.py` con todas las pruebas**

```python
"""Pruebas de la evaluación de Ownership unificada para usuarios con nivel Lead."""

import pytest
from django.db import IntegrityError

from apps.core.services import ownership_flow, scoring
from apps.evaluations.models import OwnershipAnswer, OwnershipEvaluation
from apps.core.tests.conftest import make_membership


# ---------------------------------------------------------------------------
# Modelo y constraints
# ---------------------------------------------------------------------------

def test_lead_eval_created_without_project(
    lead_collab, period, ownership_template_lead
):
    """get_or_create con project=None crea OwnershipEvaluation con project=None."""
    eval_, error = ownership_flow.get_or_create_ownership_evaluation(
        lead_collab, period, project=None
    )
    assert error is None
    assert eval_ is not None
    assert eval_.project is None
    assert eval_.user == lead_collab
    assert eval_.period == period


def test_lead_unique_constraint_enforced(
    lead_collab, period, ownership_template_lead
):
    """No se puede crear una segunda evaluación de Lead para el mismo (user, period)."""
    ownership_flow.get_or_create_ownership_evaluation(lead_collab, period, project=None)
    # El segundo get_or_create devuelve el existente (no lanza error):
    eval2, error = ownership_flow.get_or_create_ownership_evaluation(
        lead_collab, period, project=None
    )
    assert error is None
    assert OwnershipEvaluation.objects.filter(
        user=lead_collab, project__isnull=True, period=period
    ).count() == 1


def test_non_lead_constraint_unchanged(
    collaborator, period, project_finite, ownership_template
):
    """El constraint original (user, project, period) sigue funcionando para no-Leads."""
    ownership_flow.get_or_create_ownership_evaluation(
        collaborator, period, project=project_finite
    )
    eval2, _ = ownership_flow.get_or_create_ownership_evaluation(
        collaborator, period, project=project_finite
    )
    # Devuelve el existente
    assert OwnershipEvaluation.objects.filter(
        user=collaborator, project=project_finite, period=period
    ).count() == 1


def test_lead_and_regular_evals_coexist(
    lead_collab, collaborator, period, project_finite,
    ownership_template, ownership_template_lead
):
    """Un Lead puede tener eval sin proyecto y un colaborador su eval por proyecto en el mismo periodo."""
    lead_eval, _ = ownership_flow.get_or_create_ownership_evaluation(
        lead_collab, period, project=None
    )
    reg_eval, _ = ownership_flow.get_or_create_ownership_evaluation(
        collaborator, period, project=project_finite
    )
    assert lead_eval.project is None
    assert reg_eval.project == project_finite


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def test_ownership_pillar_score_lead_single_eval(
    lead_collab, period, ownership_template_lead
):
    """Con 1 eval de Lead ENVIADA, ownership_pillar_score devuelve su score directamente."""
    eval_, _ = ownership_flow.get_or_create_ownership_evaluation(
        lead_collab, period, project=None
    )
    questions = list(
        eval_.template.sections.first().questions.all()
    )
    for q in questions:
        OwnershipAnswer.objects.create(evaluation=eval_, question=q, value=4)

    eval_.strengths = "Fortalezas"
    eval_.opportunities = "Oportunidades"
    eval_.save()
    ownership_flow.close_ownership_evaluation(eval_)

    pillar = scoring.ownership_pillar_score(lead_collab, period)
    assert pillar is not None
    assert float(pillar) == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# Vistas
# ---------------------------------------------------------------------------

def test_ownership_list_lead_sees_single_card(
    client, lead_collab, period, project_finite, ownership_template_lead
):
    """Un Lead autenticado ve la tarjeta única en la lista de evaluaciones."""
    make_membership(project_finite, lead_collab)
    client.force_login(lead_collab)
    response = client.get("/evaluaciones/ownership/")
    assert response.status_code == 200
    assert response.context["is_lead"] is True
    assert "lead_projects" in response.context


def test_ownership_list_non_lead_unchanged(
    client, collaborator, period, project_finite, ownership_template
):
    """Un colaborador normal ve tarjetas por proyecto."""
    make_membership(project_finite, collaborator)
    client.force_login(collaborator)
    response = client.get("/evaluaciones/ownership/")
    assert response.status_code == 200
    assert response.context["is_lead"] is False
    assert "cards" in response.context


def test_lead_fill_context_has_lead_projects(
    client, lead_collab, period, project_finite, ownership_template_lead
):
    """_render_ownership incluye lead_projects en el contexto para evals de Lead."""
    make_membership(project_finite, lead_collab)
    eval_, _ = ownership_flow.get_or_create_ownership_evaluation(
        lead_collab, period, project=None
    )
    client.force_login(lead_collab)
    response = client.get(f"/evaluaciones/ownership/{eval_.pk}/editar/")
    assert response.status_code == 200
    assert response.context["lead_projects"] is not None
    project_names = [m.project.name for m in response.context["lead_projects"]]
    assert project_finite.name in project_names
```

- [ ] **Step 4: Ejecutar las nuevas pruebas (deben pasar)**

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_lead_ownership.py -v
```

Esperado: 8 pruebas PASSED.

- [ ] **Step 5: Ejecutar la suite completa**

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m pytest apps/core/tests/ -v
```

Esperado: 176 pruebas PASSED (168 anteriores + 8 nuevas).

- [ ] **Step 6: Commit**

```powershell
git add apps/core/tests/conftest.py apps/core/tests/test_lead_ownership.py
git commit -m @'
test(lead-ownership): 8 pruebas nuevas + fixtures level_lead y lead_collab

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
'@
```

---

## Task 7: Push y migración a Neon

**Files:** ninguno nuevo.

- [ ] **Step 1: Push a GitHub (auto-deploy a Vercel)**

```powershell
$env:GIT_TERMINAL_PROMPT='0'
$env:GCM_INTERACTIVE='never'
git push
```

Esperado: push exitoso a `main`. Vercel inicia el deploy automáticamente.

- [ ] **Step 2: Aplicar migración `0003` a Neon (BD de producción)**

Primero, configura `DATABASE_URL` con la URL **unpooled** de Neon (ver `docs/Deploy_Vercel.md` o `.env.vercel`):

```powershell
$env:DATABASE_URL='<neon-unpooled-url>'
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe manage.py migrate evaluations
```

Esperado: `Applying evaluations.0003_ownership_project_nullable... OK`

- [ ] **Step 3: Verificar en producción**

Entrar a Vercel con un usuario Lead (ej: Marco Aristeo). Confirmar:
1. `ownership/` muestra tarjeta única "Todos tus proyectos" con chips de proyectos.
2. Al iniciar → pantalla de selección de evaluador normal.
3. Al abrir la evaluación → card informativo de proyectos antes de la barra de progreso.
4. Mesa de Talento → hover sobre "Proyectos" de un Lead muestra los nombres.
5. Informe de resultados de un Lead → sección Proyectos muestra membresías con EV; retroalimentación sin crash.
