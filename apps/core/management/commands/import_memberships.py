"""Importa membresías (equipo por proyecto) desde la hoja 'Proyectos' del xlsx.

Idempotente por (proyecto, usuario). Empareja Employee → usuario con el índice
de nombres (alias por correo del HC Total). Aplica relleno hacia abajo del
Employee en blanco. Reporta filas sin proyecto o sin usuario.

Uso:
  manage.py import_memberships --dry-run
  manage.py import_memberships
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Project, ProjectMembership
from apps.core.services import imports
from apps.core.text import normalize_name

User = get_user_model()

DEFAULT_XLSX = "Quien evalua a quien Analítica 1er S 2026.xlsx"
HC_SHEET = "HC Total Nov 2024-2026"
MEMB_SHEET = "Proyectos"


def _header_index(row):
    return {str(v).strip().lower(): i for i, v in enumerate(row) if v is not None}


class Command(BaseCommand):
    help = "Importa membresías desde la hoja 'Proyectos' del xlsx de Talento."

    def add_arguments(self, parser):
        parser.add_argument("--path", default=None)
        parser.add_argument("--password", default="Arena2026!")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        import openpyxl

        path = Path(options["path"]) if options["path"] else (
            Path(settings.BASE_DIR) / "docs" / "Modelos" / DEFAULT_XLSX
        )
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"No se encontró {path}"))
            return

        wb = openpyxl.load_workbook(path, data_only=True)
        alias_pairs = self._alias_pairs(wb)
        dry = options["dry_run"]
        password = options["password"]

        rows = list(wb[MEMB_SHEET].iter_rows(values_only=True))
        header = _header_index(rows[0])
        i_emp = header.get("employee")
        i_proj = header.get("project")
        i_start = header.get("min of start")
        i_end = header.get("max of end")

        projects = {normalize_name(p.name): p for p in Project.objects.all()}

        created = skipped = 0
        unmatched = []
        last_emp = None

        with transaction.atomic():
            index = imports.build_user_index(User.objects.all(), alias_pairs)
            for raw in rows[1:]:
                emp = raw[i_emp] if i_emp is not None and i_emp < len(raw) else None
                emp = str(emp).strip() if emp else None
                if emp:
                    last_emp = emp           # relleno hacia abajo
                emp = emp or last_emp

                proj_name = raw[i_proj] if i_proj is not None and i_proj < len(raw) else None
                if not emp or not proj_name:
                    continue

                project = projects.get(normalize_name(str(proj_name)))
                if project is None:
                    unmatched.append(f"Proyecto no encontrado: {proj_name!r}")
                    continue
                user, action = imports.resolve_or_create_user(
                    emp, index, password=password, dry=dry
                )
                if action in ("would_create", "created"):
                    self.stdout.write(f"[{'dry' if dry else 'ok'}] usuario miembro: {emp}")
                if user is None:
                    unmatched.append(f"Usuario no encontrado: {emp!r} ({proj_name})")
                    continue

                start = imports.to_date(raw[i_start]) if i_start is not None else None
                end = imports.to_date(raw[i_end]) if i_end is not None else None

                if dry:
                    self.stdout.write(f"[dry] {user.full_name} ∈ {project.name} ({start}–{end})")
                    continue

                m, is_new = ProjectMembership.objects.get_or_create(
                    project=project, user=user,
                )
                m.start = start
                m.end = end
                m.save()
                created += int(is_new)
                skipped += int(not is_new)

            if dry:
                transaction.set_rollback(True)

        for msg in unmatched:
            self.stdout.write(self.style.WARNING(msg))
        self.stdout.write(self.style.SUCCESS(
            f"Membresías — nuevas: {created} · ya existían: {skipped} · sin resolver: {len(unmatched)}"
        ))

    def _alias_pairs(self, wb):
        if HC_SHEET not in wb.sheetnames:
            return []
        rows = list(wb[HC_SHEET].iter_rows(values_only=True))
        if not rows:
            return []
        header = _header_index(rows[0])
        i_short = header.get("nombre corto")
        i_email = header.get("correo")
        if i_short is None or i_email is None:
            return []
        pairs = []
        for raw in rows[1:]:
            short = raw[i_short] if i_short < len(raw) else None
            email = raw[i_email] if i_email < len(raw) else None
            if short and email:
                pairs.append((str(short).strip(), str(email).strip()))
        return pairs
