"""Perfiles semilla "deber ser" y asignación inicial por rol/nivel (spec 005, FR-011, research R8).

Idempotente: no pisa perfiles ni concesiones ya existentes, ni el perfil de quien ya tiene uno.
"""

from django.db import migrations


def seed(apps, schema_editor):
    from apps.access.seed import PROFILE_ORDER, PROFILES, SEED_MATRIX, SUPERUSER

    Profile = apps.get_model("access", "Profile")
    ProfileGrant = apps.get_model("access", "ProfileGrant")
    User = apps.get_model("accounts", "User")

    by_slug = {}
    for slug, name, desc in PROFILES:
        by_slug[slug], _ = Profile.objects.get_or_create(slug=slug, defaults={"name": name, "description": desc})
    sslug, sname, sdesc = SUPERUSER
    Profile.objects.get_or_create(slug=sslug, defaults={"name": sname, "description": sdesc, "is_system": True})

    for key, values in SEED_MATRIX.items():
        for idx, slug in enumerate(PROFILE_ORDER):
            ProfileGrant.objects.get_or_create(
                profile=by_slug[slug], permission_key=key, defaults={"scope": int(values[idx])},
            )

    for u in User.objects.filter(profile__isnull=True, is_superuser=False).select_related("level"):
        if u.role == "TALENTO":
            slug = "talento"
        elif u.role == "DIRECTOR":
            slug = "director"
        elif u.level_id and u.level.code == "LEAD":
            slug = "lead"
        else:
            slug = "colaborador"
        u.profile = by_slug[slug]
        u.save(update_fields=["profile"])


class Migration(migrations.Migration):
    dependencies = [
        ("access", "0001_initial"),
        ("accounts", "0009_user_profile"),
        ("catalog", "0010_area_director"),
    ]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
