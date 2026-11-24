"""Reestructura Área → Posición → Nivel (opcional). Idempotente.

Qué hace:
  1. Crea las Áreas Analítica y Consultoría y cuelga de Analítica las posiciones actuales (CD, ID, PM, UXUI).
  2. Crea las posiciones de Consultoría: Analista, Consultor (con «Consultor Sr» = Consultor + nivel Snr) y Gerente,
     con las mismas ponderaciones de pilares que hoy tienen Jr, Mid, Snr y Lead.
  3. Marca «Lead / Gerente» a quien hoy es nivel Lead y «Director» a quien hoy tiene el rol Director.
  4. Mueve a las personas de la antigua área CONS: Jr→Analista, Mid→Consultor, Snr→Consultor (nivel Snr),
     Lead→Gerente; los cuestionarios de CONS siguen a su puesto.
  5. Borra las evaluaciones de Ownership de Consultoría (eran de prueba) y retira la antigua área CONS.

Uso:
    python manage.py restructure_org            # simulación (no guarda nada)
    python manage.py restructure_org --apply    # aplica (deja un respaldo JSON en backups/)
"""

import json
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core import serializers
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import ProtectedError

from apps.accounts.models import User
from apps.catalog.models import (
    Area, Department, PillarWeight, Position, PositionPillarWeight, SeniorityLevel,
)
from apps.core.services import positions as positions_service
from apps.questionnaires.models import QuestionnaireTemplate

# nivel actual de CONS → (código de la nueva posición, nivel que conserva o None)
CONS_MAP = {
    "JR": ("ANAL", None),
    "MID": ("CONSUL", None),
    "SNR": ("CONSUL", "SNR"),
    "LEAD": ("GERENTE", None),
}
CONS_POSITIONS = (
    # code, nombre de la posición, [(nivel o None, nombre visible, ponderación de pilares heredada de…)]
    ("ANAL", "Analista", [(None, "Analista", "JR")]),
    ("CONSUL", "Consultor", [(None, "Consultor", "MID"), ("SNR", "Consultor Sr", "SNR")]),
    ("GERENTE", "Gerente", [(None, "Gerente", "LEAD")]),
)
ANALYTICS_CODES = ("CD", "ID", "PM", "UXUI")


