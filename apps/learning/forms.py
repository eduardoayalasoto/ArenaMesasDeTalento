"""Formularios de Arena Learn. Validan entrada; las reglas de negocio están en learning_flow."""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.urls import reverse

from apps.catalog.models import Area, SeniorityLevel

from .models import (
    CatalogCourse,
    CourseEvidence,
    CourseKind,
    CourseRequest,
    CourseReview,
    LearningSettings,
    Tag,
    TrainingPlan,
)

User = get_user_model()

INPUT = {"class": "input w-full"}
TEXTAREA = {"class": "textarea w-full", "rows": 3}
DATE = {"class": "input w-full", "type": "date"}
SELECT = {"class": "select w-full"}


def _whole(value):
    """3500.00 → 3500 para mostrar el costo sin decimales en el campo."""
    try:
        return int(value) if value is not None and value == int(value) else value
    except (TypeError, ValueError):
        return value


class WholeCostMixin:
    """Muestra los campos de costo sin decimales (el modelo conserva 2 decimales)."""

    cost_fields = ()

    def _whole_costs(self):
        for name in self.cost_fields:
            if name in self.fields:
                if name in self.initial:
                    self.initial[name] = _whole(self.initial[name])
                self.fields[name].initial = _whole(self.fields[name].initial)
                self.fields[name].decimal_places = 0
                self.fields[name].error_messages["max_decimal_places"] = "Captura el costo sin decimales."
                self.fields[name].widget.attrs["step"] = "1"


class TagInputWidget(forms.Widget):
    """Campo de etiquetas autocompletable (componente `_tag_input.html`, spec 006 R2).

    Cada ficha viaja como un `<input type="hidden" name="<campo>">`; las sugerencias
    llegan por htmx desde `learning:tag_suggest`.
    """

    def value_from_datadict(self, data, files, name):
        if hasattr(data, "getlist"):
            return data.getlist(name)
        value = data.get(name)
        return value if isinstance(value, (list, tuple)) else ([value] if value else [])

    def value_omitted_from_data(self, data, files, name):
        return False  # sin fichas = lista vacía, no "campo omitido"

    def render(self, name, value, attrs=None, renderer=None):
        names = [getattr(v, "name", v) for v in (value or [])]
        return render_to_string("components/_tag_input.html", {
            "name": name,
            "values": [n for n in names if n],
            "input_id": (attrs or {}).get("id") or f"id_{name}",
            "data_id": f"{(attrs or {}).get('id') or f'id_{name}'}-data",
            "suggest_url": reverse("learning:tag_suggest"),
            "disabled": bool((attrs or {}).get("disabled")),
        })


class TagNamesField(forms.Field):
    """Lista de nombres de etiqueta, limpia y sin duplicados (FR-001/003)."""

    widget = TagInputWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("label", "Etiquetas")
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        from apps.core.services.learning_tags import clean_names

        if not value:
            return []
        if isinstance(value, str):
            value = value.split(",")
        try:
            return clean_names(value)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages)

    def prepare_value(self, value):
        if value is None:
            return []
        if hasattr(value, "all"):
            return [t.name for t in value.all()]
        return list(value)


