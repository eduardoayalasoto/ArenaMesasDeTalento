"""Catálogos base: áreas, niveles, ponderaciones, periodos, proyectos y equipos."""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords


class Area(models.Model):
    """Área de Analítica (RN-01). Cuatro: ID, CD, PM, UXUI."""

    code = models.CharField("clave", max_length=8, unique=True)
    name = models.CharField("nombre", max_length=80)
    is_active = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "área"
        verbose_name_plural = "áreas"
        ordering = ["code"]

    def __str__(self):
        return self.name


class SeniorityLevel(models.Model):
    """Nivel de seniority (RN-01). Cuatro: JR, MID, SNR, LEAD."""

    code = models.CharField("clave", max_length=8, unique=True)
    name = models.CharField("nombre", max_length=40)
    order = models.PositiveSmallIntegerField("orden", default=1)

    class Meta:
        verbose_name = "nivel de seniority"
        verbose_name_plural = "niveles de seniority"
        ordering = ["order"]

    def __str__(self):
        return self.name


class PillarWeight(models.Model):
    """Ponderación de los 3 pilares por nivel (RN-19). Debe sumar 1.00."""

    level = models.OneToOneField(
        SeniorityLevel, on_delete=models.CASCADE, related_name="weight",
        verbose_name="nivel",
    )
    w_ownership = models.DecimalField("peso Ownership", max_digits=4, decimal_places=2)
    w_value_delivery = models.DecimalField(
        "peso Entrega de Valor", max_digits=4, decimal_places=2
    )
    w_arena_impact = models.DecimalField(
        "peso Impacto Arena", max_digits=4, decimal_places=2
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = "ponderación por nivel"
        verbose_name_plural = "ponderaciones por nivel"

    def __str__(self):
        return f"Ponderación {self.level.code}"

    def clean(self):
        total = self.w_ownership + self.w_value_delivery + self.w_arena_impact
        if total != Decimal("1.00"):
            raise ValidationError(
                "Los tres pesos deben sumar exactamente 1.00 (100%). "
                f"Actualmente suman {total}."
            )


class EvaluationPeriod(models.Model):
    """Periodo de evaluación (RN-13). Estados PLANEADO → ABIERTO → CERRADO."""

    class Kind(models.TextChoices):
        SEMESTRAL = "SEMESTRAL", "Semestral"
        TRIMESTRAL = "TRIMESTRAL", "Trimestral"

    class Status(models.TextChoices):
        PLANEADO = "PLANEADO", "Planeado"
        ABIERTO = "ABIERTO", "Abierto"
        CERRADO = "CERRADO", "Cerrado"

    name = models.CharField("nombre", max_length=40, unique=True)
    start_date = models.DateField("fecha de inicio")
    end_date = models.DateField("fecha de cierre")
    kind = models.CharField(
        "tipo", max_length=12, choices=Kind.choices, default=Kind.SEMESTRAL
    )
    status = models.CharField(
        "estado", max_length=12, choices=Status.choices, default=Status.PLANEADO
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = "periodo"
        verbose_name_plural = "periodos"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name

    @property
    def is_open(self):
        return self.status == self.Status.ABIERTO

    @property
    def is_closed(self):
        return self.status == self.Status.CERRADO


class Project(models.Model):
    """Proyecto con líder único y equipo (RN-16)."""

    class Duration(models.TextChoices):
        FINITO = "FINITO", "Tiempo finito (con fecha de entrega)"
        INDEFINIDO = "INDEFINIDO", "Servicio / iniciativa de tiempo indefinido"

    class Status(models.TextChoices):
        ON_TRACK = "ON_TRACK", "On track"
        DELAYED = "DELAYED", "Delayed"

    name = models.CharField("nombre", max_length=160)
    client = models.CharField("cliente", max_length=160, blank=True)
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="led_projects",
        verbose_name="líder de proyecto",
    )
    duration_type = models.CharField(
        "tipo de duración", max_length=12, choices=Duration.choices,
        default=Duration.FINITO,
    )
    is_active = models.BooleanField("activo", default=True)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="responsible_projects",
        verbose_name="responsable",
    )
    kickoff = models.DateField("kick-off", null=True, blank=True)
    target_close = models.DateField("cierre objetivo", null=True, blank=True)
    status = models.CharField(
        "estatus", max_length=10, choices=Status.choices, default=Status.ON_TRACK
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = "proyecto"
        verbose_name_plural = "proyectos"
        ordering = ["name"]

    def __str__(self):
        return self.name

    @property
    def is_finite(self):
        return self.duration_type == self.Duration.FINITO


class ProjectMembership(models.Model):
    """Pertenencia de un colaborador a un proyecto (RN-05, RN-16)."""

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="memberships",
        verbose_name="proyecto",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="memberships", verbose_name="colaborador",
    )
    start = models.DateField("desde", null=True, blank=True)
    end = models.DateField("hasta", null=True, blank=True)

    class Meta:
        verbose_name = "miembro de proyecto"
        verbose_name_plural = "miembros de proyecto"
        unique_together = ("project", "user")
        ordering = ["project__name", "user__full_name"]

    def __str__(self):
        return f"{self.user} en {self.project}"