class Command(BaseCommand):
    help = "Reestructura Área → Posición → Nivel (opcional). Simula salvo --apply."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Aplica los cambios (por defecto solo simula).")
        parser.add_argument("--no-backup", action="store_true", help="No escribe el respaldo JSON.")

    def handle(self, *args, **opts):
        apply = opts["apply"]
        self.say = lambda msg: self.stdout.write(msg)
        self.say(("APLICANDO" if apply else "SIMULACIÓN (no se guarda nada)") + " · reestructura de organigrama")
        old = Area.objects.filter(code="CONS").first()
        if apply and not opts["no_backup"]:
            self._backup(old)
        with transaction.atomic():
            self._run(old)
            if not apply:
                transaction.set_rollback(True)
        positions_service.invalidate()
        self.say("Listo." if apply else "Simulación terminada: ejecuta con --apply para guardar.")

    # ------------------------------------------------------------------ respaldo
    def _backup(self, old):
        from apps.evaluations.models import FinalScore, OwnershipAnswer, OwnershipEvaluation

        evaluations = OwnershipEvaluation.objects.filter(template__area=old) if old else OwnershipEvaluation.objects.none()
        user_ids = set(User.objects.filter(area=old).values_list("pk", flat=True)) if old else set()
        objects = []
        objects += list(User.objects.filter(pk__in=user_ids) | User.objects.filter(level__code="LEAD") | User.objects.filter(role="DIRECTOR"))
        objects += list(Area.objects.all()) + list(Position.objects.all()) + list(PositionPillarWeight.objects.all())
        objects += list(QuestionnaireTemplate.objects.filter(area=old)) if old else []
        objects += list(evaluations) + list(OwnershipAnswer.objects.filter(evaluation__in=evaluations))
        objects += list(FinalScore.objects.filter(user_id__in=[e.user_id for e in evaluations]))
        folder = Path(settings.BASE_DIR) / "backups"
        folder.mkdir(exist_ok=True)
        path = folder / f"restructure_org_{datetime.now():%Y%m%d_%H%M%S}.json"
        path.write_text(serializers.serialize("json", objects, indent=1), encoding="utf-8")
        self.say(f"Respaldo: {path} ({len(objects)} registros)")

    # ------------------------------------------------------------------ pasos
    def _run(self, old):
        from apps.evaluations.models import OwnershipEvaluation

        # 1) Áreas
        analytics, _ = Department.objects.get_or_create(code="ANALIT", defaults={"name": "Analítica", "order": 1})
        consulting, _ = Department.objects.get_or_create(code="CONSUL", defaults={"name": "Consultoría", "order": 2})
        linked = Area.objects.filter(code__in=ANALYTICS_CODES, department__isnull=True).update(department=analytics)
        self.say(f"Áreas: Analítica y Consultoría listas · {linked} posición(es) de Analítica enlazadas")

        # 2) Marcas de organigrama (ANTES de tocar niveles)
        leads = User.objects.filter(level__code="LEAD", is_lead_flag=False).update(is_lead_flag=True)
        directors = User.objects.filter(role=User.Role.DIRECTOR, is_director_flag=False).update(is_director_flag=True)
        self.say(f"Marcas: {leads} Lead(s)/Gerente(s) y {directors} Director(es) marcados")

        # 3) Posiciones de Consultoría (+ ponderación de pilares heredada)
        levels = {l.code: l for l in SeniorityLevel.objects.all()}
        new_areas = {}
        for code, name, combos in CONS_POSITIONS:
            area, _ = Area.objects.get_or_create(code=code, defaults={"name": name})
            area.name, area.department, area.is_active = name, consulting, True
            area.save()
            new_areas[code] = area
            for level_code, visible, inherit in combos:
                level = levels[level_code] if level_code else None
                position, _ = Position.objects.get_or_create(
                    area=area, level=level, defaults={"name": visible, "is_active": True})
                source = PillarWeight.objects.filter(level=levels[inherit]).first()
                if source:
                    PositionPillarWeight.objects.get_or_create(position=position, defaults={
                        "w_ownership": source.w_ownership, "w_value_delivery": source.w_value_delivery,
                        "w_arena_impact": source.w_arena_impact,
                    })
        self.say("Posiciones de Consultoría: Analista, Consultor (Consultor Sr = nivel Snr) y Gerente")

        if old is None:
            self.say("No hay área CONS que mover (ya estaba reestructurado).")
            return

        # 4) Evaluaciones de prueba de Consultoría: se borran (y se recalcula la calificación final)
        from apps.core.services import ownership_flow

        deleted = []
        for evaluation in OwnershipEvaluation.objects.filter(template__area=old).select_related("user", "period", "project"):
            deleted.append(f"{evaluation.user.full_name} · {evaluation.period.name} · {evaluation.get_status_display()}")
            ownership_flow.reset_ownership_evaluation(
                evaluation, actor=None, reason="Evaluación de prueba retirada al reestructurar Área/Posición/Nivel")
        self.say(f"Evaluaciones de Consultoría borradas: {len(deleted)} " + ("→ " + "; ".join(deleted) if deleted else ""))

        # 5) Cuestionarios de CONS siguen a su puesto
        moved_templates = 0
        for template in QuestionnaireTemplate.objects.filter(area=old).select_related("level"):
            target = CONS_MAP.get(template.level.code if template.level_id else "")
            if target is None:
                self.say(f"  ! Cuestionario {template} sin equivalencia: se deja como está")
                continue
            code, level_code = target
            template.area, template.level = new_areas[code], levels[level_code] if level_code else None
            template.save(update_fields=["area", "level"])
            moved_templates += 1
        self.say(f"Cuestionarios movidos: {moved_templates}")

        # 6) Personas de CONS
        moved, left = [], []
        for user in User.objects.filter(area=old).select_related("level"):
            target = CONS_MAP.get(user.level.code if user.level_id else "")
            if target is None:
                left.append(f"{user.full_name} (sin nivel: queda sin posición; asígnala en Usuarios)")
                user.area, user.level = None, None
            else:
                code, level_code = target
                user.area, user.level = new_areas[code], levels[level_code] if level_code else None
                moved.append(f"{user.full_name} → {new_areas[code].name}" + (" · Senior" if level_code else ""))
            user.save(update_fields=["area", "level"])
        self.say(f"Personas movidas: {len(moved)}")
        for line in moved + left:
            self.say(f"  - {line}")

        # 7) Antigua área CONS: sus relaciones M2M pasan a las 3 posiciones nuevas y se retira
        for rel in Area._meta.related_objects:
            if rel.many_to_many and rel.auto_created:
                for obj in rel.related_model.objects.filter(**{rel.field.name: old}):
                    getattr(obj, rel.field.name).add(*new_areas.values())
        Position.objects.filter(area=old).delete()
        try:
            with transaction.atomic():
                old.delete()
            self.say("Área antigua CONS retirada")
        except ProtectedError:
            old.is_active = False
            old.save(update_fields=["is_active"])
            self.say("Área antigua CONS desactivada (aún tiene referencias)")
