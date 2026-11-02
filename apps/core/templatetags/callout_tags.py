"""Tag de bloque `{% callout %}`: avisos en línea con ícono obligatorio por tono.

El markup vive en templates/components/_callout.html (una sola implementación);
el tag solo existe porque `{% include %}` no admite contenido rico como cuerpo.
"""
from django import template
from django.template.loader import render_to_string

register = template.Library()

TONES = {"info", "success", "warning", "error", "neutral"}


class CalloutNode(template.Node):
    def __init__(self, tone, kwargs, nodelist):
        self.tone = tone
        self.kwargs = kwargs
        self.nodelist = nodelist

    def render(self, context):
        tone = self.tone.resolve(context)
        if tone not in TONES:
            raise template.TemplateSyntaxError(f"callout: tono desconocido {tone!r} (usa {sorted(TONES)})")
        options = {k: v.resolve(context) for k, v in self.kwargs.items()}
        return render_to_string("components/_callout.html", {
            "tone": tone,
            "title": options.get("title"),
            "icon": options.get("icon"),
            "cls": options.get("cls"),
            "body": self.nodelist.render(context),
        })


@register.tag
def callout(parser, token):
    """{% callout "tono" [title=...] [icon=...] [cls=...] %}...{% endcallout %}"""
    bits = token.split_contents()
    if len(bits) < 2:
        raise template.TemplateSyntaxError("callout requiere el tono: {% callout \"info\" %}")
    tone = parser.compile_filter(bits[1])
    kwargs = template.base.token_kwargs(bits[2:], parser)
    if len(kwargs) != len(bits[2:]):
        raise template.TemplateSyntaxError("callout: solo acepta argumentos con nombre después del tono")
    unknown = set(kwargs) - {"title", "icon", "cls"}
    if unknown:
        raise template.TemplateSyntaxError(f"callout: argumentos desconocidos {sorted(unknown)}")
    nodelist = parser.parse(("endcallout",))
    parser.delete_first_token()
    return CalloutNode(tone, kwargs, nodelist)
