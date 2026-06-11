"""Catálogo administrable de cuestionarios: los cuestionarios son datos, no código."""

from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords


class QuestionnaireTemplate(models.Model):
    """Versión congelable de un cuestionario (RN: versionado). 16 Ownership + 1 Entrega de Valor."""

    class Kind(models.TextChoices):
        OWNERSHIP = "OWNERSHIP", "Ownership"
        VALUE_DELIVERY = "VALUE_DELIVERY", "Entrega de Valor"

    class Status(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        PUBLICADO = "PUBLICADO", "Publicado"
        ARCHIVADO = "ARCHIVADO", "Archivado"

    kind = models.CharField("tipo", max_length=16, choices=Kind.choices)
    area = models.ForeignKey(
        "catalog.Area", on_delete=models.PROTECT, null=True, blank=True,
        related_name="templates", verbose_name="área",
    )
    level = models.ForeignKey(
        "catalog.SeniorityLevel", on_delete=models.PROTECT, null=True, blank=True,
        related_name="templates", verbose_name="nivel",
    )
    version = models.PositiveIntegerField("versión", default=1)
    status = models.CharField(
        "estado", max_length=12, choices=Status.choices, default=Status.BORRADOR
    )
    scale_note = models.TextField(
        "nota de escala", blank=True,
        help_text="Texto de la escala que se muestra al usuario.",
    )
    history = HistoricalRecords()

    class Meta:
        verbose_name = "cuestionario"
        verbose_name_plural = "cuestionarios"
        ordering = ["kind", "area__code", "level__order", "-version"]
        constraints = [
            # Solo una versión PUBLICADA por (kind, area, level).
            models.UniqueConstraint(
                fields=["kind", "area", "level"],
                condition=models.Q(status="PUBLICADO"),
                name="unique_published_template",
            ),
            models.UniqueConstraint(
                fields=["kind", "area", "level", "version"],
                name="unique_template_version",
            ),
        ]

    def __str__(self):
        if self.kind == self.Kind.VALUE_DELIVERY:
            return f"Entrega de Valor v{self.version}"
        return f"Ownership {self.area.code}/{self.level.code} v{self.version}"

    @property
    def is_published(self):
        return self.status == self.Status.PUBLICADO

    @property
    def question_count(self):
        return Question.objects.filter(section__template=self).count()


class Section(models.Model):
    """Sección temática del cuestionario."""

    template = models.ForeignKey(
        QuestionnaireTemplate, on_delete=models.CASCADE,
        related_name="sections", verbose_name="cuestionario",
    )
    title = models.CharField("título", max_length=160)
    order = models.PositiveSmallIntegerField("orden", default=1)

    class Meta:
        verbose_name = "sección"
        verbose_name_plural = "secciones"
        ordering = ["template", "order"]

    def __str__(self):
        return self.title


class Question(models.Model):
    """Ítem calificable o de texto."""

    class Type(models.TextChoices):
        SCALE = "SCALE", "Escala 1–4 / N/A"
        TEXT_LONG = "TEXT_LONG", "Texto largo"

    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="questions", verbose_name="sección"
    )
    order = models.PositiveSmallIntegerField("orden", default=1)
    title = models.CharField("título", max_length=200)
    text = models.TextField("descripción", blank=True)
    qtype = models.CharField(
        "tipo", max_length=12, choices=Type.choices, default=Type.SCALE
    )
    weight = models.DecimalField("peso", max_digits=4, decimal_places=2, default=1)
    allow_na = models.BooleanField("permite N/A", default=True)
    is_required = models.BooleanField("obligatoria", default=True)

    class Meta:
        verbose_name = "pregunta"
        verbose_name_plural = "preguntas"
        ordering = ["section", "order"]

    def __str__(self):
        return self.title


class ScaleOption(models.Model):
    """Opción de respuesta de escala (catálogo administrable de respuestas y puntajes).

    A nivel template aplica a todas las preguntas SCALE del cuestionario; a nivel
    question permite descriptores propios (necesario en Entrega de Valor).
    """

    template = models.ForeignKey(
        QuestionnaireTemplate, on_delete=models.CASCADE, null=True, blank=True,
        related_name="scale_options", verbose_name="cuestionario",
    )
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, null=True, blank=True,
        related_name="scale_options", verbose_name="pregunta",
    )
    value = models.PositiveSmallIntegerField(
        "valor", null=True, blank=True, help_text="1–4; vacío = N/A."
    )
    label = models.CharField("etiqueta", max_length=40)
    description = models.TextField("descriptor", blank=True)
    order = models.PositiveSmallIntegerField("orden", default=1)

    class Meta:
        verbose_name = "opción de escala"
        verbose_name_plural = "opciones de escala"
        ordering = ["template", "question", "order"]

    def __str__(self):
        return f"{self.value if self.value is not None else 'N/A'} · {self.label}"

    def clean(self):
        if not self.template and not self.question:
            raise ValidationError("La opción debe pertenecer a un cuestionario o a una pregunta.")

    @property
    def is_na(self):
        return self.value is None
