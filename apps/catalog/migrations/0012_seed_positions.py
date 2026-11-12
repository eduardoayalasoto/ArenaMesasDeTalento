"""Spec 008: siembra de Puestos (área × nivel → nombre visible). Aditiva y reversible.

Analítica conserva el nombre actual del nivel; Consultoría (CONS) usa su escalera propia.
"""

from django.db import migrations

CONS_NAMES = {"JR": "Analista", "MID": "Consultor", "SNR": "Consultor Sr", "LEAD": "Gerente"}


def seed(apps, schema_editor):
    Area = apps.get_model("catalog", "Area")
    Level = apps.get_model("catalog", "SeniorityLevel")
    Position = apps.get_model("catalog", "Position")
    levels = list(Level.objects.all())
    for area in Area.objects.all():
        for level in levels:
            name = CONS_NAMES.get(level.code, level.name) if area.code == "CONS" else level.name
            Position.objects.get_or_create(area=area, level=level, defaults={"name": name})


def unseed(apps, schema_editor):
    apps.get_model("catalog", "Position").objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0011_position"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
