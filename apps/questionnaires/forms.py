"""Formularios del editor de cuestionarios."""

from django import forms
from django.core.exceptions import ValidationError

from apps.core.services import ownership_weights as ow

from .models import Category, Question, QuestionnaireTemplate

_INPUT = "input w-full"
_TEXTAREA = "textarea w-full"


class QuestionForm(forms.ModelForm):
    """Alta/edición de un reactivo con los campos del checklist (spec 007, FR-004).

    `template` se usa para validar que el título no se repita dentro del cuestionario.
    """

    class Meta:
        model = Question
        fields = ["title", "text", "category", *Question.CHECKLIST_FIELDS]
        labels = {
            "title": "Título",
            "text": "Descripción",
            "category": "Categoría",
            "acceptance_criteria": "Criterio de aceptación",
            "deliverable": "Entregable",
            "deliverable_format": "Formato",
            "frequency": "Frecuencia",
            "level_expectation": "Expectativa por nivel",
            "guidance": "Comentarios y guía",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": _INPUT}),
            "category": forms.Select(attrs={"class": "select w-full"}),
            "text": forms.Textarea(attrs={"class": _TEXTAREA, "rows": 2}),
            **{
                name: forms.Textarea(attrs={"class": _TEXTAREA, "rows": 2})
                for name in Question.CHECKLIST_FIELDS
            },
        }

    def __init__(self, *args, template=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = template
        self.fields["title"].required = True
        # La categoría solo aplica a Ownership y solo entre las del cuestionario (spec 008).
        if template is not None and template.kind == QuestionnaireTemplate.Kind.OWNERSHIP:
            self.fields["category"].queryset = Category.objects.filter(template_links__template=template)
            self.fields["category"].empty_label = "— Elige una categoría —"
        else:
            del self.fields["category"]

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("El título es obligatorio.")
        siblings = Question.objects.filter(section__template=self.template, title=title)
        if self.instance.pk:
            siblings = siblings.exclude(pk=self.instance.pk)
        if siblings.exists():
            raise forms.ValidationError("Ya hay un reactivo con ese título en este cuestionario.")
        return title

    def clean(self):
        cleaned = super().clean()
        if "category" in self.fields and not cleaned.get("category") and not self.errors.get("category"):
            linked = list(self.fields["category"].queryset[:2])
            if len(linked) == 1:          # un solo candidato: se asigna
                cleaned["category"] = linked[0]
            else:
                self.add_error("category", "Elige la categoría de la pregunta.")
        for name in ["text", *Question.CHECKLIST_FIELDS]:
            if isinstance(cleaned.get(name), str):
                cleaned[name] = cleaned[name].strip()
        return cleaned


class WeightsForm(forms.Form):
    """Pesos de un grupo (categorías de un cuestionario o preguntas de una categoría).

    Campos `<field_prefix><id>`; todos obligatorios, con un decimal como máximo y Σ = 100.0%
    (spec 008, FR-002/FR-011/FR-013). Tras `is_valid()`, `weights` = {id: Decimal}.
    """

    def __init__(self, *args, ids, field_prefix, label, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_prefix = field_prefix
        self.label = label
        self.weights = {}
        for pk in ids:
            self.fields[f"{field_prefix}{pk}"] = forms.CharField(required=False)

    def clean(self):
        cleaned = super().clean()
        values = {}
        for name, raw in cleaned.items():
            try:
                values[int(name[len(self.field_prefix):])] = ow.from_tenths(ow.to_tenths(raw))
            except ow.WeightError as exc:
                raise ValidationError(f"Los pesos de «{self.label}» no son válidos: {exc}") from None
        error = ow.group_error(self.label, values.values())
        if error:
            raise ValidationError(error)
        self.weights = values
        return cleaned
