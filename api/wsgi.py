"""Entrypoint WSGI para Vercel (lo detecta el builder de Django).

Define la aplicación directamente con get_wsgi_application() para que el
detector de Vercel la reconozca; expone `app` y `application`.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()
app = application
