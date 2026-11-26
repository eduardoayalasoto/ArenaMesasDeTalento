"""Catálogo administrable de cuestionarios: los cuestionarios son datos, no código."""

from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords


class QuestionnaireTemplate(models.Model):
    """Versión congelable de un cuestionario (RN: versionado). 16 Ownership + 1 Entrega de Valor."""

    class Kind(models.TextChoices):
        OWNERSHIP = "OWNERSHIP", "Ownership"
        VALUE_DELIVERY = "VALUE_DELIVERY", "Entrega de Valor"
        THREE_SIXTY = "THREE_SIXTY", "360 al owner"

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
            # Posiciones sin nivel: NULL no entra en las restricciones anteriores.
            models.UniqueConstraint(
                fields=["kind", "area"],
                condition=models.Q(status="PUBLICADO", level__isnull=True, area__isnull=False),
                name="unique_published_template_nolevel",
            ),
            models.UniqueConstraint(
                fields=["kind", "area", "version"],
                condition=models.Q(level__isnull=True, area__isnull=False),
                name="unique_template_version_nolevel",
            ),
        ]

    def __str__(self):
        if self.kind == self.Kind.VALUE_DELIVERY:
            return f"Entrega de Valor v{self.version}"
        if self.kind == self.Kind.THREE_SIXTY:
            return f"360 al owner v{self.version}"
        level = f"/{self.level.code}" if self.level_id else ""
        return f"Ownership {self.area.code}{level} v{self.version}"

    @property
    def is_published(self):
        return self.status == self.Status.PUBLICADO

    @property
    def question_count(self):
        return Question.objects.filter(section__template=self).count()


class Category(models.Model):
    """Categoría de pregunta (spec 008): catálogo común a todas las áreas.

    La ponderación de cada categoría dentro de un cuestionario vive en `TemplateCategory`.
    «General» es la categoría de arranque de los cuestionarios existentes.
    """

    GENERAL_CODE = "general"

    code = models.SlugField("clave", max_length=40, unique=True)
    name = models.CharField("nombre", max_length=80)
    order = models.PositiveSmallIntegerField("orden", default=1)
    is_active = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class TemplateCategory(models.Model):
    """Ponderación (en %, un decimal) de una categoría dentro de un cuestionario. Σ = 100.0."""

    template = models.ForeignKey(
        QuestionnaireTemplate, on_delete=models.CASCADE,
        related_name="template_categories", verbose_name="cuestionario",
    )
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT,
        related_name="template_links", verbose_name="categoría",
    )
    weight_pct = models.DecimalField("ponderación (%)", max_digits=4, decimal_places=1, default=0)

    class Meta:
        verbose_name = "categoría del cuestionario"
        verbose_name_plural = "categorías del cuestionario"
        ordering = ["template", "category__order"]
        constraints = [
            models.UniqueConstraint(
                fields=["template", "category"], name="unique_template_category"
            ),
        ]

    def __str__(self):
        return f"{self.template} · {self.category} {self.weight_pct}%"


