"""Bitácora y guardado/borrado auditados de los catálogos (Áreas, Posiciones, Niveles…).

Toda alta, edición y baja de un catálogo pasa por aquí y deja un renglón en `CatalogAuditLog`
(quién, qué, antes → después y cuándo).
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.catalog.models import CatalogAuditLog
from apps.core.services import catalogs


def describe(obj, labels: dict[str, str]) -> dict[str, str]:
    """{etiqueta: texto} de los campos indicados, legible para la bitácora."""
    out = {}
    for field, label in labels.items():
        value = getattr(obj, field)
        if isinstance(value, bool):
            text = "Sí" if value else "No"
        elif value is None or value == "":
            text = "—"
        else:
            text = str(value)
        out[label] = text
    return out


def diff(before: dict[str, str], after: dict[str, str]) -> str:
    return "; ".join(f"{k}: {before.get(k, '—')} → {v}" for k, v in after.items() if before.get(k) != v)


def log(actor, entity: str, obj, action: str, detail: str = "") -> CatalogAuditLog:
    return CatalogAuditLog.objects.create(
        actor=actor, entity=entity, entity_id=getattr(obj, "pk", None), label=str(obj)[:200],
        action=action, detail=detail,
    )


def history(entity: str, pk, limit: int = 8):
    return CatalogAuditLog.objects.filter(entity=entity, entity_id=pk).select_related("actor")[:limit]


@transaction.atomic
def save_form(form, actor, entity: str, labels: dict[str, str]):
    """Guarda un ModelForm ya validado y deja bitácora. Devuelve (objeto, creado, hubo_cambios)."""
    model = form._meta.model
    creating = form.instance.pk is None
    before = None if creating else describe(model.objects.get(pk=form.instance.pk), labels)
    obj = form.save()
    after = describe(obj, labels)
    if creating:
        log(actor, entity, obj, CatalogAuditLog.Action.CREATED, "; ".join(f"{k}: {v}" for k, v in after.items()))
        return obj, True, True
    changes = diff(before, after)
    if changes:
        log(actor, entity, obj, CatalogAuditLog.Action.UPDATED, changes)
    return obj, False, bool(changes)


@transaction.atomic
def delete_with_audit(obj, actor, entity: str, labels: dict[str, str], noun: str):
    """Borra un elemento que nadie usa (si algo lo usa se pide desactivarlo) y lo deja en la bitácora."""
    used = catalogs.usage(obj)
    if used:
        raise ValidationError(f"No se puede borrar {noun}: lo usan {', '.join(used)}. Desactívalo en su lugar.")
    detail = "; ".join(f"{k}: {v}" for k, v in describe(obj, labels).items())
    pk, text = obj.pk, str(obj)
    obj.delete()
    CatalogAuditLog.objects.create(
        actor=actor, entity=entity, entity_id=pk, label=text[:200],
        action=CatalogAuditLog.Action.DELETED, detail=detail,
    )
