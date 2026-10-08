# Borrado de usuarios y proyectos para Talento — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar al perfil Talento botones de eliminar usuarios y proyectos desde la UI, con borrado híbrido (soft/hard) que evita errores de FK.

**Architecture:** Soft delete para usuarios con historial (campo `deleted_at`), hard delete para usuarios sin historial; lógica equivalente para proyectos (desactivar si tiene evaluaciones, borrar si está vacío). Botones solo visibles para `request.user.is_admin`. Respuestas HTMX que eliminan o actualizan filas sin recargar página.

**Tech Stack:** Django 4.x, HTMX, Tailwind CSS, SQLite, `simple_history`.

## Global Constraints

- Solo usuarios con `is_admin=True` (Talento / superusuario) pueden ejecutar estas acciones — tanto en template como en backend.
- No se puede borrar al usuario que tiene la sesión activa.
- No se puede borrar un superusuario.
- Errores de FK (ProtectedError) deben capturarse y devolver mensaje claro, nunca 500.
- Patrón HTMX existente: `hx-post`, `hx-confirm`, `hx-target`, `hx-swap="outerHTML"` apuntando al `<tr>` de la fila.
- Iconos Lucide inline con `<i data-lucide="...">`, igual que los botones existentes.
- Tooltips con el patrón `group/tip` ya existente en `user_admin.html`.

---

### Task 1: Campo `deleted_at` en modelo User + migración

**Files:**
- Modify: `apps/accounts/models.py`
- Create: `apps/accounts/migrations/0006_user_deleted_at.py` (generada por Django)

**Interfaces:**
- Produces: `User.deleted_at` — `DateTimeField(null=True, blank=True)`

- [ ] **Step 1: Agregar campo al modelo**

En `apps/accounts/models.py`, después de `must_change_password`:

```python
deleted_at = models.DateTimeField(
    "eliminado el", null=True, blank=True,
)
```

- [ ] **Step 2: Generar y aplicar migración**

```bash
python manage.py makemigrations accounts --name user_deleted_at
python manage.py migrate
```

Salida esperada: `Applying accounts.0006_user_deleted_at... OK`

- [ ] **Step 3: Commit**

```bash
git add apps/accounts/models.py apps/accounts/migrations/0006_user_deleted_at.py
git commit -m "feat(accounts): campo deleted_at en User para soft delete"
```

---

### Task 2: Vista y URL para borrar usuario

**Files:**
- Modify: `apps/accounts/views.py`
- Modify: `apps/accounts/urls.py`

**Interfaces:**
- Consumes: `User.deleted_at` (Task 1)
- Produces: endpoint `POST /usuarios/<pk>/eliminar/` → `accounts:user_delete`

- [ ] **Step 1: Agregar imports necesarios en views.py**

Al inicio de `apps/accounts/views.py`, agregar a los imports existentes:

```python
from django.db import ProtectedError
from django.utils import timezone
```

- [ ] **Step 2: Agregar vista `user_delete`**

Al final de `apps/accounts/views.py`:

