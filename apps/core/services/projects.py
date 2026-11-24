"""Índice de proyectos: búsqueda, filtros y datos de entrega para la lista."""

from __future__ import annotations

from datetime import date

from django.db.models import Count, Exists, F, OuterRef, Q

from apps.catalog.models import Project
from apps.catalog.vigencia import evaluable_q, open_period

STATE_CHOICES = (
    ("", "Todos los estados"),
    ("evaluables", "Evaluables en el periodo abierto"),
    ("abiertos", "Abiertos"),
    ("cerrados", "Cerrados"),
    ("registro", "Solo registro (no evaluables)"),
)
DURATION_CHOICES = (
    ("", "Toda duración"),
    ("FINITO", "Con fecha de entrega"),
    ("INDEFINIDO", "Servicio continuo"),
)
FOCUS_CHOICES = (
    ("", "Sin atención especial"),
    ("vencidos", "Entrega vencida"),
    ("sin_validador", "Sin validador"),
    ("sin_equipo", "Sin equipo"),
)
SORT_CHOICES = (
    ("nombre", "Orden: nombre"),
    ("entrega", "Orden: entrega más próxima"),
)


def search_projects(*, q: str = "", state: str = "", duration: str = "", focus: str = "",
                    sort: str = "nombre", today: date | None = None):
    """Filtra por CUALQUIER palabra (nombre, cliente, owner, responsable, validador) y por los filtros."""
    from apps.evaluations.models import OwnershipEvaluation, ValueDeliveryEvaluation

    today = today or date.today()
    period = open_period()
    qs = Project.objects.select_related("owner", "responsable", "validador").annotate(
        members=Count("memberships", distinct=True),
        has_evals=(
            Exists(OwnershipEvaluation.objects.filter(project=OuterRef("pk")))
            | Exists(ValueDeliveryEvaluation.objects.filter(project=OuterRef("pk")))
        ),
    )
    for token in (q or "").split():
        qs = qs.filter(
            Q(name__icontains=token) | Q(client__icontains=token)
            | Q(owner__full_name__icontains=token) | Q(responsable__full_name__icontains=token)
            | Q(validador__full_name__icontains=token)
        )
    if state == "abiertos":
        qs = qs.filter(is_active=True)
    elif state == "cerrados":
        qs = qs.filter(is_active=False)
    elif state == "evaluables":
        qs = qs.filter(evaluable_q(period=period))
    elif state == "registro":
        qs = qs.exclude(evaluable_q(period=period))
    if duration in (Project.Duration.FINITO, Project.Duration.INDEFINIDO):
        qs = qs.filter(duration_type=duration)
    if focus == "vencidos":
        qs = qs.filter(is_active=True, duration_type=Project.Duration.FINITO, target_close__lt=today)
    elif focus == "sin_validador":
        qs = qs.filter(validador__isnull=True)
    elif focus == "sin_equipo":
        qs = qs.filter(members=0)
    if sort == "entrega":
        # Con fecha primero (la más próxima arriba); sin fecha al final.
        return qs.order_by(F("target_close").asc(nulls_last=True), "name")
    return qs.order_by("name")


def delivery_info(project, today: date | None = None) -> dict:
    """Cómo mostrar la entrega estimada: fecha, días restantes y tono (sin tiempo finito → servicio continuo)."""
    today = today or date.today()
    if not project.is_finite:
        return {"kind": "continuous"}
    if not project.target_close:
        return {"kind": "missing"}
    days = (project.target_close - today).days
    if not project.is_active:
        return {"kind": "date", "days": days, "tone": "muted", "text": ""}
    if days < 0:
        n = -days
        return {"kind": "date", "days": days, "tone": "error", "text": f"Vencida hace {n} día{'s' if n != 1 else ''}"}
    if days == 0:
        return {"kind": "date", "days": days, "tone": "warning", "text": "Vence hoy"}
    tone = "warning" if days <= 14 else "muted"
    return {"kind": "date", "days": days, "tone": tone, "text": f"En {days} día{'s' if days != 1 else ''}"}
