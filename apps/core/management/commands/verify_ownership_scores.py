"""Verifica que el cálculo ponderado (spec 008) no cambie ningún score de Ownership existente.

Solo lee. Recalcula cada evaluación con respuestas y la compara con (a) el promedio simple de
siempre cuando su cuestionario es «General» / sin pesos y (b) el score guardado de las enviadas.
Sale con error si hay una sola diferencia. Úsalo antes y después de migrar (constitución VI).

Ej.: python manage.py verify_ownership_scores [--period 2026-S1]
"""

from django.core.management.base import BaseCommand, CommandError

from apps.core.services import scoring


def _is_legacy_equivalent(evaluation) -> bool:
    """True si el cuestionario es de una sola categoría y sin pesos de pregunta (promedio simple)."""
    template = evaluation.template
    if template.template_categories.count() > 1:
        return False
    return not template.sections.filter(questions__weight_pct__isnull=False).exists()


class Command(BaseCommand):
    help = "Compara el score ponderado con el promedio simple y con el score guardado."

    def add_arguments(self, parser):
        parser.add_argument("--period", help="Nombre del periodo (p. ej. 2026-S1); por defecto todos.")

    def handle(self, *args, **opts):
        from apps.evaluations.models import OwnershipEvaluation

        evaluations = OwnershipEvaluation.objects.select_related("template", "period", "user")
        if opts["period"]:
            evaluations = evaluations.filter(period__name=opts["period"])

        checked = vs_simple = vs_stored = weighted_only = 0
        diffs = []
        for evaluation in evaluations.prefetch_related("answers"):
            values = [a.value for a in evaluation.answers.all() if not a.is_na and a.value is not None]
            if not values and evaluation.score is None:
                continue
            checked += 1
            new = scoring.ownership_evaluation_score(evaluation)
            if _is_legacy_equivalent(evaluation):
                vs_simple += 1
                simple = scoring._avg(values)
                if new != simple:
                    diffs.append(f"#{evaluation.pk} {evaluation.user} · {evaluation.period}: "
                                 f"ponderado {new} ≠ promedio simple {simple}")
            else:
                weighted_only += 1
            if evaluation.status == OwnershipEvaluation.Status.ENVIADA and evaluation.score is not None:
                vs_stored += 1
                if new != evaluation.score:
                    diffs.append(f"#{evaluation.pk} {evaluation.user} · {evaluation.period}: "
                                 f"ponderado {new} ≠ guardado {evaluation.score}")

        self.stdout.write(
            f"{checked} evaluaciones verificadas · {vs_simple} contra promedio simple · "
            f"{vs_stored} contra score guardado · {weighted_only} con ponderación propia."
        )
        if diffs:
            for line in diffs:
                self.stdout.write(self.style.ERROR("  " + line))
            raise CommandError(f"{len(diffs)} diferencias. No desplegar.")
        self.stdout.write(self.style.SUCCESS("0 diferencias."))