```python
@login_required
def user_delete(request, pk):
    """Elimina o desactiva un usuario (solo Talento/admin). RN: soft delete si tiene historial."""
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Acción reservada a Talento",
            "mensaje": "Solo Talento y Cultura puede eliminar usuarios.",
        }, status=403)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    user = get_object_or_404(User, pk=pk, is_superuser=False)

    if user.pk == request.user.pk:
        if request.headers.get("HX-Request"):
            return HttpResponse(
                '<tr><td colspan="5" class="px-4 py-2 text-sm text-rose-600">'
                'No puedes eliminarte a ti mismo.</td></tr>'
            )
        messages.error(request, "No puedes eliminarte a ti mismo.")
        return redirect("accounts:user_admin")

    from apps.evaluations.models import OwnershipEvaluation, ArenaImpactScore, FinalScore
    has_history = (
        OwnershipEvaluation.objects.filter(user=user).exists()
        or ArenaImpactScore.objects.filter(user=user).exists()
        or FinalScore.objects.filter(user=user).exists()
    )

    if has_history:
        user.is_active = False
        user.deleted_at = timezone.now()
        user.save(update_fields=["is_active", "deleted_at"])
        msg = f"{user.full_name} eliminado/a. Sus evaluaciones históricas se conservan."
    else:
        try:
            nombre = user.full_name
            user.delete()
            msg = f"{nombre} eliminado/a permanentemente."
        except ProtectedError as e:
            protected = list(e.protected_objects)[:3]
            detalle = ", ".join(str(o) for o in protected)
            error_msg = f"No se puede eliminar: hay registros vinculados ({detalle}…). Reasigna primero."
            if request.headers.get("HX-Request"):
                return HttpResponse(
                    f'<tr id="user-row-{pk}"><td colspan="5" class="px-4 py-2 text-sm text-rose-600">'
                    f'{error_msg}</td></tr>'
                )
            messages.error(request, error_msg)
            return redirect("accounts:user_admin")

    if request.headers.get("HX-Request"):
        return HttpResponse("")  # HTMX outerHTML swap elimina la fila
    messages.success(request, msg)
    return redirect("accounts:user_admin")
```

- [ ] **Step 3: Actualizar filtro en `user_admin`**

En `apps/accounts/views.py`, vista `user_admin`, cambiar la línea:

```python
users = User.objects.filter(is_superuser=False).select_related("area", "level")
```

por:

```python
users = User.objects.filter(is_superuser=False, deleted_at__isnull=True).select_related("area", "level")
```

Y también la línea del POST (actualización masiva):

```python
for user in User.objects.filter(is_superuser=False):
```

por:

```python
for user in User.objects.filter(is_superuser=False, deleted_at__isnull=True):
```

- [ ] **Step 4: Agregar URL en urls.py**

En `apps/accounts/urls.py`, dentro de `urlpatterns`, después de la ruta `user_reset_password`:

```python
path("usuarios/<int:pk>/eliminar/", views.user_delete, name="user_delete"),
```

- [ ] **Step 5: Commit**

```bash
git add apps/accounts/views.py apps/accounts/urls.py
git commit -m "feat(accounts): vista y URL para borrar usuario (soft/hard delete)"
```

---

### Task 3: Botón de borrar en `user_admin.html`

**Files:**
- Modify: `templates/accounts/user_admin.html`

**Interfaces:**
- Consumes: `accounts:user_delete` (Task 2)

- [ ] **Step 1: Agregar `id` a cada `<tr>`**

Cambiar la línea:

```html
<tr class="hover:bg-slate-50 transition-colors">
```

por:

```html
<tr id="user-row-{{ u.id }}" class="hover:bg-slate-50 transition-colors">
```

- [ ] **Step 2: Agregar botón de borrar en columna Acciones**

Dentro del `<div class="flex items-center gap-1">` de la columna Acciones, después del botón de `reset-eval`, agregar:

```html
{% if request.user.is_admin %}
<span id="del-user-{{ u.id }}" class="relative group/tip3">
  <button type="button"
    hx-post="{% url 'accounts:user_delete' u.id %}"
    hx-target="#user-row-{{ u.id }}"
    hx-swap="outerHTML"
    hx-confirm="¿Eliminar a {{ u.full_name }}? Esta acción no se puede deshacer."
    class="p-1.5 rounded-lg text-red-600 hover:bg-red-50 border border-transparent hover:border-red-200 transition cursor-pointer">
    <i data-lucide="trash-2" class="w-4 h-4"></i>
  </button>
  <span class="pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap rounded-md bg-slate-800 px-2 py-1 text-xs text-white opacity-0 transition-opacity duration-150 group-hover/tip3:opacity-100 z-20">Eliminar usuario</span>
</span>
{% endif %}
```

- [ ] **Step 3: Commit**

```bash
git add templates/accounts/user_admin.html
git commit -m "feat(ui): botón eliminar usuario en user_admin (solo Talento)"
```

---

### Task 4: Vistas y URLs para borrar/reactivar proyectos

**Files:**
- Modify: `apps/catalog/views.py`
- Modify: `apps/catalog/urls.py`

