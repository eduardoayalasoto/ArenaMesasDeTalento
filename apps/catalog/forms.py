"""Formularios de administración de catálogos."""

from django import forms

from .models import Project

_INPUT = "input"


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
