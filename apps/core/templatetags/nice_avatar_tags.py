"""`{% nice_avatar user size=32 %}` — equivalente en arena-talento del tag de arena-crm.

En arena-crm compone un avatar ilustrado; en arena-talento la foto de la persona es obligatoria
(PhotoRequiredMiddleware), así que se dibuja la FOTO real (miniatura) con el mismo marco circular,
y como respaldo el avatar de iniciales de components/_avatar.html.
"""

from django import template
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html

register = template.Library()


@register.simple_tag
def nice_avatar(user, size=32, **_ignored):
    if user is None:
        return ""
    size = int(size or 32)
    if getattr(user, "photo_mime", ""):
        url = reverse("accounts:user_photo", args=[user.pk]) + ("?mini=1" if size <= 64 else "")
        return format_html(
            '<img src="{}" alt="Foto de {}" width="{}" height="{}" class="rounded-full object-cover shrink-0" '
            'loading="lazy">',
            url, getattr(user, "full_name", ""), size, size,
        )
    return render_to_string("components/_avatar.html", {"user": user, "size": size})