class Section(models.Model):
    """Sección temática del cuestionario."""

    template = models.ForeignKey(
        QuestionnaireTemplate, on_delete=models.CASCADE,
        related_name="sections", verbose_name="cuestionario",
    )
    title = models.CharField("título", max_length=160)
    order = models.PositiveSmallIntegerField("orden", default=1)
    # Solo cuestionarios 360: la sección es la dimensión y esta es su ponderación (Σ = 100.0; 0 = se califica, no pesa).
    weight_pct = models.DecimalField("ponderación de la dimensión (%)", max_digits=4, decimal_places=1, null=True, blank=True)

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
    # Sin uso desde la spec 008 (la ponderación real es `weight_pct`); se retirará en un spec posterior.
    weight = models.DecimalField("ponderación", max_digits=4, decimal_places=2, default=1)
    category = models.ForeignKey(
        "Category", on_delete=models.PROTECT, null=True, blank=True,
        related_name="questions", verbose_name="categoría",
    )
    weight_pct = models.DecimalField(
        "ponderación en su categoría (%)", max_digits=4, decimal_places=1, null=True, blank=True,
        help_text="Vacío = partes iguales; 0 = se califica pero no pondera.",
    )

    class Mastery(models.IntegerChoices):
        EXPUESTO = 1, "N1 · Expuesto"
        CONTRIBUYE = 2, "N2 · Contribuye"
        AUTONOMO = 3, "N3 · Autónomo"
        REFERENTE = 4, "N4 · Referente"

    # Competencia = título; el bloque del catálogo aporta los skills que la componen.
    block = models.ForeignKey(
        "CompetencyBlock", on_delete=models.PROTECT, null=True, blank=True,
        related_name="questions", verbose_name="bloque del catálogo",
    )
    target_level = models.PositiveSmallIntegerField(
        "nivel de dominio objetivo", choices=Mastery.choices, null=True, blank=True,
        help_text="Con él se calcula la ponderación automática: a mayor nivel, mayor ponderación.",
    )
    is_weighted = models.BooleanField(
        "pondera", default=True,
        help_text="Desmárcala si la pregunta se califica pero no mueve la calificación (ponderación 0).",
    )
    allow_na = models.BooleanField("permite N/A", default=True)
    is_required = models.BooleanField("obligatoria", default=True)
    # Campos del checklist de actividades (spec 007); opcionales, se muestran en "Ver criterio".
    acceptance_criteria = models.TextField("criterio de aceptación", blank=True)
    deliverable = models.TextField("entregable", blank=True)
    deliverable_format = models.TextField("formato", blank=True)
    frequency = models.TextField("frecuencia", blank=True)
    level_expectation = models.TextField("expectativa por nivel", blank=True)
    guidance = models.TextField("comentarios y guía", blank=True)

    CHECKLIST_FIELDS = (
        "acceptance_criteria", "deliverable", "deliverable_format",
        "frequency", "level_expectation", "guidance",
    )

    class Meta:
        verbose_name = "pregunta"
        verbose_name_plural = "preguntas"
        ordering = ["section", "order"]

    def __str__(self):
        return self.title

    @property
    def skills(self):
        """Skills que componen la competencia: los del bloque del catálogo."""
        return [s.name for s in self.block.skills.all()] if self.block_id else []

    @property
    def checklist_details(self):
        """[(etiqueta, texto)] de los campos del checklist con contenido, en orden de despliegue."""
        return [
            (self._meta.get_field(name).verbose_name.capitalize(), getattr(self, name))
            for name in self.CHECKLIST_FIELDS
            if getattr(self, name)
        ]

    @property
    def has_checklist_details(self):
        return any(getattr(self, name) for name in self.CHECKLIST_FIELDS)


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


class CompetencyBlock(models.Model):
    """Bloque del catálogo de competencias (p. ej. «Disciplina de WoW y gestión»): agrupa sus skills."""

    code = models.SlugField("clave", max_length=60, unique=True)
    name = models.CharField("nombre", max_length=120)
    order = models.PositiveSmallIntegerField("orden", default=1)
    is_active = models.BooleanField("activo", default=True)

    class Meta:
        verbose_name = "bloque del catálogo"
        verbose_name_plural = "bloques del catálogo"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class BlockSkill(models.Model):
    """Skill que compone un bloque del catálogo."""

    block = models.ForeignKey(CompetencyBlock, on_delete=models.CASCADE, related_name="skills", verbose_name="bloque")
    name = models.CharField("skill", max_length=160)
    order = models.PositiveSmallIntegerField("orden", default=1)

    class Meta:
        verbose_name = "skill"
        verbose_name_plural = "skills"
        ordering = ["block", "order"]
        constraints = [models.UniqueConstraint(fields=["block", "name"], name="unique_block_skill")]

    def __str__(self):
        return self.name
