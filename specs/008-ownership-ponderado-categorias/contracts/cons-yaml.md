# Contrato: YAML de importación con categorías y pesos

Extiende el formato de la spec 007 (`fixtures/questionnaires/2027/<AREA>.yaml`). Los archivos antiguos siguen funcionando sin cambios (una sola categoría «General» implícita).

```yaml
source: docs/Matrices/Matriz de Competencias y Pesos por Puesto v1.1.xlsx
templates:
- area: CONS
  level: JR                         # clave global de nivel (JR = Analista)
  scale_note: "Escala 1–4 …"        # opcional; si falta y existe v1, se copia de la v1
  scale:                            # opcional; obligatorio si el puesto no tiene v1
  - {value: 1, label: No cumple, description: "…", order: 1}
  - {value: 2, label: Necesita mejorar, description: "…", order: 2}
  - {value: 3, label: Cumple satisfactoriamente, description: "…", order: 3}
  - {value: 4, label: Excede, description: "…", order: 4}
  - {value: null, label: N/A, description: "", order: 5}
  categories:                       # opcional; si falta, «General» al 100%
  - {code: delivery_cliente, name: Delivery al cliente, weight: 13.6}
  - {code: desarrollo_producto, name: Desarrollo de producto, weight: 22.7}
  - {code: herramientas_gestion, name: Herramientas de gestión, weight: 18.2}
  - {code: actitud_persona, name: Actitud y persona, weight: 45.5}
  questions:
  - title: Habilidad de comunicación
    category: delivery_cliente      # obligatorio si hay `categories`
    weight: 30.0                    # % dentro de su categoría; omitido = partes iguales (todas o ninguna de la categoría)
    text: "Redacta de manera adecuada y concisa…"      # descripción del nivel esperado
    level_expectation: "N1 · Expuesto"
    guidance: "Skills: Mapeo de actores y RACI · …"
```

## Reglas

- Pesos con máximo 1 decimal. Suma de `categories[].weight` = 100.0; suma de `weight` de las preguntas de cada categoría = 100.0 (o todas omitidas).
- `category` de cada pregunta debe existir en `categories`; los códigos deben existir en el catálogo o se crean con su nombre.
- Una **sección por categoría** cuando `categories` tiene más de una; una sola sección «Checklist de Ownership» si es una o ninguna.
- Llave de identidad: (OWNERSHIP, área, nivel, versión). Idempotente; si la versión ya existe y alguna pregunta tiene respuestas, el puesto se **rechaza**; si existe sin respuestas se reconstruye.
- `--target-version 1` se admite solo cuando el puesto no tiene v1 y el YAML trae `scale`.
- Con `--publish` se publica vía `questionnaire_editor.publish_template`, que valida pesos, categorías y escala. Sin `--publish` queda en BORRADOR.
- `--dry-run` revierte la transacción y solo reporta.

## Comando

```text
python manage.py import_questionnaire_version --dir fixtures/questionnaires/cons --target-version 1 [--publish] [--dry-run]
```

## Generador

`scripts/matriz_consultoria_to_yaml.py <xlsx> <salida.yaml>` lee la hoja «01 · Matriz por Puesto», aplica el mapeo bloque → categoría de la spec (FR-022), calcula los pesos de categoría y de pregunta con mayor residuo a un decimal, imprime un reporte de desviaciones contra la matriz original y **falla** si alguna suma no es 100.0.
