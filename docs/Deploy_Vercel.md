# Deploy a Vercel — Guía paso a paso

> Estado: **configuración lista** (`vercel.json`, `.vercelignore`, `wsgi.app`, WhiteNoise sin collectstatic, `psycopg` en requirements). Falta ejecutar el deploy, que requiere tu cuenta de Vercel y un Postgres gestionado.

## Lo que necesito de ti (bloqueantes)
1. **Cuenta de Vercel** y autenticación de la CLI — es interactivo, lo corres tú:
   - Instalar la CLI: `npm i -g vercel` (requiere Node; no está instalado en este equipo).
     - Si no quieres instalar Node, también puedes hacer todo desde el **dashboard de Vercel** (importar el repo de Git).
   - `vercel login`
2. **Base de datos Postgres gestionada** (Vercel no permite SQLite). Opciones: **Vercel Postgres**, **Neon** o **Supabase**. Necesito el `DATABASE_URL` (formato `postgres://usuario:password@host:5432/dbname`).
3. **Repositorio Git** (recomendado): subir este proyecto a GitHub para el deploy automático. Hoy la carpeta **no es un repo git**; si prefieres, se puede desplegar por CLI sin Git (`vercel` desde la carpeta).
4. Decidir los **valores de las variables de entorno** (abajo).

## Variables de entorno a configurar en Vercel (Project Settings → Environment Variables)
| Variable | Valor |
|---|---|
| `DJANGO_SECRET_KEY` | una cadena larga y secreta (genera una nueva, no la de dev) |
| `DJANGO_DEBUG` | `0` |
| `DATABASE_URL` | el de tu Postgres gestionado |
| `DJANGO_ALLOWED_HOSTS` | `.vercel.app` (y tu dominio propio si aplica) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://*.vercel.app` (y tu dominio) |
| `EMAIL_USE_SMTP` | `1` para correo real (reset de contraseña); con `0` se manda a consola |
| `EMAIL_HOST` / `EMAIL_PORT` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | datos de tu proveedor SMTP |
| `DEFAULT_FROM_EMAIL` | `Evaluaciones Arena <no-reply@arena-analytics.com>` |
| `SEED_SU_EMAIL` / `SEED_SU_PASSWORD` / `SEED_SU_NAME` | superusuario inicial |

## Pasos del deploy
```bash
# 1) En la carpeta del proyecto, vincular
vercel link

# 2) Cargar las variables de entorno (o hacerlo en el dashboard)
vercel env add DJANGO_SECRET_KEY
# … repetir para cada variable …

# 3) Deploy de preview
vercel

# 4) Preparar la base de datos (UNA sola vez) apuntando al Postgres de producción.
#    Desde tu máquina, con el DATABASE_URL de producción exportado:
#    (PowerShell)  $env:DATABASE_URL = "postgres://…"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py seed_all          # catálogos, cuestionarios, usuarios, superusuario
# (opcional, solo para demo)  manage.py seed_demo

# 4b) PRIMERA SALIDA A PRODUCCIÓN — forzar cambio de contraseña a todos:
#     (opcional: --temp-password fija una contraseña temporal común para el primer ingreso)
.\.venv\Scripts\python.exe manage.py require_password_change --all --temp-password "Arena-Temporal-2026"
#     Para desactivar el switch:  manage.py require_password_change --all --clear

# 5) Deploy a producción
vercel --prod
```

## Notas técnicas
- **Runtime Python 3.12** en Vercel (el código es compatible; el equipo local usa 3.14).
- **Estáticos:** WhiteNoise con `WHITENOISE_USE_FINDERS=True` sirve los assets del admin sin `collectstatic`. El resto de la UI (Tailwind/Alpine/htmx) carga por CDN.
- **Tailwind/Alpine/htmx:** ya están **locales** (sin CDN). El CSS se compila con `tailwindcss.exe` → `static/css/app.css` (versionado), y Alpine/htmx están en `static/vendor/`. WhiteNoise los sirve. Si editas plantillas y agregas clases nuevas, recompila con `.\build_css.ps1` antes de subir.
- **Migraciones:** Vercel no las corre solo; se ejecutan desde local contra el `DATABASE_URL` de producción (paso 4).
- **Cold starts:** aceptable para el volumen (~54 usuarios). `CONN_MAX_AGE=0` ya está configurado para serverless.
