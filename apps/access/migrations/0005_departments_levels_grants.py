"""Áreas y Niveles: concesión de las claves nuevas (solo Talento).

Solo agrega las que faltan: no pisa lo que Talento ya haya editado en la matriz.
"""

from django.db import migrations

NEW_KEYS = ("departments.manage", "levels.manage")


def add_grants(apps, schema_editor):
    from apps.access.seed import PROFILE_ORDER, SEED_MATRIX

    Profile = apps.get_model("access", "Profile")
    ProfileGrant = apps.get_model("access", "ProfileGrant")
    profiles = {p.slug: p for p in Profile.objects.filter(slug__in=PROFILE_ORDER)}
    for key in NEW_KEYS:
        for idx, slug in enumerate(PROFILE_ORDER):
            if slug in profiles:
                ProfileGrant.objects.get_or_create(
                    profile=profiles[slug], permission_key=key,
                    defaults={"scope": int(SEED_MATRIX[key][idx])},
                )


def remove_grants(apps, schema_editor):
    apps.get_model("access", "ProfileGrant").objects.filter(permission_key__in=NEW_KEYS).delete()


class Migration(migrations.Migration):
    dependencies = [("access", "0004_catalog_positions_categories_grants")]

    operations = [migrations.RunPython(add_grants, remove_grants)]
