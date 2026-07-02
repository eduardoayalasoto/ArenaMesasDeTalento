"""Modelos de los tres pilares: Ownership, Entrega de Valor, Impacto Arena y la calificación final."""

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from simple_history.models import HistoricalRecords


class OwnershipEvaluation(models.Model):
    """Evaluación de Ownership de un colaborador en un proyecto y periodo (RN-05/06)."""

    class Status(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        ENVIADA = "ENVIADA", "Enviada"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="ownership_evaluations", verbose_name="colaborador",
    )
    project = models.ForeignKey(
        "catalog.Project", on_delete=models.PROTECT,
        related_name="ownership_evaluations", verbose_name="proyecto",
        null=True, blank=True,
    )
    period = models.ForeignKey(
        "catalog.EvaluationPeriod", on_delete=models.PROTECT,
        related_name="ownership_evaluations", verbose_name="periodo",
    )
    template = models.ForeignKey(
        "questionnaires.QuestionnaireTemplate", on_delete=models.PROTECT,
        related_name="ownership_evaluations", verbose_name="cuestionario (versión)",
    )
    status = models.CharField(
        "estado", max_length=10, choices=Status.choices, default=Status.BORRADOR
    )
    strengths = models.TextField("fortalezas", blank=True)
    opportunities = models.TextField("oportunidades", blank=True)
    comments = models.TextField("comentarios", blank=True)
    confirmed_with_leader = models.BooleanField("confirmada con el líder", default=False)
    score = models.DecimalField(
        "calificación", max_digits=3, decimal_places=2, null=True, blank=True
    )
    submitted_at = models.DateTimeField("enviada el", null=True, blank=True)
    created_at = models.DateTimeField("creada el", auto_now_add=True)
    updated_at = models.DateTimeField("actualizada el", auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "evaluación de Ownership"
        verbose_name_plural = "evaluaciones de Ownership"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "project", "period"],
                condition=models.Q(project__isnull=False),
                name="unique_ownership_eval",
            ),
            models.UniqueConstraint(
                fields=["user", "period"],
                condition=models.Q(project__isnull=True),
                name="unique_lead_ownership_eval",
            ),
        ]

    def __str__(self):
        return f"Ownership de {self.user} en {self.project} ({self.period})"

    @property
    def is_submitted(self):
        return self.status == self.Status.ENVIADA

    def primary_evaluator(self):
        rec = self.evaluators.filter(is_primary=True).select_related("user").first()
        return rec.user if rec else None


class OwnershipEvaluator(models.Model):
    """Evaluador asignado a una evaluación de Ownership (primario o secundario)."""

    evaluation = models.ForeignKey(
        OwnershipEvaluation, on_delete=models.CASCADE,
        related_name="evaluators", verbose_name="evaluación",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="ownership_evaluator_records", verbose_name="evaluador",
    )
    is_primary = models.BooleanField("es primario", default=False)
    added_at = models.DateTimeField("agregado el", auto_now_add=True)

    class Meta:
        verbose_name = "evaluador de Ownership"
        verbose_name_plural = "evaluadores de Ownership"
        constraints = [
            models.UniqueConstraint(fields=["evaluation", "user"], name="unique_ownership_evaluator"),
        ]

    def __str__(self):
        role = "Primario" if self.is_primary else "Secundario"
        return f"{self.user} ({role}) — {self.evaluation}"


class OwnershipAnswer(models.Model):
    """Respuesta a una pregunta de escala. value None + is_na=True representa N/A (RN-03)."""

    evaluation = models.ForeignKey(
        OwnershipEvaluation, on_delete=models.CASCADE,
        related_name="answers", verbose_name="evaluación",
    )
    question = models.ForeignKey(
        "questionnaires.Question", on_delete=models.PROTECT,
        related_name="ownership_answers", verbose_name="pregunta",
    )
    value = models.PositiveSmallIntegerField("valor", null=True, blank=True)
    is_na = models.BooleanField("no aplica", default=False)

    class Meta:
        verbose_name = "respuesta de Ownership"
        verbose_name_plural = "respuestas de Ownership"
        constraints = [
            models.UniqueConstraint(
                fields=["evaluation", "question"], name="unique_answer_per_question"
            )
        ]

    def __str__(self):
        return f"{self.question} = {'N/A' if self.is_na else self.value}"


