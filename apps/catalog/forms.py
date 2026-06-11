"""Formularios de administración de catálogos."""

from django import forms

from .models import EvaluationPeriod, Project

_INPUT = "input"


class PeriodForm(forms.ModelForm):
    """Alta/edición de periodo de evaluación (RN-13)."""

    class Meta:
        model = EvaluationPeriod
        fields = ["name", "start_date", "end_date", "kind", "status"]
        labels = {
            "name": "Nombre",
            "start_date": "Fecha de inicio",
            "end_date": "Fecha de cierre",
            "kind": "Tipo",
            "status": "Estado",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ej. 2026-S2"}),
            "start_date": forms.DateInput(attrs={"class": _INPUT, "type": "date"}, format="%Y-%m-%d"),
            "end_date": forms.DateInput(attrs={"class": _INPUT, "type": "date"}, format="%Y-%m-%d"),
            "kind": forms.Select(attrs={"class": _INPUT}),
            "status": forms.Select(attrs={"class": _INPUT}),
        }


class ProjectForm(forms.ModelForm):
    """Alta/edición de proyecto. El tipo de duración define el criterio de tiempo en Entrega de Valor."""

    class Meta:
        model = Project
        fields = ["name", "client", "lead", "duration_type", "is_active"]
        labels = {
            "name": "Nombre del proyecto",
            "client": "Cliente",
            "lead": "Líder de proyecto",
            "duration_type": "Tipo de duración",
            "is_active": "Activo",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ej. Tablero Comercial"}),
            "client": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ej. Cliente Retail (opcional)"}),
            "lead": forms.Select(attrs={"class": _INPUT}),
            "duration_type": forms.RadioSelect(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["lead"].queryset = self.fields["lead"].queryset.filter(is_active=True)
        self.fields["lead"].empty_label = "— Selecciona un líder —"
