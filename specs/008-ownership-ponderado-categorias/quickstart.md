# Quickstart: validar Ownership ponderado por categorías

Guía de validación de extremo a extremo. Detalles en [data-model.md](./data-model.md) y [contracts/](./contracts/).

## Prerrequisitos

- `.\.venv\Scripts\python.exe` con `PYTHONIOENCODING=utf-8`.
- Migraciones aplicadas en local y en la BD de pruebas.
- Para producción: URL unpooled de `docs/neon.md` (nunca en el repo).

## 1. No regresión (SC-001)

```text
python manage.py verify_ownership_scores            # antes de migrar (línea base)
python manage.py migrate
python manage.py verify_ownership_scores            # después: diferencia cero en todas
```

Esperado: «N evaluaciones verificadas, 0 diferencias». Cualquier diferencia detiene el despliegue.

## 2. Cálculo ponderado

```text
.\.venv\Scripts\python.exe scripts/pytest_changed.py apps/core/tests/test_scoring_weighted.py apps/core/tests/test_ownership_weights.py
```

Esperado: «General» → promedio simple; 60/40 con 4.00 y 2.00 → 3.20; peso 0 no pondera; categoría toda N/A se redistribuye.

## 3. Editor con validación de 100% (SC-003, SC-004)

1. Entrar como Talento a *Cuestionarios*, duplicar un cuestionario y abrir el borrador.
2. En «Categorías del cuestionario» agregar dos categorías y poner 60.0 y 39.9: aparece «Suma actual 99.9% — debe llegar a 100%», «Guardar pesos» y «Publicar» deshabilitados.
3. Corregir a 40.0: el indicador pasa a correcto y se habilita guardar.
4. «Repartir en partes iguales» con 3 categorías: 33.4 / 33.3 / 33.3.
5. Intentar enviar un peso con dos decimales saltándose la pantalla: el servidor lo rechaza con el mismo mensaje.

## 4. Puestos

1. *Catálogos → Puestos*: ver la tabla; CONS muestra Analista, Consultor, Consultor Sr, Gerente.
2. Abrir el perfil de un usuario de CONS nivel JR: «Analista». Un usuario de Analítica sigue mostrando su nivel actual.

## 5. Cuestionarios de Consultoría

```text
python scripts/matriz_consultoria_to_yaml.py "docs/Matrices/Matriz de Competencias y Pesos por Puesto v1.1.xlsx" fixtures/questionnaires/cons/CONS.yaml
python manage.py import_questionnaire_version --dir fixtures/questionnaires/cons --target-version 1 --dry-run
python manage.py import_questionnaire_version --dir fixtures/questionnaires/cons --target-version 1
```

Esperado: reporte con pesos de categoría por puesto (Analista 13.6/22.7/18.2/45.5, etc.) y 4 cuestionarios en BORRADOR. Publicar solo con el VOBO de Dirección de Consultoría (o con `--publish`).

## 6. Evaluación de Consultoría

1. Como un Analista de CONS, abrir *Mis evaluaciones*, iniciar en un proyecto vigente: el evaluador sugerido aparece preseleccionado.
2. Responder: el panel de categorías se actualiza con el autoguardado; el promedio coincide con el cálculo de la matriz (± 0.01).
3. Como evaluador, completar Fortalezas y Oportunidades y cerrar: el informe del periodo muestra el desglose por categoría y el total.
4. Como usuario de Analítica: el desglose no aparece y el total es el de siempre.

## 7. Permisos y compilación de plantillas

```text
.\.venv\Scripts\python.exe scripts/pytest_changed.py apps/core/tests/test_access_coverage.py apps/core/tests/test_templates_compile.py
```

Esperado: en verde. Cambios de UI revisados por `frontend-auditor` (CUMPLE).