class ValueDeliveryEvaluation(models.Model):
    """Entrega de Valor de un proyecto en un periodo (RN-07/08). Una por proyecto-periodo."""

    class Status(models.TextChoices):
        BORRADOR = "BORRADOR", "Borrador"
        EN_VALIDACION = "EN_VALIDACION", "En validación"
        VALIDADA = "VALIDADA", "Validada"

    project = models.ForeignKey(
        "catalog.Project", on_delete=models.PROTECT,
        related_name="value_deliveries", verbose_name="proyecto",
    )
    period = models.ForeignKey(
        "catalog.EvaluationPeriod", on_delete=models.PROTECT,
        related_name="value_deliveries", verbose_name="periodo",
    )
    evaluator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="vd_evaluations", verbose_name="líder evaluador",
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="vd_validations", verbose_name="validado por",
    )
    status = models.CharField(
        "estado", max_length=14, choices=Status.choices, default=Status.BORRADOR
    )
    client_satisfaction = models.PositiveSmallIntegerField("satisfacción del cliente", null=True, blank=True)
    deliverables = models.PositiveSmallIntegerField("entregables", null=True, blank=True)
    time_finite = models.PositiveSmallIntegerField("tiempo (finito)", null=True, blank=True)
    time_indefinite = models.PositiveSmallIntegerField("tiempo (indefinido)", null=True, blank=True)
    rejection_comment = models.TextField("comentario de rechazo", blank=True)
    comments = models.TextField(
        "comentarios",
        blank=True,
        help_text="Notas de contexto sobre la Entrega de Valor. Las captura el responsable "
        "y puede complementarlas el Validador; se muestran también en la Mesa de Talento.",
    )
    score = models.DecimalField("calificación", max_digits=3, decimal_places=2, null=True, blank=True)
    validated_at = models.DateTimeField("validada el", null=True, blank=True)
    created_at = models.DateTimeField("creada el", auto_now_add=True)
    updated_at = models.DateTimeField("actualizada el", auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "evaluación de Entrega de Valor"
        verbose_name_plural = "evaluaciones de Entrega de Valor"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["project", "period"], name="unique_vd_eval")
        ]

    def __str__(self):
        return f"Entrega de Valor de {self.project} ({self.period})"

    def clean(self):
        # Exactamente uno de los criterios de tiempo aplica, según el tipo de proyecto (RN-08).
        if self.project_id and self.project.is_finite and self.time_indefinite is not None:
            raise ValidationError("Un proyecto finito no debe capturar el criterio de tiempo indefinido.")
        if self.project_id and not self.project.is_finite and self.time_finite is not None:
            raise ValidationError("Un proyecto indefinido no debe capturar el criterio de tiempo finito.")


class ArenaImpactScore(models.Model):
    """Impacto Arena capturado por Talento (RN-11). Uno por colaborador-periodo."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="arena_impacts", verbose_name="colaborador",
    )
    period = models.ForeignKey(
        "catalog.EvaluationPeriod", on_delete=models.PROTECT,
        related_name="arena_impacts", verbose_name="periodo",
    )
    score = models.DecimalField("calificación", max_digits=3, decimal_places=2, null=True, blank=True)
    notes = models.TextField("notas", blank=True)
    captured_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="captured_impacts", verbose_name="capturado por",
    )
    updated_at = models.DateTimeField("actualizado el", auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "Impacto Arena"
        verbose_name_plural = "Impactos Arena"
        constraints = [
            models.UniqueConstraint(fields=["user", "period"], name="unique_arena_impact")
        ]

    def __str__(self):
        return f"Impacto Arena de {self.user} ({self.period})"


class FinalScore(models.Model):
    """Calificación final materializada por colaborador-periodo (RN-12/19/20)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="final_scores", verbose_name="colaborador",
    )
    period = models.ForeignKey(
        "catalog.EvaluationPeriod", on_delete=models.PROTECT,
        related_name="final_scores", verbose_name="periodo",
    )
    ownership_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    value_delivery_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    arena_impact_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    final_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    band = models.CharField("banda", max_length=20, blank=True)
    is_complete = models.BooleanField("completa", default=False)
    updated_at = models.DateTimeField("actualizada el", auto_now=True)

    class Meta:
        verbose_name = "calificación final"
        verbose_name_plural = "calificaciones finales"
        constraints = [
            models.UniqueConstraint(fields=["user", "period"], name="unique_final_score")
        ]

    def __str__(self):
        return f"Final de {self.user} ({self.period}): {self.final_score}"


