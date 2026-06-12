# Importación de proyectos/equipos y edición de proyecto — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enriquecer el modelo `Project` con responsable/fechas/status, importar 17 proyectos y sus equipos desde el xlsx de Talento, y exponer los campos nuevos en la vista de edición existente.

**Architecture:** Migración de esquema en `catalog`; lógica de normalización/emparejamiento de nombres como funciones puras en `apps/core` (testeables sin BD); dos management commands idempotentes (`import_projects`, `import_memberships`) que leen el xlsx con openpyxl (import perezoso) siguiendo el patrón de `import_csv_users`; extensión del `ProjectForm` y su template.

**Tech Stack:** Django 6, pytest + pytest-django, openpyxl, Tailwind (clases `input`/`label`/`card` ya existentes).

---

## Estructura de archivos

- **Modificar** `apps/catalog/models.py` — `Project`: enum `Status` + campos `responsable, kickoff, target_close, status`.
- **Crear** `apps/catalog/migrations/0002_project_extra_fields.py` — vía `makemigrations`.
- **Modificar** `apps/core/text.py` — añadir `normalize_name`.
- **Crear** `apps/core/services/imports.py` — índices y resolución de usuarios, mapa de duración, mapa de usuarios a crear, `to_date`.
- **Crear** `apps/core/management/commands/import_projects.py`.
- **Crear** `apps/core/management/commands/import_memberships.py`.
- **Modificar** `apps/catalog/forms.py` — `ProjectForm`: añadir los 4 campos.
- **Modificar** `templates/catalog/project_form.html` — render de los 4 campos.
- **Modificar** `requirements.txt` — añadir `openpyxl`.
- **Crear** `apps/core/tests/test_project_extra_fields.py` — modelo + form.
- **Crear** `apps/core/tests/test_imports_helpers.py` — funciones puras.
- **Crear** `apps/core/tests/test_import_commands.py` — comandos contra un xlsx generado.

Comandos de prueba: `.\.venv\Scripts\python.exe -m pytest <ruta> -v` (DATABASE_URL vacío → SQLite). Trabajar en la rama `feat/import-proyectos-edicion`.

---

## Task 1: Campos nuevos en el modelo `Project`

**Files:**
- Modify: `apps/catalog/models.py` (clase `Project`, ~líneas 115-148)
- Test: `apps/core/tests/test_project_extra_fields.py`

- [ ] **Step 1: Escribir la prueba que falla**

Crear `apps/core/tests/test_project_extra_fields.py`:

```python
"""Campos nuevos de Project (responsable, fechas, status) y su edición."""

from datetime import date

import pytest
from django.contrib.auth import get_user_model

from apps.catalog.models import Project

User = get_user_model()


@pytest.fixture
def lead(db):
    return User.objects.create_user(
        email="lead@arena-analytics.com", password="x", full_name="Líder Proyecto",
    )


@pytest.mark.django_db
def test_project_acepta_responsable_fechas_status(lead):
    resp = User.objects.create_user(
        email="resp@arena-analytics.com", password="x", full_name="Responsable Uno",
    )
    p = Project.objects.create(
        name="Demo", lead=lead, responsable=resp,
        kickoff=date(2026, 1, 1), target_close=date(2026, 6, 30),
        status=Project.Status.DELAYED,
    )
    p.refresh_from_db()
    assert p.responsable == resp
    assert p.kickoff == date(2026, 1, 1)
    assert p.target_close == date(2026, 6, 30)
    assert p.status == Project.Status.DELAYED


@pytest.mark.django_db
def test_project_status_default_on_track(lead):
    p = Project.objects.create(name="Demo2", lead=lead)
    assert p.status == Project.Status.ON_TRACK
    assert p.responsable is None
    assert p.kickoff is None
```

- [ ] **Step 2: Correr la prueba y verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_project_extra_fields.py -v`
Expected: FAIL (`AttributeError: type object 'Project' has no attribute 'Status'` / campos inexistentes).

- [ ] **Step 3: Implementar los campos en `Project`**

En `apps/catalog/models.py`, dentro de `class Project(models.Model):`, después de `class Duration(...)` añadir el enum `Status`, y después del campo `is_active` añadir los 4 campos:

```python
    class Status(models.TextChoices):
        ON_TRACK = "ON_TRACK", "On track"
        DELAYED = "DELAYED", "Delayed"
```

```python
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="responsible_projects",
        verbose_name="responsable",
    )
    kickoff = models.DateField("kick-off", null=True, blank=True)
    target_close = models.DateField("cierre objetivo", null=True, blank=True)
    status = models.CharField(
        "estatus", max_length=10, choices=Status.choices, default=Status.ON_TRACK
    )
