"""Carga los 16 cuestionarios de Ownership (fixtures YAML) + 1 de Entrega de Valor. Idempotente."""

from pathlib import Path

import yaml
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Area, SeniorityLevel
from apps.questionnaires.models import (
    Question,
    QuestionnaireTemplate,
    ScaleOption,
    Section,
)

OWNERSHIP_SCALE_NOTE = (
    "Califica cada punto del 1 al 4 según la evidencia. Marca N/A si la actividad "
    "no aplicó en este periodo por razones justificadas; los N/A no entran al promedio."
)

# Escala uniforme de Ownership (RN-03). value None = N/A.
OWNERSHIP_SCALE = [
    (1, "No cumple", "La actividad no se ejecutó o se ejecutó con deficiencias significativas que impactaron el proyecto o al equipo."),
    (2, "Cumple parcial", "Se ejecutó pero con omisiones, inconsistencias o calidad por debajo del estándar esperado para el nivel."),
    (3, "Cumple", "Se ejecutó conforme al estándar esperado para el nivel."),
    (4, "Excede", "Se ejecutó por encima del estándar del nivel, con iniciativa, precisión o impacto adicional notable."),
    (None, "N/A", "No aplica en este periodo por razones justificadas. No entra al promedio."),
]

# Criterios de Entrega de Valor (RN-08). El criterio de tiempo aplicable se resuelve por proyecto.
VALUE_DELIVERY_CRITERIA = [
    ("Satisfacción del cliente", "Nivel de satisfacción del cliente con el trabajo entregado en el periodo."),
    ("Entregables", "Cumplimiento y calidad de los entregables comprometidos."),
    ("Tiempo (proyecto finito)", "Cumplimiento de la fecha de entrega definida. Aplica solo si el proyecto tiene fecha de cierre."),
    ("Tiempo (servicio indefinido)", "Consistencia y continuidad del servicio. Aplica solo si el proyecto es de tiempo indefinido."),
]


class Command(BaseCommand):
    help = "Siembra los cuestionarios de Ownership y Entrega de Valor (publicados, versión 1)."

    @transaction.atomic
    def handle(self, *args, **options):
        fixtures_dir = Path(settings.BASE_DIR) / "fixtures" / "questionnaires"
        total_q = 0

        for area in Area.objects.all():
            path = fixtures_dir / f"{area.code}.yaml"
            if not path.exists():
                self.stderr.write(self.style.WARNING(f"  - Sin fixture para {area.code}"))
                continue
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            for tpl in data.get("templates", []):
                level = SeniorityLevel.objects.get(code=tpl["level"].upper())
                total_q += self._seed_ownership_template(area, level, tpl["questions"])

        self._seed_value_delivery_template()

        self.stdout.write(self.style.SUCCESS(
            f"Cuestionarios: {QuestionnaireTemplate.objects.count()} plantillas, "
            f"{Question.objects.count()} preguntas ({total_q} de Ownership)."
        ))

    def _seed_ownership_template(self, area, level, questions) -> int:
        template, _ = QuestionnaireTemplate.objects.update_or_create(
            kind=QuestionnaireTemplate.Kind.OWNERSHIP,
            area=area,
            level=level,
            version=1,
            defaults={
                "status": QuestionnaireTemplate.Status.PUBLICADO,
                "scale_note": OWNERSHIP_SCALE_NOTE,
            },
        )
        # Reconstruye contenido para reflejar el fixture (idempotente).
        template.sections.all().delete()
        template.scale_options.all().delete()

        section = Section.objects.create(
            template=template, title="Checklist de Ownership", order=1
        )
        for i, q in enumerate(questions, start=1):
            Question.objects.create(
                section=section, order=i, title=q["title"], text=q.get("text", ""),
                qtype=Question.Type.SCALE, allow_na=True, is_required=True,
            )
        for order, (value, label, desc) in enumerate(OWNERSHIP_SCALE, start=1):
            ScaleOption.objects.create(
                template=template, value=value, label=label, description=desc, order=order
            )
        return len(questions)

    def _seed_value_delivery_template(self):
        template, _ = QuestionnaireTemplate.objects.update_or_create(
            kind=QuestionnaireTemplate.Kind.VALUE_DELIVERY,
            area=None,
            level=None,
            version=1,
            defaults={
                "status": QuestionnaireTemplate.Status.PUBLICADO,
                "scale_note": "Cada criterio se califica del 1 al 4. El criterio de tiempo "
                "no aplicable se marca N/A y se excluye del promedio (RN-08).",
            },
        )
        template.sections.all().delete()
        template.scale_options.all().delete()

        section = Section.objects.create(
            template=template, title="Criterios de Entrega de Valor", order=1
        )
        for i, (title, desc) in enumerate(VALUE_DELIVERY_CRITERIA, start=1):
            Question.objects.create(
                section=section, order=i, title=title, text=desc,
                qtype=Question.Type.SCALE, allow_na=True, is_required=False,
            )
        for order, (value, label, desc) in enumerate(OWNERSHIP_SCALE, start=1):
            ScaleOption.objects.create(
                template=template, value=value, label=label, description=desc, order=order
            )
