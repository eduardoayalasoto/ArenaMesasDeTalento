"""Planes de capacitación por área y Mi plan (spec 006, US2/US3/US5).

- Un plan por área y año (BORRADOR / PUBLICADO / ARCHIVADO). Sus cursos se agrupan por el
  tipo de aprendizaje del curso del catálogo; cada curso del plan tiene sus propios niveles.
- Mi plan no guarda estado de avance: se deriva de las solicitudes/registros (R8).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Max, Q, QuerySet
from django.utils import timezone

from apps.access import services as access
from apps.access.registry import Scope

MONTHS = ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
          "octubre", "noviembre", "diciembre")


def _m():
    from apps.learning import models

    return models


# --- Planes por área ------------------------------------------------------------------


def can_manage(user) -> bool:
    return access.has(user, "learn.plans.manage")


def visible_plans(user) -> QuerySet:
    """Publicados y archivados para todos; borradores solo para quien gestiona planes (FR-013)."""
    m = _m()
    qs = m.TrainingPlan.objects.select_related("area")
    if not can_manage(user):
        qs = qs.exclude(status=m.TrainingPlan.Status.BORRADOR)
    return qs.order_by("-year", "area__name")


def can_view_plan(user, plan) -> bool:
    return plan.status != plan.Status.BORRADOR or can_manage(user)


def current_plan_for(user, year: int | None = None):
    """Plan publicado del área del usuario para el año (o el más reciente publicado). FR-015."""
    m = _m()
    if not getattr(user, "area_id", None):
        return None
    qs = m.TrainingPlan.objects.filter(area_id=user.area_id, status=m.TrainingPlan.Status.PUBLICADO)
    if year:
        return qs.filter(year=year).first()
    return qs.filter(year=timezone.localdate().year).first() or qs.order_by("-year").first()


def period_label(plan) -> str:
    return f"{MONTHS[plan.start_month].capitalize()} – {MONTHS[plan.end_month]} {plan.year}"


def plan_groups(plan, filters: dict | None = None) -> list[dict]:
    """Cursos del plan agrupados por tipo de aprendizaje, en el orden fijo de `CourseKind`.

    Filtros: `kind`, `level` (id: cursos con ese nivel o sin niveles = "Todos") y `tags`
    (ids, AND). Cada elemento trae `avg_rating` y `completed_count` de Arena Learn.
    """
    m = _m()
    f = filters or {}
    items = (
        m.PlanCourse.objects.filter(plan=plan)
        .select_related("course")
        .prefetch_related("levels", "course__tags")
        .order_by("order", "pk")
    )
    if f.get("kind"):
        items = items.filter(course__kind=f["kind"])
    if f.get("level"):
        items = items.annotate(n_levels=Count("levels")).filter(Q(levels__pk=f["level"]) | Q(n_levels=0)).distinct()
    for tid in f.get("tags") or ():
        items = items.filter(course__tags__pk=tid)
    items = list(items)

    St = m.CourseRequest.Status
    done = Q(requests__status__in=(St.COMPLETADA, St.VALIDADA))
    stats = {
        c["pk"]: c for c in m.CatalogCourse.objects.filter(pk__in=[i.course_id for i in items]).annotate(
            completed_count=Count("requests__user", filter=done, distinct=True),
            avg_rating=Avg("requests__review__rating", filter=done),
        ).values("pk", "completed_count", "avg_rating")
    }
    groups: dict[str, dict] = {}
    for it in items:
        st = stats.get(it.course_id, {})
        it.avg_rating = st.get("avg_rating")
        it.completed_count = st.get("completed_count", 0)
        g = groups.setdefault(it.course.kind, {
            "kind": it.course.kind, "label": it.course.get_kind_display(),
            "note": (plan.type_notes or {}).get(it.course.kind, ""), "items": [],
        })
        g["items"].append(it)
    return sorted(groups.values(), key=lambda g: m.KIND_ORDER.get(g["kind"], 99))


def _require_manage(actor):
    access.require(actor, "learn.plans.manage")


def _validate_plan(plan):
    errors = {}
    if not (1 <= (plan.start_month or 0) <= 12):
        errors["start_month"] = "Mes inválido."
    if not (1 <= (plan.end_month or 0) <= 12):
        errors["end_month"] = "Mes inválido."
    if not errors and plan.end_month < plan.start_month:
        errors["end_month"] = "El mes final no puede ser anterior al inicial."
    if plan.hours_min and plan.hours_max and plan.hours_max < plan.hours_min:
        errors["hours_max"] = "El máximo no puede ser menor que el mínimo."
    if errors:
        raise ValidationError(errors)


def save_plan(plan, actor):
    _require_manage(actor)
    _validate_plan(plan)
    if plan.pk is None:
        plan.created_by = actor
    try:
        with transaction.atomic():
            plan.save()
    except IntegrityError:
        raise ValidationError({"year": "Ya existe un plan para esa área y año."})
    return plan


@transaction.atomic
def set_status(plan, action: str, actor):
    """publish | unpublish | archive | reopen (FR-013/014)."""
    _require_manage(actor)
    m = _m()
    S = m.TrainingPlan.Status
    plan = m.TrainingPlan.objects.select_for_update().get(pk=plan.pk)
    if action in ("publish", "reopen"):
        if not plan.items.exists():
            raise ValidationError("Agrega al menos un curso antes de publicar el plan.")
        plan.status = S.PUBLICADO
        plan.published_at = plan.published_at or timezone.now()
    elif action == "unpublish":
        plan.status = S.BORRADOR
    elif action == "archive":
        plan.status = S.ARCHIVADO
    else:
        raise ValidationError("Acción inválida.")
    plan.save(update_fields=["status", "published_at", "updated_at"])
    return plan


@transaction.atomic
def save_item(plan, actor, *, course, levels=(), note="", item=None):
    """Agrega o edita un curso del plan (un curso aparece una vez por plan)."""
    _require_manage(actor)
    m = _m()
    if item is None:
        if not course.is_active:
            raise ValidationError("Ese curso está archivado en el catálogo.")
        if m.PlanCourse.objects.filter(plan=plan, course=course).exists():
            raise ValidationError("Ese curso ya está en el plan.")
        order = (m.PlanCourse.objects.filter(plan=plan).aggregate(o=Max("order"))["o"] or 0) + 1
        item = m.PlanCourse.objects.create(plan=plan, course=course, order=order, note=note or "")
    else:
        item.note = note or ""
        item.save(update_fields=["note"])
    item.levels.set(levels)
    return item


@transaction.atomic
def move_item(item, direction: str, actor):
    """Sube o baja un curso dentro de su grupo (mismo tipo de aprendizaje)."""
    _require_manage(actor)
    m = _m()
    siblings = list(
        m.PlanCourse.objects.filter(plan_id=item.plan_id, course__kind=item.course.kind).order_by("order", "pk")
    )
    idx = next(i for i, s in enumerate(siblings) if s.pk == item.pk)
    j = idx - 1 if direction == "up" else idx + 1
    if 0 <= j < len(siblings):
        a, b = siblings[idx], siblings[j]
        if a.order == b.order:  # órdenes empatados: renumerar el grupo
            for n, s in enumerate(siblings):
                s.order = n
            a, b = siblings[idx], siblings[j]
        a.order, b.order = b.order, a.order
        m.PlanCourse.objects.bulk_update([s for s in siblings], ["order"])
    return item


def delete_item(item, actor):
    """Quita el curso del plan; Mi plan de quien ya lo eligió no cambia (US2-5)."""
    _require_manage(actor)
    item.delete()


# --- Mi plan (US3) --------------------------------------------------------------------

PENDIENTE, EN_CURSO, COMPLETADO, DESCARTADO = "PENDIENTE", "EN_CURSO", "COMPLETADO", "DESCARTADO"
STATE_LABELS = {PENDIENTE: "Pendiente", EN_CURSO: "En curso", COMPLETADO: "Completado", DESCARTADO: "Descartado"}
STATE_TONES = {PENDIENTE: "neutral", EN_CURSO: "info", COMPLETADO: "success", DESCARTADO: "neutral"}


@dataclass
class ItemState:
    code: str
    detail: str = ""
    request: object = None

    @property
    def label(self) -> str:
        return STATE_LABELS[self.code]

    @property
    def tone(self) -> str:
        return STATE_TONES[self.code]


@dataclass
class MyPlanView:
    plan: object
    rows: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)


def _requests_index(users):
    """Solicitudes/registros de los usuarios, indexados por (usuario, curso) y (usuario, liga)."""
    from apps.core.services.learning_flow import normalize_url

    m = _m()
    by_course, by_url = {}, {}
    reqs = m.CourseRequest.objects.filter(user__in=users).only(
        "pk", "user_id", "catalog_course_id", "url", "status", "current_stage", "created_at",
    ).order_by("created_at", "pk")
    for r in reqs:  # el más reciente gana
        if r.catalog_course_id:
            by_course[(r.user_id, r.catalog_course_id)] = r
        key = normalize_url(r.url)
        if key:
            by_url[(r.user_id, key)] = r
    return by_course, by_url


def _state_for(item, user_id, by_course, by_url) -> ItemState:
    from apps.core.services.learning_flow import normalize_url

    m = _m()
    St = m.CourseRequest.Status
    if item.discarded:
        return ItemState(DESCARTADO)
    req = by_course.get((user_id, item.course_id)) or by_url.get((user_id, normalize_url(item.course.url)))
    if req is not None:
        if req.status in (St.COMPLETADA, St.VALIDADA):
            return ItemState(COMPLETADO, req.status_display, req)
        if req.status in (St.EN_REVISION, St.REQUIERE_AJUSTES, St.AUTORIZADA):
            return ItemState(EN_CURSO, req.status_display, req)
        if req.status == St.BORRADOR:
            return ItemState(PENDIENTE, "Borrador de solicitud", req)
    if item.started_at:
        return ItemState(EN_CURSO, "Empezado sin costo")
    if req is not None:  # rechazada, cancelada o no concluida
        return ItemState(PENDIENTE, f"Último intento: {req.status_display.lower()}", req)
    return ItemState(PENDIENTE)


def item_states(items, user) -> dict:
    by_course, by_url = _requests_index([user])
    return {it.pk: _state_for(it, user.pk, by_course, by_url) for it in items}


def my_plan(user, year: int) -> MyPlanView:
    m = _m()
    plan = m.PersonalPlan.objects.filter(user=user, year=year).first()
    view = MyPlanView(plan=plan, counts={k: 0 for k in STATE_LABELS})
    if plan is None:
        return view
    items = list(plan.items.select_related("course", "source__plan__area").prefetch_related("course__tags"))
    states = item_states(items, user)
    for it in items:
        st = states[it.pk]
        view.rows.append({"item": it, "state": st})
        view.counts[st.code] += 1
    order = {EN_CURSO: 0, PENDIENTE: 1, COMPLETADO: 2, DESCARTADO: 3}
    view.rows.sort(key=lambda r: (order[r["state"].code], m.KIND_ORDER.get(r["item"].course.kind, 99),
                                  r["item"].course.name.lower()))
    return view


def my_plan_course_ids(user, year: int) -> set[int]:
    m = _m()
    return set(m.PersonalPlanItem.objects.filter(personal_plan__user=user, personal_plan__year=year)
               .values_list("course_id", flat=True))


@transaction.atomic
def add_to_my_plan(user, *, course=None, plan_course=None):
    """Agrega un curso a Mi plan del año del plan (o del año en curso si viene del catálogo)."""
    access.require(user, "learn.myplan")
    m = _m()
    if plan_course is not None:
        status, year = m.TrainingPlan.objects.values_list("status", "year").get(pk=plan_course.plan_id)
        if status != m.TrainingPlan.Status.PUBLICADO:
            raise ValidationError("Solo puedes agregar cursos de un plan publicado.")
        course = m.CatalogCourse.objects.get(pk=plan_course.course_id)
    else:
        year = timezone.localdate().year
    if course is None or not course.is_active:
        raise ValidationError("Ese curso no está disponible.")
    personal, _ = m.PersonalPlan.objects.get_or_create(user=user, year=year)
    item, created = m.PersonalPlanItem.objects.get_or_create(
        personal_plan=personal, course=course, defaults={"source": plan_course},
    )
    if not created and item.discarded:
        item.discarded = False
        item.save(update_fields=["discarded"])
    return item


def _own_item(item, user):
    if item.personal_plan.user_id != user.pk:
        raise PermissionDenied("Solo puedes cambiar tu propio plan.")


def start_item(item, user):
    """"Empezar" sin costo: queda En curso sin autorización (FR-019)."""
    _own_item(item, user)
    if item.discarded:
        raise ValidationError("Reactiva el curso antes de empezarlo.")
    if not item.started_at:
        item.started_at = timezone.now()
        item.save(update_fields=["started_at"])
    return item


def discard_item(item, user, discard: bool = True):
    _own_item(item, user)
    item.discarded = discard
    item.save(update_fields=["discarded"])
    return item


def can_view_personal_plan(viewer, owner) -> bool:
    """Dueño (P), su Lead directo (A), área (AR) o todos (T) según la matriz (FR-022)."""
    if viewer.pk == owner.pk:
        return access.has(viewer, "learn.myplan")
    return access.allows_person(
        viewer, "learn.myplan.others", owner, assigned=getattr(owner, "direct_lead_id", None) == viewer.pk,
    ) and access.scope(viewer, "learn.myplan.others") > Scope.PROPIO


# --- Seguimiento (US5) ----------------------------------------------------------------


def tracking_people(viewer):
    """Personas cuyo plan puede ver `viewer` en el tablero (alcance de learn.plans.tracking)."""
    from django.contrib.auth import get_user_model

    User = get_user_model()
    s = access.scope(viewer, "learn.plans.tracking")
    qs = User.objects.filter(is_active=True, deleted_at__isnull=True)
    if s >= Scope.TODOS:
        return qs
    if s >= Scope.AREA and viewer.area_id:
        return qs.filter(Q(area_id=viewer.area_id) | Q(direct_lead=viewer))
    if s >= Scope.ASIGNADO:
        return qs.filter(direct_lead=viewer)
    return qs.none()


def tracking_rows(viewer, filters: dict | None = None) -> dict:
    """Totales por estado y avance por persona (FR-032/033). 3 consultas + memoria."""
    m = _m()
    f = filters or {}
    year = f.get("year") or timezone.localdate().year
    people = tracking_people(viewer).select_related("area")
    if f.get("area"):
        people = people.filter(area_id=f["area"])
    if f.get("person"):
        people = people.filter(pk=f["person"])
    people = list(people.order_by("full_name"))
    items = list(
        m.PersonalPlanItem.objects.filter(personal_plan__user__in=people, personal_plan__year=year)
        .select_related("course", "personal_plan")
    )
    by_course, by_url = _requests_index(people)
    totals = {k: 0 for k in STATE_LABELS}
    per_person: dict[int, dict] = {}
    detail = []
    for it in items:
        uid = it.personal_plan.user_id
        st = _state_for(it, uid, by_course, by_url)
        totals[st.code] += 1
        row = per_person.setdefault(uid, {k: 0 for k in STATE_LABELS})
        row[st.code] += 1
        detail.append((uid, it, st))
    rows = []
    for person in people:
        c = per_person.get(person.pk)
        if not c:
            continue
        active = sum(v for k, v in c.items() if k != DESCARTADO)
        rows.append({
            "person": person, "counts": c, "active": active,
            "progress": round(100 * c[COMPLETADO] / active) if active else 0,
        })
    names = {p.pk: p for p in people}
    return {"year": year, "totals": totals, "rows": rows, "people_with_plan": len(rows),
            "detail": [(names[uid], it, st) for uid, it, st in detail]}


TRACKING_HEADERS = ["Colaborador", "Correo", "Área", "Año", "Curso", "Plataforma", "Tipo de aprendizaje",
                    "Enfoque", "Estado", "Detalle", "Agregado"]


def tracking_export_rows(viewer, filters: dict | None = None) -> list[list]:
    data = tracking_rows(viewer, filters)
    out = []
    for person, it, st in sorted(data["detail"], key=lambda d: (d[0].full_name, d[1].course.name)):
        out.append([
            person.full_name, person.email, person.area.name if person.area else "", data["year"],
            it.course.name, it.course.provider, it.course.get_kind_display(), it.course.get_focus_display(),
            st.label, st.detail, timezone.localtime(it.added_at).replace(tzinfo=None),
        ])
    return out