```

(`settings` ya está importado en el archivo.)

- [ ] **Step 4: Generar la migración**

Run: `.\.venv\Scripts\python.exe manage.py makemigrations catalog`
Expected: crea `apps/catalog/migrations/0002_*.py` con `AddField` para los 4 campos (y para `HistoricalProject`).

Renombrar el archivo a `0002_project_extra_fields.py` si Django usó otro sufijo (opcional, no obligatorio).

- [ ] **Step 5: Correr la prueba y verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_project_extra_fields.py -v`
Expected: PASS (2 passed). pytest aplica migraciones sobre SQLite automáticamente.

- [ ] **Step 6: Commit**

```bash
git add apps/catalog/models.py apps/catalog/migrations/ apps/core/tests/test_project_extra_fields.py
git commit -m "feat(catalog): Project con responsable, kickoff, target_close y status"
```

---

## Task 2: `normalize_name` (función pura)

**Files:**
- Modify: `apps/core/text.py`
- Test: `apps/core/tests/test_imports_helpers.py`

- [ ] **Step 1: Escribir la prueba que falla**

Crear `apps/core/tests/test_imports_helpers.py`:

```python
"""Funciones puras de importación: normalización y resolución de usuarios."""

from apps.core.text import normalize_name


def test_normalize_quita_acentos_y_colapsa_espacios():
    assert normalize_name("  José   Antonio  ") == "jose antonio"


def test_normalize_minusculas():
    assert normalize_name("MARÍA Magdalena") == "maria magdalena"


def test_normalize_none_y_vacio():
    assert normalize_name(None) == ""
    assert normalize_name("") == ""
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_imports_helpers.py -v`
Expected: FAIL (`ImportError: cannot import name 'normalize_name'`).

- [ ] **Step 3: Implementar `normalize_name`**

Al final de `apps/core/text.py` añadir:

```python
import unicodedata


def normalize_name(raw) -> str:
    """Minúsculas, sin acentos y espacios colapsados, para emparejar nombres."""
    if not raw:
        return ""
    s = unicodedata.normalize("NFKD", str(raw))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())
```

(Mover el `import unicodedata` al bloque de imports superior del archivo si prefieres; funcional en ambos sitios.)

- [ ] **Step 4: Correr y verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_imports_helpers.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/core/text.py apps/core/tests/test_imports_helpers.py
git commit -m "feat(core): normalize_name para emparejar nombres en importaciones"
```

---

## Task 3: Servicio `imports.py` (índices, resolución, mapas)

**Files:**
- Create: `apps/core/services/imports.py`
- Test: `apps/core/tests/test_imports_helpers.py` (añadir casos)

- [ ] **Step 1: Añadir pruebas que fallan**

Añadir a `apps/core/tests/test_imports_helpers.py`:

```python
import pytest
from django.contrib.auth import get_user_model

from apps.core.services import imports

User = get_user_model()


@pytest.mark.django_db
def test_build_index_y_resolve_por_nombre_completo():
    u = User.objects.create_user(
        email="oscar@arena-analytics.com", password="x",
        full_name="Oscar Andrés Mancha",
    )
    index = imports.build_user_index([u])
    # substring bidireccional: el nombre del Excel trae apellido extra
    assert imports.resolve_user("Oscar Andrés Mancha Mendoza", index) == u


@pytest.mark.django_db
def test_resolve_por_alias_de_correo():
    u = User.objects.create_user(
        email="abad.arellano@arena-analytics.com", password="x",
        full_name="Ramiro Abad Arellano Carmona",
    )
    # El nombre corto del HC no empata por substring (Cardona vs Carmona),
    # pero el alias por correo sí lo resuelve.
    index = imports.build_user_index(
        [u], alias_pairs=[("Abad Arellano Cardona", "abad.arellano@arena-analytics.com")]
    )
    assert imports.resolve_user("Abad Arellano Cardona", index) == u


def test_resolve_devuelve_none_si_no_encuentra():
    assert imports.resolve_user("Nadie Existe", {}) is None


def test_mapas_de_duracion_y_usuarios_a_crear():
    from apps.core.text import normalize_name
    assert imports.DURATION_BY_PROJECT[normalize_name("Data Ops / MPM")] == "INDEFINIDO"
    assert imports.DURATION_BY_PROJECT[normalize_name("Weather")] == "FINITO"
    assert normalize_name("Carolina Palacio") in imports.USERS_TO_CREATE


@pytest.mark.django_db
def test_resolve_or_create_crea_usuario_faltante():
    index = {}
    user, action = imports.resolve_or_create_user(
        "Carolina Palacio", index, password="x", dry=False
    )
    assert action == "created"
    assert user.email == "carolina.palacio@arena-analytics.com"
    # segunda vez: ya existe en el índice
    user2, action2 = imports.resolve_or_create_user(
        "Carolina Palacio", index, password="x", dry=False
    )
    assert action2 == "found" and user2 == user


@pytest.mark.django_db
def test_resolve_or_create_dry_no_crea():
    user, action = imports.resolve_or_create_user(
        "Carolina Palacio", {}, password="x", dry=True
    )
    assert action == "would_create" and user is None