**Interfaces:**
- Produces:
  - `POST /proyectos/<pk>/eliminar/` → `catalog:project_delete`
  - `POST /proyectos/<pk>/reactivar/` → `catalog:project_reactivate`

- [ ] **Step 1: Agregar imports en catalog/views.py**

Al inicio de `apps/catalog/views.py`, agregar a los imports existentes:

```python
from django.db import ProtectedError
from django.http import HttpResponse, HttpResponseNotAllowed
```

- [ ] **Step 2: Agregar vista `project_delete`**

Al final de `apps/catalog/views.py`:

```python
@login_required
def project_delete(request, pk):
    """Borra o desactiva un proyecto (solo Talento/admin)."""
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Acción reservada a Talento",
            "mensaje": "Solo Talento y Cultura puede eliminar proyectos.",
        }, status=403)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    project = get_object_or_404(Project, pk=pk)

    from apps.evaluations.models import OwnershipEvaluation, ValueDeliveryEvaluation
    has_evals = (
        OwnershipEvaluation.objects.filter(project=project).exists()
        or ValueDeliveryEvaluation.objects.filter(project=project).exists()
    )

    if has_evals:
        project.is_active = False
        project.save(update_fields=["is_active"])
        if request.headers.get("HX-Request"):
            return HttpResponse(
                f'<tr id="project-row-{pk}">'
                f'<td class="px-4 py-3"><p class="font-medium text-slate-900">{project.name}</p>'
                f'{"<p class=\'text-xs text-slate-500\'>" + project.client + "</p>" if project.client else ""}</td>'
                f'<td class="px-4 py-3 text-slate-600">{project.owner.full_name}</td>'
                f'<td class="px-4 py-3 text-slate-600">{project.get_duration_type_display()}</td>'
                f'<td class="px-4 py-3 text-center tabular-nums">—</td>'
                f'<td class="px-4 py-3"><span class="badge bg-slate-100 text-slate-500">Inactivo</span></td>'
                f'<td class="px-4 py-3 text-right">'
                f'<a href="/catalogo/proyectos/{pk}/" class="btn-soft mr-1">Editar</a>'
                f'<button type="button" hx-post="/catalogo/proyectos/{pk}/reactivar/" hx-target="#project-row-{pk}" hx-swap="outerHTML" hx-confirm="¿Reactivar {project.name}?" class="btn-soft">'
                f'<i data-lucide="rotate-ccw" class="w-3.5 h-3.5 inline"></i> Reactivar</button>'
                f'</td></tr>'
            )
        messages.info(request, f"Proyecto «{project.name}» desactivado. Puedes reactivarlo desde la lista.")
    else:
        nombre = project.name
        project.delete()
        if request.headers.get("HX-Request"):
            return HttpResponse("")
        messages.success(request, f"Proyecto «{nombre}» eliminado permanentemente.")

    return redirect("catalog:project_admin")


@login_required
def project_reactivate(request, pk):
    """Reactiva un proyecto desactivado (solo Talento/admin)."""
    if not request.user.is_admin:
        return render(request, "errors/403.html", {
            "titulo": "Acción reservada a Talento",
            "mensaje": "Solo Talento y Cultura puede reactivar proyectos.",
        }, status=403)
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    project = get_object_or_404(Project, pk=pk)
    project.is_active = True
    project.save(update_fields=["is_active"])

    if request.headers.get("HX-Request"):
        from apps.catalog.models import ProjectMembership
        members_count = ProjectMembership.objects.filter(project=project).count()
        return HttpResponse(
            f'<tr id="project-row-{pk}">'
            f'<td class="px-4 py-3"><p class="font-medium text-slate-900">{project.name}</p>'
            f'{"<p class=\'text-xs text-slate-500\'>" + project.client + "</p>" if project.client else ""}</td>'
            f'<td class="px-4 py-3 text-slate-600">{project.owner.full_name}</td>'
            f'<td class="px-4 py-3 text-slate-600">{project.get_duration_type_display()}</td>'
            f'<td class="px-4 py-3 text-center tabular-nums">{members_count}</td>'
            f'<td class="px-4 py-3"><span class="badge bg-emerald-50 text-emerald-700">Activo</span></td>'
            f'<td class="px-4 py-3 text-right">'
            f'<a href="/catalogo/proyectos/{pk}/" class="btn-soft mr-1">Editar</a>'
            f'<button type="button" hx-post="/catalogo/proyectos/{pk}/eliminar/" hx-target="#project-row-{pk}" hx-swap="outerHTML" hx-confirm="¿Eliminar {project.name}? Esta acción no se puede deshacer." class="p-1.5 rounded-lg text-red-600 hover:bg-red-50 border border-transparent hover:border-red-200 transition cursor-pointer"><i data-lucide="trash-2" class="w-4 h-4 inline"></i></button>'
            f'</td></tr>'
        )
    messages.success(request, f"Proyecto «{project.name}» reactivado.")
    return redirect("catalog:project_admin")
```

