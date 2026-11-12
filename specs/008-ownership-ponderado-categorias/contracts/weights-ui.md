# Contrato: pantallas de pesos y desglose

## Editor de cuestionarios (`questionnaires:template_edit`, solo BORRADOR)

Permiso: `questionnaires.manage`. Acciones POST nuevas (todas validadas por Django Forms y por `ownership_weights`):

| `action` | Campos | Efecto |
|---|---|---|
| `add_template_category` | `category` | Agrega la categoría con peso 0.0 (la suma sigue en 100.0) |
| `remove_template_category` | `category` | Solo si no tiene preguntas; exige re-guardar los pesos para volver a 100.0 |
| `save_category_weights` | `w_<category_id>` por cada categoría | Guarda todos o ninguno; rechaza si Σ ≠ 100.0 |
| `save_question_weights` | `category`, `q_<question_id>` por pregunta de esa categoría | Guarda todos o ninguno; rechaza si Σ ≠ 100.0 |
| `equalize_category_weights` | — | Reparto en partes iguales (mayor residuo) |
| `equalize_question_weights` | `category` | Reparto en partes iguales entre las preguntas de la categoría |
| `clear_question_weights` | `category` | Vuelve las preguntas de la categoría a «partes iguales» (peso nulo) |
| `save_question` (existente) | + `category` | Asigna la categoría de la pregunta |

### Comportamiento en pantalla (Alpine, sin `fetch`)

- Cada grupo de pesos (categorías del cuestionario; preguntas de cada categoría) es un formulario con un componente que lleva el **total en décimas enteras**.
- Mientras el total ≠ 1000 décimas: aviso `Suma actual {X}% — debe llegar a 100%` (con el faltante o sobrante) en estado de advertencia, y el botón «Guardar pesos» deshabilitado. Con total = 100.0: indicador de correcto y botón habilitado.
- El botón «Publicar» está deshabilitado mientras cualquier grupo no cuadre y muestra qué grupo falla.
- Campos numéricos con `step=0.1`, `min=0`, `max=100`; un decimal como máximo (el valor se normaliza a un decimal al salir del campo).
- «Repartir en partes iguales» actualiza los campos en el cliente con el mismo algoritmo (mayor residuo) y refleja el total.
- Mensajes de error del servidor (si se salta la pantalla) usan el mismo texto: `Los pesos de «{grupo}» suman {X}%; deben sumar 100%.`

## Catálogos

- `catalog:position_admin` — lista área × nivel con nombre y estado; editar nombre y activar/desactivar; clave `catalog.positions.manage`.
- `catalog:category_admin` — lista y alta/edición de categorías (nombre, orden, activa); clave `catalog.categories.manage`.

## Evaluación de Ownership

- `ownership_fill.html` muestra el panel de **score por categoría** (`_category_scores.html`) solo si el cuestionario tiene más de una categoría: fila por categoría con nombre, peso, score y calificadas/total; «sin calificar» si no hay respuestas.
- `ownership_autosave` conserva su respuesta JSON y **agrega** `categories`:

```json
{
  "ok": true, "answered": 12, "total": 17, "average": "3.21",
  "categories": [
    {"code": "delivery_cliente", "name": "Delivery al cliente", "weight": "30.2", "score": "3.40", "answered": 4, "total": 5}
  ]
}
```

`categories` es una lista vacía cuando el cuestionario tiene una sola categoría.

## Informe de resultados

`dashboards/_results_body.html` muestra, bajo la tarjeta de Ownership, el desglose por categoría del periodo (promedio de las evaluaciones enviadas por categoría) cuando existe más de una categoría; se oculta para «General».

## Inicio de evaluación

`ownership_start` recibe `suggested_id` (evaluador sugerido → owner → responsable, nunca el propio colaborador) y lo preselecciona como principal; el colaborador puede cambiarlo y agregar secundarios.
