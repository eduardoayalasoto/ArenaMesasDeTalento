"""Carga una versión nueva de los cuestionarios de Ownership desde fixtures YAML (spec 007).

Ej.: python manage.py import_questionnaire_version --dir fixtures/questionnaires/2027 --target-version 2 --publish
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.services import questionnaire_import


class _DryRun(Exception):
    pass


class Command(BaseCommand):
    help = "Carga (y opcionalmente publica) una versión de los cuestionarios de Ownership desde YAML."

    def add_arguments(self, parser):
        parser.add_argument("--dir", required=True, help="Carpeta con <AREA>.yaml.")
        parser.add_argument("--target-version", type=int, required=True, help="Versión destino (≥ 2).")
        parser.add_argument("--publish", action="store_true", help="Publica cada versión cargada.")
        parser.add_argument("--dry-run", action="store_true", help="Revierte todo al final; solo reporta.")

    def handle(self, *args, **opts):
        if opts["target_version"] < 2:
            raise CommandError("La versión destino debe ser 2 o mayor (la v1 la siembra seed_questionnaires).")
        directory = Path(opts["dir"])
        if not directory.is_absolute():
            directory = Path(settings.BASE_DIR) / directory
        entries = questionnaire_import.load_dir(directory)
        if not entries:
            raise CommandError(f"No encontré cuestionarios en {directory}.")

        try:
            with transaction.atomic():
                for area, level, questions in entries:
                    result = questionnaire_import.import_version(
                        area, level, questions, opts["target_version"], publish=opts["publish"]
                    )
                    self.stdout.write(f"  {result}")
                if opts["dry_run"]:
                    raise _DryRun
        except questionnaire_import.ImportRejected as exc:
            raise CommandError(str(exc)) from exc
        except _DryRun:
            self.stdout.write(self.style.WARNING(f"Simulación: {len(entries)} cuestionarios, nada se guardó."))
            return
        self.stdout.write(self.style.SUCCESS(f"Listo: {len(entries)} cuestionarios v{opts['target_version']}."))
