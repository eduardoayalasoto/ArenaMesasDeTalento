"""Arena Learn (spec 004): solicitud, autorización y registro de cursos con costo.

La lógica de negocio (transiciones, aprobadores, evidencia) vive en
`apps/core/services/learning_flow.py`; aquí solo hay estructura y reglas locales.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords


class CourseKind(models.TextChoices):
    CURSO = "CURSO", "Curso"
    CERTIFICACION = "CERTIFICACION", "Certificación"
    CAPACITACION = "CAPACITACION", "Capacitación"
    CONFERENCIA = "CONFERENCIA", "Conferencia"
    OTRO = "OTRO", "Otro"


class Currency(models.TextChoices):
    MXN = "MXN", "MXN"
    USD = "USD", "USD"


class Pillar(models.TextChoices):
    NINGUNO = "", "Sin pilar específico"
    OWNERSHIP = "OWNERSHIP", "Ownership"
    ENTREGA_VALOR = "ENTREGA_VALOR", "Entrega de Valor"
    IMPACTO_ARENA = "IMPACTO_ARENA", "Impacto Arena"


def normalize_tags(raw: str) -> str:
    """'Power BI,  mlops ,power bi' -> 'power bi, mlops' (minúsculas, sin duplicados)."""
    seen: list[str] = []
    for part in (raw or "").split(","):
        tag = " ".join(part.strip().lower().split())
        if tag and tag not in seen:
            seen.append(tag)
    return ", ".join(seen)


class CatalogCourse(models.Model):
    """Curso del catálogo sugerido, administrado por Talento."""

    name = models.CharField("nombre", max_length=160)
    provider = models.CharField("proveedor / plataforma", max_length=120)
    url = models.URLField("liga", blank=True)
    kind = models.CharField("tipo", max_length=16, choices=CourseKind.choices, default=CourseKind.CURSO)
    reference_cost = models.DecimalField(
        "costo de referencia", max_digits=10, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField("moneda", max_length=3, choices=Currency.choices, default=Currency.MXN)
    duration_hours = models.PositiveSmallIntegerField("duración (horas)", null=True, blank=True)
    pillar = models.CharField("pilar", max_length=16, choices=Pillar.choices, blank=True, default="")
    tags = models.CharField("etiquetas", max_length=200, blank=True, help_text="Separadas por coma.")
    areas = models.ManyToManyField("catalog.Area", blank=True, related_name="+", verbose_name="áreas recomendadas")
    levels = models.ManyToManyField(
        "catalog.SeniorityLevel", blank=True, related_name="+", verbose_name="niveles recomendados",
    )
    description = models.TextField("descripción", blank=True)
    is_active = models.BooleanField("activo", default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    promoted_from = models.ForeignKey(
        "learning.CourseRequest", on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
        verbose_name="promovido desde",
    )

    class Meta:
        verbose_name = "curso del catálogo"
        verbose_name_plural = "catálogo de cursos"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.tags = normalize_tags(self.tags)
        super().save(*args, **kwargs)

    @property
    def tag_list(self) -> list[str]:
        return [t for t in self.tags.split(", ") if t]


class CourseRequest(models.Model):
    """Solicitud (o registro directo/histórico) de un curso por un colaborador."""

    class Status(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        EN_REVISION = "EN_REVISION", "En revisión"
        REQUIERE_AJUSTES = "REQUIERE_AJUSTES", "Requiere ajustes"
        RECHAZADA = "RECHAZADA", "Rechazada"
        CANCELADA = "CANCELADA", "Cancelada"
        AUTORIZADA = "AUTORIZADA", "En progreso"
        COMPLETADA = "COMPLETADA", "Completado · por validar"
        VALIDADA = "VALIDADA", "Completado"
        NO_CONCLUIDA = "NO_CONCLUIDA", "No concluido"

    class Stage(models.TextChoices):
        NINGUNA = "", "—"
        LEAD = "LEAD", "Lead"
        DIRECCION = "DIRECCION", "Dirección"
        TALENTO = "TALENTO", "Talento"

    class Origin(models.TextChoices):
        SOLICITUD = "SOLICITUD", "Solicitud con autorización"
        REGISTRO_DIRECTO = "REGISTRO_DIRECTO", "Registro directo"
        HISTORICO = "HISTORICO", "Histórico"

    class PaymentMode(models.TextChoices):
        NINGUNO = "", "Sin definir"
        REEMBOLSO = "REEMBOLSO", "Reembolso al colaborador"
        PAGO_DIRECTO = "PAGO_DIRECTO", "Pago directo de Arena"
        GRATUITO = "GRATUITO", "Gratuito / beca"
        OTRO = "OTRO", "Otro"

    class PaymentStatus(models.TextChoices):
        NINGUNO = "", "Sin definir"
        PENDIENTE_COMPRA = "PENDIENTE_COMPRA", "Pendiente de compra"
        COMPRADO = "COMPRADO", "Comprado"
        REEMBOLSO_SOLICITADO = "REEMBOLSO_SOLICITADO", "Reembolso solicitado"
        PAGADO = "PAGADO", "Reembolsado / pagado"

    class ReceiptType(models.TextChoices):
        NINGUNO = "", "Sin definir"
        CFDI = "CFDI", "CFDI a nombre de Arena Analytics"
        NOTA_RECIBO = "NOTA_RECIBO", "Nota / recibo con datos fiscales"
        SIN_COMPROBANTE = "SIN_COMPROBANTE", "Sin comprobante"

    # Estados visibles en el perfil público (FR-023/025).
    PUBLIC_STATUSES = (Status.AUTORIZADA, Status.COMPLETADA, Status.VALIDADA)
    # Estados en los que el dueño aún puede editar los datos del curso.
    EDITABLE_STATUSES = (Status.BORRADOR, Status.REQUIERE_AJUSTES)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="course_requests",
        verbose_name="colaborador",
    )
    catalog_course = models.ForeignKey(
        CatalogCourse, on_delete=models.PROTECT, null=True, blank=True, related_name="requests",
        verbose_name="curso del catálogo",
    )
    # Snapshot de los datos del curso (no cambia si se edita el catálogo).
    name = models.CharField("nombre del curso", max_length=160)
    provider = models.CharField("proveedor / plataforma", max_length=120)
    url = models.URLField("liga", blank=True)
    kind = models.CharField("tipo", max_length=16, choices=CourseKind.choices, default=CourseKind.CURSO)
    duration_hours = models.PositiveSmallIntegerField("duración (horas)", null=True, blank=True)
    pillar = models.CharField("pilar", max_length=16, choices=Pillar.choices, blank=True, default="")
    tags = models.CharField("etiquetas", max_length=200, blank=True)

    estimated_cost = models.DecimalField(
        "costo estimado", max_digits=10, decimal_places=2, null=True, blank=True,
    )
    currency = models.CharField("moneda", max_length=3, choices=Currency.choices, default=Currency.MXN)
    start_date_planned = models.DateField("inicio tentativo", null=True, blank=True)
    end_date_planned = models.DateField("fin tentativo", null=True, blank=True)
    justification = models.TextField("justificación", blank=True)

    origin = models.CharField("origen", max_length=16, choices=Origin.choices, default=Origin.SOLICITUD)
    status = models.CharField("estado", max_length=16, choices=Status.choices, default=Status.BORRADOR)
    current_stage = models.CharField(
        "etapa actual", max_length=10, choices=Stage.choices, blank=True, default="",
    )
    returned_from_stage = models.CharField(
        "regresada desde", max_length=10, choices=Stage.choices, blank=True, default="",
    )
    missing_lead = models.BooleanField("sin Lead", default=False)

    payment_mode = models.CharField(
        "modalidad de pago", max_length=16, choices=PaymentMode.choices, blank=True, default="",
    )
    payment_status = models.CharField(
        "estado del pago", max_length=24, choices=PaymentStatus.choices, blank=True, default="",
    )
    final_cost = models.DecimalField("costo final real", max_digits=10, decimal_places=2, null=True, blank=True)
    receipt_type = models.CharField(
        "tipo de comprobante", max_length=16, choices=ReceiptType.choices, blank=True, default="",
    )
    not_completed_reason = models.TextField("motivo de no conclusión", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    authorized_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "solicitud de curso"
        verbose_name_plural = "solicitudes de curso"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["status", "current_stage"]),
        ]

    def __str__(self):
        return f"{self.name} · {self.user}"

    @property
    def status_display(self) -> str:
        """Etiqueta para la UI: combina estado y etapa ('En revisión de Dirección')."""
        if self.status == self.Status.EN_REVISION and self.current_stage:
            return {
                self.Stage.LEAD: "En revisión del Lead",
                self.Stage.DIRECCION: "En revisión de Dirección",
                self.Stage.TALENTO: "En revisión de Talento",
            }[self.current_stage]
        return self.get_status_display()

    @property
    def status_tone(self) -> str:
        """Tono del badge: success / warning / danger / neutral / info."""
        S = self.Status
        return {
            S.VALIDADA: "success", S.COMPLETADA: "success", S.AUTORIZADA: "info",
            S.EN_REVISION: "warning", S.REQUIERE_AJUSTES: "warning",
            S.RECHAZADA: "danger", S.CANCELADA: "neutral", S.NO_CONCLUIDA: "neutral",
            S.BORRADOR: "neutral",
        }.get(self.status, "neutral")

    @property
    def is_editable(self) -> bool:
        return self.status in self.EDITABLE_STATUSES

    @property
    def is_public(self) -> bool:
        return self.status in self.PUBLIC_STATUSES

    @property
    def cost_overrun(self) -> bool:
        """Costo real supera al autorizado en más de 10% (FR-016)."""
        if self.final_cost is None or not self.estimated_cost:
            return False
        return self.final_cost > self.estimated_cost * Decimal("1.10")

    @property
    def tag_list(self) -> list[str]:
        return [t for t in self.tags.split(", ") if t]


class ApprovalStep(models.Model):
    """Bitácora inmutable de cada transición de una solicitud (FR-010)."""

    class Stage(models.TextChoices):
        LEAD = "LEAD", "Lead"
        DIRECCION = "DIRECCION", "Dirección"
        TALENTO = "TALENTO", "Talento"
        COLABORADOR = "COLABORADOR", "Colaborador"
        SISTEMA = "SISTEMA", "Sistema"

    class Action(models.TextChoices):
        ENVIAR = "ENVIAR", "Envió la solicitud"
        APROBAR = "APROBAR", "Aprobó"
        REGRESAR = "REGRESAR", "Regresó con comentarios"
        RECHAZAR = "RECHAZAR", "Rechazó"
        REENVIAR = "REENVIAR", "Reenvió con ajustes"
        OMITIR = "OMITIR", "Etapa omitida"
        REASIGNAR = "REASIGNAR", "Reasignó aprobador"
        CANCELAR = "CANCELAR", "Canceló"
        COMPLETAR = "COMPLETAR", "Cerró el curso con evidencia"
        NO_CONCLUIR = "NO_CONCLUIR", "Marcó como no concluido"
        VALIDAR_EVIDENCIA = "VALIDAR_EVIDENCIA", "Validó la evidencia"
        REGRESAR_EVIDENCIA = "REGRESAR_EVIDENCIA", "Regresó la evidencia"
        REEMPLAZAR_EVIDENCIA = "REEMPLAZAR_EVIDENCIA", "Reemplazó la evidencia"
        REGISTRAR = "REGISTRAR", "Registró el curso"

    request = models.ForeignKey(CourseRequest, on_delete=models.CASCADE, related_name="steps")
    stage = models.CharField(max_length=12, choices=Stage.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
    )
    action = models.CharField(max_length=24, choices=Action.choices)
    from_status = models.CharField(max_length=16, blank=True)
    to_status = models.CharField(max_length=16, blank=True)
    comment = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "paso de autorización"
        verbose_name_plural = "bitácora de autorización"
        ordering = ["created_at", "pk"]

    def __str__(self):
        return f"{self.get_action_display()} · {self.request_id}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise ValueError("La bitácora de autorización es inmutable.")
        super().save(*args, **kwargs)


class CourseEvidence(models.Model):
    """Archivo de evidencia (certificado público o comprobante fiscal privado)."""

    class Kind(models.TextChoices):
        CERTIFICADO = "CERTIFICADO", "Certificado / constancia"
        COMPROBANTE_FISCAL = "COMPROBANTE_FISCAL", "Comprobante fiscal"

    class Validation(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Por validar"
        VALIDADA = "VALIDADA", "Validada"
        REGRESADA = "REGRESADA", "Regresada"

    request = models.ForeignKey(CourseRequest, on_delete=models.CASCADE, related_name="evidences")
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CERTIFICADO)
    filename = models.CharField(max_length=200)
    mime = models.CharField(max_length=40)
    size = models.PositiveIntegerField()
    # Se guarda en la BD: el FS de Vercel es de solo lectura (research R3).
    data = models.BinaryField(editable=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    validation = models.CharField(
        max_length=10, choices=Validation.choices, default=Validation.PENDIENTE,
    )
    validation_comment = models.TextField(blank=True)

    class Meta:
        verbose_name = "evidencia"
        verbose_name_plural = "evidencias"
        ordering = ["uploaded_at", "pk"]

    def __str__(self):
        return self.filename

    @property
    def is_private(self) -> bool:
        return self.kind == self.Kind.COMPROBANTE_FISCAL

    @property
    def is_image(self) -> bool:
        return self.mime.startswith("image/")


class CourseReview(models.Model):
    """Reseña del colaborador sobre un curso que completó (FR-019)."""

    class Recommends(models.TextChoices):
        SI = "SI", "Sí, lo recomiendo"
        CON_RESERVAS = "CON_RESERVAS", "Con reservas"
        NO = "NO", "No lo recomiendo"

    request = models.OneToOneField(CourseRequest, on_delete=models.CASCADE, related_name="review")
    rating = models.PositiveSmallIntegerField("calificación", choices=[(i, str(i)) for i in range(1, 6)])
    opinion = models.TextField("opinión")
    recommends = models.CharField("¿lo recomiendas?", max_length=14, choices=Recommends.choices)
    recommend_why = models.TextField("¿por qué?")
    audience_areas = models.ManyToManyField(
        "catalog.Area", blank=True, related_name="+", verbose_name="áreas a las que lo recomiendas",
    )
    audience_levels = models.ManyToManyField(
        "catalog.SeniorityLevel", blank=True, related_name="+", verbose_name="niveles a los que lo recomiendas",
    )
    audience_notes = models.TextField("¿a quién más se lo recomiendas?", blank=True)
    learnings = models.TextField("aprendizajes clave y cómo los aplicaste")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "reseña"
        verbose_name_plural = "reseñas"

    def __str__(self):
        return f"Reseña de {self.request}"


DEFAULT_FISCAL_INSTRUCTIONS = (
    "Al comprar tu curso, solicita tu comprobante fiscal:\n"
    "• Preferente: CFDI a nombre de Arena Analytics.\n"
    "• Si la plataforma no emite CFDI: nota o recibo que incluya la razón social "
    "(Arena Analytics) y la dirección fiscal completa.\n"
    "Si tu modalidad es reembolso, registra aquí cuando lo hayas solicitado."
)


class LearningSettings(models.Model):
    """Configuración de Arena Learn editable por Talento (singleton pk=1)."""

    fiscal_instructions = models.TextField("instrucciones fiscales", default=DEFAULT_FISCAL_INSTRUCTIONS)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "configuración de Arena Learn"
        verbose_name_plural = "configuración de Arena Learn"

    def __str__(self):
        return "Configuración de Arena Learn"

    @classmethod
    def load(cls) -> "LearningSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
