"""Vigencia de un proyecto: ¿se le pueden hacer cuestionarios en el periodo abierto?

Regla (una sola fuente de verdad): un proyecto es **evaluable** si está abierto, o si está cerrado pero su
fecha de entrega cae dentro del periodo (semestre) abierto. Un proyecto cerrado fuera de esa ventana ya no
se ofrece para evaluar y queda solo como registro.
"""

from __future__ import annotations

from django.db.models import Q


def open_period():
    from .models import EvaluationPeriod

    return EvaluationPeriod.objects.filter(status=EvaluationPeriod.Status.ABIERTO).first()


def evaluable_q(prefix: str = "", period=None) -> Q:
    """Filtro de proyectos evaluables. `prefix` para relaciones (p. ej. "project__")."""
    q = Q(**{f"{prefix}is_active": True})
    period = period or open_period()
    if period is not None:
        q |= Q(**{f"{prefix}target_close__gte": period.start_date, f"{prefix}target_close__lte": period.end_date})
    return q


def is_evaluable(project, period=None) -> bool:
    if project.is_active:
        return True
    period = period or open_period()
    close = project.target_close
    return bool(period and close and period.start_date <= close <= period.end_date)
