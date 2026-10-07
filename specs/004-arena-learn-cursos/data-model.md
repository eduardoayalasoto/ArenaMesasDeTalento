# Data Model: Arena Learn (004)

App nueva `apps/learning`. Hay dos cambios en apps existentes, que viven en `accounts` y `catalog` con su propia migración cada uno.

## Cambios en modelos existentes

| Modelo | Campo nuevo | Tipo | Notas |
|---|---|---|---|
| `accounts.User` | `direct_lead` | FK → User, null, `SET_NULL`, `related_name="direct_reports"` | Lead directo (FR-006). No puede ser él mismo; esto se valida en el form y en el servicio |
| `catalog.Area` | `director` | FK → User, null, `SET_NULL`, `limit_choices_to={"role": "DIRECTOR"}` | Director del área (FR-007) |

## Modelos nuevos (`apps/learning/models.py`)

### `CatalogCourse`: curso del catálogo sugerido
- `name` (160), `provider` (120), `url` (URLField, blank)
- `kind`: `CURSO | CERTIFICACION | CAPACITACION | CONFERENCIA | OTRO`
- `reference_cost` (Decimal 10,2, null), `currency` (`MXN | USD`, default MXN)
- `duration_hours` (PositiveSmallInteger, null)
- `pillar`: `OWNERSHIP | ENTREGA_VALOR | IMPACTO_ARENA | ""` (opcional)
- `tags` (CharField 200, separadas por coma; se normaliza a minúsculas sin espacios dobles)
- `areas` M2M `catalog.Area` (blank) y `levels` M2M `catalog.SeniorityLevel` (blank): audiencia recomendada
- `description` (Text, blank)
- `is_active` (bool): archivado = False
- `created_by` FK User, `created_at`, `promoted_from` FK `CourseRequest` null (FR-029)
- Agregados, que se calculan y no se persisten: `completed_count`, `avg_rating`

### `CourseRequest`: solicitud o registro de curso (entidad central)
- `user` FK User (`PROTECT`), `catalog_course` FK CatalogCourse null (`PROTECT`)
- Snapshot de datos del curso (se copian del catálogo al crear, así el historial no cambia si el catálogo se edita): `name`, `provider`, `url`, `kind`, `duration_hours`, `pillar`, `tags`
- `estimated_cost` (Decimal, null si es gratuito), `currency`
- `start_date_planned`, `end_date_planned` (Date)
- `justification` (Text). Es obligatoria para `origin=SOLICITUD`
- `origin`: `SOLICITUD | REGISTRO_DIRECTO | HISTORICO`
- `status`: ver la máquina de estados abajo
- `current_stage`: `LEAD | DIRECCION | TALENTO | ""`
- `returned_from_stage`: igual que `current_stage`, para FR-009
- `missing_lead` (bool), `submitted_at`, `authorized_at`, `closed_at`
- **Pago (US3)**: `payment_mode` (`REEMBOLSO | PAGO_DIRECTO | GRATUITO | OTRO | ""`), `payment_status` (`PENDIENTE_COMPRA | COMPRADO | REEMBOLSO_SOLICITADO | PAGADO | ""`), `final_cost` (Decimal null), `receipt_type` (`CFDI | NOTA_RECIBO | SIN_COMPROBANTE | ""`)
- `not_completed_reason` (Text, blank)
- `history = HistoricalRecords()`
- Índices: `(user, status)` y `(status, current_stage)`
- Propiedad `cost_overrun`: True si `final_cost > estimated_cost * 1.10` (FR-016)

### `ApprovalStep`: bitácora inmutable (FR-010)
- `request` FK CourseRequest (`CASCADE`), `stage` (`LEAD | DIRECCION | TALENTO | COLABORADOR | SISTEMA`)
- `actor` FK User null (null para los saltos automáticos del sistema)
- `action`: `ENVIAR | APROBAR | REGRESAR | RECHAZAR | REENVIAR | OMITIR | REASIGNAR | CANCELAR | COMPLETAR | NO_CONCLUIR | VALIDAR_EVIDENCIA | REGRESAR_EVIDENCIA`
- `from_status`, `to_status`, `comment` (Text, blank; obligatorio en REGRESAR, RECHAZAR, CANCELAR y REASIGNAR), `created_at`
- Para REASIGNAR: `assigned_to` FK User null. Define al aprobador explícito de la etapa (FR-013) y tiene prioridad sobre la resolución automática
- `save()` lanza un error si `pk` ya existe (es inmutable)

