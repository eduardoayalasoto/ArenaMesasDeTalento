# Quickstart: validar la matriz de permisos (005)

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_access.py apps/core/tests/test_access_coverage.py --reuse-db
.\.venv\Scripts\python.exe manage.py access_report            # qué gana / pierde cada persona (FR-011b)
```

## Escenarios

1. **Cobertura**: agrega una ruta de prueba sin `@requires`. `test_access_coverage` debe fallar y nombrarla.
2. **Paridad**: `test_access_parity` compara la regla anterior contra la matriz para cada perfil y permiso. Toda diferencia debe estar en `EXPECTED_CHANGES`.
3. **Matriz**: en `/catalogo/perfiles/`, quita a Director el permiso `talent_table.view`. El Director deja de ver "Mesa de Talento" en el menú y recibe 403 por URL. Restablécelo.
4. **Lead flexible**: da a Lead `talent_table.view` = Ár. Un Lead de PM ve solo a las personas de PM.
5. **Asignación**: en Usuarios, cambia el perfil de una persona. El cambio aplica en su siguiente request y queda en la bitácora.
6. **Auto-bloqueo**: intenta quitar `access.manage` al único perfil de Talento. Se impide.
7. **Asignables**: quita `assign.direct_lead` a Lead. Los Leads ya no aparecen en el selector de "Lead directo".

## Despliegue

Este cambio lleva migraciones (access, accounts y semilla). Aplícalas a Neon **antes** del push. Antes de activar, comparte con Talento la salida de `access_report`.
