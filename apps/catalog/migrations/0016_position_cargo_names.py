"""Spec 009: el cargo (posición) va por área y el nivel aparte.

Renombra solo las posiciones que conservan un nombre por defecto (nombre del nivel o la escalera
antigua de Consultoría); respeta lo que Talento ya haya editado. Reversible a nombres de nivel.
"""

from django.db import migrations

CARGOS = {
    "CD": "Científico de Datos", "CONS": "Consultor", "ID": "Ingeniero de Datos",
    "PM": "Project Manager", "UXUI": "Diseñador UX/UI",
}
OLD_CONS = {"Analista", "Consultor", "Consultor Sr", "Gerente"}


def forwards(apps, schema_editor):
    Position = apps.get_model("catalog", "Position")
    for p in Position.objects.select_related("area", "level"):
        cargo = CARGOS.get(p.area.code)
        if not cargo:
            continue
        default_names = {p.level.name} | (OLD_CONS if p.area.code == "CONS" else set())
        if p.name in default_names and p.name != cargo:
            p.name = cargo
            p.save(update_fields=["name"])


def backwards(apps, schema_editor):
    Position = apps.get_model("catalog", "Position")
    for p in Position.objects.select_related("area", "level"):
        if p.name == CARGOS.get(p.area.code):
            p.name = p.level.name
            p.save(update_fields=["name"])


class Migration(migrations.Migration):

    dependencies = [("catalog", "0015_position_pillar_weight")]

    operations = [migrations.RunPython(forwards, backwards)]
