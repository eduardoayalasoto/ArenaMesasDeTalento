"""Importa el catálogo y los planes 2026 de Arena Learn (spec 006, US4).

    python manage.py import_learning_plans --dry-run      # simula y muestra el resumen
    python manage.py import_learning_plans                # aplica
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.core.services import learning_import


class Command(BaseCommand):
    help = "Importa el catálogo y los planes de capacitación desde apps/learning/data/planes_2026.json."

    def add_arguments(self, parser):
        parser.add_argument("--plans", default=str(learning_import.DEFAULT_PLANS_PATH),
                            help="Ruta del JSON de planes (default: apps/learning/data/planes_2026.json).")
        parser.add_argument("--year", type=int, default=None, help="Año del plan (default: el del JSON).")
        parser.add_argument("--dry-run", action="store_true", help="Simula y revierte: no guarda nada.")

    def handle(self, *args, **opts):
        try:
            summary = learning_import.import_plans(opts["plans"], year=opts["year"], dry_run=opts["dry_run"])
        except ValidationError as exc:
            raise CommandError("El archivo no es válido:\n" + "\n".join(exc.messages))
        for line in summary.lines():
            self.stdout.write(line)