def test_resolve_or_create_desconocido_unmatched():
    user, action = imports.resolve_or_create_user(
        "Persona Inexistente", {}, password="x", dry=False
    )
    assert action == "unmatched" and user is None
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_imports_helpers.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'apps.core.services.imports'`).

- [ ] **Step 3: Implementar el servicio**

Crear `apps/core/services/imports.py`:

```python
"""Helpers para importar proyectos y membresías desde el xlsx de Talento."""

from datetime import date, datetime

from apps.core.text import normalize_name

# Personas que aparecen en el Excel pero no existen como usuario: se crean.
# clave: nombre normalizado -> (nombre completo, correo)
USERS_TO_CREATE = {
    normalize_name("Carolina Palacio"): (
        "Carolina Palacio", "carolina.palacio@arena-analytics.com",
    ),
    normalize_name("Carlos Alejandro Rodríguez Ochoa"): (
        "Carlos Alejandro Rodríguez Ochoa", "carlos.rodriguez@arena-analytics.com",
    ),
    normalize_name("Arturo Carranza Lucio"): (
        "Arturo Carranza Lucio", "arturo.carranza@arena-analytics.com",
    ),
}

# Clasificación FINITO/INDEFINIDO validada (spec 2026-06-12).
_DURATION_RAW = {
    "MSI": "FINITO",
    "Share Forecast LATAM / Apollo 2.0": "INDEFINIDO",
    "Data Ops / MPM": "INDEFINIDO",
    "GenAI": "FINITO",
    "AI Latam Office Program Manager": "INDEFINIDO",
    "OBPPC": "INDEFINIDO",
    "Weather": "FINITO",
    "Migración 360 a 720": "FINITO",
    "CCL Engineering Cell": "INDEFINIDO",
    "Hypercare Migración 360 a 720": "FINITO",
    "Business Terms Harmonization & SSOT": "FINITO",
    "Rodin": "INDEFINIDO",
    "Urrea Bolsa de Horas": "INDEFINIDO",
    "Coppel Portal (Sistema de Gestión de Categorías)": "FINITO",
    "NSR PM & Comm": "FINITO",
    "Prime Partners Support": "INDEFINIDO",
    "C&CL Report": "FINITO",
}
DURATION_BY_PROJECT = {normalize_name(k): v for k, v in _DURATION_RAW.items()}


def build_user_index(users, alias_pairs=()):
    """Devuelve {nombre_normalizado: user}.

    alias_pairs: iterable de (nombre_corto, correo) del HC Total para
    resolver nombres que no empatan por el nombre completo.
    """
    index = {}
    for u in users:
        key = normalize_name(u.full_name)
        if key:
            index[key] = u
    by_email = {u.email.lower(): u for u in users}
    for short, email in alias_pairs:
        u = by_email.get((email or "").strip().lower())
        if u:
            index.setdefault(normalize_name(short), u)
    return index


def resolve_user(name, index):
    """Resuelve un nombre a User por igualdad y por substring bidireccional."""
    norm = normalize_name(name)
    if not norm:
        return None
    if norm in index:
        return index[norm]
    for key, u in index.items():
        if key and (key in norm or norm in key):
            return u
    return None


def resolve_or_create_user(name, index, *, password, dry):
    """Resuelve un nombre; si está en USERS_TO_CREATE y no existe, lo crea.

    Devuelve (user|None, action) con action en
    {'found', 'created', 'would_create', 'unmatched', 'empty'}.
    Muta `index` al crear, para que llamadas siguientes lo encuentren.
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()
    if not name or not str(name).strip():
        return None, "empty"
    user = resolve_user(name, index)
    if user:
        return user, "found"
    key = normalize_name(name)
    if key in USERS_TO_CREATE:
        full_name, email = USERS_TO_CREATE[key]
        if dry:
            return None, "would_create"
        user, _ = User.objects.get_or_create(
            email=email,
            defaults={"full_name": full_name, "role": User.Role.COLABORADOR},
        )
        user.set_password(password)
        user.must_change_password = False
        user.save()
        index[key] = user
        return user, "created"
    return None, "unmatched"


def to_date(value):
    """Convierte celdas datetime/date/None a date o None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return None
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_imports_helpers.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add apps/core/services/imports.py apps/core/tests/test_imports_helpers.py
git commit -m "feat(core): servicio de importación (índices, resolución, mapas)"
```

---

## Task 4: Añadir openpyxl a requirements

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Añadir la dependencia**

En `requirements.txt`, bajo la sección "Desarrollo / pruebas", añadir:

```
# Lectura de xlsx para importaciones de Talento (comandos import_*)
openpyxl>=3.1
```

- [ ] **Step 2: Verificar que está instalado en el venv**

Run: `.\.venv\Scripts\python.exe -c "import openpyxl; print(openpyxl.__version__)"`
Expected: imprime una versión `3.1.x` (ya instalado en este entorno).

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "build: openpyxl para importaciones desde xlsx"
```

