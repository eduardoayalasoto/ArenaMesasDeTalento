"""Importa los colaboradores desde fixtures/users.yaml (Anexo C). Área/nivel quedan null. Idempotente."""

from pathlib import Path

import yaml
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.core.text import titlecase_name

User = get_user_model()


class Command(BaseCommand):
    help = "Crea los colaboradores del fixture users.yaml (sin contraseña usable hasta el reset)."

    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR) / "fixtures" / "users.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        rows = data.get("users", [])

        created = 0
        for row in rows:
            email = row["email"].strip().lower()
            full_name = titlecase_name(row["name"])
            user, was_created = User.objects.get_or_create(
                email=email,
                defaults={"full_name": full_name, "role": User.Role.COLABORADOR},
            )
            if was_created:
                # Sin contraseña usable: el colaborador la establece por correo.
                user.set_unusable_password()
                user.save(update_fields=["password"])
                created += 1
            elif user.full_name != full_name:
                user.full_name = full_name
                user.save(update_fields=["full_name"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Colaboradores: {User.objects.count()} en total ({created} nuevos)."
            )
        )
