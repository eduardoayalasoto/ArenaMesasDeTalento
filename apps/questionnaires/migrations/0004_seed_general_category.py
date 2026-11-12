"""Spec 008: categorías sembradas y «General» al 100% en todos los cuestionarios de Ownership.

Aditiva y reversible. No toca Entrega de Valor ni respuestas. Con una sola categoría «General» y
preguntas en partes iguales (peso nulo) el cálculo es idéntico al promedio simple anterior.
"""

from decimal import Decimal

from django.db import migrations

CATEGORIES = [
    ("general", "General", 0),
    ("delivery_cliente", "Delivery al cliente", 1),
    ("desarrollo_producto", "Desarrollo de producto", 2),
    ("herramientas_gestion", "Herramientas de gestión", 3),
    ("actitud_persona", "Actitud y persona", 4),
]


def seed(apps, schema_editor):
    Category = apps.get_model("questionnaires", "Category")
    Template = apps.get_model("questionnaires", "QuestionnaireTemplate")
    TemplateCategory = apps.get_model("questionnaires", "TemplateCategory")
    Question = apps.get_model("questionnaires", "Question")

    for code, name, order in CATEGORIES:
        Category.objects.get_or_create(code=code, defaults={"name": name, "order": order})
    general = Category.objects.get(code="general")

    for template in Template.objects.filter(kind="OWNERSHIP"):
        TemplateCategory.objects.get_or_create(
            template=template, category=general, defaults={"weight_pct": Decimal("100.0")}
        )
        Question.objects.filter(
            section__template=template, qtype="SCALE", category__isnull=True
        ).update(category=general)


def unseed(apps, schema_editor):
    Category = apps.get_model("questionnaires", "Category")
    TemplateCategory = apps.get_model("questionnaires", "TemplateCategory")
    Question = apps.get_model("questionnaires", "Question")

    Question.objects.update(category=None, weight_pct=None)
    TemplateCategory.objects.all().delete()
    Category.objects.filter(code__in=[c[0] for c in CATEGORIES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("questionnaires", "0003_category_templatecategory_question_fields"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
