# Quickstart — validación de 006

Requisitos: `.venv` activa y `PYTHONIOENCODING=utf-8`. Las pruebas corren contra Neon con `--reuse-db` y nunca en paralelo.

## 1. Pruebas automatizadas

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_learning_tags.py apps/core/tests/test_learning_plans.py apps/core/tests/test_learning_import.py apps/core/tests/test_learning.py apps/core/tests/test_access_coverage.py apps/core/tests/test_navigation.py --reuse-db
```

Resultado esperado: todo en verde. `test_access_coverage` confirma que cada ruta nueva tiene su clave en registry, seed y legacy.

## 2. Importación en seco (sin escribir)

```powershell
.\.venv\Scripts\python.exe manage.py import_learning_plans --dry-run
```

Resultado esperado en el resumen:
- ~249 cursos del Excel + las certificaciones del JSON; 0 filas no procesadas o solo las justificadas
- 4 planes (PM, UXUI, ID, CD) con estado PUBLICADO, agrupados por tipo de aprendizaje, sin agrupación KO
- La etiqueta "KO" asignada a los cursos de `ko` del JSON y ninguna otra etiqueta
- Alias reportados: las 3 ligas con dos nombres (AI-901, Unilever, Alison)
- 4 videos de YouTube como 4 cursos distintos

## 3. Corrida real en producción (orden de R11)

1. Aplicar las migraciones con la URL directa de `docs/neon.md`.
2. `manage.py reset_learning_data --before 2026-10-13` → los conteos deben coincidir con FR-039 (5 / 4 / 5 / 0 / 0 / 7).
3. Crear la rama de respaldo en Neon `backup-pre-006` y luego `reset_learning_data --before 2026-10-13 --confirm`.
4. `import_learning_plans` → guardar el resumen en `specs/006-…/reporte-importacion.md`.
5. Repetir el paso 4: el resumen debe decir **0 cursos creados, 0 planes creados** (SC-003).
6. Push a `main`.

## 4. Recorrido manual (después del deploy)

| Paso | Esperado |
|---|---|
| Colaborador PM entra a Arena Learn → Planes | Abre "Plan de Capacitación PM 2026" publicado |
| Filtra nivel Jr + etiqueta KO | Solo cursos KO con Jr o sin nivel (SC-004, < 30 s) |
| Agrega 5 cursos a Mi plan | Los 5 aparecen como Pendiente (SC-005, < 3 min) |
| "Empezar" en uno y "Solicitar autorización" en otro | El primero queda En curso; el segundo abre la solicitud precargada y Mi plan muestra "En revisión del Lead" |
| Su Lead abre Personas → la persona → Plan | Ve los mismos estados; otro colaborador recibe 403 (SC-008) |
| Talento → Etiquetas: crea "PowerBI", fusiona en "Power BI" | Los cursos quedan en "Power BI" sin duplicados |
| Talento → Seguimiento → Planes, filtro PM 2026 → Exportar | El Excel coincide con los totales en pantalla |