---

## Task 5: Comando `import_projects`

**Files:**
- Create: `apps/core/management/commands/import_projects.py`
- Test: `apps/core/tests/test_import_commands.py`

- [ ] **Step 1: Escribir la prueba que falla**

Crear `apps/core/tests/test_import_commands.py`:

```python
"""Comandos import_projects / import_memberships contra un xlsx generado."""

from datetime import datetime

import openpyxl
import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.catalog.models import Project, ProjectMembership

User = get_user_model()


def _build_workbook(path):
    wb = openpyxl.Workbook()
    hc = wb.active
    hc.title = "HC Total Nov 2024-2026"
    hc.append([
        "No", "NOMBRE COMPLETO", "Nombre corto", "Correo", "Área", "Puesto",
        "Cliente", "Proyecto 1", "Evaluador 1",
    ])
    hc.append([
        1, "ANA LOPEZ PEREZ", "Ana Lopez", "ana@arena-analytics.com",
        "Analítica", "Ing Jr", "Cliente X", "Weather", "Ana Lopez",
    ])

    duenos = wb.create_sheet("Proyectos Dueños")
    duenos.append([
        "ID", "Nombre", "Cliente", "Owner", "Responsable",
        "Kick-off", "Target Cierre", "Status", "Descripción",
    ])
    # Proyecto cuyo owner ya existe (Ana) -> FINITO por la tabla (Weather)
    duenos.append([
        "P8", "Weather", "Cliente X", "Ana Lopez", "Ana Lopez",
        datetime(2026, 1, 20), datetime(2026, 6, 5), "On track", "",
    ])
    # Proyecto cuyo owner hay que CREAR (Carolina Palacio) -> Coppel = FINITO
    duenos.append([
        "P11", "Coppel Portal (Sistema de Gestión de Categorías)", "Coppel",
        "Carolina Palacio", "Ana Lopez",
        datetime(2025, 1, 13), datetime(2026, 5, 15), "Delayed", "",
    ])

    proj = wb.create_sheet("Proyectos")
    proj.append(["Employee", "Project", "Min of Start", "Max of End"])
    proj.append(["Ana Lopez", "Weather", datetime(2026, 1, 20), datetime(2026, 6, 5)])

    wb.save(path)


@pytest.fixture
def xlsx(tmp_path):
    path = tmp_path / "datos.xlsx"
    _build_workbook(path)
    return str(path)


@pytest.fixture
def ana(db):
    return User.objects.create_user(
        email="ana@arena-analytics.com", password="x", full_name="Ana Lopez Perez",
    )


@pytest.mark.django_db
def test_import_projects_crea_proyectos_y_usuario_faltante(xlsx, ana):
    call_command("import_projects", "--path", xlsx)

    weather = Project.objects.get(name="Weather")
    assert weather.lead == ana
    assert weather.responsable == ana
    assert weather.client == "Cliente X"
    assert weather.duration_type == Project.Duration.FINITO
    assert weather.status == Project.Status.ON_TRACK

    # Carolina Palacio se creó como usuario y quedó como lead de Coppel
    coppel = Project.objects.get(name__startswith="Coppel Portal")
    assert coppel.lead.email == "carolina.palacio@arena-analytics.com"
    assert coppel.status == Project.Status.DELAYED


@pytest.mark.django_db
def test_import_projects_es_idempotente(xlsx, ana):
    call_command("import_projects", "--path", xlsx)
    call_command("import_projects", "--path", xlsx)
    assert Project.objects.filter(name="Weather").count() == 1


@pytest.mark.django_db
def test_import_projects_dry_run_no_escribe(xlsx, ana):
    call_command("import_projects", "--path", xlsx, "--dry-run")
    assert Project.objects.count() == 0
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_import_commands.py -v`
Expected: FAIL (`CommandError: Unknown command: 'import_projects'`).

- [ ] **Step 3: Implementar el comando**

Crear `apps/core/management/commands/import_projects.py`:

