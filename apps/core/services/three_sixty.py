"""Evaluación 360 al owner del proyecto (spec 010): informativa, NO alimenta ninguna calificación.

El equipo del proyecto (membresías vigentes en el periodo, sin el owner) califica al owner con el cuestionario
tipo 360 vigente. El owner ve un score por proyecto en vivo (calificación directa con una respuesta, promedio con
varias). La interfaz nunca muestra quién respondió qué: `respondent` se guarda solo como dato interno.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.access import services as access
from apps.access.registry import Scope
from apps.core.services import scoring

TWO_DP = Decimal("0.01")


def active_template():
    from apps.questionnaires.models import QuestionnaireTemplate as T

    return T.objects.filter(kind=T.Kind.THREE_SIXTY, status=T.Status.PUBLICADO).order_by("-version").first()


def open_period():
    from apps.catalog.models import EvaluationPeriod

    return EvaluationPeriod.objects.filter(status=EvaluationPeriod.Status.ABIERTO).first()


def enabled_projects():
    from apps.catalog.models import Project

    return Project.objects.filter(three_sixty_enabled=True, is_active=True).select_related("owner")


def respondents(project, period):
    """Personas que deben contestar: membresías que tocan el periodo, activas, sin el owner."""
    from django.contrib.auth import get_user_model

    members = project.memberships.filter(
        Q(start__isnull=True) | Q(start__lte=period.end_date),
        Q(end__isnull=True) | Q(end__gte=period.start_date),
    ).values_list("user_id", flat=True)
    return get_user_model().objects.filter(
        pk__in=members, is_active=True, deleted_at__isnull=True,
    ).exclude(pk=project.owner_id).order_by("full_name")


def to_answer(user, period):
    """Proyectos con 360 activa donde `user` debe contestar: [{project, response|None}], pendientes primero."""
    from apps.evaluations.models import ThreeSixtyResponse

    if period is None or active_template() is None:
        return []
    rows = []
    for project in enabled_projects().exclude(owner=user):
        if not respondents(project, period).filter(pk=user.pk).exists():
            continue
        response = ThreeSixtyResponse.objects.filter(project=project, period=period, respondent=user).first()
        rows.append({"project": project, "response": response,
                     "pending": response is None or not response.is_submitted})
    return sorted(rows, key=lambda r: (not r["pending"], r["project"].name))


def pending_count(user) -> int:
    period = open_period()
    return sum(1 for r in to_answer(user, period) if r["pending"]) if period else 0


def owned_projects(user):
    return enabled_projects().filter(owner=user).order_by("name")


# --- Responder ---------------------------------------------------------------------------------------

def get_or_start(project, period, user):
    """Borrador (o respuesta) de `user` para el proyecto; lo crea con el cuestionario vigente."""
    from apps.evaluations.models import ThreeSixtyResponse

    if not project.three_sixty_enabled or not project.is_active:
        raise ValidationError("Este proyecto no tiene activa la evaluación 360.")
    if period is None or not period.is_open:
        raise ValidationError("No hay un periodo abierto para contestar.")
    if project.owner_id == user.pk or not respondents(project, period).filter(pk=user.pk).exists():
        raise ValidationError("Esta evaluación no te corresponde.")
    template = active_template()
    if template is None:
        raise ValidationError("Todavía no hay un cuestionario 360 publicado.")
    response, created = ThreeSixtyResponse.objects.get_or_create(
        project=project, period=period, respondent=user,
        defaults={"template": template, "evaluee": project.owner},
    )
    if not created and not response.is_submitted and response.template_id != template.pk:
        # Se publicó una versión nueva mientras era borrador: pasa a la vigente, conservando lo que siga existiendo.
        response.template = template
        response.evaluee = project.owner
        response.save(update_fields=["template", "evaluee", "updated_at"])
        response.answers.exclude(question__section__template=template).delete()
    return response


def questions(template):
    from apps.questionnaires.models import Question

    return list(Question.objects.filter(section__template=template, qtype=Question.Type.SCALE)
                .select_related("section").order_by("section__order", "order"))


@transaction.atomic
def save_answers(response, values: dict, comment: str | None = None):
    """Guarda (borrador) las calificaciones {question_id: 1–4 | None}. Solo mientras no esté enviada."""
    from apps.evaluations.models import ThreeSixtyAnswer

    if response.is_submitted:
        raise ValidationError("Esta evaluación ya se envió y no se puede cambiar.")
    valid = {q.pk for q in questions(response.template)}
    allowed = {o.value for o in response.template.scale_options.filter(question__isnull=True) if o.value is not None}
    for qid, raw in values.items():
        if qid not in valid:
            continue
        if raw in (None, ""):
            ThreeSixtyAnswer.objects.filter(response=response, question_id=qid).delete()
            continue
        value = int(raw)
        if value not in allowed:
            raise ValidationError("Respuesta fuera de la escala.")
        ThreeSixtyAnswer.objects.update_or_create(response=response, question_id=qid, defaults={"value": value})
    if comment is not None:
        response.comment = comment.strip()
    response.save(update_fields=["comment", "updated_at"])


def missing_questions(response):
    answered = set(response.answers.exclude(value__isnull=True).values_list("question_id", flat=True))
    return [q for q in questions(response.template) if q.pk not in answered]


@transaction.atomic
def submit(response) -> list[str]:
    """Envía la respuesta si todo está contestado. Devuelve errores (vacío = enviada)."""
    if response.is_submitted:
        return ["Esta evaluación ya se envió."]
    missing = missing_questions(response)
    if missing:
        return [f"Faltan {len(missing)} pregunta(s) por contestar."]
    now = timezone.now()
    response.status = response.Status.ENVIADA
    response.submitted_at = now
    response.duration_seconds = max(0, int((now - response.started_at).total_seconds()))
    response.evaluee = response.project.owner
    response.save(update_fields=["status", "submitted_at", "duration_seconds", "evaluee", "updated_at"])
    return []


# --- Resultados ---------------------------------------------------------------------------------------

@dataclass
class Dimension:
    title: str
    weight: Decimal
    average: Decimal | None


def _stable_key(response, project, period):
    return hashlib.sha256(f"360-{project.pk}-{period.pk}-{response.pk}".encode()).hexdigest()


def result(project, period) -> dict:
    """Score del owner (informativo): por dimensión e índice ponderado, comentarios sin autor y avance.

    Con una respuesta el índice ES esa calificación; con varias, el promedio. Nada de esto toca FinalScore."""
    from apps.evaluations.models import ThreeSixtyAnswer, ThreeSixtyResponse

    sent = list(ThreeSixtyResponse.objects.filter(project=project, period=period, status=ThreeSixtyResponse.Status.ENVIADA)
                .select_related("template"))
    expected = list(respondents(project, period))
    sent_ids = {r.respondent_id for r in sent}
    answers = ThreeSixtyAnswer.objects.filter(response__in=sent, value__isnull=False).select_related("question__section")
    by_title, order, weights = {}, [], {}
    for a in answers:
        title = a.question.section.title
        by_title.setdefault(title, []).append(a.value)
    latest = max(sent, key=lambda r: r.template.version, default=None)
    if latest:
        for s in latest.template.sections.order_by("order"):
            order.append(s.title)
            weights[s.title] = s.weight_pct or Decimal(0)
    dims = []
    for title in order:
        vals = by_title.get(title)
        avg = (Decimal(sum(vals)) / len(vals)).quantize(TWO_DP, rounding=ROUND_HALF_UP) if vals else None
        dims.append(Dimension(title, Decimal(weights[title]), avg))
    scored = [d for d in dims if d.average is not None and d.weight > 0]
    total_w = sum(d.weight for d in scored)
    index = (sum(d.average * d.weight for d in scored) / total_w).quantize(TWO_DP, rounding=ROUND_HALF_UP) if total_w else None
    comments = [r.comment for r in sorted(sent, key=lambda r: _stable_key(r, project, period)) if r.comment]
    return {
        "dimensions": dims,
        "index": index,
        "band": scoring.interpretation_band(index) if index is not None else "",
        "comments": comments,
        "n_sent": len(sent),
        "n_expected": len(expected),
        "missing": [u for u in expected if u.pk not in sent_ids],
        "has_template": latest is not None,
    }


def owner_summary(project, period) -> dict | None:
    """Mini score para Mesa de Talento y listas: {index, band} o None si aún no hay respuestas."""
    if period is None:
        return None
    r = result(project, period)
    if r["index"] is None:
        return None
    return {"index": r["index"], "band": r["band"], "n_sent": r["n_sent"], "n_expected": r["n_expected"]}


# --- Permisos -----------------------------------------------------------------------------------------

def can_view_results(user, project) -> bool:
    """El owner ve lo suyo; Dirección/Talento según el alcance de `three_sixty.results.view`."""
    if project.owner_id == user.pk and access.has(user, "three_sixty.results.own"):
        return True
    return access.allows_person(user, "three_sixty.results.view", project.owner) and access.has(
        user, "three_sixty.results.view", Scope.AREA)


def sees_followup(user) -> bool:
    """Quién ve avance (X de Y) y quién falta: Talento/Dirección, no el owner."""
    return access.has(user, "three_sixty.results.view", Scope.AREA)


def all_projects_for(user):
    """Proyectos 360 que `user` puede consultar como Talento/Dirección (por alcance)."""
    if not sees_followup(user):
        return enabled_projects().none()
    qs = enabled_projects()
    if access.scope(user, "three_sixty.results.view") >= Scope.TODOS:
        return qs
    return qs.filter(owner__area_id=user.area_id) if user.area_id else qs.none()
