"""Orquesta todo el seed (idempotente). Ejecuta cada paso en orden seguro."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ejecuta seed_superuser + seed_catalogs + seed_users (+ seed_questionnaires si existe)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--demo",
            action="store_true",
            help="Incluye datos de demostración (solo desarrollo).",
        )

    def handle(self, *args, **options):
        steps = ["seed_superuser", "seed_catalogs", "seed_users", "seed_questionnaires"]
        if options["demo"]:
            steps.append("seed_demo")

        for step in steps:
            self.stdout.write(self.style.MIGRATE_HEADING(f"\n>> {step}"))
            try:
                call_command(step)
            except Exception as exc:  # noqa: BLE001
                # Pasos aún no implementados (fases posteriores) no detienen el seed.
                self.stderr.write(self.style.WARNING(f"  - {step} omitido: {exc}"))

        self.stdout.write(self.style.SUCCESS("\n[OK] Seed completo."))