```python
"""Importa proyectos desde la hoja 'Proyectos Dueños' del xlsx de Talento.

Idempotente por nombre de proyecto. Crea los usuarios faltantes definidos en
imports.USERS_TO_CREATE. Asigna duration_type según imports.DURATION_BY_PROJECT.

Uso (contra DATABASE_URL):
  manage.py import_projects --dry-run
  manage.py import_projects
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Project
from apps.core.services import imports
from apps.core.text import normalize_name

User = get_user_model()

DEFAULT_XLSX = "Quien evalua a quien Analítica 1er S 2026.xlsx"
HC_SHEET = "HC Total Nov 2024-2026"
OWNERS_SHEET = "Proyectos Dueños"


def _header_index(row):
    return {str(v).strip().lower(): i for i, v in enumerate(row) if v is not None}


class Command(BaseCommand):
    help = "Importa proyectos desde la hoja 'Proyectos Dueños' del xlsx de Talento."

    def add_arguments(self, parser):
        parser.add_argument("--path", default=None)
        parser.add_argument("--password", default="Arena2026!")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        import openpyxl

        path = Path(options["path"]) if options["path"] else (
            Path(settings.BASE_DIR) / "docs" / "Modelos" / DEFAULT_XLSX
        )
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"No se encontró {path}"))
            return

        wb = openpyxl.load_workbook(path, data_only=True)
        alias_pairs = self._alias_pairs(wb)
        dry = options["dry_run"]
        password = options["password"]

        rows = list(wb[OWNERS_SHEET].iter_rows(values_only=True))
        header = _header_index(rows[0])
        col = lambda name: header.get(name)

        created = updated = 0
        unmatched = []

        with transaction.atomic():
            index = imports.build_user_index(User.objects.all(), alias_pairs)
            for raw in rows[1:]:
                name = (raw[col("nombre")] or "").strip() if col("nombre") is not None else ""
                if not name:
                    continue
                owner_name = raw[col("owner")] if col("owner") is not None else None
                resp_name = raw[col("responsable")] if col("responsable") is not None else None

                lead, lead_action = imports.resolve_or_create_user(
                    owner_name, index, password=password, dry=dry
                )
                if lead_action in ("would_create", "created"):
                    self.stdout.write(f"[{'dry' if dry else 'ok'}] usuario owner: {owner_name}")
                if lead is None:
                    unmatched.append(f"Owner no resuelto: {owner_name!r} ({name})")
                    continue
                responsable, _ = imports.resolve_or_create_user(
                    resp_name, index, password=password, dry=dry
                )

                client = (raw[col("cliente")] or "").strip() if col("cliente") is not None else ""
                status_raw = (raw[col("status")] or "").strip().lower() if col("status") is not None else ""
                status = Project.Status.DELAYED if "delay" in status_raw else Project.Status.ON_TRACK
                kickoff = imports.to_date(raw[col("kick-off")]) if col("kick-off") is not None else None
                target = imports.to_date(raw[col("target cierre")]) if col("target cierre") is not None else None
                duration = imports.DURATION_BY_PROJECT.get(normalize_name(name), Project.Duration.FINITO)

                if dry:
                    self.stdout.write(
                        f"[dry] {name} | lead={lead} | resp={responsable} | "
                        f"{duration} | {status} | {kickoff}–{target}"
                    )
                    continue

                project, is_new = Project.objects.get_or_create(
                    name=name, defaults={"lead": lead},
                )
                project.client = client
                project.lead = lead
                project.responsable = responsable
                project.kickoff = kickoff
                project.target_close = target
                project.status = status
                project.duration_type = duration
                project.is_active = True
                project.save()
                created += int(is_new)
                updated += int(not is_new)

            if dry:
                transaction.set_rollback(True)

        for msg in unmatched:
            self.stdout.write(self.style.WARNING(msg))
        self.stdout.write(self.style.SUCCESS(
            f"Proyectos — nuevos: {created} · actualizados: {updated} · sin resolver: {len(unmatched)}"
        ))

    def _alias_pairs(self, wb):
        """(nombre corto, correo) desde HC Total para resolver por correo."""
        if HC_SHEET not in wb.sheetnames:
            return []
        rows = list(wb[HC_SHEET].iter_rows(values_only=True))
        if not rows:
            return []
        header = _header_index(rows[0])
        i_short = header.get("nombre corto")
        i_email = header.get("correo")
        if i_short is None or i_email is None:
            return []
        pairs = []
        for raw in rows[1:]:
            short = raw[i_short] if i_short < len(raw) else None
            email = raw[i_email] if i_email < len(raw) else None
            if short and email:
                pairs.append((str(short).strip(), str(email).strip()))
        return pairs
```

Nota sobre `--dry-run`: usa `transaction.set_rollback(True)` para no escribir nada (incluidos usuarios). En dry-run, `resolve_or_create_user` devuelve `would_create` y el proyecto se reporta como "sin resolver" en seco — es esperado; en la corrida real sí se crean.

- [ ] **Step 4: Correr y verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_import_commands.py::test_import_projects_crea_proyectos_y_usuario_faltante apps/core/tests/test_import_commands.py::test_import_projects_es_idempotente apps/core/tests/test_import_commands.py::test_import_projects_dry_run_no_escribe -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add apps/core/management/commands/import_projects.py apps/core/tests/test_import_commands.py
git commit -m "feat(core): comando import_projects desde xlsx"
```

---

## Task 6: Comando `import_memberships`

**Files:**
- Create: `apps/core/management/commands/import_memberships.py`
- Test: `apps/core/tests/test_import_commands.py` (añadir casos)

- [ ] **Step 1: Añadir pruebas que fallan**

Añadir a `apps/core/tests/test_import_commands.py`:

```python
@pytest.mark.django_db
def test_import_memberships_crea_membresias_con_fechas(xlsx, ana):
    call_command("import_projects", "--path", xlsx)
    call_command("import_memberships", "--path", xlsx)

    weather = Project.objects.get(name="Weather")
    m = ProjectMembership.objects.get(project=weather, user=ana)
    assert m.start is not None and m.end is not None


