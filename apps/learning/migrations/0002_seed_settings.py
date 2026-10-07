"""Siembra la configuración de Arena Learn con las instrucciones fiscales del proceso actual."""

from django.db import migrations


def seed(apps, schema_editor):
    from apps.learning.models import DEFAULT_FISCAL_INSTRUCTIONS

    LearningSettings = apps.get_model("learning", "LearningSettings")
    LearningSettings.objects.get_or_create(pk=1, defaults={"fiscal_instructions": DEFAULT_FISCAL_INSTRUCTIONS})


class Migration(migrations.Migration):
    dependencies = [("learning", "0001_initial")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