- [ ] **Step 3: Agregar URLs en catalog/urls.py**

En `apps/catalog/urls.py`, dentro de `urlpatterns`:

```python
path("proyectos/<int:pk>/eliminar/", views.project_delete, name="project_delete"),
path("proyectos/<int:pk>/reactivar/", views.project_reactivate, name="project_reactivate"),
```

- [ ] **Step 4: Commit**

```bash
git add apps/catalog/views.py apps/catalog/urls.py
git commit -m "feat(catalog): vistas y URLs para borrar/reactivar proyectos"
```

---

### Task 5: Botones de borrar/reactivar en `project_admin.html`

**Files:**
- Modify: `templates/catalog/project_admin.html`

**Interfaces:**
- Consumes: `catalog:project_delete`, `catalog:project_reactivate` (Task 4)

- [ ] **Step 1: Agregar `id` a cada `<tr>` y botones de acción**

Reemplazar la sección `<td>` de acciones (actualmente solo tiene enlace "Editar") y agregar `id` a la fila:

Cambiar:
```html
<tr>
```
por:
```html
<tr id="project-row-{{ p.pk }}">
```

Cambiar la celda de acciones de:
```html
<td class="px-4 py-3 text-right"><a href="{% url 'catalog:project_edit' pk=p.pk %}" class="btn-soft">Editar</a></td>
```
por:
```html
<td class="px-4 py-3 text-right flex items-center justify-end gap-1">
  <a href="{% url 'catalog:project_edit' pk=p.pk %}" class="btn-soft">Editar</a>
  {% if request.user.is_admin %}
    {% if not p.is_active %}
      <button type="button"
        hx-post="{% url 'catalog:project_reactivate' pk=p.pk %}"
        hx-target="#project-row-{{ p.pk }}"
        hx-swap="outerHTML"
        hx-confirm="¿Reactivar «{{ p.name }}»?"
        class="btn-soft">
        {% include "partials/icon.html" with name="rotate-ccw" cls="w-3.5 h-3.5" %} Reactivar
      </button>
    {% else %}
      <span class="relative group/ptip">
        <button type="button"
          hx-post="{% url 'catalog:project_delete' pk=p.pk %}"
          hx-target="#project-row-{{ p.pk }}"
          hx-swap="outerHTML"
          hx-confirm="¿Eliminar «{{ p.name }}»? Esta acción no se puede deshacer."
          class="p-1.5 rounded-lg text-red-600 hover:bg-red-50 border border-transparent hover:border-red-200 transition cursor-pointer">
          <i data-lucide="trash-2" class="w-4 h-4"></i>
        </button>
        <span class="pointer-events-none absolute bottom-full right-0 mb-1.5 whitespace-nowrap rounded-md bg-slate-800 px-2 py-1 text-xs text-white opacity-0 transition-opacity duration-150 group-hover/ptip:opacity-100 z-20">Eliminar proyecto</span>
      </span>
    {% endif %}
  {% endif %}
</td>
```

- [ ] **Step 2: Commit**

```bash
git add templates/catalog/project_admin.html
git commit -m "feat(ui): botones eliminar/reactivar proyecto en project_admin (solo Talento)"
```