@pytest.mark.django_db
def test_import_memberships_idempotente(xlsx, ana):
    call_command("import_projects", "--path", xlsx)
    call_command("import_memberships", "--path", xlsx)
    call_command("import_memberships", "--path", xlsx)
    weather = Project.objects.get(name="Weather")
    assert ProjectMembership.objects.filter(project=weather).count() == 1


@pytest.mark.django_db
def test_import_memberships_fill_down_empleado_en_blanco(tmp_path, ana):
    # Hoja Proyectos con relleno hacia abajo: 2da fila sin Employee
    path = tmp_path / "fd.xlsx"
    _build_workbook(path)
    wb = openpyxl.load_workbook(path)
    proj = wb["Proyectos"]
    proj.append([None, "Coppel Portal (Sistema de Gestión de Categorías)",
                 datetime(2025, 1, 13), datetime(2026, 5, 15)])
    wb.save(path)

    call_command("import_projects", "--path", str(path))
    call_command("import_memberships", "--path", str(path))

    coppel = Project.objects.get(name__startswith="Coppel Portal")
    # La fila en blanco se atribuye a Ana (la de arriba)
    assert ProjectMembership.objects.filter(project=coppel, user=ana).exists()
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_import_commands.py -k memberships -v`
Expected: FAIL (`Unknown command: 'import_memberships'`).

- [ ] **Step 3: Implementar el comando**

Crear `apps/core/management/commands/import_memberships.py`:

```python
"""Importa membresías (equipo por proyecto) desde la hoja 'Proyectos' del xlsx.

Idempotente por (proyecto, usuario). Empareja Employee → usuario con el índice
de nombres (alias por correo del HC Total). Aplica relleno hacia abajo del
Employee en blanco. Reporta filas sin proyecto o sin usuario.

Uso:
  manage.py import_memberships --dry-run
  manage.py import_memberships
"""

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.models import Project, ProjectMembership
from apps.core.services import imports
from apps.core.text import normalize_name

User = get_user_model()

DEFAULT_XLSX = "Quien evalua a quien Analítica 1er S 2026.xlsx"
HC_SHEET = "HC Total Nov 2024-2026"
MEMB_SHEET = "Proyectos"


def _header_index(row):
    return {str(v).strip().lower(): i for i, v in enumerate(row) if v is not None}


class Command(BaseCommand):
    help = "Importa membresías desde la hoja 'Proyectos' del xlsx de Talento."

    def add_arguments(self, parser):
        parser.add_argument("--path", default=None)
        parser.add_argument("--password", default="Arena2026!")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        import openpyxl

        path = Path(options["path"]) if options["path"] else (
            Path(settings.BASE_DIR) / "docs" / "Modelos" / DEFAULT_XLSX
        )
        if not path.exists():
            self.stderr.write(self.style.ERROR(f"No se encontró {path}"))
            return

        wb = openpyxl.load_workbook(path, data_only=True)
        alias_pairs = self._alias_pairs(wb)
        dry = options["dry_run"]
        password = options["password"]

        rows = list(wb[MEMB_SHEET].iter_rows(values_only=True))
        header = _header_index(rows[0])
        i_emp = header.get("employee")
        i_proj = header.get("project")
        i_start = header.get("min of start")
        i_end = header.get("max of end")

        projects = {normalize_name(p.name): p for p in Project.objects.all()}

        created = skipped = 0
        unmatched = []
        last_emp = None

        with transaction.atomic():
            index = imports.build_user_index(User.objects.all(), alias_pairs)
            for raw in rows[1:]:
                emp = raw[i_emp] if i_emp is not None and i_emp < len(raw) else None
                emp = str(emp).strip() if emp else None
                if emp:
                    last_emp = emp           # relleno hacia abajo
                emp = emp or last_emp

                proj_name = raw[i_proj] if i_proj is not None and i_proj < len(raw) else None
                if not emp or not proj_name:
                    continue

                project = projects.get(normalize_name(str(proj_name)))
                if project is None:
                    unmatched.append(f"Proyecto no encontrado: {proj_name!r}")
                    continue
                user, action = imports.resolve_or_create_user(
                    emp, index, password=password, dry=dry
                )
                if action in ("would_create", "created"):
                    self.stdout.write(f"[{'dry' if dry else 'ok'}] usuario miembro: {emp}")
                if user is None:
                    unmatched.append(f"Usuario no encontrado: {emp!r} ({proj_name})")
                    continue

                start = imports.to_date(raw[i_start]) if i_start is not None else None
                end = imports.to_date(raw[i_end]) if i_end is not None else None

                if dry:
                    self.stdout.write(f"[dry] {user.full_name} ∈ {project.name} ({start}–{end})")
                    continue

                m, is_new = ProjectMembership.objects.get_or_create(
                    project=project, user=user,
                )
                m.start = start
                m.end = end
                m.save()
                created += int(is_new)
                skipped += int(not is_new)

            if dry:
                transaction.set_rollback(True)

        for msg in unmatched:
            self.stdout.write(self.style.WARNING(msg))
        self.stdout.write(self.style.SUCCESS(
            f"Membresías — nuevas: {created} · ya existían: {skipped} · sin resolver: {len(unmatched)}"
        ))

    def _alias_pairs(self, wb):
        if HC_SHEET not in wb.sheetnames:
            return []
        rows = list(wb[HC_SHEET].iter_rows(values_only=True))
        if not rows:
            return []
        header = _header_index(rows[0])
        i_short = header.get("nombre corto")
        i_email = header.get("correo")
        if i_short is None or i_email is None:
            return []
        pairs = []
        for raw in rows[1:]:
            short = raw[i_short] if i_short < len(raw) else None
            email = raw[i_email] if i_email < len(raw) else None
            if short and email:
                pairs.append((str(short).strip(), str(email).strip()))
        return pairs
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_import_commands.py -v`
Expected: PASS (todos, incluyendo los de Task 5).

- [ ] **Step 5: Commit**

```bash
git add apps/core/management/commands/import_memberships.py apps/core/tests/test_import_commands.py
git commit -m "feat(core): comando import_memberships desde xlsx (con fill-down)"
```

---

## Task 7: Exponer los campos nuevos en `ProjectForm` + template

**Files:**
- Modify: `apps/catalog/forms.py` (`ProjectForm`, líneas 32-55)
- Modify: `templates/catalog/project_form.html`
- Test: `apps/core/tests/test_project_extra_fields.py` (añadir caso de form)

- [ ] **Step 1: Añadir prueba que falla**

Añadir a `apps/core/tests/test_project_extra_fields.py`:

```python
from datetime import date as _date

