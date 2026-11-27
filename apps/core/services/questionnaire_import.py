"""Carga de una versión nueva de los cuestionarios de Ownership desde fixtures YAML (spec 007/008).

El YAML lo genera `scripts/checklists_2027_to_yaml.py` (checklists) o
`scripts/matriz_consultoria_to_yaml.py` (matriz de Consultoría); aquí solo se carga. Reglas
(contracts/import-command.md y specs/008-ownership-ponderado-categorias/contracts/cons-yaml.md):
- llave (OWNERSHIP, área, nivel, versión); escala y nota de escala se copian de la v1, salvo que
  el YAML traiga `scale` propia (única forma de importar una versión 1);
- categorías y ponderaciones (spec 008): sin `categories` el cuestionario queda en «General» al 100%;
  toda ponderación con un decimal y cada grupo suma exactamente 100.0, o se rechaza el puesto;
- si la versión ya existe y algún reactivo tiene respuestas, el puesto se rechaza;
- si existe sin respuestas, se reconstruye; borradores de versión mayor sin respuestas se archivan;
- con `publish`, se publica vía `questionnaire_editor.publish_template` (valida y archiva la anterior).
"""

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import yaml
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.core.services import ownership_weights as ow
from apps.core.services import questionnaire_editor

SECTION_TITLE = "Checklist de Ownership"


class ImportRejected(Exception):
    """El puesto no se puede cargar sin poner en riesgo respuestas existentes."""


@dataclass
class ImportResult:
    area: str
    level: str
    version: int
    questions: int
    status: str
    archived: list

    def __str__(self):
        extra = f" · archivados: {', '.join(self.archived)}" if self.archived else ""
        return f"{self.area}/{self.level} v{self.version}: {self.questions} reactivos · {self.status}{extra}"


