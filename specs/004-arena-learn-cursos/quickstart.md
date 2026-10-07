# Quickstart: validar Arena Learn (004)

## Prerrequisitos

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe manage.py migrate
.\build_css.ps1
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Las pruebas corren contra `test_neondb`. Usa `--reuse-db` y nunca corras dos procesos de pytest en paralelo:

```powershell
.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_learning_flow.py apps/core/tests/test_learning_views.py --reuse-db
.\.venv\Scripts\python.exe -m pytest apps/core/tests/ --reuse-db   # regresión completa
```

## Escenarios de validación (los mismos que el spec)

1. **Solicitud desde el catálogo (US1, US6)**: como Talento, da de alta un curso en `/arena-learn/catalogo/nuevo/`. Luego, como colaborador, en `/arena-learn/catalogo/` usa "Solicitar". Se espera un form precargado, y al enviar el estado "En revisión del Lead".
2. **Flujo completo (US2)**: asigna un Lead directo en `/cuenta/usuarios/` y un Director al área. Aprueba como Lead, luego como Director y luego como Talento desde `/arena-learn/por-aprobar/`. Se espera AUTORIZADA, con la bitácora de 4 pasos en el detalle.
3. **Regresar y reanudar (FR-009)**: el Director regresa la solicitud con un comentario y el colaborador la reenvía. Se espera que vuelva a "En revisión de Dirección", sin pasar por el Lead.
4. **Saltos de etapa**: un solicitante de nivel LEAD empieza en Dirección. Un solicitante de UX/UI sin Lead empieza en Dirección con la marca "sin Lead".
5. **Bloqueo FR-004**: con un curso AUTORIZADO sin cerrar, una nueva solicitud se rechaza indicando qué curso falta cerrar. Si lo marcas como No concluido, ya puedes enviar.
6. **Cierre (US4)**: sube un PDF de 3 MB y llena la reseña. Se espera COMPLETADA. Un archivo de 5 MB o un `.exe` renombrado se rechazan.
7. **Perfil público (US5)**: con otro usuario colaborador, abre `/arena-learn/personas/<pk>/`. Se ven el curso, la reseña y el certificado, pero **no** el costo, la justificación, el pago ni el comprobante. La URL del comprobante responde 403.
8. **Tablero (US7)**: en `/arena-learn/seguimiento/` revisa los conteos, la solicitud atascada (simula `created_at` de hace 8 días hábiles) y el exporte `.xlsx`.
9. **Campana**: el aprobador ve "1 solicitud de curso por aprobar" y el colaborador ve "Cierra tu curso X".

## Despliegue

Este cambio tiene migraciones (accounts, catalog, learning) y Vercel no las corre. Hay que aplicarlas contra Neon con la URL unpooled antes o junto con el push (ver `docs/neon.md`).
