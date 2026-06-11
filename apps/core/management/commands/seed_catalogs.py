"""Siembra catálogos base: áreas, niveles, ponderaciones (RN-19) y periodo inicial (RN-13). Idempotente."""

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.catalog.models import Area, EvaluationPeriod, PillarWeight, SeniorityLevel

AREAS = [
    ("ID", "Ingeniería de Datos"),
    ("CD", "Ciencia de Datos"),
    ("PM", "Gestión de Proyectos"),
    ("UXUI", "UX/UI"),
]

# (code, name, order)
LEVELS = [
    ("JR", "Junior", 1),
    ("MID", "Mid", 2),
    ("SNR", "Senior", 3),
    ("LEAD", "Lead", 4),
]

# code -> (w_ownership, w_value_delivery, w_arena_impact). Suman 1.00 (Ponderación.md).
WEIGHTS = {
    "JR": ("0.60", "0.20", "0.20"),
    "MID": ("0.50", "0.25", "0.25"),
    "SNR": ("0.40", "0.30", "0.30"),
    "LEAD": ("0.30", "0.35", "0.35"),
}


class Command(BaseCommand):
    help = "Crea áreas, niveles, ponderaciones y el periodo 2026-S1 (idempotente)."

    def handle(self, *args, **options):
        for code, name in AREAS:
            Area.objects.update_or_create(code=code, defaults={"name": name})
        self.stdout.write(self.style.SUCCESS(f"Áreas: {Area.objects.count()}"))

        levels: dict[str, SeniorityLevel] = {}
        for code, name, order in LEVELS:
            level, _ = SeniorityLevel.objects.update_or_create(
                code=code, defaults={"name": name, "order": order}
            )
            levels[code] = level
        self.stdout.write(self.style.SUCCESS(f"Niveles: {SeniorityLevel.objects.count()}"))

        for code, (wo, wv, wa) in WEIGHTS.items():
            PillarWeight.objects.update_or_create(
                level=levels[code],
                defaults={
                    "w_ownership": Decimal(wo),
                    "w_value_delivery": Decimal(wv),
                    "w_arena_impact": Decimal(wa),
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Ponderaciones: {PillarWeight.objects.count()}"))

        EvaluationPeriod.objects.update_or_create(
            name="2026-S1",
            defaults={
                "start_date": date(2026, 1, 1),
                "end_date": date(2026, 6, 30),
                "kind": EvaluationPeriod.Kind.SEMESTRAL,
                "status": EvaluationPeriod.Status.ABIERTO,
            },
        )
        self.stdout.write(self.style.SUCCESS("Periodo 2026-S1 (ABIERTO) listo."))
