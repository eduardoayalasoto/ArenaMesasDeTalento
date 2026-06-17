"""Crea/actualiza colaboradores desde docs/Modelos/usuarios.csv.

Deduce área y nivel del puesto, asigna contraseña por defecto y desactiva el
cambio forzado de contraseña. Idempotente. No toca superusuarios.

Uso (contra la BD configurada en DATABASE_URL):
  manage.py import_csv_users
  manage.py import_csv_users --password "Arena2026!" --dry-run
"""

import csv
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.catalog.models import Area, SeniorityLevel
from apps.core.text import titlecase_name

User = get_user_model()

DEFAULT_PASSWORD = "Arena2026!"


def parse_position(area_dept: str, puesto: str):
    """Devuelve (area_code|None, level_code|None, role). UX/UI sin nivel → MID."""
    p = puesto.strip().lower()
    dept = (area_dept or "").strip().lower()

    # Director de Analítica → DIRECTOR (sin área/nivel)
    if "director" in p and "anal" in p:
        return None, None, User.Role.DIRECTOR

    # Departamento de Tecnología → sin área/nivel del modelo de Analítica
    if dept.startswith("tecnolog"):
        return None, None, User.Role.COLABORADOR

    # Área (sub-área de Analítica) por puesto
    if "ingenier" in p:
        area = "ID"
    elif "cient" in p:
        area = "CD"
    elif "product manager" in p:
        area = "PM"
    elif "ux" in p:
        area = "UXUI"
    else:
        area = None

    # Nivel por sufijo
    if "lead" in p:
        level = "LEAD"
    elif "snr" in p:
        level = "SNR"
    elif "mid" in p:
        level = "MID"
    elif "jr" in p:
        level = "JR"
    else:
        level = "MID" if area == "UXUI" else None  # UX/UI sin nivel → MID

    return area, level, User.Role.COLABORADOR


class Command(BaseCommand):
    help = "Importa colaboradores desde docs/Modelos/usuarios.csv (área/nivel/rol + contraseña)."

    def add_arguments(self, parser):
        parser.add_argument("--password", default=DEFAULT_PASSWORD)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument(
            "--skip-password",
            action="store_true",
            help="Actualiza área/nivel/rol sin modificar contraseñas (útil para restaurar datos).",
        )

    def handle(self, *args, **options):
        path = Path(settings.BASE_DIR) / "docs" / "Modelos" / "usuarios.csv"
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"No se encontró {path}"))
            return

        areas = {a.code: a for a in Area.objects.all()}
        levels = {l.code: l for l in SeniorityLevel.objects.all()}
        password = options["password"]
        dry = options["dry_run"]
        skip_password = options["skip_password"]

        created = updated = skipped = 0
        no_area = []

        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                email = (row.get("Correo") or "").strip().lower()
                name = (row.get("Nombre COMPLETO") or "").strip()
                puesto = (row.get("Puesto") or "").strip()
                dept = (row.get("Área") or "").strip()
                if not email:
                    continue

                area_code, level_code, role = parse_position(dept, puesto)
                if role == User.Role.COLABORADOR and dept.lower().startswith("anal") and area_code is None:
                    no_area.append(f"{email} ({puesto})")

                if dry:
                    self.stdout.write(
                        f"[dry] {email:42} -> área={area_code or '—'} nivel={level_code or '—'} rol={role}"
                    )
                    continue

                user = User.objects.filter(email=email).first()
                is_new = user is None
                if is_new:
                    user = User(email=email)
                if user.is_superuser:
                    skipped += 1
                    continue

                user.full_name = titlecase_name(name) if name else (user.full_name or email)
                user.area = areas.get(area_code) if area_code else None
                user.level = levels.get(level_code) if level_code else None
                user.role = role
                user.is_active = True
                if not skip_password or is_new:
                    user.must_change_password = False
                    user.set_password(password)
                user.save()
                created += int(is_new)
                updated += int(not is_new)

        if no_area:
            self.stdout.write(self.style.WARNING(
                "Sin área deducible (revisar):\n  " + "\n  ".join(no_area)
            ))
        self.stdout.write(self.style.SUCCESS(
            f"Listo. Nuevos: {created} · Actualizados: {updated} · Superusuarios omitidos: {skipped}"
        ))
