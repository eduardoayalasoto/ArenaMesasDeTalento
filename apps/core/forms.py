"""Helpers de estilo/estado compartidos entre Forms de distintas apps.

Desde 2026-09-22, botones/inputs/forms usan clases de **daisyUI** (biblioteca
de clases CSS sobre Tailwind v4, ver DESIGN_SYSTEM.md) directamente sobre
widgets NATIVOS de Django (`TextInput`/`Select`/`CheckboxInput`/`Textarea`)
-- a diferencia del intento anterior con `@material/web` (Web Components,
retirado el mismo día), daisyUI no necesita un widget custom por tipo de
campo: es solo una clase CSS sobre el `<input>`/`<select>` que Django ya
renderiza solo. `field_classes()` es el único helper que hace falta.
"""


def field_classes(bound_field, base: str, extra: str = "") -> str:
    """Clases daisyUI para el widget de un `BoundField` -- `<base>-error`
    si el campo ya fue validado y falló (`bound_field.errors`), sin
    modificador si no. Uso típico en `Form.__init__`:

        self.fields["name"].widget.attrs["class"] = field_classes(self["name"], "input")
        self.fields["owner"].widget.attrs["class"] = field_classes(self["owner"], "select")
        self.fields["notes"].widget.attrs["class"] = field_classes(self["notes"], "textarea")

    `base`: el componente daisyUI (`input`, `select`, `textarea`,
    `checkbox`, `radio`, `toggle`). `extra`: clases Tailwind adicionales
    (ej. `"w-full"`, `"js-flatpickr"`) que se agregan tal cual, sin
    condicionar a `base`.

    Nunca deja un campo "roto" visualmente sin indicarlo -- ver
    `components/_form_field.html` para el texto de ayuda/error que lo
    acompaña.
    """
    classes = [base]
    if bound_field.errors:
        classes.append(f"{base}-error")
    if extra:
        classes.append(extra)
    return " ".join(classes)


# Excepción permanente: campos de fecha/hora (`js-flatpickr`/
# `js-flatpickr-datetime`) y `ModelMultipleChoiceField`/`SelectMultiple`
# usan estas constantes en vez de `field_classes()` cuando el campo no
# tiene un `BoundField` a mano en el punto de declaración del widget (ej.
# `forms.DateInput(attrs={"class": INPUT_CLASSES_JS_FLATPICKR})`).
INPUT_CLASSES = "input w-full"
INPUT_CLASSES_JS_FLATPICKR = "input w-full js-flatpickr"
INPUT_CLASSES_JS_FLATPICKR_DATETIME = "input w-full js-flatpickr-datetime"
SELECT_CLASSES = "select w-full"
