"""Datos de demostración (solo desarrollo): asigna área/nivel y crea proyectos y equipos. Idempotente."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.catalog.models import Area, EvaluationPeriod, Project, ProjectMembership, SeniorityLevel

User = get_user_model()

# email -> (area_code, level_code, role)
ASSIGNMENTS = {
    "eduardo.ayala@arena-analytics.com": ("ID", "MID", "COLABORADOR"),
    "hector@arena-analytics.com": ("ID", "LEAD", "COLABORADOR"),
    "edward.gomez@arena-analytics.com": ("ID", "JR", "COLABORADOR"),
    "elias.garcia@arena-analytics.com": ("ID", "SNR", "COLABORADOR"),
    "maria.castro@arena-analytics.com": ("CD", "LEAD", "COLABORADOR"),
    "samuel.aguilar@arena-analytics.com": ("CD", "JR", "COLABORADOR"),
    "andrea.plascencia@arena-analytics.com": ("UXUI", "MID", "COLABORADOR"),
    "juan.montoya@arena-analytics.com": ("PM", "SNR", "COLABORADOR"),
    "lorenzo@arena-analytics.com": (None, None, "DIRECTOR"),
}

# name, client, lead_email, duration, [member_emails]
PROJECTS = [
    ("Tablero Comercial", "Cliente Retail", "hector@arena-analytics.com", "FINITO",
     ["eduardo.ayala@arena-analytics.com", "edward.gomez@arena-analytics.com", "elias.garcia@arena-analytics.com"]),
    ("Plataforma de Datos", "Interno", "hector@arena-analytics.com", "INDEFINIDO",
     ["eduardo.ayala@arena-analytics.com", "edward.gomez@arena-analytics.com"]),
    ("Modelo de Churn", "Cliente Telco", "maria.castro@arena-analytics.com", "FINITO",
     ["samuel.aguilar@arena-analytics.com"]),
]


class Command(BaseCommand):
    help = "Asigna área/nivel a usuarios y crea proyectos/equipos de demostración."

    def handle(self, *args, **options):
        areas = {a.code: a for a in Area.objects.all()}
        levels = {l.code: l for l in SeniorityLevel.objects.all()}

        assigned = 0
        for email, (area_code, level_code, role) in ASSIGNMENTS.items():
            user = User.objects.filter(email=email).first()
            if not user:
                continue
            user.area = areas.get(area_code) if area_code else None
            user.level = levels.get(level_code) if level_code else None
            user.role = role
            user.save(update_fields=["area", "level", "role"])
            assigned += 1
        self.stdout.write(self.style.SUCCESS(f"Asignaciones de área/nivel: {assigned}"))

        for name, client, lead_email, duration, members in PROJECTS:
            lead = User.objects.filter(email=lead_email).first()
            if not lead:
                continue
            project, _ = Project.objects.update_or_create(
                name=name,
                defaults={"client": client, "owner": lead, "responsable": lead, "duration_type": duration},
            )
            for member_email in members:
                member = User.objects.filter(email=member_email).first()
                if member:
                    ProjectMembership.objects.get_or_create(project=project, user=member)
        self.stdout.write(self.style.SUCCESS(f"Proyectos: {Project.objects.count()}"))
        if not EvaluationPeriod.objects.filter(status=EvaluationPeriod.Status.ABIERTO).exists():
            self.stderr.write(self.style.WARNING("No hay periodo ABIERTO; corre seed_catalogs."))
