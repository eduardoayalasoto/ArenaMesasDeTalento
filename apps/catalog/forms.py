"""Formularios de administración de catálogos."""

from django import forms

from .models import EvaluationPeriod, Project

_INPUT = "input w-full"
_SELECT = "select w-full"


class PeriodForm(forms.ModelForm):
    """Alta/edición de periodo de evaluación (RN-13)."""

    class Meta:
        model = EvaluationPeriod
        # `status` NO se expone aquí: sus transiciones solo pasan por
        # `period_lifecycle` (acciones Abrir/Cerrar en period_admin), nunca
        # por este formulario de alta/edición (spec 002-ciclo-vida-periodos, FR-002/FR-005).
        fields = ["name", "start_date", "end_date", "kind"]
        labels = {
            "name": "Nombre",
            "start_date": "Fecha de inicio",
            "end_date": "Fecha de cierre",
            "kind": "Tipo",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ej. 2026-S2"}),
            "start_date": forms.DateInput(attrs={"class": _INPUT, "type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"class": _INPUT, "type": "date"}, format="%Y-%m-%d"),
            "kind": forms.Select(attrs={"class": _SELECT}),
        }


class ProjectForm(forms.ModelForm):
    """Alta/edición de proyecto. El tipo de duración define el criterio de tiempo en Entrega de Valor."""

    class Meta:
        model = Project
        fields = [
            "name", "client", "owner", "responsable", "validador", "suggested_evaluator",
            "duration_type", "kickoff", "target_close", "is_active",
        ]
        labels = {
            "name": "Nombre del proyecto",
            "client": "Cliente",
            "owner": "Owner",
            "responsable": "Responsable (evaluará la Entrega de Valor)",
            "validador": "Validador de Entrega de Valor",
            "suggested_evaluator": "Evaluador sugerido de Ownership",
            "duration_type": "Tipo de duración",
            "kickoff": "Kick-off",
            "target_close": "Fecha estimada de entrega",
            "is_active": "Proyecto abierto",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ej. Tablero Comercial"}),
            "client": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ej. Cliente Retail (opcional)"}),
            "owner": forms.Select(attrs={"class": _SELECT}),
            "responsable": forms.Select(attrs={"class": _SELECT}),
            "validador": forms.Select(attrs={"class": _SELECT}),
            "suggested_evaluator": forms.Select(attrs={"class": _SELECT}),
            "duration_type": forms.RadioSelect(),
            "kickoff": forms.DateInput(attrs={"class": _INPUT, "type": "date"}, format="%Y-%m-%d"),
            "target_close": forms.DateInput(attrs={"class": _INPUT, "type": "date"}, format="%Y-%m-%d"),
            "is_active": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo quien tiene "Asignable como rol de proyecto" en su perfil (spec 005, FR-020).
        from apps.access.services import assignable_users

        active = assignable_users("assign.project_role").order_by("full_name")
        self.fields["owner"].queryset = active
        self.fields["owner"].empty_label = "— Selecciona un Owner —"
        self.fields["responsable"].queryset = active
        self.fields["responsable"].empty_label = "— Selecciona un Responsable —"
        self.fields["validador"].queryset = active
        self.fields["validador"].required = False
        self.fields["validador"].empty_label = "— Selecciona un Validador —"
        self.fields["suggested_evaluator"].queryset = assignable_users("assign.ownership_evaluator").order_by("full_name")
        self.fields["suggested_evaluator"].required = False
        self.fields["suggested_evaluator"].empty_label = "— Sin sugerido (se usa el Owner) —"
        self.fields["suggested_evaluator"].help_text = "Se preselecciona al iniciar la evaluación; cada persona puede cambiarlo."


class AreaForm(forms.Form):
    """Alta y edición de un área (spec 009). Sin `area` crea una nueva."""

    area = forms.IntegerField(widget=forms.HiddenInput, required=False)
    code = forms.CharField(label="Clave", max_length=8)
    name = forms.CharField(label="Nombre", max_length=80)
    director = forms.IntegerField(required=False)
    is_active = forms.BooleanField(label="Activa", required=False)

    def clean_code(self):
        code = self.cleaned_data["code"].strip()
        if not code:
            raise forms.ValidationError("La clave del área es obligatoria.")
        return code

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("El nombre del área es obligatorio.")
        return name


class AreaDirectorForm(forms.Form):
    """Director del área (Arena Learn, spec 004): aprueba el nivel Dirección de solicitudes de curso."""

    area = forms.IntegerField(widget=forms.HiddenInput)
    director = forms.IntegerField(required=False)


class PositionForm(forms.Form):
    """Nombre y estado de un puesto (área × nivel). Crea el puesto si aún no existe."""

    position = forms.IntegerField(widget=forms.HiddenInput, required=False)
    area = forms.IntegerField(label="Posición")
    level = forms.IntegerField(label="Nivel (opcional)", required=False)
    name = forms.CharField(label="Nombre visible", max_length=60)
    is_active = forms.BooleanField(label="Activo", required=False)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("El nombre de la posición es obligatorio.")
        return name


class CategoryForm(forms.Form):
    """Alta y edición de una categoría de pregunta (spec 008)."""

    category = forms.IntegerField(widget=forms.HiddenInput, required=False)
    name = forms.CharField(label="Nombre", max_length=80)
    order = forms.IntegerField(label="Orden", min_value=0, max_value=999, initial=1)
    is_active = forms.BooleanField(label="Activa", required=False)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("El nombre de la categoría es obligatorio.")
        return name


class PillarWeightForm(forms.Form):
    """Ponderaciones en % de los 3 pilares de una posición (spec 009). La suma la valida el servicio."""

    position = forms.IntegerField(widget=forms.HiddenInput)
    w_ownership = forms.DecimalField(label="Ownership", min_value=0, max_value=100, decimal_places=1)
    w_value_delivery = forms.DecimalField(label="Entrega de Valor", min_value=0, max_value=100, decimal_places=1)
    w_arena_impact = forms.DecimalField(label="Impacto Arena", min_value=0, max_value=100, decimal_places=1)


# --- Áreas, Posiciones y Niveles (vocabulario de la interfaz: Área → Posición → Nivel) ------------------

def _director_queryset():
    from apps.access.services import assignable_users

    return assignable_users("assign.area_director").order_by("full_name")


class _CodeMixin:
    def clean_code(self):
        code = self.cleaned_data["code"].strip().upper()
        if not code:
            raise forms.ValidationError("La clave es obligatoria.")
        return code

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("El nombre es obligatorio.")
        return name


class DepartmentForm(_CodeMixin, forms.ModelForm):
    """Área de la organización (Analítica, Consultoría): clave, nombre, orden, Director y estado."""

    class Meta:
        from .models import Department

        model = Department
        fields = ["name", "code", "order", "director", "is_active"]
        labels = {"name": "Nombre", "code": "Clave", "order": "Orden", "director": "Director del área",
                  "is_active": "Área activa"}
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ej. Analítica"}),
            "code": forms.TextInput(attrs={"class": _INPUT, "maxlength": 8, "placeholder": "Ej. ANALIT"}),
            "order": forms.NumberInput(attrs={"class": _INPUT, "min": 1}),
            "director": forms.Select(attrs={"class": _SELECT}),
            "is_active": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }
        help_texts = {"director": "Aprueba el nivel Dirección de las solicitudes de curso de Arena Learn."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["director"].queryset = _director_queryset()
        self.fields["director"].required = False
        self.fields["director"].empty_label = "— Cualquier Director —"


class AreaPositionForm(_CodeMixin, forms.ModelForm):
    """Posición (puesto) de un Área: Ingeniero de Datos, Analista, Gerente… (modelo `Area` en el código)."""

    class Meta:
        from .models import Area

        model = Area
        fields = ["name", "code", "department", "director", "is_active"]
        labels = {"name": "Nombre de la posición", "code": "Clave", "department": "Área",
                  "director": "Director (opcional)", "is_active": "Posición activa"}
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ej. Ingeniero de Datos"}),
            "code": forms.TextInput(attrs={"class": _INPUT, "maxlength": 8}),
            "department": forms.Select(attrs={"class": _SELECT}),
            "director": forms.Select(attrs={"class": _SELECT}),
            "is_active": forms.CheckboxInput(attrs={"class": "checkbox"}),
        }
        help_texts = {"director": "Solo si esta posición tiene un Director propio; si no, aplica el del Área."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Department

        self.fields["department"].queryset = Department.objects.filter(is_active=True) | Department.objects.filter(
            pk=getattr(self.instance, "department_id", None))
        self.fields["department"].empty_label = "— Elige el área —"
        self.fields["department"].required = True
        self.fields["director"].queryset = _director_queryset()
        self.fields["director"].required = False
        self.fields["director"].empty_label = "— Director del Área —"


class LevelForm(_CodeMixin, forms.ModelForm):
    """Nivel (Jr, Mid, Snr, Lead…): catálogo abierto; cada persona o cuestionario lo usa solo si quiere."""

    class Meta:
        from .models import SeniorityLevel

        model = SeniorityLevel
        fields = ["name", "code", "order"]
        labels = {"name": "Nombre", "code": "Clave", "order": "Orden"}
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ej. Senior"}),
            "code": forms.TextInput(attrs={"class": _INPUT, "maxlength": 8, "placeholder": "Ej. SNR"}),
            "order": forms.NumberInput(attrs={"class": _INPUT, "min": 1}),
        }
        help_texts = {"order": "Define el orden en listas y la escalera (1 = el más junior)."}
