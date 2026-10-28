# Quickstart: validar los checklists 2027

Prerequisitos: `.venv`, `PYTHONIOENCODING=utf-8`, acceso a Neon.

1. Regenerar el YAML (solo si cambian los Excel):
   `.\.venv\Scripts\python.exe scripts/checklists_2027_to_yaml.py` → 16 líneas "AREA/NIVEL: N reactivos", sin errores.
2. Pruebas: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_checklists_2027.py apps/core/tests/test_questionnaire_editor.py apps/core/tests/test_access_coverage.py --reuse-db`.
3. Producción (URL unpooled de `docs/neon.md` en `DATABASE_URL`):
   - `manage.py migrate questionnaires`
   - `manage.py import_questionnaire_version --dir fixtures/questionnaires/2027 --target-version 2 --dry-run` → 16 puestos OK.
   - Igual sin `--dry-run` y con `--publish`.
4. Verificación:
   - Cuestionarios: 16 Ownership v2 **Publicado**, v1 **Archivado**, Entrega de Valor v1 Publicado.
   - Conteo de respuestas = 2.116 (igual que antes).
   - Abrir una evaluación de 2026-S1 en borrador (PM Snr): sigue en v1 con sus respuestas.
   - Editor → Ownership CD Jr v2: cada reactivo muestra "Ver criterio".
