"""Entrypoint para Vercel.

El builder de Django de Vercel detecta automáticamente `api/wsgi.py` y usa el
callable `app`. Aquí reexponemos la aplicación WSGI de Django (config/wsgi.py).
"""

from config.wsgi import app  # noqa: F401
