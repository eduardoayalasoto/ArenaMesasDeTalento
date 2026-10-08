"""Template tags/filters transversales de arena-crm."""
import re
from datetime import date, datetime

from django import template
from django.utils import timezone

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Acceso a un dict por una clave dinámica (variable de template).

    Django no soporta `{{ dict.variable }}` cuando `variable` es en sí
    misma una variable de template (solo literales) -- usado por
    templates/components/_table.html para leer `row[column.key]` con
    `column.key` dinámico por fila de la tabla.
    """
    if dictionary is None:
        return ""
    try:
        return dictionary.get(key, "")
    except AttributeError:
        return getattr(dictionary, key, "")


@register.filter
def money(value, currency="MXN"):
    """Formatea un monto con signo de peso, separador de miles (coma) y
    decimales (punto) -- ej. `1234567.891|money:"MXN"` -> "$1,234,567.89
    MXN". Pedido explícito del usuario: formato fijo, nunca depende del
    locale activo de Django (es-mx podría invertir coma/punto vía
    `django.utils.numberformat` si USE_THOUSAND_SEPARATOR estuviera
    activo) -- el spec del mini-lenguaje de formato de Python (`,.2f`)
    siempre usa coma/punto sin importar el locale del proceso.
    """
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return value
    return f"${amount:,.2f} {currency}"


@register.filter
def initials(full_name, max_letters=2):
    """Iniciales de un nombre completo -- primera letra de cada una de
    las primeras `max_letters` palabras. Usado por components/_avatar.html
    con el prop `name` (ej. Person.full_name, que no tiene `get_full_name()`
    como un User real) -- pedido explícito del usuario: "avatar con dos
    letras" siempre que se muestre una Persona seleccionada."""
    words = (full_name or "").split()
    return "".join(w[0] for w in words[:max_letters]).upper()


@register.filter
def whatsapp_digits(phone):
    """Solo dígitos de un teléfono, para armar un link `https://wa.me/<numero>`
    -- pedido explícito del usuario: "empezando con la lada... sin signo de
    más". wa.me exige el número completo con lada y SIN ningún separador
    (espacios, guiones, paréntesis) ni el `+` que sí usa el formato E.164."""
    return re.sub(r"\D", "", phone or "")


@register.filter
def matches_today(value):
    """True si `value` (fecha) cae hoy -- usado por
    crm/_activity_quick_form_body.html para decidir, en el PRIMER render
    del servidor, si el badge "Hoy" arranca visible (2026-09-25, pedido
    explícito: el badge no debe aparecer recién después de que Alpine
    hidrata, porque eso salta el layout del modal unos px -- debe estar
    presente desde el HTML crudo cuando la fecha default ya es hoy).

    Acepta el mismo valor crudo que trae `BoundField.value()`: un objeto
    date/datetime cuando el form no está ligado (usa `initial`), o el
    string `dd/mm/aaaa` tal cual lo manda el navegador (ver
    ActivityQuickCreateForm.input_formats) cuando el form está ligado con
    errores de otro campo."""
    today = timezone.localdate()
    if isinstance(value, datetime):
        return value.date() == today
    if isinstance(value, date):
        return value == today
    match = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", str(value or ""))
    if not match:
        return False
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day) == today
    except ValueError:
        return False


@register.filter
def thousands(value, decimals=0):
    """Formatea un número con separador de miles (coma) y `decimals`
    decimales (punto) -- sin signo de moneda, para conteos/porcentajes
    grandes. Mismo criterio de formato fijo que `money`."""
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return value
    return f"{amount:,.{int(decimals)}f}"


@register.simple_tag
def static_v(path):
    """`{% static %}` + `?v=<mtime>` para los estáticos PROPIOS (css/js no
    vendorizados), 2026-09-28. Bug real: runserver (y cualquier servidor que
    solo mande `Last-Modified`) deja que Chrome aplique caché heurística y
    sirva por horas un tailwind.css/JS viejo junto con HTML nuevo -- clases
    nuevas inexistentes en el CSS viejo dejaban botones tapados (modales que
    "no abren"). Con la fecha de modificación en la URL, cada cambio del
    archivo es una URL nueva que el navegador SIEMPRE descarga. Los de
    `vendor/` ya llevan la versión en la ruta y no lo necesitan."""
    import os

    from django.contrib.staticfiles import finders
    from django.templatetags.static import static

    url = static(path)
    try:
        found = finders.find(path)
        if found:
            return f"{url}?v={int(os.path.getmtime(found))}"
    except (OSError, ValueError):
        pass
    return url



@register.filter
def tag_badge_class(color):
    """Clase daisyUI del chip de una etiqueta (Tag/DealTag.color) -- ver
    Tag.COLOR_BADGE_CLASSES. Color desconocido = neutral (nunca rompe)."""
    from apps.crm.models import Tag

    return Tag.COLOR_BADGE_CLASSES.get(color, "badge-neutral")


@register.simple_tag
def tag_color_swatches():
    """[(valor, etiqueta, clase del círculo)] para el selector de color de
    etiquetas (components/_tag_picker.html)."""
    from apps.crm.models import Tag

    return [(value, label, Tag.COLOR_SWATCH_CLASSES[value]) for value, label in Tag.COLOR_CHOICES]
