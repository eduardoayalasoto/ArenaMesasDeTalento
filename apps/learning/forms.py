"""Formularios de Arena Learn. Validan entrada; las reglas de negocio están en learning_flow."""

from django import forms
from django.contrib.auth import get_user_model

from apps.catalog.models import Area, SeniorityLevel

from .models import CatalogCourse, CourseEvidence, CourseRequest, CourseReview, LearningSettings

User = get_user_model()

INPUT = {"class": "input"}
TEXTAREA = {"class": "input", "rows": 3}
DATE = {"class": "input", "type": "date"}


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


class RequestForm(forms.Form):
    """Datos de la solicitud (FR-002). Con curso de catálogo, los datos del curso se precargan."""

    name = forms.CharField(label="Nombre del curso", max_length=160, required=False,
                           widget=forms.TextInput(attrs=INPUT))
    provider = forms.CharField(label="Proveedor / plataforma", max_length=120, required=False,
                               widget=forms.TextInput(attrs={**INPUT, "placeholder": "Coursera, Udemy, DataCamp…"}))
    url = forms.URLField(label="Liga del curso", required=False,
                         widget=forms.URLInput(attrs={**INPUT, "placeholder": "https://"}))
    kind = forms.ChoiceField(label="Tipo", choices=CourseRequest._meta.get_field("kind").choices,
                             widget=forms.Select(attrs=INPUT))
    duration_hours = forms.IntegerField(label="Duración estimada (horas)", required=False, min_value=1,
                                        widget=forms.NumberInput(attrs=INPUT))
    pillar = forms.ChoiceField(label="Pilar que fortalece", required=False,
                               choices=CourseRequest._meta.get_field("pillar").choices,
                               widget=forms.Select(attrs=INPUT))
    tags = forms.CharField(label="Etiquetas temáticas", max_length=200, required=False,
                           widget=forms.TextInput(attrs={**INPUT, "placeholder": "power bi, mlops, liderazgo"}))
    estimated_cost = forms.DecimalField(label="Costo", required=False, min_value=0, max_digits=10,
                                        decimal_places=0,
                                        error_messages={"max_decimal_places": "Captura el costo sin decimales."}, widget=forms.NumberInput(attrs={**INPUT, "step": "1"}))
    currency = forms.ChoiceField(label="Moneda", choices=CourseRequest._meta.get_field("currency").choices,
                                 widget=forms.Select(attrs=INPUT))
    start_date_planned = forms.DateField(label="Inicio tentativo", required=False, widget=forms.DateInput(attrs=DATE))
    end_date_planned = forms.DateField(label="Fin tentativo", required=False, widget=forms.DateInput(attrs=DATE))
    justification = forms.CharField(
        label="Justificación", required=False,
        widget=forms.Textarea(attrs={**TEXTAREA, "rows": 4, "placeholder":
            "¿Qué problema resuelve? ¿Cómo se relaciona con tu rol y tus proyectos? ¿Qué quieres desarrollar?"}),
    )
    payment_mode = forms.ChoiceField(label="Modalidad de pago propuesta", required=False,
                                     choices=CourseRequest._meta.get_field("payment_mode").choices,
                                     widget=forms.Select(attrs=INPUT))

    def __init__(self, *args, catalog_course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.catalog_course = catalog_course
        if catalog_course is not None:
            for f in ("name", "provider", "url", "kind", "duration_hours", "pillar", "tags", "currency"):
                self.fields[f].disabled = True
                self.fields[f].initial = getattr(catalog_course, f)
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
        return {f: getattr(req, f) for f in (
            "name", "provider", "url", "kind", "duration_hours", "pillar", "tags", "estimated_cost",
            "currency", "start_date_planned", "end_date_planned", "justification", "payment_mode",
        )}


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
        widget=forms.Select(attrs=INPUT),
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
        queryset=User.objects.filter(is_active=True, deleted_at__isnull=True).order_by("full_name"),
        widget=forms.Select(attrs=INPUT),
    )
    comment = forms.CharField(label="Motivo", widget=forms.Textarea(attrs={**TEXTAREA, "rows": 2}))


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
            "payment_mode": forms.Select(attrs=INPUT),
            "payment_status": forms.Select(attrs=INPUT),
            "final_cost": forms.NumberInput(attrs={**INPUT, "step": "1", "min": "0"}),
            "receipt_type": forms.Select(attrs=INPUT),
        }


class CatalogCourseForm(WholeCostMixin, forms.ModelForm):
    cost_fields = ("reference_cost",)

    class Meta:
        model = CatalogCourse
        fields = ["name", "provider", "url", "kind", "reference_cost", "currency", "duration_hours",
                  "pillar", "tags", "areas", "levels", "description"]
        widgets = {
            "name": forms.TextInput(attrs=INPUT),
            "provider": forms.TextInput(attrs=INPUT),
            "url": forms.URLInput(attrs=INPUT),
            "kind": forms.Select(attrs=INPUT),
            "reference_cost": forms.NumberInput(attrs={**INPUT, "step": "1", "min": "0"}),
            "currency": forms.Select(attrs=INPUT),
            "duration_hours": forms.NumberInput(attrs=INPUT),
            "pillar": forms.Select(attrs=INPUT),
            "tags": forms.TextInput(attrs=INPUT),
            "areas": forms.CheckboxSelectMultiple,
            "levels": forms.CheckboxSelectMultiple,
            "description": forms.Textarea(attrs=TEXTAREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["areas"].queryset = Area.objects.filter(is_active=True)
        self._whole_costs()


class SettingsForm(forms.ModelForm):
    class Meta:
        model = LearningSettings
        fields = ["fiscal_instructions"]
        widgets = {"fiscal_instructions": forms.Textarea(attrs={**TEXTAREA, "rows": 8})}