def load_dir(directory):
    """[(area_code, level_code, questions, options)] de todos los <AREA>.yaml de la carpeta.

    `options` = {"categories", "scale", "scale_note"} (None si el YAML no los trae).
    """
    entries = []
    for path in sorted(Path(directory).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for tpl in data.get("templates", []):
            options = {key: tpl.get(key) for key in ("categories", "scale", "scale_note")}
            entries.append((tpl["area"], tpl["level"], tpl["questions"], options))
    return entries


def _has_answers(template):
    from apps.evaluations.models import OwnershipAnswer

    return OwnershipAnswer.objects.filter(question__section__template=template).exists()


def _plan_categories(label, categories, questions):
    """[(código, nombre, ponderación, [preguntas])] validado; sin `categories` = «General» al 100%."""
    if not categories:
        return [("general", "General", Decimal("100.0"), list(questions))]
    plan = [(entry["code"], entry["name"], entry["weight"], []) for entry in categories]
    by_code = {code: group for code, _, _, group in plan}
    for q in questions:
        code = q.get("category") or (plan[0][0] if len(plan) == 1 else None)
        if code not in by_code:
            raise ImportRejected(f"{label}: la pregunta «{q['title']}» no tiene una categoría válida.")
        by_code[code].append(q)
    try:
        errors = [ow.group_error(f"{label} · categorías", [weight for _, _, weight, _ in plan])]
        for _, name, weight, group in plan:
            weights = [q.get("weight") for q in group]
            if any(w is not None for w in weights):
                if any(w is None for w in weights):
                    raise ImportRejected(f"{label}: en «{name}» hay preguntas con ponderación y otras sin ponderación.")
                errors.append(ow.group_error(f"{label} · preguntas de {name}", weights))
            if ow.to_tenths(weight) > 0 and not group:
                raise ImportRejected(f"{label}: la categoría «{name}» pondera {weight}% pero no tiene preguntas.")
    except ow.WeightError as exc:
        raise ImportRejected(f"{label}: {exc}") from exc
    errors = [e for e in errors if e]
    if errors:
        raise ImportRejected(" ".join(errors))
    return plan


@transaction.atomic
def import_version(area_code, level_code, questions, version, publish=False, *,
                   categories=None, scale=None, scale_note=None):
    """Crea o reconstruye la `version` del cuestionario de Ownership de un puesto."""
    from apps.catalog.models import Area, SeniorityLevel
    from apps.questionnaires.models import (
        Category,
        Question,
        QuestionnaireTemplate,
        ScaleOption,
        Section,
        TemplateCategory,
    )

    T = QuestionnaireTemplate
    shown = f"{area_code}/{level_code or 'sin nivel'}"
    label = f"{shown} v{version}"
    area = Area.objects.get(code=area_code)
    level = SeniorityLevel.objects.get(code=level_code) if level_code else None   # None = posición sin nivel
    siblings = T.objects.filter(kind=T.Kind.OWNERSHIP, area=area, level=level)

    base = siblings.filter(version=1).first()
    if scale is None and base is None:
        # Posición nueva sin v1: hereda la escala y su nota del cuestionario de Ownership vigente más reciente.
        base = (T.objects.filter(kind=T.Kind.OWNERSHIP, status=T.Status.PUBLICADO, scale_options__isnull=False)
                .order_by("-version", "-pk").distinct().first())
        if base is None:
            raise ImportRejected(f"{shown}: no hay ningún cuestionario de Ownership publicado del cual copiar la escala.")

    newer = siblings.filter(version__gt=version, status=T.Status.PUBLICADO).first()
    if newer:
        # Ya hay una versión posterior vigente (p. ej. CD/JR v3): nunca se publica una menor encima.
        return ImportResult(area_code, level_code or "sin nivel", version, 0, f"omitido (v{newer.version} publicada)", [])

    plan = _plan_categories(label, categories, questions)

    template = siblings.filter(version=version).first()
    if template and _has_answers(template):
        raise ImportRejected(
            f"{shown} v{version}: ya tiene respuestas capturadas; no se modifica."
        )
    note = scale_note if scale_note is not None else (base.scale_note if base else "")
    if template is None:
        template = T.objects.create(
            kind=T.Kind.OWNERSHIP, area=area, level=level, version=version,
            status=T.Status.BORRADOR, scale_note=note,
        )
    else:
        template.sections.all().delete()
        template.scale_options.all().delete()
        template.template_categories.all().delete()
        template.scale_note = note
        template.save(update_fields=["scale_note"])

    # Categorías y ponderaciones (spec 008). Los nombres de categorías ya existentes no se pisan.
    sections = {}
    for idx, (code, name, weight, _group) in enumerate(plan):
        category, _ = Category.objects.get_or_create(code=code, defaults={"name": name, "order": idx})
        TemplateCategory.objects.create(
            template=template, category=category, weight_pct=ow.from_tenths(ow.to_tenths(weight)),
        )
        sections[code] = (category, Section.objects.create(
            template=template, order=idx + 1, title=name if len(plan) > 1 else SECTION_TITLE,
        ))
    for code, _name, _weight, group in plan:
        category, section = sections[code]
        Question.objects.bulk_create([
            Question(
                section=section, order=i, title=q["title"], text=q.get("text", ""),
                qtype=Question.Type.SCALE, allow_na=True, is_required=True, category=category,
                weight_pct=None if q.get("weight") is None else ow.from_tenths(ow.to_tenths(q["weight"])),
                **{name: q.get(name, "") for name in Question.CHECKLIST_FIELDS},
            )
            for i, q in enumerate(group, start=1)
        ])

    if scale is not None:
        ScaleOption.objects.bulk_create([
            ScaleOption(
                template=template, value=opt.get("value"), label=opt["label"],
                description=opt.get("description", ""), order=opt.get("order", i),
            )
            for i, opt in enumerate(scale, start=1)
        ])
    else:
        ScaleOption.objects.bulk_create([
            ScaleOption(
                template=template, value=opt.value, label=opt.label,
                description=opt.description, order=opt.order,
            )
            for opt in base.scale_options.filter(question__isnull=True).order_by("order")
        ])

    archived = []
    for stale in siblings.filter(version__gt=version, status=T.Status.BORRADOR):
        if not _has_answers(stale):
            stale.status = T.Status.ARCHIVADO
            stale.save(update_fields=["status"])
            archived.append(f"v{stale.version}")

    if publish and template.status != T.Status.PUBLICADO:
        try:
            questionnaire_editor.publish_template(template)
        except ValidationError as exc:
            raise ImportRejected(f"{label}: " + " ".join(exc.messages)) from exc
    elif template.status == T.Status.PUBLICADO:
        errors = questionnaire_editor.validate_for_publish(template)
        if errors:
            raise ImportRejected(f"{shown} v{version}: " + " ".join(errors))

    template.refresh_from_db()
    return ImportResult(area_code, level_code or "sin nivel", version, len(questions), template.get_status_display(), archived)
