"""360 al owner (spec 010): concesión de las claves nuevas. Solo agrega las que faltan."""

from django.db import migrations

NEW_KEYS = ("three_sixty.respond", "three_sixty.results.own", "three_sixty.results.view")


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
    dependencies = [("access", "0005_departments_levels_grants")]

    operations = [migrations.RunPython(add_grants, remove_grants)]
