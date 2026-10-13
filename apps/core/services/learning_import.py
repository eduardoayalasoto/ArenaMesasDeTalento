"""Importación del catálogo y los planes 2026, y limpieza de datos de prueba (spec 006, US4).

- `import_plans`: carga `apps/learning/data/planes_2026.json` (armado del Excel y los HTML con
  `scripts/build_plans_json.py`). Idempotente: identifica el curso por liga normalizada (o, sin
  liga, por nombre + proveedor), nunca sobrescribe lo que Talento ya editó (solo completa campos
  vacíos) y deja los planes PUBLICADOS sin tocar los que Talento archivó (FR-029/031).
- `reset_learning_data`: borra el contenido de prueba de Arena Learn (FR-039/040).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

DEFAULT_PLANS_PATH = Path(__file__).resolve().parents[2] / "learning" / "data" / "planes_2026.json"


def _m():
    from apps.learning import models

    return models


@dataclass
class ImportSummary:
    dry_run: bool = False
    courses_created: int = 0
    courses_updated: int = 0
    courses_unchanged: int = 0
    plans_created: int = 0
    plans_updated: int = 0
    items_created: int = 0
    items_unchanged: int = 0
    ko_assigned: int = 0
    proposed: int = 0
    aliases: list = field(default_factory=list)
    unprocessed: list = field(default_factory=list)

    def lines(self) -> list[str]:
        head = "SIMULACIÓN (no se guardó nada)" if self.dry_run else "Importación aplicada"
        out = [
            head,
            f"Cursos: {self.courses_created} creados · {self.courses_updated} completados · "
            f"{self.courses_unchanged} sin cambio",
            f"Planes: {self.plans_created} creados · {self.plans_updated} actualizados",
            f"Cursos en planes: {self.items_created} agregados · {self.items_unchanged} ya estaban",
            f"Etiqueta KO asignada a {self.ko_assigned} curso(s) · {self.proposed} curso(s) con datos propuestos",
        ]
        if self.aliases:
            out.append(f"Misma liga con otro nombre ({len(self.aliases)}):")
            out += [f"  - {a}" for a in self.aliases]
        if self.unprocessed:
            out.append(f"No procesados ({len(self.unprocessed)}):")
            out += [f"  - {u}" for u in self.unprocessed]
        return out


def _validate(data, areas, levels):
    m = _m()
    errors = []
    kinds, focuses = set(m.CourseKind.values), set(m.Focus.values)
    keys = set()
    for c in data.get("courses", []):
        keys.add(c["key"])
        if c.get("kind") not in kinds:
            errors.append(f"Curso «{c.get('name')}»: tipo inválido {c.get('kind')!r}.")
        if c.get("focus") not in focuses:
            errors.append(f"Curso «{c.get('name')}»: enfoque inválido {c.get('focus')!r}.")
        if not (c.get("name") or "").strip():
            errors.append(f"Curso {c.get('key')!r} sin nombre.")
    for p in data.get("plans", []):
        if p.get("area") not in areas:
            errors.append(f"Plan con área inexistente {p.get('area')!r}.")
        for mth in ("start_month", "end_month"):
            if not 1 <= int(p.get(mth) or 0) <= 12:
                errors.append(f"Plan {p.get('area')}: {mth} inválido.")
        for kind in (p.get("type_notes") or {}):
            if kind not in kinds:
                errors.append(f"Plan {p.get('area')}: tipo inválido en textos {kind!r}.")
        for it in p.get("items", []):
            if it["course"] not in keys:
                errors.append(f"Plan {p.get('area')}: curso inexistente {it['course']!r}.")
            for lv in it.get("levels", []):
                if lv not in levels:
                    errors.append(f"Plan {p.get('area')}: nivel inexistente {lv!r}.")
    if errors:
        raise ValidationError(errors[:20])


def _find_course(c, by_url, by_name):
    from apps.core.services.learning_flow import normalize_url

    key = normalize_url(c.get("url") or "")
    if key:
        return by_url.get(key)
    return by_name.get((c["name"].strip().lower(), c["provider"].strip().lower()))


def import_plans(path=None, *, year: int | None = None, actor=None, dry_run: bool = False) -> ImportSummary:
    """Carga el catálogo y los planes. `dry_run` ejecuta todo y revierte (para revisar el resumen)."""
    from apps.catalog.models import Area, SeniorityLevel
    from apps.core.services import learning_tags
    from apps.core.services.learning_flow import normalize_url

    m = _m()
    data = json.loads(Path(path or DEFAULT_PLANS_PATH).read_text(encoding="utf-8"))
    areas = {a.code: a for a in Area.objects.all()}
    levels = {lv.code: lv for lv in SeniorityLevel.objects.all()}
    _validate(data, areas, levels)
    year = year or data.get("year")
    summary = ImportSummary(dry_run=dry_run)

    with transaction.atomic():
        ko = learning_tags.resolve(["KO"], actor)[0]
        by_url, by_name = {}, {}
        for course in m.CatalogCourse.objects.all():
            if course.url:
                by_url.setdefault(normalize_url(course.url), course)
            by_name.setdefault((course.name.strip().lower(), course.provider.strip().lower()), course)

        courses = {}
        for c in data["courses"]:
            obj = _find_course(c, by_url, by_name)
            cost = c.get("reference_cost")
            if obj is None:
                obj = m.CatalogCourse.objects.create(
                    name=c["name"][:160], provider=c["provider"][:120], url=c.get("url") or "",
                    kind=c["kind"], focus=c["focus"],
                    duration_hours=Decimal(str(c["duration_hours"])) if c.get("duration_hours") else None,
                    reference_cost=Decimal(str(cost)) if cost is not None else None,
                    currency=c.get("currency") or "MXN", created_by=actor,
                )
                summary.courses_created += 1
                if obj.url:
                    by_url[normalize_url(obj.url)] = obj
                by_name[(obj.name.lower(), obj.provider.lower())] = obj
            else:  # solo completa lo vacío: tipo, enfoque y lo que Talento editó no se tocan (FR-029)
                changed = []
                if obj.duration_hours is None and c.get("duration_hours"):
                    obj.duration_hours = Decimal(str(c["duration_hours"]))
                    changed.append("duration_hours")
                if obj.reference_cost is None and cost is not None:
                    obj.reference_cost, obj.currency = Decimal(str(cost)), c.get("currency") or obj.currency
                    changed += ["reference_cost", "currency"]
                if not obj.url and c.get("url"):
                    obj.url = c["url"]
                    changed.append("url")
                if changed:
                    obj.save(update_fields=changed)
                    summary.courses_updated += 1
                else:
                    summary.courses_unchanged += 1
            if c.get("ko") and not obj.tags.filter(pk=ko.pk).exists():
                obj.tags.add(ko)
                summary.ko_assigned += 1
            if c.get("proposed"):
                summary.proposed += 1
            for alias in c.get("aliases", []):
                summary.aliases.append(f"«{obj.name}» = «{alias}»")
            courses[c["key"]] = obj

        for p in data["plans"]:
            plan = m.TrainingPlan.objects.filter(area=areas[p["area"]], year=year).first()
            if plan is None:
                plan = m.TrainingPlan.objects.create(
                    area=areas[p["area"]], year=year, title=p["title"], start_month=p["start_month"],
                    end_month=p["end_month"], hours_min=p.get("hours_min"), hours_max=p.get("hours_max"),
                    intro=p.get("intro", ""), type_notes=p.get("type_notes") or {},
                    status=m.TrainingPlan.Status.PUBLICADO, published_at=timezone.now(), created_by=actor,
                )
                summary.plans_created += 1
            else:
                changed = []
                notes = dict(plan.type_notes or {})
                for kind, text in (p.get("type_notes") or {}).items():
                    if not notes.get(kind):
                        notes[kind] = text
                if notes != (plan.type_notes or {}):
                    plan.type_notes = notes
                    changed.append("type_notes")
                if not plan.intro and p.get("intro"):
                    plan.intro = p["intro"]
                    changed.append("intro")
                if plan.status == m.TrainingPlan.Status.BORRADOR:  # archivado: se respeta (FR-031)
                    plan.status, plan.published_at = m.TrainingPlan.Status.PUBLICADO, timezone.now()
                    changed += ["status", "published_at"]
                if changed:
                    plan.save(update_fields=[*changed, "updated_at"])
                    summary.plans_updated += 1
            existing = {pc.course_id: pc for pc in plan.items.all()}
            next_order = max((pc.order for pc in existing.values()), default=0)
            for it in p["items"]:
                course = courses[it["course"]]
                if course.pk in existing:
                    summary.items_unchanged += 1  # niveles y nota del plan no se pisan
                    continue
                next_order += 1
                pc = m.PlanCourse.objects.create(plan=plan, course=course, order=next_order,
                                                 note=(it.get("note") or "")[:200])
                pc.levels.set([levels[code] for code in it.get("levels", [])])
                existing[course.pk] = pc
                summary.items_created += 1

        if dry_run:
            transaction.set_rollback(True)
    return summary


# --- Limpieza de datos de prueba (FR-039/040) -----------------------------------------------


def _reset_targets():
    m = _m()
    # Orden de borrado: primero lo que protege (PROTECT) a lo siguiente.
    return [
        ("Pasos de aprobación", m.ApprovalStep.objects.all()),
        ("Evidencias", m.CourseEvidence.objects.all()),
        ("Reseñas", m.CourseReview.objects.all()),
        ("Cursos en Mi plan", m.PersonalPlanItem.objects.all()),
        ("Planes personales", m.PersonalPlan.objects.all()),
        ("Solicitudes y registros", m.CourseRequest.objects.all()),
        ("Historial de solicitudes", m.CourseRequest.history.model.objects.all()),
        ("Cursos en planes", m.PlanCourse.objects.all()),
        ("Planes de capacitación", m.TrainingPlan.objects.all()),
        ("Cursos del catálogo", m.CatalogCourse.objects.all()),
        ("Etiquetas", m.Tag.objects.all()),
    ]


def reset_learning_data(before: date, confirm: bool = False) -> dict[str, int]:
    """Cuenta (y con `confirm`, borra) el contenido de Arena Learn. Conserva LearningSettings.

    Se niega si hay solicitudes o cursos creados en `before` o después: protege datos reales
    capturados entre la revisión y la corrida.
    """
    m = _m()
    recent = (m.CourseRequest.objects.filter(created_at__date__gte=before).count()
              + m.CatalogCourse.objects.filter(created_at__date__gte=before).count())
    if recent:
        raise ValidationError(
            f"Hay {recent} solicitud(es) o curso(s) creados desde el {before:%d/%m/%Y}: revisa antes de borrar.")
    counts = {label: qs.count() for label, qs in _reset_targets()}
    if confirm:
        with transaction.atomic():
            for label, qs in _reset_targets():
                qs.delete()
            # Borrar solicitudes genera filas de historial "eliminado": también se limpian.
            m.CourseRequest.history.model.objects.all().delete()
    return counts
