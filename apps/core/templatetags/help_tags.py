"""Tag de bloque `{% help_step %}` del Centro de ayuda (spec 011): paso numerado con ícono Lucide y cuerpo rico."""
from django import template
from django.template.loader import render_to_string

register = template.Library()


class HelpStepNode(template.Node):
    def __init__(self, kwargs, nodelist):
        self.kwargs = kwargs
        self.nodelist = nodelist

    def render(self, context):
        options = {k: v.resolve(context) for k, v in self.kwargs.items()}
        return render_to_string("help/_step.html", {**options, "body": self.nodelist.render(context)})


@register.tag
def help_step(parser, token):
    """{% help_step n=1 icon="camera" title="Sube tu foto" %}cuerpo con <b>HTML</b> y {{ variables }}{% end_help_step %}"""
    bits = token.split_contents()[1:]
    kwargs = template.base.token_kwargs(list(bits), parser)   # token_kwargs consume la lista: se le pasa una copia
    if len(kwargs) != len(bits) or not {"n", "icon", "title"} <= set(kwargs):
        raise template.TemplateSyntaxError('help_step requiere n=, icon= y title=')
    nodelist = parser.parse(("end_help_step",))
    parser.delete_first_token()
    return HelpStepNode(kwargs, nodelist)
