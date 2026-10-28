"""Formularios del editor de cuestionarios."""

from django import forms

from .models import Question

_INPUT = "input w-full"
_TEXTAREA = "textarea w-full"


class QuestionForm(forms.ModelForm):
    """Alta/edición de un reactivo con los campos del checklist (spec 007, FR-004).

    `template` se usa para validar que el título no se repita dentro del cuestionario.
    """

    class Meta:
        model = Question
        fields = ["title", "text", *Question.CHECKLIST_FIELDS]
        labels = {
            "title": "Título",
            "text": "Descripción",
            "acceptance_criteria": "Criterio de aceptación",
            "deliverable": "Entregable",
            "deliverable_format": "Formato",
            "frequency": "Frecuencia",
            "level_expectation": "Expectativa por nivel",
            "guidance": "Comentarios y guía",
        }
        widgets = {
            "title": forms.TextInput(attrs={"class": _INPUT}),
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
        for name in ["text", *Question.CHECKLIST_FIELDS]:
            if isinstance(cleaned.get(name), str):
                cleaned[name] = cleaned[name].strip()
        return cleaned
