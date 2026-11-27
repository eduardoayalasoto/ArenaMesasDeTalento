"""Formularios del editor de cuestionarios."""

from django import forms
from django.core.exceptions import ValidationError

from apps.core.services import ownership_weights as ow

from apps.catalog.models import Position

from .models import Category, CompetencyBlock, Question, QuestionnaireTemplate, Section

_INPUT = "input w-full"
_TEXTAREA = "textarea w-full"


class TemplateCreateForm(forms.Form):
    """Alta de un cuestionario nuevo: tipo + (para Ownership) la posición que aún no tiene ninguno."""

    kind = forms.ChoiceField(
        label="Tipo", choices=QuestionnaireTemplate.Kind.choices,
        widget=forms.Select(attrs={"class": "select w-full"}),
    )
    position = forms.ModelChoiceField(
        label="Posición", queryset=Position.objects.none(), required=False,
        empty_label="— Elige la posición —", widget=forms.Select(attrs={"class": "select w-full"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._taken = set(
            QuestionnaireTemplate.objects.filter(kind=QuestionnaireTemplate.Kind.OWNERSHIP)
            .values_list("area_id", "level_id")
        )
        field = self.fields["position"]
        field.queryset = (
            Position.objects.filter(is_active=True).select_related("area__department", "level")
            .order_by("area__department__order", "area__code", "level__order")
        )
        field.label_from_instance = lambda p: (
            f"{p.area.full_name} · {p.name}" + (f" ({p.level.name})" if p.level_id else "")
            + (" — ya tiene cuestionario" if (p.area_id, p.level_id) in self._taken else "")
        )

    def funnel_data(self) -> dict:
        """Datos del embudo Área → Posición → Nivel (opcional) para la pantalla.

        Cada combinación válida es una fila de «Posición × nivel»; el embudo solo ofrece las que existen.
        """
        combos, areas, departments, levels = [], {}, {}, {}
        for p in self.fields["position"].queryset:
            department = p.area.department
            combos.append({
                "id": p.pk, "department": department.pk if department else 0, "area": p.area_id,
                "level": p.level_id or 0, "taken": (p.area_id, p.level_id) in self._taken,
            })
            areas[p.area_id] = {"id": p.area_id, "name": p.area.name, "department": department.pk if department else 0}
            if department:
                departments[department.pk] = {"id": department.pk, "name": department.name}
            if p.level_id:
                levels[p.level_id] = {"id": p.level_id, "name": p.level.name}
        return {"combos": combos, "areas": list(areas.values()), "departments": list(departments.values()),
                "levels": list(levels.values())}

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("kind")
        if kind == QuestionnaireTemplate.Kind.OWNERSHIP and not cleaned.get("position"):
            self.add_error("position", "Elige el Área, la posición y, si la usa, el nivel del cuestionario de Ownership.")
        position = cleaned.get("position")
        if kind == QuestionnaireTemplate.Kind.OWNERSHIP and position and (position.area_id, position.level_id) in self._taken:
            self.add_error("position", "Esa combinación ya tiene cuestionario: ábrelo y edítalo.")
        return cleaned


class SectionForm(forms.Form):
    """Título de una sección (alta y renombrado)."""

    title = forms.CharField(
        label="Título de la sección", max_length=160,
        widget=forms.TextInput(attrs={"class": _INPUT}),
        error_messages={"required": "Escribe el título de la sección."},
    )

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("Escribe el título de la sección.")
        return title


class ScaleOptionForm(forms.Form):
    """Opción de la escala de respuestas: valor 1–4 (vacío = N/A), etiqueta y descriptor."""

    value = forms.IntegerField(
        label="Valor", required=False, min_value=1, max_value=4,
        error_messages={
            "min_value": "El valor va de 1 a 4 (déjalo vacío para N/A).",
            "max_value": "El valor va de 1 a 4 (déjalo vacío para N/A).",
            "invalid": "El valor debe ser un número del 1 al 4 (vacío para N/A).",
        },
    )
    label = forms.CharField(
        label="Etiqueta", max_length=40, error_messages={"required": "Escribe la etiqueta de la opción."},
    )
    description = forms.CharField(label="Descriptor", required=False)

    def __init__(self, *args, template, option=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.template = template
        self.option = option

    def clean_label(self):
        label = self.cleaned_data["label"].strip()
        if not label:
            raise forms.ValidationError("Escribe la etiqueta de la opción.")
        return label

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        siblings = self.template.scale_options.filter(question__isnull=True)
        if self.option is not None:
            siblings = siblings.exclude(pk=self.option.pk)
        value = cleaned.get("value")
        if value is None and siblings.filter(value__isnull=True).exists():
            raise ValidationError("Ya hay una opción N/A en la escala.")
        if value is not None and siblings.filter(value=value).exists():
            raise ValidationError(f"Ya hay una opción con valor {value} en la escala.")
        cleaned["description"] = (cleaned.get("description") or "").strip()
        return cleaned


class QuestionForm(forms.ModelForm):
    """Alta/edición de un reactivo con los campos del checklist (spec 007, FR-004).

    `template` se usa para validar que el título no se repita dentro del cuestionario.
    `section` es opcional: si llega, la pregunta se mueve a esa sección del mismo cuestionario.
    """

    class Meta:
        model = Question
        fields = ["title", "text", "section", "category", "block", "target_level", "is_weighted",
                  *Question.CHECKLIST_FIELDS]
        labels = {
            "block": "Bloque del catálogo",
            "target_level": "Nivel de dominio objetivo",
            "is_weighted": "Pondera",
            "title": "Título",
            "text": "Descripción",
            "section": "Sección",
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
            "block": forms.Select(attrs={"class": "select w-full"}),
            "target_level": forms.Select(attrs={"class": "select w-full"}),
            "is_weighted": forms.CheckboxInput(attrs={"class": "checkbox"}),
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
        self.fields["section"].required = False
        self.fields["section"].queryset = (
            template.sections.all() if template is not None else Section.objects.none()
        )
        # La categoría solo aplica a Ownership y solo entre las del cuestionario (spec 008).
        if template is not None and template.kind == QuestionnaireTemplate.Kind.OWNERSHIP:
            self.fields["category"].queryset = Category.objects.filter(template_links__template=template)
            self.fields["category"].empty_label = "— Elige una categoría —"
            self.fields["block"].queryset = CompetencyBlock.objects.filter(is_active=True)
            self.fields["block"].required = False
            self.fields["block"].empty_label = "— Sin bloque —"
            self.fields["target_level"].required = False
            self.fields["target_level"].choices = [("", "— Sin nivel —")] + list(Question.Mastery.choices)
            # Los campos de ponderación solo se tocan si el formulario los trae (marca `weighting_fields`):
            # así un guardado que no los incluye no borra el bloque ni convierte la pregunta en «no pondera».
            if self.is_bound and self.data.get("weighting_fields") != "1":
                for name in ("block", "target_level", "is_weighted"):
                    self.fields.pop(name, None)
        else:
            for name in ("category", "block", "target_level", "is_weighted"):
                self.fields.pop(name, None)

    def clean_section(self):
        # Sin sección en el envío, una pregunta existente se queda donde está (nunca queda sin sección).
        section = self.cleaned_data.get("section")
        if section is None and self.instance.pk:
            return self.instance.section
        return section

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
    """Ponderaciones de un grupo (categorías de un cuestionario o preguntas de una categoría).

    Campos `<field_prefix><id>`; todos obligatorios, con un decimal como máximo y Σ = 100.0%
    (spec 008, FR-002/FR-011/FR-013). Tras `is_valid()`, `weights` = {id: Decimal}.
    """

    def __init__(self, *args, ids, field_prefix, label, positive_for=None, titles=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_prefix = field_prefix
        self.label = label
        # `positive_for` = nombre de la categoría: ninguna de sus preguntas puede ponderar 0.
        # `titles` = {id: título} para nombrar en el error a quien quedó en 0.
        self.positive_for = positive_for
        self.titles = titles or {}
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
                raise ValidationError(f"Las ponderaciones de «{self.label}» no son válidas: {exc}") from None
        if self.positive_for:
            zeros = [self.titles.get(pk, str(pk)) for pk, weight in values.items() if weight == 0]
            if zeros:
                raise ValidationError(ow.zero_weight_error(self.positive_for, zeros))
        error = ow.group_error(self.label, values.values())
        if error:
            raise ValidationError(error)
        self.weights = values
        return cleaned


class BlockForm(forms.Form):
    """Alta y edición de un bloque del catálogo de competencias (con sus skills, uno por línea)."""

    block = forms.IntegerField(widget=forms.HiddenInput, required=False)
    name = forms.CharField(label="Nombre", max_length=120)
    order = forms.IntegerField(label="Orden", min_value=0, max_value=999, initial=1)
    is_active = forms.BooleanField(label="Activo", required=False)
    skills = forms.CharField(label="Skills", required=False, widget=forms.Textarea)