class TalentSessionNote(models.Model):
    """Nota de Mesa de Talento por colaborador-periodo (fortalezas, oportunidades, escenarios)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="talent_notes", verbose_name="colaborador",
    )
    period = models.ForeignKey(
        "catalog.EvaluationPeriod", on_delete=models.PROTECT,
        related_name="talent_notes", verbose_name="periodo",
    )
    fortalezas = models.TextField("fortalezas Mesa de Talento", blank=True)
    oportunidades = models.TextField("oportunidades Mesa de Talento", blank=True)
    scenario_actual = models.ManyToManyField(
        "catalog.ScenarioOption", related_name="notes_actual",
        blank=True, verbose_name="escenario actual",
    )
    scenario_s1 = models.ManyToManyField(
        "catalog.ScenarioOption", related_name="notes_s1",
        blank=True, verbose_name="escenario S+1",
    )
    scenario_s2 = models.ManyToManyField(
        "catalog.ScenarioOption", related_name="notes_s2",
        blank=True, verbose_name="escenario S+2",
    )
    # Sesión de retroalimentación: la captura quien esté asignado como responsable
    # (primario o secundario) en `responsables`; se vuelve visible al colaborador
    # en cuanto tiene contenido (ver `has_feedback_session` abajo).
    objetivo_desarrollo_1 = models.TextField("objetivo de desarrollo 1", blank=True)
    objetivo_desarrollo_2 = models.TextField("objetivo de desarrollo 2", blank=True)
    objetivo_desarrollo_3 = models.TextField("objetivo de desarrollo 3", blank=True)
    expectativas_profesionales = models.TextField("expectativas profesionales", blank=True)
    expectativas_personales = models.TextField("expectativas personales", blank=True)
    comentarios_adicionales = models.TextField("comentarios adicionales de retroalimentación", blank=True)
    feedback_agreed = models.BooleanField("acordado con el colaborador", default=False)
    feedback_agreed_at = models.DateTimeField("acordado el", null=True, blank=True)
    feedback_agreed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name="feedback_sessions_agreed", verbose_name="acordado por",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        null=True, blank=True, related_name="created_talent_notes", verbose_name="creado por",
    )
    updated_at = models.DateTimeField("actualizado el", auto_now=True)
    created_at = models.DateTimeField("creado el", auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name = "nota de Mesa de Talento"
        verbose_name_plural = "notas de Mesa de Talento"
        constraints = [
            models.UniqueConstraint(fields=["user", "period"], name="unique_talent_note")
        ]

    def __str__(self):
        return f"Nota Mesa de Talento · {self.user} ({self.period})"

    @property
    def has_feedback_session(self) -> bool:
        """True si la sesión de retroalimentación tiene algún contenido capturado."""
        return any(
            getattr(self, field).strip()
            for field in (
                "objetivo_desarrollo_1", "objetivo_desarrollo_2", "objetivo_desarrollo_3",
                "expectativas_profesionales", "expectativas_personales", "comentarios_adicionales",
            )
        )


class FeedbackResponsible(models.Model):
    """Responsable de retroalimentación ligado a una nota de Mesa de Talento."""

    note = models.ForeignKey(
        TalentSessionNote, on_delete=models.CASCADE,
        related_name="responsables", verbose_name="nota",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="feedback_responsable_records", verbose_name="responsable",
    )
    is_primary = models.BooleanField("es principal", default=False)

    class Meta:
        verbose_name = "responsable de retroalimentación"
        verbose_name_plural = "responsables de retroalimentación"
        constraints = [
            models.UniqueConstraint(fields=["note", "user"], name="unique_feedback_responsible")
        ]

    def __str__(self):
        return f"{'Principal' if self.is_primary else 'Secundario'}: {self.user} — {self.note}"
