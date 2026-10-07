# Research: Arena Learn (004)

Decisiones de diseño tomadas contra el código real del repo (auditoría 2026-10-06).

## R1. ¿Dónde viven los modelos y la lógica?

- **Decision**: App nueva `apps/learning` (modelos, urls, views, forms, admin). La lógica de negocio va en `apps/core/services/learning_flow.py` y la visibilidad en `apps/core/services/permissions.py`, igual que el resto del sistema. Tests en `apps/core/tests/test_learning_*.py`.
- **Rationale**: es un dominio nuevo, con 7 modelos y sus propias URLs. Mezclarlo en `evaluations` lo acoplaría al ciclo de periodos, y Arena Learn no depende de periodos. Además, la convención documentada (`docs/CONTEXTO_Sistema.md` §7) es que toda la lógica viva en `apps/core/services/`.
- **Alternatives**: poner los modelos en `apps/evaluations` (se descartó por el acoplamiento a periodos). Poner `services.py` dentro de la app (se descartó porque rompe la convención del repo).

## R2. ¿Quién es "el Lead" y quién es "el Director"? (Clarifications 2026-10-06)

- **Decision**:
  - Se agrega `User.direct_lead`: un FK a `User` que acepta vacío, con `on_delete=SET_NULL` y `limit_choices_to` a usuarios activos. Se edita en `/cuenta/usuarios/`.
  - Se agrega `Area.director`: un FK a `User` que acepta vacío, limitado a `role=DIRECTOR`. Se edita en el catálogo de áreas, o vía admin/servicio si no existe pantalla.
  - La resolución de aprobadores es una función pura de servicio, `eligible_approvers(request, stage)`:
    - **LEAD**: el `direct_lead`. Si no hay, cualquier usuario `level.code=="LEAD"` del área del solicitante, excluyéndolo a él. Si no hay ninguno, la etapa se omite y se marca `missing_lead=True`.
    - **DIRECCION**: `area.director`. Si no hay, cualquier usuario `role=DIRECTOR`. Siempre excluye al solicitante.
    - **TALENTO**: cualquier `is_admin` (Talento o superusuario) distinto del solicitante.
- **Rationale**: hoy en datos reales PM tiene 2 Leads, UX/UI tiene 0 y Tecnología no es un `Area`. Un dato explícito con respaldo cubre todos los casos sin bloquear el flujo.
- **Alternatives**: responsable del proyecto (N candidatos, y cambia con los proyectos). Cualquier Director (permitiría aprobaciones cruzadas entre Analítica y Tecnología).

## R3. Almacenamiento de evidencia

- **Decision**: guardar los archivos **en la BD** en un modelo `CourseEvidence`, con `data` BinaryField, `mime`, `filename` y `size`. Se sirven con una vista autenticada que valida permisos, el mismo patrón que `accounts:user_photo`.
  - Límite de **4 MB** por archivo (el cuerpo máximo de Vercel es 4.5 MB). La validación se hace en el form y también en el servicio.
  - Las imágenes se re-encodan con Pillow (lado mayor ≤ 2000 px, JPEG o WEBP de calidad 85) para reducir el peso. Los PDF se guardan tal cual.
  - Se valida el tipo con magic bytes (`%PDF`, PNG, JPEG, WEBP), no con la extensión.
- **Rationale**: el FS de Vercel es de solo lectura y no hay almacenamiento de objetos configurado (`STORAGES.default=FileSystemStorage`, sin dependencias de storage). Las fotos ya siguen este patrón en producción. El volumen esperado es bajo: unas 65 personas por unos 3 cursos al año por menos de 2 MB, o sea menos de 0.5 GB al año.
- **Riesgo / salida**: si el volumen crece, se migra a Vercel Blob (privado) cambiando solo `CourseEvidence` y la vista de descarga. La API del servicio no cambia.
- **Alternatives**: Vercel Blob privado (agrega dependencia, token y subida directa desde el cliente; es desproporcionado para el volumen actual). S3 (igual).

## R4. Notificaciones

- **Decision**:
  - **Campana**: se extiende `apps/core/context_processors.notifications` con los pendientes de Arena Learn: solicitudes en mi etapa como aprobador, mis solicitudes regresadas, mis cursos autorizados por cerrar y, para Talento, las evidencias por validar.
  - **Correo**: en cada transición se llama a `send_mail(..., fail_silently=True)` desde el servicio, después del commit (`transaction.on_commit`). Solo se envía de verdad si `EMAIL_USE_SMTP` está activo; si no, sale al backend de consola.
