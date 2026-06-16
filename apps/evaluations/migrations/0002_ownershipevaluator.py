"""Reemplaza el campo validator de OwnershipEvaluation por el modelo OwnershipEvaluator."""

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_validator_to_evaluator(apps, schema_editor):
    OwnershipEvaluation = apps.get_model("evaluations", "OwnershipEvaluation")
    OwnershipEvaluator = apps.get_model("evaluations", "OwnershipEvaluator")
    for ev in OwnershipEvaluation.objects.exclude(validator=None).select_related("validator"):
        OwnershipEvaluator.objects.get_or_create(
            evaluation=ev,
            user=ev.validator,
            defaults={"is_primary": True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("evaluations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Crear tabla OwnershipEvaluator
        migrations.CreateModel(
            name="OwnershipEvaluator",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_primary", models.BooleanField(default=False, verbose_name="es primario")),
                ("added_at", models.DateTimeField(auto_now_add=True, verbose_name="agregado el")),
                (
                    "evaluation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="evaluators",
                        to="evaluations.ownershipevaluation",
                        verbose_name="evaluación",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="ownership_evaluator_records",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="evaluador",
                    ),
                ),
            ],
            options={
                "verbose_name": "evaluador de Ownership",
                "verbose_name_plural": "evaluadores de Ownership",
            },
        ),
        migrations.AddConstraint(
            model_name="ownershipevaluator",
            constraint=models.UniqueConstraint(
                fields=["evaluation", "user"], name="unique_ownership_evaluator"
            ),
        ),
        # 2. Migrar datos: validator → OwnershipEvaluator(is_primary=True)
        migrations.RunPython(migrate_validator_to_evaluator, migrations.RunPython.noop),
        # 3. Eliminar campo validator de la tabla principal y la histórica
        migrations.RemoveField(model_name="ownershipevaluation", name="validator"),
        migrations.RemoveField(model_name="historicalownershipevaluation", name="validator"),
    ]
