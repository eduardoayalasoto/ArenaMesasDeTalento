"""
Configuración de Django para Webapp de Evaluaciones de Desempeño Arena.

Una sola configuración dirigida por variables de entorno (.env):
- DJANGO_DEBUG: "1" en desarrollo, "0" en producción.
- DATABASE_URL: si está presente (Postgres), se usa; si no, SQLite local.
- Idioma es-mx, zona horaria de México.
"""

from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, "1" if default else "0").lower() in {"1", "true", "yes", "on"}


# --- Núcleo ---------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY", "dev-insecure-key-cambiar-en-produccion-0123456789"
)
DEBUG = env_bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,.vercel.app").split(",")
    if h.strip()
]
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS", "https://*.vercel.app"
    ).split(",")
    if o.strip()
]

# --- Aplicaciones ---------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # Terceros
    "simple_history",
    # Apps del proyecto
    "apps.core",
    "apps.accounts",
    "apps.catalog",
    "apps.questionnaires",
    "apps.evaluations",
    "apps.dashboards",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "apps.core.middleware.PasswordChangeRequiredMiddleware",
    "apps.core.middleware.PhotoRequiredMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.navigation",
                "apps.core.context_processors.notifications",
                "apps.core.context_processors.asset_version",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Base de datos --------------------------------------------------------
def _resolve_database_url() -> str:
    """Devuelve la primera cadena de conexión Postgres VÁLIDA disponible.

    Tolera un DATABASE_URL mal configurado (p. ej. un placeholder) cayendo a las
    variables que inyecta la integración de Neon/Vercel.
    """
    for key in (
        "DATABASE_URL", "POSTGRES_URL", "POSTGRES_URL_NON_POOLING",
        "DATABASE_URL_UNPOOLED",
    ):
        value = os.environ.get(key, "").strip()
        if value.startswith(("postgres://", "postgresql://")):
            return value
    return ""


DATABASE_URL = _resolve_database_url()
if DATABASE_URL:
    # Postgres gestionado (Neon / Vercel Postgres / Supabase)
    from urllib.parse import parse_qs, urlparse

    url = urlparse(DATABASE_URL)
    qs = parse_qs(url.query)
    options = {
        "sslmode": qs.get("sslmode", [os.environ.get("DB_SSLMODE", "require")])[0],
        # Falla rápido si no alcanza la BD (evita colgarse hasta el timeout de la función).
        "connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "10")),
    }
    if "channel_binding" in qs:
        options["channel_binding"] = qs["channel_binding"][0]
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": url.path.lstrip("/"),
            "USER": url.username,
            "PASSWORD": url.password,
            "HOST": url.hostname,
            "PORT": url.port or "5432",
            "CONN_MAX_AGE": 0,  # serverless: sin conexiones persistentes
            "OPTIONS": options,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --- Autenticación --------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboards:home"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internacionalización (100% español, México) --------------------------
LANGUAGE_CODE = "es-mx"
TIME_ZONE = "America/Mexico_City"
USE_I18N = True
USE_TZ = True

# --- Archivos estáticos (whitenoise) --------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Servir estáticos con finders evita depender de `collectstatic` en serverless (Vercel).
# El footprint de estáticos es mínimo (admin de Django); el resto de la UI va por CDN.
WHITENOISE_USE_FINDERS = True
# Cachea estáticos en el navegador 1 día (el CSS lleva ?v= para invalidar al cambiar).
WHITENOISE_MAX_AGE = 86400
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Correo ---------------------------------------------------------------
if env_bool("EMAIL_USE_SMTP", default=False):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = True
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL", "Evaluaciones Arena <no-reply@arena-analytics.com>"
)

# --- Seguridad en producción ---------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# --- Mensajería (mapeo a clases de UI) ------------------------------------
from django.contrib.messages import constants as messages  # noqa: E402

MESSAGE_TAGS = {
    messages.DEBUG: "debug",
    messages.INFO: "info",
    messages.SUCCESS: "success",
    messages.WARNING: "warning",
    messages.ERROR: "error",
}

# --- Logging --------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        # Errores de request (500) con traza completa.
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
    },
}

# --- Monitoreo de errores (opcional) --------------------------------------
# Se activa solo si defines SENTRY_DSN y tienes instalado sentry-sdk.
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=0.0,
            send_default_pii=False,
        )
    except Exception:  # noqa: BLE001  (el monitoreo nunca debe tumbar el arranque)
        pass
