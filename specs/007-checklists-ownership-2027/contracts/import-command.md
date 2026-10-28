# Contrato: `manage.py import_questionnaire_version`

```text
python manage.py import_questionnaire_version --dir fixtures/questionnaires/2027 --target-version 2 [--publish] [--dry-run]
```

| Opción | Obligatoria | Efecto |
|---|---|---|
| `--dir` | sí | Carpeta con `<AREA>.yaml` (formato en data-model.md). |
| `--target-version` | sí | Versión destino (entero ≥ 2). |
| `--publish` | no | Publica cada versión cargada (`publish_template`: valida y archiva la anterior). |
| `--dry-run` | no | Ejecuta todo en una transacción que se revierte; solo reporta. |

Comportamiento por puesto (área + nivel). Toda la carga es una sola transacción: si un puesto falla, no se guarda ninguno.

1. Sin v1 publicada/archivada del puesto → error (no hay escala de la cual copiar).
2. Versión destino existe y algún reactivo tiene respuestas → `CommandError`, no se toca nada.
3. Versión destino existe sin respuestas → se reconstruye (sección única, reactivos, escala, nota). Si estaba PUBLICADA sigue publicada.
4. No existe → se crea en BORRADOR.
5. Borradores de versión mayor sin respuestas → ARCHIVADO.
6. `--publish` → `publish_template`.

Salida: una línea por puesto `CD/JR v2: 21 reactivos · PUBLICADO` y un total. Código de salida ≠ 0 ante cualquier error.
