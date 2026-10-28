"""Carga de una versión nueva de los cuestionarios de Ownership desde fixtures YAML (spec 007).

El YAML lo genera `scripts/checklists_2027_to_yaml.py` a partir de los Excel de Talento; aquí
solo se carga. Reglas (contracts/import-command.md):
- llave (OWNERSHIP, área, nivel, versión); escala y nota de escala se copian de la v1;
- si la versión ya existe y algún reactivo tiene respuestas, el puesto se rechaza;
- si existe sin respuestas, se reconstruye; borradores de versión mayor sin respuestas se archivan;
- con `publish`, se publica vía `questionnaire_editor.publish_template` (valida y archiva la anterior).
"""

from dataclasses import dataclass
from pathlib import Path

import yaml
from django.db import transaction

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
    """[(area_code, level_code, questions)] de todos los <AREA>.yaml de la carpeta."""
    entries = []
    for path in sorted(Path(directory).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for tpl in data.get("templates", []):
            entries.append((tpl["area"], tpl["level"], tpl["questions"]))
    return entries


def _has_answers(template):
    from apps.evaluations.models import OwnershipAnswer

    return OwnershipAnswer.objects.filter(question__section__template=template).exists()


@transaction.atomic
def import_version(area_code, level_code, questions, version, publish=False):
    """Crea o reconstruye la `version` del cuestionario de Ownership de un puesto."""
    from apps.catalog.models import Area, SeniorityLevel
    from apps.questionnaires.models import Question, QuestionnaireTemplate, ScaleOption, Section

    T = QuestionnaireTemplate
    area = Area.objects.get(code=area_code)
    level = SeniorityLevel.objects.get(code=level_code)
    siblings = T.objects.filter(kind=T.Kind.OWNERSHIP, area=area, level=level)

    base = siblings.filter(version=1).first()
    if base is None:
        raise ImportRejected(f"{area_code}/{level_code}: no existe la v1 de la cual copiar la escala.")

    template = siblings.filter(version=version).first()
    if template and _has_answers(template):
        raise ImportRejected(
            f"{area_code}/{level_code} v{version}: ya tiene respuestas capturadas; no se modifica."
        )
    if template is None:
        template = T.objects.create(
            kind=T.Kind.OWNERSHIP, area=area, level=level, version=version,
            status=T.Status.BORRADOR, scale_note=base.scale_note,
        )
    else:
        template.sections.all().delete()
        template.scale_options.all().delete()
        template.scale_note = base.scale_note
        template.save(update_fields=["scale_note"])

    section = Section.objects.create(template=template, title=SECTION_TITLE, order=1)
    Question.objects.bulk_create([
        Question(
            section=section, order=i, title=q["title"], text=q.get("text", ""),
            qtype=Question.Type.SCALE, allow_na=True, is_required=True,
            **{name: q.get(name, "") for name in Question.CHECKLIST_FIELDS},
        )
        for i, q in enumerate(questions, start=1)
    ])
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
        questionnaire_editor.publish_template(template)
    elif template.status == T.Status.PUBLICADO:
        errors = questionnaire_editor.validate_for_publish(template)
        if errors:
            raise ImportRejected(f"{area_code}/{level_code} v{version}: " + " ".join(errors))

    template.refresh_from_db()
    return ImportResult(area_code, level_code, version, len(questions), template.get_status_display(), archived)