- **Rationale**: FR-012 se degradó a "campana siempre, correo si está habilitado". Hoy no hay SMTP en producción.
- **Alternatives**: cola o cron (no hay infraestructura de cron configurada).

## R5. Máquina de estados y auditoría

- **Decision**:
  - El campo `CourseRequest.status` es un `TextChoices`. Las transiciones están permitidas solo por funciones del servicio, que usan `transaction.atomic` y `select_for_update`.
  - Cada transición crea un `ApprovalStep`, inmutable: no tiene vista de edición y `save()` rechaza actualizaciones.
  - `CourseRequest` lleva `HistoricalRecords` para auditar los cambios de campos (pago, costo final).
  - `returned_from_stage` guarda en qué etapa se regresó la solicitud, para reanudar ahí (FR-009).
- **Rationale**: es el mismo patrón que `period_lifecycle` y `ownership_flow`. `simple_history` ya está instalado.

## R6. Visibilidad pública (excepción a RN-14)

- **Decision**: se agregan funciones nuevas en `permissions.py`. `visible_users` **no se toca**.
  - `can_view_learning_profile(viewer, person)`: siempre True para un usuario autenticado y activo. Solo expone la ficha pública y Arena Learn.
  - `can_view_course_private(viewer, req)`: devuelve True para el dueño, para los aprobadores que actuaron o son elegibles en la etapa actual, para `is_admin` y para `is_director`.
  - `learning_public_requests(person)`: devuelve los registros con estado `AUTORIZADA`, `COMPLETADA` o `VALIDADA` (FR-023/025).
  - Los templates públicos **no** reciben los campos privados en el contexto. No se trata de ocultarlos con `{% if %}`: la vista pública arma un dict o queryset `.only(...)` sin costo, justificación ni pago.
- **Rationale**: así la excepción queda acotada y se puede probar. Cambiar `visible_users` filtraría las calificaciones.

## R7. Regla "cierra antes de pedir otro" (FR-004)

- **Decision**: `assert_can_submit(user)` lanza `ValidationError` si existe una `CourseRequest` del usuario en `AUTORIZADA` cuyo `origin=SOLICITUD`. Los cursos `COMPLETADA` (pendiente de validar) **no** bloquean, para no castigar la demora de Talento. Los `REGISTRO_DIRECTO` nunca bloquean.

## R8. Días hábiles y alertas

- **Decision**: "Atascada" significa más de 5 días hábiles (lunes a viernes, sin feriados) desde el último `ApprovalStep`. "Vencido" significa `AUTORIZADA` y `end_date_planned + 30 días < hoy`. Ambas se calculan en el servicio `learning_dashboard_rows()`, sin persistir.
- **Alternatives**: un calendario de feriados MX (se pospone; el margen de error es aceptable para una alerta).

## R9. UI

- **Decision**:
  - Plantillas Django + Tailwind (se recompila con `build_css.ps1`), Lucide, Alpine solo para el estado local (tabs, vista previa de archivo) y htmx para las acciones de aprobación desde la bandeja: `hx-post` devuelve la fila parcial y un toast, igual que `user_admin.html`.
  - Las confirmaciones destructivas (rechazar, cancelar) usan el patrón de modal ya existente en `ownership_fill.html`, con motivo obligatorio.
  - Se agrega al sidebar el ítem **Arena Learn** (`graduation-cap`) visible para todos. Dentro tiene las subsecciones Mis cursos, Catálogo, Personas, Por aprobar (si aplica) y Seguimiento (solo Talento).

## R10. Exporte

- **Decision**: `learning_export_xlsx` con openpyxl, mismo patrón que `dashboards:export_scores_xlsx`. El costo va como celda numérica y la moneda en columna aparte.

## R12. Ajustes de /speckit-analyze (2026-10-06)

- **I1**: US2-AS1 alineado a FR-007 (Director del área, con respaldo).
- **I2/I3**: el tablero filtra por **año**, no por periodo de evaluación. Dirección lo ve en solo lectura.
- **U1**: se agrega `replace_evidence` para reemplazar una evidencia regresada (T030/T032).
- **U2**: no existe pantalla de áreas; T054 la crea.
- **U3**: el perfil de un usuario dado de baja sigue accesible; el directorio lo excluye (T041).
- **T2**: T048 (registro directo, FR-022) se reetiqueta como US4.

## R11. Instrucciones fiscales

- **Decision**: modelo singleton `LearningSettings` (pk=1) con `fiscal_instructions` (TextField) y `currency_default`. Lo edita Talento y se siembra en la migración con el texto del proceso actual: CFDI a nombre de Arena Analytics, o nota/recibo con razón social y dirección fiscal completa.
