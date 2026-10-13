"""Borra el contenido de prueba de Arena Learn antes de la importación (spec 006, FR-039/040).

    python manage.py reset_learning_data --before 2026-10-13             # solo cuenta
    python manage.py reset_learning_data --before 2026-10-13 --confirm   # borra

Conserva la configuración de Arena Learn; no toca usuarios, áreas, niveles ni otros módulos.
Requisito: respaldo previo (rama de Neon) antes de --confirm.
"""

from datetime import date

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.core.services import learning_import


class Command(BaseCommand):
    help = "Cuenta (y con --confirm borra) los datos de prueba de Arena Learn."

    def add_arguments(self, parser):
        parser.add_argument("--before", required=True, type=date.fromisoformat,
                            help="Fecha de corte (AAAA-MM-DD): se niega si hay datos creados desde ese día.")
        parser.add_argument("--confirm", action="store_true", help="Borra de verdad (sin esto solo cuenta).")

    def handle(self, *args, **opts):
        try:
            counts = learning_import.reset_learning_data(opts["before"], confirm=opts["confirm"])
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages))
        self.stdout.write("BORRADO" if opts["confirm"] else "SIMULACIÓN (no se borró nada)")
        for label, n in counts.items():
            self.stdout.write(f"  {label}: {n}")
