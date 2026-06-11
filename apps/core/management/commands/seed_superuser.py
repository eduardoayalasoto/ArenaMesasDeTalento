"""Crea el superusuario desde variables de entorno (SEED_SU_*). Idempotente."""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Crea o actualiza el superusuario inicial desde SEED_SU_EMAIL/SEED_SU_PASSWORD/SEED_SU_NAME."

    def handle(self, *args, **options):
        email = os.environ.get("SEED_SU_EMAIL")
        password = os.environ.get("SEED_SU_PASSWORD")
        name = os.environ.get("SEED_SU_NAME", "Administrador Arena")

        if not email or not password:
            self.stderr.write(
                self.style.WARNING(
                    "Faltan SEED_SU_EMAIL y/o SEED_SU_PASSWORD; se omite el superusuario."
                )
            )
            return

        user, created = User.objects.get_or_create(
            email=email.lower(),
            defaults={
                "full_name": name,
                "role": User.Role.TALENTO,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Superusuario creado: {email}"))
        else:
            self.stdout.write(f"Superusuario ya existía: {email} (sin cambios de contraseña)")