### `CourseEvidence`: archivos
- `request` FK CourseRequest (`CASCADE`), `kind`: `CERTIFICADO | COMPROBANTE_FISCAL`
- `filename`, `mime`, `size`, `data` (BinaryField), `uploaded_by`, `uploaded_at`
- `validation`: `PENDIENTE | VALIDADA | REGRESADA` (solo aplica a CERTIFICADO), `validation_comment`
- Privacidad: `COMPROBANTE_FISCAL` siempre es privado (FR-016, FR-024)

### `CourseReview`: reseña (FR-019), relación 1:1 con `CourseRequest`
- `rating` (1–5), `opinion` (Text), `recommends`: `SI | NO | CON_RESERVAS`, `recommend_why` (Text)
- `audience_areas` M2M Area y `audience_levels` M2M SeniorityLevel (blank), `audience_notes` (Text, blank)
- `learnings` (Text: aprendizajes y cómo los aplicó), `created_at`, `updated_at`

### `LearningSettings`: singleton (pk=1)
- `fiscal_instructions` (Text, sembrado en la migración), `updated_by`, `updated_at`

## Máquina de estados de `CourseRequest`

```
BORRADOR ──enviar──▶ EN_REVISION(stage=primera etapa aplicable)
EN_REVISION(LEAD) ──aprobar──▶ EN_REVISION(DIRECCION) ──aprobar──▶ EN_REVISION(TALENTO) ──aprobar──▶ AUTORIZADA
EN_REVISION(*) ──regresar──▶ REQUIERE_AJUSTES(returned_from_stage=*) ──reenviar──▶ EN_REVISION(returned_from_stage)
EN_REVISION(*) ──rechazar──▶ RECHAZADA                       (terminal)
BORRADOR | EN_REVISION | REQUIERE_AJUSTES ──cancelar (dueño)──▶ CANCELADA   (terminal)
AUTORIZADA ──cancelar (Talento, motivo)──▶ CANCELADA
AUTORIZADA ──completar (evidencia+reseña)──▶ COMPLETADA ──validar (Talento)──▶ VALIDADA
COMPLETADA ──regresar evidencia──▶ COMPLETADA (validation=REGRESADA; el dueño reemplaza el archivo)
AUTORIZADA ──no concluir (motivo)──▶ NO_CONCLUIDA            (terminal)
REGISTRO_DIRECTO / HISTORICO: se crean directamente en COMPLETADA (evidencia+reseña obligatorias)
```

Nota de terminología: los estados de la spec ("En revisión del Lead", etc.) equivalen a `status=EN_REVISION` + `current_stage`. `status` lleva los valores `BORRADOR, EN_REVISION, REQUIERE_AJUSTES, RECHAZADA, CANCELADA, AUTORIZADA, COMPLETADA, VALIDADA, NO_CONCLUIDA`. La etapa se guarda aparte, en `current_stage`. La UI muestra la combinación, por ejemplo "En revisión de Dirección".

**Omisión de etapas** (FR-005, edge cases). Al entrar a una etapa:
- Si el solicitante es el único aprobador posible, o si el conjunto de aprobadores elegibles (excluyendo al solicitante) está vacío, la etapa se marca como `OMITIR` (actor=None) y se pasa a la siguiente.
- La etapa TALENTO nunca se omite. Si el solicitante es el único Talento, aprueba un superusuario.
- Si no hay ningún aprobador elegible en TALENTO, el servicio lanza un error y la solicitud no avanza.

## Reglas de validación
- `end_date_planned >= start_date_planned`.
- `estimated_cost >= 0`. Un costo de 0 o null para `SOLICITUD` se acepta, pero la UI sugiere usar el registro directo.
- Evidencia: mime en {pdf, png, jpeg, webp} validado por magic bytes, y tamaño ≤ 4 MB.
- `COMPLETADA` exige al menos 1 evidencia `CERTIFICADO` y una `CourseReview`.
- Solo el dueño edita los datos en `BORRADOR` y `REQUIERE_AJUSTES`. Nadie los edita en los demás estados, salvo los campos de pago (dueño y Talento) en `AUTORIZADA`, `COMPLETADA` y `VALIDADA`.
