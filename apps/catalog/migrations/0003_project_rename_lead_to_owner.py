"""Renombra Project.lead → Project.owner, actualiza related_name, rellena datos faltantes
y hace Project.responsable NOT NULL."""

import unicodedata

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

# Tabla canónica: (prefijo_nombre, owner, responsable)
PROJECT_DATA = [
    ("MSI",                    "José Antonio Pedraza Rangel",      "Mario De Gyves"),
    ("Share Forecast LATAM",   "Oscar Andrés Mancha Mendoza",      "Mario De Gyves"),
    ("Data Ops",               "Kareem Galván Delgadillo",         "Oscar Nafarrate"),
    ("GenAI",                  "Iñaki Fernandez",                   "Héctor Rangel Castro"),
    ("AI Latam Office",        "Lorenzo Llaguno",                   "Héctor Rangel Castro"),
    ("OBPPC",                  "Luis Adrián Lara García",           "Mario De Gyves"),
    ("Weather",                "Eduardo Ayala",                     "Luis Becerril"),
    ("Migración 360",          "Kareem Galvan",                     "Héctor Rangel Castro"),
    ("CCL Engineering",        "Héctor Rangel Castro",              "Marco Aristeo Garcia"),
    ("Hypercare",              "Kareem Galván",                     "Héctor Rangel Castro"),
    ("Business Terms",         "Carlos Alejandro Rodríguez Ochoa", "Oscar Nafarrate"),
    ("Rodin",                  "Emanuel Alvarado",                  "Luis Becerril"),
    ("Urrea",                  "Rodolfo Navarrete",                 "Héctor Rangel Castro"),
    ("Coppel Portal",          "Carolina Palacio",                  "Fernando Díaz"),
    ("NSR PM",                 "Eduardo Ayala",                     "Oscar Nafarrate"),
    ("Prime Partners",         "Marco Aristeo García",              "Héctor Rangel Castro"),
    ("C&CL Report",            "José Antonio Pedraza Rangel",      "Héctor Rangel Castro"),
]


def _norm(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.split())


def fill_project_data(apps, schema_editor):
    Project = apps.get_model("catalog", "Project")
    User = apps.get_model("accounts", "User")

    all_users = list(User.objects.filter(is_active=True))
    norm_index = {_norm(u.full_name): u for u in all_users}

    def find_user(name):
        n = _norm(name)
        if n in norm_index:
            return norm_index[n]
        tokens = set(n.split())
        best, best_score = None, 0
        for u in all_users:
            score = len(tokens & set(_norm(u.full_name).split()))
            if score > best_score:
                best, best_score = u, score
        return best if best_score >= 2 else None

    for prefix, owner_name, resp_name in PROJECT_DATA:
        prefix_n = _norm(prefix)
        project = None
        for p in Project.objects.select_related("owner").all():
            pn = _norm(p.name)
            if pn.startswith(prefix_n) or prefix_n in pn:
                project = p
                break
        if not project:
            continue

        update = []
        owner = find_user(owner_name)
        if owner and project.owner_id != owner.pk:
            project.owner = owner
            update.append("owner")

        resp = find_user(resp_name)
        if resp and project.responsable_id != resp.pk:
            project.responsable = resp
            update.append("responsable")

        if update:
            project.save(update_fields=update)

    # Garantiza que ningún proyecto quede sin responsable (fallback: usar owner)
    for p in Project.objects.filter(responsable__isnull=True).select_related("owner"):
        p.responsable = p.owner
        p.save(update_fields=["responsable"])


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_historicalproject_kickoff_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Renombrar columna lead → owner en ambas tablas
        migrations.RenameField(
            model_name="project",
            old_name="lead",
            new_name="owner",
        ),
        migrations.RenameField(
            model_name="historicalproject",
            old_name="lead",
            new_name="owner",
        ),
        # 2. Actualizar related_name y verbose_name del campo owner
        migrations.AlterField(
            model_name="project",
            name="owner",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="owned_projects",
                to=settings.AUTH_USER_MODEL,
                verbose_name="owner",
            ),
        ),
        migrations.AlterField(
            model_name="historicalproject",
            name="owner",
            field=models.ForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
                verbose_name="owner",
            ),
        ),
        # 3. Rellenar responsables faltantes usando la tabla canónica
        migrations.RunPython(fill_project_data, migrations.RunPython.noop),
        # 4. Hacer responsable obligatorio (NOT NULL)
        migrations.AlterField(
            model_name="project",
            name="responsable",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="responsible_projects",
                to=settings.AUTH_USER_MODEL,
                verbose_name="responsable",
            ),
        ),
    ]
