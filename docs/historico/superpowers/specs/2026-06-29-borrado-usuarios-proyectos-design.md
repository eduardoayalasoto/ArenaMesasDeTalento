# Spec: Borrado de usuarios y proyectos para Talento

**Fecha:** 2026-06-29  
**Scope:** Permitir al perfil Talento eliminar usuarios y proyectos desde la UI, con manejo seguro de restricciones de FK.

---

## Contexto

Talento necesita poder dar de baja usuarios que ya no están en la empresa y limpiar proyectos obsoletos. El sistema tiene restricciones de integridad referencial (PROTECT y CASCADE) que deben respetarse. La regla principal: conservar el historial de evaluaciones con el nombre del usuario aunque la cuenta ya no exista.

---

## Acceso

Los botones de borrar/reactivar **solo son visibles y accesibles** para `request.user.is_admin` (rol TALENTO o superusuario). En el template se condicionan con `{% if request.user.is_admin %}`. Los endpoints backend validan lo mismo y devuelven 403 si no aplica.

---

## 1. Borrado de usuarios

### Lógica híbrida

**Caso A — Usuario sin historial propio** (sin `OwnershipEvaluation`, `ArenaImpactScore` ni `FinalScore`):

- Se intenta **hard delete** (`user.delete()`).
- Django borra por CASCADE: `ProjectMembership`, cualquier `OwnershipEvaluation` vacía.
- Si Django lanza `ProtectedError` (el usuario es `owner`/`responsable` de un proyecto, o está asignado como evaluador de otra persona, o capturó un ArenaImpact ajeno), se captura la excepción y se devuelve un mensaje de error claro explicando el bloqueo (p. ej. "Primero reasigna los proyectos donde es responsable").
- En éxito: la fila desaparece de la tabla vía HTMX.

**Caso B — Usuario con historial propio** (tiene al menos una evaluación, ArenaImpact o FinalScore):

- **Soft delete**: `user.is_active = False` + `user.deleted_at = timezone.now()`.
- No se toca ningún FK; el registro sigue en la BD.
- Las evaluaciones históricas conservan la referencia al usuario y muestran su nombre.
- En éxito: la fila desaparece de la tabla vía HTMX. Mensaje: "Usuario eliminado. Sus evaluaciones históricas se conservan."

### Cambio al modelo User

```python
deleted_at = models.DateTimeField("eliminado el", null=True, blank=True)
```

Requiere migración. No afecta ningún comportamiento existente.

### Filtros

- `user_admin` view: agregar `deleted_at__isnull=True` al queryset de usuarios.
- La vista `catalog/views.py:79` ya filtra `is_active=True`; con el soft delete (`is_active=False`) el usuario eliminado desaparece automáticamente de listas de miembros disponibles.

### Salvaguardas

- No se puede borrar al usuario que tiene la sesión activa.
- No se puede borrar un superusuario.

### Nuevo endpoint

```
POST /usuarios/<pk>/eliminar/   →  accounts:user_delete
```

Responde con fragmento HTMX que hace `outerHTML` swap del `<tr id="user-row-<pk>">` a string vacío (elimina la fila).

### UI

- Botón `trash-2` rojo en la columna Acciones de `user_admin.html`, dentro de `{% if request.user.is_admin %}`.
- Cada `<tr>` recibe `id="user-row-{{ u.id }}"` para ser el target del swap.
- `hx-confirm` con mensaje: "¿Borrar a [nombre]? [Si tiene historial: Sus evaluaciones se conservarán. | Si no tiene historial: Se eliminará permanentemente.]" — el texto del confirm se determina en la vista o se simplifica a uno genérico.
- Simplificación práctica: un solo mensaje de confirm genérico `"¿Eliminar a {{ u.full_name }}? Esta acción no se puede deshacer."` La lógica de si es soft o hard delete ocurre en el servidor.

---

## 2. Borrado / desactivación de proyectos

### Lógica híbrida

**Caso A — Proyecto sin evaluaciones** (sin `OwnershipEvaluation` ni `ValueDeliveryEvaluation`):

- **Hard delete** (`project.delete()`).
- Django borra por CASCADE: `ProjectMembership` del proyecto.
- En éxito: la fila desaparece.

**Caso B — Proyecto con evaluaciones:**

- `project.is_active = False`.
- Las evaluaciones históricas (Ownership, VD, FinalScore de miembros) se conservan intactas.
- La fila permanece en la tabla con badge "Inactivo" y aparece el botón "Reactivar".

### Reactivación de proyectos

```
POST /proyectos/<pk>/reactivar/   →  catalog:project_reactivate
```

- `project.is_active = True`.
- La fila se actualiza en la tabla vía HTMX: badge vuelve a "Activo", botón "Reactivar" desaparece, botón "Eliminar" vuelve.

### Nuevos endpoints

```
POST /proyectos/<pk>/eliminar/    →  catalog:project_delete
POST /proyectos/<pk>/reactivar/   →  catalog:project_reactivate
```

### UI

- Botón `trash-2` rojo en la columna de acciones de `project_admin.html`, dentro de `{% if request.user.is_admin %}`.
- Para proyectos inactivos: botón `rotate-ccw` (estilo `btn-soft`) "Reactivar".
- La tabla muestra proyectos activos e inactivos juntos; los inactivos se distinguen por el badge "Inactivo" ya existente.
- Cada `<tr>` recibe `id="project-row-<pk>"`.

---

## Resumen de cambios

| Componente | Cambio |
|---|---|
| `apps/accounts/models.py` | Añadir campo `deleted_at` |
| `accounts` migration | Nueva migración automática |
| `apps/accounts/views.py` | Nueva vista `user_delete`; filtro `deleted_at__isnull=True` en `user_admin` |
| `apps/accounts/urls.py` | Nueva ruta `user_delete` |
| `apps/catalog/views.py` | Nuevas vistas `project_delete`, `project_reactivate` |
| `apps/catalog/urls.py` | Dos nuevas rutas |
| `templates/accounts/user_admin.html` | Botón borrar en cada fila (guard `is_admin`), `id` en `<tr>` |
| `templates/catalog/project_admin.html` | Botón borrar + botón reactivar (guard `is_admin`), `id` en `<tr>` |
