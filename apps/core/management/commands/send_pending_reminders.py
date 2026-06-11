"""Envía recordatorios por correo de pendientes (cuestionarios por llenar / validar).

Pensado para agendarse (Vercel Cron, Programador de tareas, cron). Ejemplo:
  manage.py send_pending_reminders
  manage.py send_pending_reminders --dry-run   (no envía; solo cuenta)
"""

from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from apps.catalog.models import EvaluationPeriod
from apps.evaluations.models import OwnershipEvaluation

User = get_user_model()


class Command(BaseCommand):
    help = "Envía un correo a cada persona con cuestionarios de Ownership pendientes en el periodo abierto."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="No envía; solo reporta.")

    def handle(self, *args, **options):
        period = EvaluationPeriod.objects.filter(
            status=EvaluationPeriod.Status.ABIERTO
        ).first()
        if not period:
            self.stdout.write(self.style.WARNING("No hay periodo abierto; nada que recordar."))
            return

        sent = 0
        for user in User.objects.filter(is_active=True, is_superuser=False):
            pending = []
            for m in user.memberships.select_related("project").filter(project__is_active=True):
                ev = OwnershipEvaluation.objects.filter(
                    user=user, project=m.project, period=period
                ).first()
                if ev is None or not ev.is_submitted:
                    pending.append(m.project.name)
            if not pending:
                continue

            lines = "\n".join(f"  · {p}" for p in pending)
            if options["dry_run"]:
                self.stdout.write(f"[dry-run] {user.email}: {len(pending)} pendiente(s)")
            else:
                send_mail(
                    subject=f"Tienes evaluaciones pendientes — {period.name}",
                    message=(
                        f"Hola {user.get_short_name()},\n\n"
                        f"Tienes {len(pending)} evaluación(es) de Ownership por completar este periodo:\n"
                        f"{lines}\n\n"
                        f"Ingresa a Evaluaciones Arena para continuar.\n\n— Talento y Cultura"
                    ),
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Recordatorios procesados: {sent} persona(s)."))