class RequestForm(forms.Form):
    """Datos de la solicitud (FR-002). Con curso de catálogo, los datos del curso se precargan."""

    name = forms.CharField(label="Nombre del curso", max_length=160, required=False,
                           widget=forms.TextInput(attrs=INPUT))
    provider = forms.CharField(label="Proveedor / plataforma", max_length=120, required=False,
                               widget=forms.TextInput(attrs={**INPUT, "placeholder": "Coursera, Udemy, DataCamp…"}))
    url = forms.URLField(label="Liga del curso", required=False,
                         widget=forms.URLInput(attrs={**INPUT, "placeholder": "https://"}))
    kind = forms.ChoiceField(label="Tipo de aprendizaje", choices=CourseRequest._meta.get_field("kind").choices,
                             widget=forms.Select(attrs=SELECT))
    duration_hours = forms.DecimalField(label="Duración estimada (horas)", required=False, min_value=0.5,
                                        max_digits=5, decimal_places=1,
                                        widget=forms.NumberInput(attrs={**INPUT, "step": "0.5"}))
    pillar = forms.ChoiceField(label="Pilar que fortalece", required=False,
                               choices=CourseRequest._meta.get_field("pillar").choices,
                               widget=forms.Select(attrs=SELECT))
    tags = TagNamesField(label="Etiquetas temáticas",
                         help_text="Escribe y elige una existente, o presiona Enter para crear una nueva.")
    estimated_cost = forms.DecimalField(label="Costo", required=False, min_value=0, max_digits=10,
                                        decimal_places=0,
                                        error_messages={"max_decimal_places": "Captura el costo sin decimales."}, widget=forms.NumberInput(attrs={**INPUT, "step": "1"}))
    currency = forms.ChoiceField(label="Moneda", choices=CourseRequest._meta.get_field("currency").choices,
                                 widget=forms.Select(attrs=SELECT))
    start_date_planned = forms.DateField(label="Inicio tentativo", required=False, widget=forms.DateInput(attrs=DATE))
    end_date_planned = forms.DateField(label="Fin tentativo", required=False, widget=forms.DateInput(attrs=DATE))
    justification = forms.CharField(
        label="Justificación", required=False,
        widget=forms.Textarea(attrs={**TEXTAREA, "rows": 4, "placeholder":
            "¿Qué problema resuelve? ¿Cómo se relaciona con tu rol y tus proyectos? ¿Qué quieres desarrollar?"}),
    )
    payment_mode = forms.ChoiceField(label="Modalidad de pago propuesta", required=False,
                                     choices=CourseRequest._meta.get_field("payment_mode").choices,
                                     widget=forms.Select(attrs=SELECT))

    def __init__(self, *args, catalog_course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.catalog_course = catalog_course
        self.fields["url"].help_text = "Copia la liga de la página del curso: lo identifica y evita pedirlo dos veces."
        if catalog_course is not None:
            for f in ("name", "provider", "url", "kind", "duration_hours", "currency"):
                self.fields[f].disabled = True
                self.fields[f].initial = getattr(catalog_course, f)
            # Las etiquetas del curso se precargan, pero el colaborador puede ajustarlas (FR-004).
            if "tags" not in self.initial:
                self.initial["tags"] = [t.name for t in catalog_course.tags.all()]
            if catalog_course.reference_cost is not None:
                self.fields["estimated_cost"].initial = _whole(catalog_course.reference_cost)
        if "estimated_cost" in self.initial:
            self.initial["estimated_cost"] = _whole(self.initial["estimated_cost"])

    def clean(self):
        data = super().clean()
        start, end = data.get("start_date_planned"), data.get("end_date_planned")
        if start and end and end < start:
            self.add_error("end_date_planned", "La fecha de fin no puede ser anterior a la de inicio.")
        return data

    def service_data(self) -> dict:
        d = dict(self.cleaned_data)
        d.pop("payment_mode", None)
        return d

    @staticmethod
    def initial_from(req: CourseRequest) -> dict:
        data = {f: getattr(req, f) for f in (
            "name", "provider", "url", "kind", "duration_hours", "pillar", "estimated_cost",
            "currency", "start_date_planned", "end_date_planned", "justification", "payment_mode",
        )}
        data["tags"] = [t.name for t in req.tags.all()] if req.pk else []
        return data


class DirectCourseForm(RequestForm):
    """Registro directo / histórico: sin justificación ni autorización."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("justification")
        self.fields.pop("payment_mode")
        if self.catalog_course is None:
            self.fields["name"].required = True
            self.fields["provider"].required = True


class HistoricCourseForm(DirectCourseForm):
    person = forms.ModelChoiceField(
        label="Colaborador", queryset=User.objects.filter(deleted_at__isnull=True).order_by("full_name"),
        widget=forms.Select(attrs=SELECT),
    )


class ReviewForm(forms.ModelForm):
    class Meta:
        model = CourseReview
        fields = ["rating", "opinion", "recommends", "recommend_why",
                  "audience_areas", "audience_levels", "audience_notes", "learnings"]
        widgets = {
            "rating": forms.RadioSelect,
            "opinion": forms.Textarea(attrs={**TEXTAREA, "placeholder": "¿Qué te pareció el curso?"}),
            "recommends": forms.RadioSelect,
            "recommend_why": forms.Textarea(attrs=TEXTAREA),
            "audience_areas": forms.CheckboxSelectMultiple,
            "audience_levels": forms.CheckboxSelectMultiple,
            "audience_notes": forms.Textarea(attrs={**TEXTAREA, "rows": 2,
                                                   "placeholder": "p. ej. quien empiece con Spark"}),
            "learnings": forms.Textarea(attrs={**TEXTAREA, "rows": 4,
                                              "placeholder": "¿Qué aprendiste y cómo lo aplicaste en tu trabajo?"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sin la opción vacía "---------" que Django agrega a los radios sin valor por defecto.
        self.fields["rating"].choices = [(i, str(i)) for i in range(1, 6)]
        self.fields["recommends"].choices = CourseReview.Recommends.choices
        self.fields["audience_areas"].queryset = Area.objects.filter(is_active=True)
        self.fields["audience_levels"].queryset = SeniorityLevel.objects.all()
        self.fields["audience_areas"].required = False
        self.fields["audience_levels"].required = False

    def service_data(self) -> dict:
        return dict(self.cleaned_data)


class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class EvidenceFilesField(forms.FileField):
    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, (list, tuple)):
            return [single(d, initial) for d in data if d]
        return [single(data, initial)] if data else []


ACCEPT = "application/pdf,image/png,image/jpeg,image/webp"


class EvidenceUploadForm(forms.Form):
    files = EvidenceFilesField(
        label="Certificado, constancia o captura", required=False,
        widget=MultiFileInput(attrs={"accept": ACCEPT, "class": "sr-only"}),
        help_text="PDF, PNG, JPG o WEBP · máximo 4 MB por archivo.",
    )


class SingleEvidenceForm(forms.Form):
    file = forms.FileField(label="Archivo", widget=forms.ClearableFileInput(attrs={"accept": ACCEPT}))
    kind = forms.ChoiceField(choices=CourseEvidence.Kind.choices, initial=CourseEvidence.Kind.CERTIFICADO,
                             widget=forms.HiddenInput)


class DecisionForm(forms.Form):
    action = forms.ChoiceField(choices=[("approve", "Aprobar"), ("return", "Regresar"), ("reject", "Rechazar")])
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=TEXTAREA))

    def clean(self):
        data = super().clean()
        if data.get("action") in ("return", "reject") and not (data.get("comment") or "").strip():
            self.add_error("comment", "El comentario es obligatorio para regresar o rechazar.")
        return data


class CommentForm(forms.Form):
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs=TEXTAREA))


class ReasonForm(forms.Form):
    reason = forms.CharField(label="Motivo", widget=forms.Textarea(attrs=TEXTAREA))


class ReassignForm(forms.Form):
    approver = forms.ModelChoiceField(
        label="Nuevo aprobador",
        queryset=User.objects.none(),
        widget=forms.Select(attrs=SELECT),
    )
    comment = forms.CharField(label="Motivo", widget=forms.Textarea(attrs={**TEXTAREA, "rows": 2}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo quien tiene "Asignable como aprobador reasignado" (spec 005, FR-020).
        from apps.access.services import assignable_users

        self.fields["approver"].queryset = assignable_users("assign.learn_approver").order_by("full_name")


class EvidenceValidationForm(forms.Form):
    action = forms.ChoiceField(choices=[("validate", "Validar"), ("return", "Regresar")])
    comment = forms.CharField(required=False, widget=forms.Textarea(attrs={**TEXTAREA, "rows": 2}))


class PaymentForm(WholeCostMixin, forms.ModelForm):
    cost_fields = ("final_cost",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._whole_costs()

    class Meta:
        model = CourseRequest
        fields = ["payment_mode", "payment_status", "final_cost", "receipt_type"]
        widgets = {
            "payment_mode": forms.Select(attrs=SELECT),
            "payment_status": forms.Select(attrs=SELECT),
            "final_cost": forms.NumberInput(attrs={**INPUT, "step": "1", "min": "0"}),
            "receipt_type": forms.Select(attrs=SELECT),
        }


class CatalogCourseForm(WholeCostMixin, forms.ModelForm):
    """Datos propios de la plataforma del curso (spec 006: sin niveles, pilar ni áreas)."""

    cost_fields = ("reference_cost",)
    tag_names = TagNamesField(label="Etiquetas")

    class Meta:
        model = CatalogCourse
        fields = ["name", "provider", "url", "kind", "focus", "reference_cost", "currency", "duration_hours",
                  "description"]
        widgets = {
            "name": forms.TextInput(attrs=INPUT),
            "provider": forms.TextInput(attrs=INPUT),
            "url": forms.URLInput(attrs=INPUT),
            "kind": forms.Select(attrs=SELECT),
            "focus": forms.Select(attrs=SELECT),
            "reference_cost": forms.NumberInput(attrs={**INPUT, "step": "1", "min": "0"}),
            "currency": forms.Select(attrs=SELECT),
            "duration_hours": forms.NumberInput(attrs={**INPUT, "step": "0.5", "min": "0.5"}),
            "description": forms.Textarea(attrs=TEXTAREA),
        }
        help_texts = {
            "kind": "Qué clase de aprendizaje es.",
            "focus": "Horizontal: da amplitud en varios temas. Vertical: profundiza en uno.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial.setdefault("tag_names", [t.name for t in self.instance.tags.all()])
        self._whole_costs()


class SettingsForm(forms.ModelForm):
    class Meta:
        model = LearningSettings
        fields = ["fiscal_instructions"]
        widgets = {"fiscal_instructions": forms.Textarea(attrs={**TEXTAREA, "rows": 8})}


class TagRenameForm(forms.Form):
    name = forms.CharField(label="Nombre", max_length=60, widget=forms.TextInput(attrs={**INPUT, "class": "input input-sm w-full"}))


class TagMergeForm(forms.Form):
    target = forms.ModelChoiceField(label="Fusionar en", queryset=None, widget=forms.Select(attrs=SELECT))

    def __init__(self, *args, source=None, **kwargs):
        super().__init__(*args, **kwargs)
        qs = Tag.objects.filter(is_active=True)
        if source is not None:
            qs = qs.exclude(pk=source.pk)
        self.fields["target"].queryset = qs.order_by("name")


# --- Planes de capacitación (spec 006, US2) -----------------------------------------------

MONTH_CHOICES = [(i, m.capitalize()) for i, m in enumerate(
    ("", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
     "octubre", "noviembre", "diciembre")) if i]


class PlanForm(forms.ModelForm):
    """Cabecera del plan + un texto opcional por tipo de aprendizaje (`type_notes`)."""

    class Meta:
        model = TrainingPlan
        fields = ["area", "year", "title", "start_month", "end_month", "hours_min", "hours_max", "intro"]
        widgets = {
            "area": forms.Select(attrs=SELECT),
            "year": forms.NumberInput(attrs={**INPUT, "min": "2024", "max": "2100"}),
            "title": forms.TextInput(attrs=INPUT),
            "start_month": forms.Select(attrs=SELECT, choices=MONTH_CHOICES),
            "end_month": forms.Select(attrs=SELECT, choices=MONTH_CHOICES),
            "hours_min": forms.NumberInput(attrs={**INPUT, "min": "1"}),
            "hours_max": forms.NumberInput(attrs={**INPUT, "min": "1"}),
            "intro": forms.Textarea(attrs={**TEXTAREA, "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["area"].queryset = Area.objects.filter(is_active=True)
        notes = (self.instance.type_notes or {}) if self.instance.pk else {}
        self.kind_fields = []
        for value, label in CourseKind.choices:
            name = f"note_{value}"
            self.fields[name] = forms.CharField(
                label=f"Texto para «{label}»", required=False,
                widget=forms.Textarea(attrs={**TEXTAREA, "rows": 2}), initial=notes.get(value, ""),
            )
            self.kind_fields.append(name)
        if self.instance.pk:  # área y año identifican el plan: no se cambian
            self.fields["area"].disabled = True
            self.fields["year"].disabled = True

    def type_notes(self) -> dict:
        return {v: self.cleaned_data[f"note_{v}"].strip() for v in CourseKind.values
                if self.cleaned_data.get(f"note_{v}", "").strip()}


class PlanItemForm(forms.Form):
    course = forms.ModelChoiceField(label="Curso del catálogo", queryset=CatalogCourse.objects.none(),
                                    widget=forms.Select(attrs=SELECT), required=False)
    levels = forms.ModelMultipleChoiceField(label="Niveles recomendados", queryset=SeniorityLevel.objects.all(),
                                            required=False,
                                            widget=forms.CheckboxSelectMultiple(attrs={"class": "checkbox checkbox-sm"}),
                                            help_text="Sin niveles = «Todos los niveles».")
    note = forms.CharField(label="Nota", max_length=200, required=False, widget=forms.TextInput(attrs=INPUT))

    def __init__(self, *args, plan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["levels"].queryset = SeniorityLevel.objects.order_by("order")
        if plan is not None:
            self.fields["course"].queryset = CatalogCourse.objects.filter(is_active=True).exclude(
                plan_items__plan=plan).order_by("name")


class MyPlanAddForm(forms.Form):
    plan_course = forms.IntegerField(required=False)
    course = forms.IntegerField(required=False)

    def clean(self):
        data = super().clean()
        if not data.get("plan_course") and not data.get("course"):
            raise forms.ValidationError("Elige un curso.")
        return data
