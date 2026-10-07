# Implementation Plan: Arena Learn — solicitud, autorización y registro de cursos con costo

**Branch**: `004-arena-learn-cursos` | **Date**: 2026-10-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-arena-learn-cursos/spec.md`

## Summary

Se reemplaza el proceso de Forms/SharePoint por un flujo dentro de la plataforma. Se crea la app nueva `apps/learning` con 6 modelos: `CatalogCourse`, `CourseRequest`, `ApprovalStep`, `CourseEvidence`, `CourseReview` y `LearningSettings`. Su lógica vive en `apps/core/services/learning_flow.py` y su visibilidad en `permissions.py`.

El flujo es secuencial: Lead → Dirección → Talento, con omisión automática de etapas y una bitácora inmutable. Después solo se registra el pago (sin gestionarlo), se cierra el curso con evidencia y reseña (archivos en la BD, máximo 4 MB) y se publica la sección Arena Learn en un perfil consultable por todo Arena. Esa publicación es una excepción acotada a RN-14.

También cambian dos modelos existentes, cada uno con su migración: `User.direct_lead` y `Area.director` (Clarifications 2026-10-06). Las notificaciones se reutilizan: la campana siempre y el correo cuando hay SMTP.

## Technical Context

**Language/Version**: Python 3.14 (local) / 3.12 (Vercel), Django 6.0

**Primary Dependencies**: Django, django-simple-history (bitácora de campos), Pillow (re-encode de imágenes de evidencia), openpyxl (exporte), htmx, Alpine y Lucide vendorizados. **No se agregan dependencias nuevas.**

**Storage**: Postgres (Neon). Los archivos de evidencia van en BinaryField, mismo patrón que `User.photo_data` (research R3). Hay 3 migraciones: `accounts` (direct_lead), `catalog` (Area.director) y `learning` (0001 + seed de `LearningSettings`).

**Testing**: pytest + pytest-django contra `test_neondb` con `--reuse-db`. Los archivos nuevos son `apps/core/tests/test_learning_flow.py` (servicio y máquina de estados), `test_learning_permissions.py` (visibilidad pública/privada) y `test_learning_views.py` (vistas, subida de archivos, htmx). Cubren el camino feliz y los errores de cada servicio.

**Target Platform**: Vercel (FS de solo lectura, cuerpo de request ≤ 4.5 MB) + Neon

**Project Type**: Web application monolítica Django (server-rendered)

**Performance Goals**: unos 65 usuarios y menos de 300 cursos al año. Los listados usan `select_related`/`prefetch_related`, y el perfil público y el catálogo no deben hacer N+1. Las fotos usan miniatura (`?mini=1`).

**Constraints**:
- Archivos de máximo 4 MB, con tipo validado por magic bytes.
- Los campos privados nunca llegan al contexto de las plantillas públicas.
- La campana no debe agregar más de 3 consultas por request.

**Scale/Scope**:
- 1 app nueva, unas 26 rutas y unas 14 plantillas.
- Cambios en `accounts` (modelo, form y template de Usuarios, tab en perfil), `catalog` (Area.director), `core` (servicio, permisos, context processors de navegación y notificaciones) y `config` (INSTALLED_APPS, urls).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` sigue siendo la plantilla sin ratificar, así que no hay gates formales. Se verifican las convenciones de facto del repo (`docs/CONTEXTO_Sistema.md`):

| Convención | Cumple |
|---|---|
| Lógica en `apps/core/services/`, no en vistas ni plantillas | ✅ `learning_flow.py` |
| Visibilidad filtrada a nivel queryset en `permissions.py` | ✅ funciones nuevas; `visible_users` intacto |
| Sin CDN; vendor local; Tailwind compilado con `build_css.ps1` | ✅ sin librerías nuevas |
| Archivos en BD (FS de Vercel de solo lectura) | ✅ R3 |
| UI en español, código en inglés | ✅ |
| Migraciones aplicadas manualmente a Neon | ✅ quickstart |

*Re-chequeo post-diseño*: sin violaciones. La única desviación es la app nueva, justificada en R1.

## Project Structure

### Documentation (this feature)

```text
specs/004-arena-learn-cursos/
├── spec.md
├── plan.md              # este archivo
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/routes.md  # Fase 1: rutas + servicios + permisos
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
apps/
├── learning/                       # NUEVA
│   ├── apps.py, admin.py
│   ├── models.py                   # CatalogCourse, CourseRequest, ApprovalStep, CourseEvidence, CourseReview, LearningSettings
│   ├── forms.py                    # RequestForm, ReviewForm, EvidenceUploadForm, CatalogCourseForm, PaymentForm, DecisionForm, SettingsForm
│   ├── views.py                    # validar → servicio → render (parcial htmx cuando aplica)
│   ├── urls.py                     # app_name="learning"
│   └── migrations/0001_initial.py, 0002_seed_settings.py
├── accounts/
│   ├── models.py                   # + User.direct_lead
│   ├── forms.py / views.py         # user_admin: columna "Lead directo"; profile: tab Arena Learn
│   └── migrations/00xx_user_direct_lead.py
├── catalog/
│   ├── models.py                   # + Area.director
│   └── migrations/00xx_area_director.py
└── core/
    ├── services/learning_flow.py   # NUEVO: máquina de estados, aprobadores, evidencia, tablero
    ├── services/permissions.py     # + funciones de Arena Learn
    ├── context_processors.py       # navigation: ítem Arena Learn; notifications: pendientes de Learn
    └── tests/test_learning_flow.py, test_learning_permissions.py, test_learning_views.py

config/settings.py                  # INSTALLED_APPS += "apps.learning"
config/urls.py                      # path("arena-learn/", include("apps.learning.urls"))

templates/learning/
├── my_courses.html, request_form.html, request_detail.html, _decision_row.html, _payment_block.html
├── complete_form.html, direct_form.html, approvals_inbox.html
├── catalog_list.html, catalog_detail.html, catalog_form.html
├── people_list.html, person_profile.html, course_public.html
├── tracking.html, settings_form.html
templates/accounts/profile.html, user_admin.html   # tab Arena Learn y columna Lead directo
```

**Structure Decision**: se crea la app Django `apps/learning` para modelos, URLs y vistas. La lógica y los permisos van en `apps/core/services/`, según la convención del repo, y las pruebas en `apps/core/tests/`.

## Fases de entrega sugeridas (MVP primero)

1. **MVP (P1)**: modelos y migraciones, Lead directo y Director de área, US1 (solicitud), US2 (autorización + bandeja + campana) y US4 (cierre con evidencia y reseña). Con esto ya se puede dar de baja el Forms.
2. **P2**: US5 (perfil público y directorio), US6 (catálogo y promoción), US3 (pago e instrucciones fiscales) y registro directo.
3. **P3**: US7 (tablero, alertas y exporte) y carga histórica.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| App Django nueva (`apps/learning`) | Dominio nuevo, independiente de periodos, con 6 modelos | Meterlo en `evaluations` lo acopla a `EvaluationPeriod` y su ciclo de cierre |
| Archivos en BD | El FS de Vercel es de solo lectura y no hay storage de objetos | Vercel Blob: dependencia + token + subida directa, desproporcionado para menos de 0.5 GB al año |
