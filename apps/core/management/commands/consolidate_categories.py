"""Deja como categorías de pregunta solo las familias de la matriz de competencias + «General».

Uso:
    python manage.py consolidate_categories "C:/ruta/Matriz.xlsx"           # simulación (no guarda)
    python manage.py consolidate_categories "C:/ruta/Matriz.xlsx" --apply   # reclasifica y borra las sobrantes
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.services import competency_matrix


class Command(BaseCommand):
    help = "Reclasifica las preguntas por la «Familia» de la matriz y borra las categorías sobrantes. Simula salvo --apply."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Ruta del archivo .xlsx de la matriz.")
        parser.add_argument("--apply", action="store_true", help="Guarda los cambios (por defecto solo simula).")

    def handle(self, *args, path, apply=False, **opts):
        self.stdout.write(("APLICANDO" if apply else "SIMULACIÓN (no se guarda nada)") + f" · {path}")
        try:
            rows = competency_matrix.read_matrix(path)
            with transaction.atomic():
                summary = competency_matrix.consolidate_categories(rows)
                for origin, targets in summary["moved"].items():
                    detail = " · ".join(f"{name}: {n}" for name, n in targets.items()) or "sin preguntas"
                    self.stdout.write(f"- {origin} → {detail}")
                self.stdout.write(f"Categorías eliminadas: {', '.join(summary['deleted']) or 'ninguna'}")
                if not apply:
                    transaction.set_rollback(True)
        except (ValidationError, FileNotFoundError) as exc:
            raise CommandError(" ".join(getattr(exc, "messages", [str(exc)]))) from exc
        self.stdout.write("Listo." if apply else "Simulación terminada: ejecuta con --apply para guardar.")
