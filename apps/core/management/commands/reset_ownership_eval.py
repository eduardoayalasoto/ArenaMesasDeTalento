"""Reinicia la evaluación de Ownership de un colaborador para que pueda empezar desde cero.

Uso:
  manage.py reset_ownership_eval usuario@arena-analytics.com
  manage.py reset_ownership_eval usuario@arena-analytics.com --proyecto 12
  manage.py reset_ownership_eval usuario@arena-analytics.com --dry-run

Solo debe ejecutarse por Talento y Cultura.
"""

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Reinicia (elimina) la evaluación de Ownership de un colaborador "
        "para que pueda comenzar desde cero. Solo para uso de Talento y Cultura."
    )

    def add_arguments(self, parser):
        parser.add_argument("email", help="Correo del colaborador cuya evaluación se reiniciará.")
        parser.add_argument(
            "--proyecto",
            dest="project_id",
            type=int,
            default=None,
            help="ID del proyecto (omitir para Leads con evaluación transversal).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Muestra lo que se borraría sin realizar cambios.",
        )

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model

        from apps.catalog.models import EvaluationPeriod, Project
        from apps.core.services.ownership_flow import reset_ownership_evaluation
        from apps.evaluations.models import OwnershipEvaluation

        User = get_user_model()
        email = options["email"].strip().lower()
        dry_run = options["dry_run"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f"No existe un usuario con correo '{email}'.")

        period = EvaluationPeriod.objects.filter(status=EvaluationPeriod.Status.ABIERTO).first()
        if not period:
            raise CommandError("No hay un periodo de evaluación abierto.")

        project_id = options["project_id"]
        if project_id is not None:
            try:
                project = Project.objects.get(pk=project_id)
            except Project.DoesNotExist:
                raise CommandError(f"No existe un proyecto con ID {project_id}.")
            evaluation = OwnershipEvaluation.objects.filter(
                user=user, project=project, period=period
            ).first()
            project_label = project.name
        else:
            evaluation = OwnershipEvaluation.objects.filter(
                user=user, project__isnull=True, period=period
            ).first()
            project_label = "todos los proyectos (Lead)"

        if not evaluation:
            self.stdout.write(self.style.WARNING(
                f"No se encontró evaluación de {user.full_name} "
                f"para '{project_label}' en el periodo {period}."
            ))
            return

        answers_count = evaluation.answers.count()
        evaluators_count = evaluation.evaluators.count()

        self.stdout.write(
            f"\nEvaluación a reiniciar:"
            f"\n  Colaborador : {user.full_name} <{user.email}>"
            f"\n  Proyecto    : {project_label}"
            f"\n  Periodo     : {period}"
            f"\n  Estado      : {evaluation.get_status_display()}"
            f"\n  Respuestas  : {answers_count}"
            f"\n  Evaluadores : {evaluators_count}"
        )

        if dry_run:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No se realizaron cambios."))
            return

        confirm = input("\nEsta accion borra todas las respuestas y el evaluador asignado.\n"
                        "Escribe 'si' para confirmar: ")
        if confirm.strip().lower() != "si":
            self.stdout.write(self.style.WARNING("Cancelado."))
            return

        reset_ownership_evaluation(evaluation)
        self.stdout.write(self.style.SUCCESS(
            f"\nEvaluacion de {user.full_name} reiniciada. "
            "Ahora puede volver a elegir evaluador y comenzar desde cero."
        ))