from apps.catalog.forms import ProjectForm


@pytest.mark.django_db
def test_projectform_guarda_campos_nuevos(lead):
    resp = User.objects.create_user(
        email="resp2@arena-analytics.com", password="x", full_name="Responsable Dos",
    )
    form = ProjectForm(data={
        "name": "Con Form", "client": "C", "lead": lead.pk, "responsable": resp.pk,
        "duration_type": Project.Duration.FINITO, "is_active": "on",
        "kickoff": "2026-01-01", "target_close": "2026-06-30", "status": "DELAYED",
    })
    assert form.is_valid(), form.errors
    p = form.save()
    assert p.responsable == resp
    assert p.kickoff == _date(2026, 1, 1)
    assert p.status == Project.Status.DELAYED
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_project_extra_fields.py::test_projectform_guarda_campos_nuevos -v`
Expected: FAIL (los campos nuevos no están en el form → no se guardan; `responsable` queda None).

- [ ] **Step 3: Extender `ProjectForm`**

En `apps/catalog/forms.py`, reemplazar la clase `Meta` de `ProjectForm` y su `__init__`:

```python
    class Meta:
        model = Project
        fields = [
            "name", "client", "lead", "responsable",
            "duration_type", "status", "kickoff", "target_close", "is_active",
        ]
        labels = {
            "name": "Nombre del proyecto",
            "client": "Cliente",
            "lead": "Lead (Owner)",
            "responsable": "Responsable",
            "duration_type": "Tipo de duración",
            "status": "Estatus",
            "kickoff": "Kick-off",
            "target_close": "Cierre objetivo",
            "is_active": "Activo",
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ej. Tablero Comercial"}),
            "client": forms.TextInput(attrs={"class": _INPUT, "placeholder": "Ej. Cliente Retail (opcional)"}),
            "lead": forms.Select(attrs={"class": _INPUT}),
            "responsable": forms.Select(attrs={"class": _INPUT}),
            "duration_type": forms.RadioSelect(),
            "status": forms.Select(attrs={"class": _INPUT}),
            "kickoff": forms.DateInput(attrs={"class": _INPUT, "type": "date"}, format="%Y-%m-%d"),
            "target_close": forms.DateInput(attrs={"class": _INPUT, "type": "date"}, format="%Y-%m-%d"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        active = self.fields["lead"].queryset.filter(is_active=True)
        self.fields["lead"].queryset = active
        self.fields["lead"].empty_label = "— Selecciona un Lead —"
        self.fields["responsable"].queryset = active
        self.fields["responsable"].empty_label = "— Sin responsable —"
        self.fields["responsable"].required = False
```

- [ ] **Step 4: Renderizar los campos en el template**

En `templates/catalog/project_form.html`, dentro del `<form>` de "Datos del proyecto", justo después del bloque del campo `lead` (línea ~25, antes del bloque `duration_type`), insertar:

```html
      <div>
        <label class="label" for="{{ form.responsable.id_for_label }}">{{ form.responsable.label }}</label>
        {{ form.responsable }}
        {% for e in form.responsable.errors %}<p class="mt-1 text-sm text-rose-600">{{ e }}</p>{% endfor %}
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="label" for="{{ form.kickoff.id_for_label }}">{{ form.kickoff.label }}</label>
          {{ form.kickoff }}
        </div>
        <div>
          <label class="label" for="{{ form.target_close.id_for_label }}">{{ form.target_close.label }}</label>
          {{ form.target_close }}
        </div>
      </div>
      <div>
        <label class="label" for="{{ form.status.id_for_label }}">{{ form.status.label }}</label>
        {{ form.status }}
      </div>
```

- [ ] **Step 5: Correr la prueba y verificar que pasa**

Run: `.\.venv\Scripts\python.exe -m pytest apps/core/tests/test_project_extra_fields.py -v`
Expected: PASS (todos).

- [ ] **Step 6: Commit**

```bash
git add apps/catalog/forms.py templates/catalog/project_form.html apps/core/tests/test_project_extra_fields.py
git commit -m "feat(catalog): editar responsable/fechas/status en el formulario de proyecto"
```

---

## Task 8: Suite completa + corrida real contra Neon (verificación manual)

**Files:** ninguno (operación)

- [ ] **Step 1: Correr toda la suite (regresión)**

Run: `.\.venv\Scripts\python.exe -m pytest -q`
Expected: todos los tests existentes + nuevos en verde.

- [ ] **Step 2: Dry-run de proyectos contra Neon**

```powershell
$env:DATABASE_URL = "<URL Neon unpooled de docs/neon.md>"
$env:PYTHONUTF8 = "1"
.\.venv\Scripts\python.exe manage.py import_projects --dry-run
```
Expected: lista los 17 proyectos y reporta "crearía usuario" para Carolina Palacio y Carlos Alejandro Rodríguez Ochoa. Revisar que no haya owners "sin resolver" inesperados.

- [ ] **Step 3: Corrida real de proyectos**

Run: `.\.venv\Scripts\python.exe manage.py import_projects`
Expected: "Proyectos — nuevos: 17 · actualizados: 0 · sin resolver: 0". Se crean Carolina Palacio y Carlos Alejandro Rodríguez Ochoa (owners).

- [ ] **Step 4: Dry-run de membresías**

Run: `.\.venv\Scripts\python.exe manage.py import_memberships --dry-run`
Expected: lista membresías; reporta `[dry] usuario miembro: Arturo Carranza Lucio` (se creará en la corrida real). Revisar que no haya otros "Usuario no encontrado" inesperados.

- [ ] **Step 5: Corrida real de membresías**

Run: `.\.venv\Scripts\python.exe manage.py import_memberships`
Expected: nuevas = número de filas válidas; sin resolver = 0. Arturo Carranza Lucio se crea automáticamente.

- [ ] **Step 6: Verificación en BD y UI**

```powershell
.\.venv\Scripts\python.exe manage.py shell -c "from apps.catalog.models import Project, ProjectMembership; print('proyectos', Project.objects.count()); print('membresias', ProjectMembership.objects.count())"
```
Expected: 17 proyectos; membresías > 0. Luego abrir `/catalogos/proyectos/<id>/` en el navegador, confirmar que responsable/kickoff/target_close/status se muestran y guardan, y que el panel de Equipo lista a los miembros importados.

- [ ] **Step 7: Snapshot post-import (punto de retorno)**

```powershell
.\.venv\Scripts\python.exe manage.py dumpdata accounts catalog questionnaires evaluations --indent 2 -o backups\snapshot_2026-06-12_post-import.json
```

---

## Self-review (cobertura del spec)

- Migración con responsable/kickoff/target_close/status → Task 1. ✅
- 3 usuarios nuevos → `resolve_or_create_user` (Task 3) usado por ambos comandos: Carolina y Carlos vía `import_projects` (owners), Arturo vía `import_memberships` (miembro). Sin pasos manuales. ✅
- Clasificación FINITO/INDEFINIDO → `DURATION_BY_PROJECT` (Task 3). ✅
- import_projects idempotente + dry-run → Task 5. ✅
- import_memberships con fechas + fill-down + matching por alias → Task 6. ✅
- Evaluador no se persiste → no hay campo; confirmado. ✅
- Fechas a nivel proyecto, membresías sin UI → form expone kickoff/target_close del proyecto; panel de equipo sin cambios. ✅
- openpyxl como dependencia → Task 4. ✅
- Edición en UI de los 4 campos → Task 7. ✅
- Verificación (dry-run, conteos, UI, snapshot) → Task 8. ✅
