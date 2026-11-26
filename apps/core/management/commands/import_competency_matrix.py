"""Carga la Matriz de competencias y pesos por puesto (Excel) como cuestionarios de Ownership.

Uso:
    python manage.py import_competency_matrix "C:/ruta/Matriz.xlsx"           # simulación (no guarda)
    python manage.py import_competency_matrix "C:/ruta/Matriz.xlsx" --apply   # crea y publica las versiones nuevas
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.services import competency_matrix


class Command(BaseCommand):
    help = "Carga la matriz de competencias como cuestionarios de Ownership. Simula salvo --apply."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Ruta del archivo .xlsx de la matriz.")
        parser.add_argument("--apply", action="store_true", help="Guarda los cambios (por defecto solo simula).")
        parser.add_argument("--360", dest="three_sixty", action="store_true",
                            help="Carga la hoja «03 · 360 al Gerente» como cuestionario 360 al owner (en lugar de Ownership).")

    def handle(self, *args, path, apply=False, three_sixty=False, **opts):
        self.stdout.write(("APLICANDO" if apply else "SIMULACIÓN (no se guarda nada)") + f" · {path}")
        if three_sixty:
            return self._handle_360(path, apply)
        try:
            rows = competency_matrix.read_matrix(path)
            self.stdout.write(f"Filas leídas: {len(rows)}")
            with transaction.atomic():
                report = competency_matrix.load(rows)
                for item in report:
                    cats = " · ".join(f"{name} {pct}%" for name, pct in item["categories"].items())
                    t = item["template"]
                    self.stdout.write(
                        f"- {item['puesto']}: v{t.version} · {item['questions']} competencias · {cats} "
                        f"· desviación máx. vs Excel {item['max_deviation']} pp")
                if not apply:
                    transaction.set_rollback(True)
        except (ValidationError, FileNotFoundError) as exc:
            raise CommandError(" ".join(getattr(exc, "messages", [str(exc)]))) from exc
        self.stdout.write("Listo." if apply else "Simulación terminada: ejecuta con --apply para guardar.")

    def _handle_360(self, path, apply):
        try:
            data = competency_matrix.read_360(path)
            self.stdout.write(f"Escala: {data['scale']} · preguntas leídas: {len(data['rows'])}")
            with transaction.atomic():
                report = competency_matrix.load_360(data)
                t = report["template"]
                self.stdout.write(f"- 360 al owner v{t.version}: {report['dimensions']} dimensiones · {report['questions']} preguntas")
                for name, weight in report["weights"].items():
                    self.stdout.write(f"    {name}: {weight}%")
                if not apply:
                    transaction.set_rollback(True)
        except (ValidationError, FileNotFoundError) as exc:
            raise CommandError(" ".join(getattr(exc, "messages", [str(exc)]))) from exc
        self.stdout.write("Listo." if apply else "Simulación terminada: ejecuta con --apply para guardar.")
