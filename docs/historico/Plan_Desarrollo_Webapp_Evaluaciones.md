# Plan de Desarrollo — Webapp de Evaluaciones de Desempeño Arena
## Stack: Django · Alpine.js · Tailwind CSS

> **Documento compañero de:** `KB_Modelo_Desempeno_2026.md` (fuente de verdad de reglas de negocio, escalas, fórmulas y cuestionarios). Este plan define la arquitectura, el modelo de datos, los permisos, el seed y las fases de construcción. Las reglas de negocio se referencian por su ID (RN-xx) del KB.

---

## 1. Visión del producto

Sistema web interno para ejecutar el Modelo de Desempeño Analítica 2026: cada colaborador responde su checklist de Ownership según su área/nivel y por proyecto; el líder de proyecto valida y captura la Entrega de Valor; Talento captura Impacto Arena y administra catálogos; el sistema calcula promedios (excluyendo N/A), pondera por seniority y muestra resultados con segregación estricta de visibilidad.

**Usuarios:** ~54 colaboradores, 4 áreas × 4 niveles, equipo de Talento y un superusuario.

---

## 2. Stack técnico y decisiones de arquitectura

> **Regla general de versiones:** usar siempre la **última versión estable** de todos los assets y dependencias al momento de iniciar el desarrollo (Django 6.x, Alpine.js, Tailwind, htmx, Python, librerías). Verificar versiones vigentes antes de fijar el lockfile.

| Capa | Elección | Justificación |
|------|----------|---------------|
| Backend | **Django 6.x** (última estable) + Python 3.13 | Admin integrado, auth robusto, ORM, velocidad de desarrollo |
| Frontend | Templates de Django + **htmx (última versión)** para actualizaciones parciales servidor→pantalla + **Alpine.js 3 (última versión)** para estado/interactividad local | Actualización en pantalla sin recargas ni POST de página completa; es el sucesor moderno del patrón AJAX clásico y se integra nativamente con Django |
| Estilos | **Tailwind CSS v4** (última versión, vía CLI o `django-tailwind`) | Sistema de diseño utilitario, build simple |
| BD | **SQLite en desarrollo local** → **PostgreSQL gestionado** (Neon / Vercel Postgres / Supabase) en preview y producción | Vercel es serverless: sin filesystem persistente ni volúmenes, SQLite no puede usarse desplegado. Decisión confirmada: Vercel + Postgres gestionado; SQLite solo local |
| Auth | `django.contrib.auth` con modelo de usuario custom (email como username) | El correo @arena-analytics.com es el identificador natural. SSO Microsoft Entra ID como mejora futura (v2) |
| Tareas async | Ninguna en v1 (cálculos síncronos, correo con `send_mail`) | Volumen pequeño; evitar complejidad |
| Despliegue | **Vercel** (runtime Python/serverless + whitenoise o CDN para estáticos) | Decisión de publicación del proyecto; cada despliegue se ejecuta con la skill de Vercel |
| Auditoría | `django-simple-history` en modelos críticos | Trazabilidad de cambios en evaluaciones y catálogos |

**Principios:**
- **Actualización en pantalla sin POST de página completa siempre que sea posible:** toda interacción (autosave, validaciones, filtros, cambios de estado, colas, tablas) se resuelve con peticiones asíncronas (htmx/fetch) que actualizan fragmentos de la pantalla. La recarga completa es la excepción, no la regla.
- Server-side rendering con respuestas parciales (templates parciales para htmx); endpoints JSON internos donde aplique (autosave). Sin API REST pública en v1.
- Toda regla de cálculo vive en una capa de servicios (`core/services/scoring.py`) con pruebas unitarias — nunca en templates ni views.
- Los cuestionarios son **datos, no código**: motor genérico de formularios dirigido por el catálogo.
- **Idioma:** el sistema es 100% en **español**. `LANGUAGE_CODE = "es-mx"`, zona horaria de México. Toda la terminología de la interfaz usa exactamente los conceptos del KB y los documentos fuente: *Ownership, Entrega de Valor, Impacto Arena, Checklist, Fortalezas, Oportunidades, Comentarios, No cumple / Cumple parcial / Cumple / Excede, N/A, Lead, Evaluado, Líder de proyecto, Talento y Cultura, Periodo*. El código (modelos, variables) se escribe en inglés; las etiquetas visibles, mensajes, correos y validaciones, en español.

### 2.1 Skills obligatorias durante el desarrollo

El agente/equipo que construya este sistema debe usar las siguientes skills de forma **obligatoria y recurrente**, no opcional:

| Skill | Cuándo se invoca | Regla |
|-------|------------------|-------|
| **UX UI Pro Max** | **Siempre**, en cualquier trabajo de UX o UI: diseño de cada pantalla, componente, flujo, microinteracción, estados vacíos, responsive, accesibilidad | Usar todos sus "super powers" para cualquier necesidad de experiencia e interfaz. Ninguna pantalla se diseña ni se ajusta sin pasar por esta skill |
| **Feature skill** | **Al inicio de cada feature** del backlog/fases | Cada feature se construye invocando la skill, siguiendo su workflow completo y **revisando el workflow al cierre** (definición → implementación → revisión). Ningún feature se da por terminado sin esa revisión |
| **Code simplifier** | Después de implementar cada módulo/feature y antes de cerrar cada fase | Pasada de simplificación sobre el código nuevo: menos complejidad, menos duplicación, más legibilidad, conservando el comportamiento |
| **Vercel** | **En toda publicación o despliegue** (preview y producción), y para la configuración inicial del proyecto en Vercel | Cualquier deploy, variable de entorno, dominio o ajuste de build en Vercel se hace a través de esta skill |

### 2.2 Manejo de errores amigable (estándar transversal)

El error handling es un requisito de producto, no un detalle técnico. Estándar obligatorio en toda la app:

- **Nunca** mostrar pantallas crudas de error de Django (debug amarillo, stack traces) ni mensajes técnicos al usuario. Páginas 403/404/500 personalizadas, en español, con tono amable y una acción de salida ("Volver a mi tablero").
- **Validación inline y en vivo:** los formularios validan campo por campo vía htmx/Alpine antes del envío; los errores aparecen junto al campo, en lenguaje claro y propositivo ("Para enviar tu evaluación, primero captura las Fortalezas"), nunca códigos ni jerga.
- **Flujo nunca bloqueado:** ante un fallo de red en autosave, reintento automático con indicador discreto ("Guardando… / Guardado / Sin conexión, reintentando") sin perder respuestas capturadas (estado local en Alpine hasta confirmar persistencia).
- **Toasts/notificaciones no intrusivas** para confirmaciones y errores recuperables; modales solo para acciones destructivas o irreversibles (ej. "Enviar evaluación — esta acción no se puede deshacer").
- **Estados vacíos y de carga diseñados** (skeletons, mensajes guía: "Aún no tienes evaluaciones en este periodo. Se habilitarán cuando Talento abra el periodo").
- Los errores de permisos explican el porqué en términos del modelo ("Esta evaluación pertenece a otra área; solo su Lead y Talento pueden verla").
- Logging completo del lado servidor (Sentry o equivalente) para que lo amigable hacia el usuario no oculte errores al equipo técnico.

---

## 3. Estructura del proyecto

```
arena_evals/
├── config/                  # settings (base/dev/prod), urls, wsgi
├── apps/
│   ├── accounts/            # User custom, roles, perfiles
│   ├── catalog/             # Area, SeniorityLevel, Position, Project, Period, PillarWeight
│   ├── questionnaires/      # QuestionnaireTemplate, Section, Question (catálogo administrable)
│   ├── evaluations/         # OwnershipEvaluation, Answer, ValueDeliveryEvaluation, ArenaImpactScore, FinalScore
│   ├── dashboards/          # vistas de resultados, exportes
│   └── core/                # services/ (scoring, permissions), mixins, utils
├── templates/               # base.html + por app
├── static/                  # tailwind build, alpine
├── fixtures/                # seed JSON/YAML (cuestionarios, áreas, niveles, pesos, usuarios)
└── manage.py
```

---

## 4. Modelo de datos

### 4.1 accounts

**User** (extiende `AbstractUser`; `USERNAME_FIELD = email`)
- `email` (único, @arena-analytics.com), `full_name`
- `area` → FK Area (null para Talento/superuser)
- `level` → FK SeniorityLevel (null para Talento/superuser)
- `role` (enum): `COLABORADOR` | `TALENTO` | `DIRECTOR` — el rol `LEAD` **no se guarda aquí**: ser Lead deriva de `level.code == "LEAD"`; ser líder de proyecto deriva del catálogo de proyectos
- `is_active`, `date_joined`

> Decisión: un solo modelo de usuario con rol simple + permisos derivados. Evitar grupos de Django para lógica de negocio (usarlos solo como complemento del admin).

### 4.2 catalog

**Area:** `code` (ID/CD/PM/UXUI), `name`, `is_active`
**SeniorityLevel:** `code` (JR/MID/SNR/LEAD), `name`, `order`
**PillarWeight:** `level` FK, `w_ownership`, `w_value_delivery`, `w_arena_impact` (decimales; validación: suman 1.00) — RN-19. Administrable para futuros ajustes, con historial.
**EvaluationPeriod:** `name` (ej. "2026-S1"), `start_date`, `end_date`, `kind` (`SEMESTRAL`|`TRIMESTRAL`), `status` (`PLANEADO`|`ABIERTO`|`CERRADO`) — RN-13
**Project:** `name`, `client`, `lead` FK User (líder de proyecto), `duration_type` (`FINITO`|`INDEFINIDO`), `is_active`
**ProjectMembership:** `project` FK, `user` FK, `start`, `end` — define el equipo; un usuario con N membresías activas en el periodo puede crear N evaluaciones de Ownership (RN-05, RN-16)

### 4.3 questionnaires (catálogo administrable)

**QuestionnaireTemplate:** `kind` (`OWNERSHIP`|`VALUE_DELIVERY`), `area` FK (null para VALUE_DELIVERY), `level` FK (null para VALUE_DELIVERY), `version` (entero), `status` (`BORRADOR`|`PUBLICADO`|`ARCHIVADO`), `scale_note` (texto de escala mostrado al usuario)
- Restricción: solo una versión PUBLICADA por (kind, area, level).
- **Versionado:** publicar una nueva versión archiva la anterior; las evaluaciones ya creadas conservan FK a su versión (los resultados históricos nunca cambian de preguntas).

**Section:** `template` FK, `title`, `order`
**Question:** `section` FK, `order`, `title` (corto), `text` (descripción completa), `qtype`:
- `SCALE` (1–4 + N/A; flags: `allow_na` default true) — para todos los ítems de checklist y criterios de EV
- `TEXT_LONG` (fortalezas/oportunidades/comentarios — aunque en v1 estos son campos fijos de la evaluación, el tipo existe para flexibilidad futura)
- `weight` (default 1.00; v1 usa promedio simple — RN-04 — pero el campo deja la puerta abierta)
- `is_required`

**ScaleOption** (catálogo de respuestas administrable): `question` FK (o a nivel template para no repetir), `value` (1–4 o null para N/A), `label` ("Cumple", "Excede"…), `description` (anclaje del criterio — necesario en EV donde cada criterio tiene descriptores propios por valor)

> Con esto, Talento puede administrar **todas las preguntas, respuestas y puntajes** desde la app (requisito explícito), y los 17 cuestionarios (16 Ownership + 1 Entrega de Valor) se precargan como datos (Anexos A/B del KB).

### 4.4 evaluations

**OwnershipEvaluation:**
- `user` FK, `project` FK, `period` FK, `template` FK (versión congelada)
- `validator` FK User (default: `project.lead`)
- `status`: `BORRADOR` → `ENVIADA` (reapertura solo Talento/admin — RN-06)
- `strengths` (texto), `opportunities` (texto), `comments` (texto, opcional)
- `confirmed_with_leader` (bool; requerido = True para enviar)
- `score` (decimal 2 dp, calculado al enviar y persistido; recalculable)
- `submitted_at`, timestamps; `unique_together (user, project, period)`

**OwnershipAnswer:** `evaluation` FK, `question` FK, `value` (1–4 o null=N/A), `is_na` (bool) — autosave por pregunta.

**ValueDeliveryEvaluation:**
- `project` FK, `period` FK; `unique_together (project, period)` — RN-07
- `evaluator` FK (líder del proyecto), `validated_by` FK (director), `status`: `BORRADOR` → `EN_VALIDACION` → `VALIDADA` (rechazo regresa a BORRADOR con `rejection_comment`)
- `client_satisfaction` (1–4), `deliverables` (1–4), `time_finite` (1–4|null), `time_indefinite` (1–4|null)
- Validación: exactamente uno de los dos criterios de tiempo según `project.duration_type` (RN-08)
- `score` = promedio de los 3 aplicables (RN-08), persistido al validar

**ArenaImpactScore:** `user` FK, `period` FK, `score` (1.00–4.00), `notes`, `captured_by` FK (Talento); `unique_together (user, period)` — RN-11

**FinalScore** (materializado por colaborador-periodo):
- `user`, `period`, `ownership_score`, `value_delivery_score`, `arena_impact_score`, `final_score`, `band` (Excede/Cumple/Cumple parcial/No cumple — RN-20), `is_complete` (bool — sección 7.3 del KB)
- Recalculado por señal/servicio cada vez que cambia un componente.

### 4.5 Diagrama entidad-relación (resumen)

```
Area ──< User >── SeniorityLevel ──< PillarWeight
User ──< ProjectMembership >── Project (lead: User)
Area+Level ──< QuestionnaireTemplate ──< Section ──< Question ──< ScaleOption
User+Project+Period ──< OwnershipEvaluation ──< OwnershipAnswer >── Question
Project+Period ── ValueDeliveryEvaluation
User+Period ── ArenaImpactScore
User+Period ── FinalScore
```

---

## 5. Capa de servicios (lógica de negocio)

`core/services/scoring.py` — funciones puras y testeadas:

```python
def ownership_evaluation_score(evaluation) -> Decimal
    # AVG de respuestas numéricas, excluye N/A (RN-03, RN-04), 2 dp ROUND_HALF_UP

def ownership_pillar_score(user, period) -> Decimal | None
    # AVG simple de scores de evaluaciones ENVIADAS del usuario en el periodo (RN-05)

def value_delivery_project_score(vd_eval) -> Decimal
    # AVG de (satisfacción, entregables, tiempo aplicable) (RN-08)

def value_delivery_pillar_score(user, period) -> Decimal | None
    # AVG de scores VALIDADOS de los proyectos donde el usuario fue miembro (RN-09)

def final_score(user, period) -> FinalScoreResult
    # ponderado por PillarWeight del nivel del usuario (RN-12, RN-19)
    # banda según RN-20; is_complete según KB §7.3

def interpretation_band(score) -> str
```

`core/services/permissions.py`:

```python
def can_view_evaluation(viewer, evaluation) -> bool   # RN-15
def visible_users(viewer) -> QuerySet                 # propio / su área / todos
def projects_led_by(user) -> QuerySet
def can_validate_ownership(viewer, evaluation)        # viewer == evaluation.validator o admin
def can_capture_value_delivery(viewer, project)
def can_validate_value_delivery(viewer)               # rol DIRECTOR o admin
```

---

## 6. Permisos y pantallas por rol

### 6.1 Matriz de acceso (implementación de RN-14/RN-15 y KB §9)

| Pantalla | Colaborador | Lead de área | Líder de proyecto | Talento | Director | Superuser |
|---|---|---|---|---|---|---|
| **Mi dashboard** (mis evaluaciones, mis scores) | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| **Mi evaluación de Ownership** (crear/editar por proyecto) | ✔ | ✔ | ✔ | — | — | ✔ |
| **Mis resultados** (vista integral final) | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| **Mi área** (lista de colaboradores del área + sus evaluaciones y scores) | — | ✔ | — | ✔ | ✔ | ✔ |
| **Validación de Ownership** (cola de evaluaciones de mis proyectos) | — | ✔* | ✔ | — | — | ✔ |
| **Entrega de Valor** (capturar por proyecto liderado) | — | ✔* | ✔ | — | — | ✔ |
| **Validar Entrega de Valor** (cola del director) | — | — | — | — | ✔ | ✔ |
| **Impacto Arena** (captura masiva por periodo) | — | — | — | ✔ | — | ✔ |
| **Admin: cuestionarios** (CRUD secciones/preguntas/respuestas/puntajes, versionar, publicar) | — | — | — | ✔ | — | ✔ |
| **Admin: usuarios** (alta/baja, área, nivel, rol) | — | — | — | ✔ | — | ✔ |
| **Admin: proyectos** (CRUD, asignar lead y equipo) | — | — | — | ✔ | — | ✔ |
| **Admin: periodos** (abrir/cerrar) | — | — | — | ✔ | — | ✔ |
| **Admin: ponderaciones** | — | — | — | ✔ | — | ✔ |
| **Reportes/exportes** (CSV/XLSX global) | — | su área | sus proyectos | ✔ | ✔ | ✔ |

\* solo si además es líder de algún proyecto.

### 6.2 Implementación

- Mixins por vista (`LoginRequired` + mixin de rol) y filtrado **siempre** a nivel queryset (`visible_users(viewer)`), nunca solo ocultando botones.
- El menú lateral se construye según las capacidades del usuario (segregación de pantallas).
- El admin de Django queda solo para el superusuario como herramienta de soporte; Talento usa pantallas propias de administración (mejor UX y validaciones de negocio).
- Tests de permisos por rol: matriz completa cubierta en suite automática.

---

## 7. Pantallas y UX (con htmx + Alpine.js)

> **Toda pantalla de esta sección se diseña y revisa con la skill UX UI Pro Max.** Todas las interacciones listadas actualizan la pantalla parcialmente (htmx/fetch), sin POST de página completa salvo login/logout.

1. **Login** (email + contraseña; reset por correo).
2. **Mi dashboard:** tarjetas por periodo abierto: estado de cada evaluación de Ownership por proyecto (Borrador/Enviada), score parcial, pendientes.
3. **Wizard de cuestionario Ownership** (corazón de la app):
   - Secciones como pasos; barra de progreso; contador respondidas/total.
   - Cada pregunta: título, descripción completa, radio 1–4 + N/A (con descriptores en tooltip).
   - **Autosave** por respuesta (Alpine `$watch` + fetch a endpoint JSON) — nunca se pierde captura.
   - Vista resumen final con promedio preliminar **en vivo** (excluyendo N/A), campos de Fortalezas/Oportunidades/Comentarios y checkbox de confirmación; botón Enviar deshabilitado hasta cumplir RN-06.
   - Banner claro: "No envíes hasta tu sesión de validación con tu líder".
4. **Validación de Ownership (líder):** cola de evaluaciones de sus proyectos; vista lado a lado durante la sesión; el líder puede ajustar calificaciones y co-redactar comentarios antes del envío conjunto.
5. **Entrega de Valor (líder):** formulario de 3 criterios con descriptores visibles; el criterio de tiempo se muestra según `duration_type` del proyecto; lista de miembros afectados visible ("esta calificación se aplicará a N personas").
6. **Cola del director:** validar/rechazar con comentario.
7. **Impacto Arena (Talento):** tabla editable por periodo (todas las personas, input 1–4 + notas), guardado en lote.
8. **Mis resultados:** vista integral — calificación final, banda, gauge por pilar, desglose por proyecto, fortalezas/oportunidades, histórico de periodos.
9. **Mi área (Lead):** tabla filtrable (nivel, proyecto, estado) con drill-down a cada evaluación.
10. **Administración:** CRUDs de cuestionarios (editor de secciones/preguntas con drag-and-drop de orden vía Alpine), usuarios, proyectos (con gestión de equipo), periodos, ponderaciones.

---

## 8. Seed (datos iniciales)

Management command: `python manage.py seed_all` (idempotente), compuesto de:

1. **`seed_superuser`** — crea superusuario desde variables de entorno (`SEED_SU_EMAIL`, `SEED_SU_PASSWORD`); requisito explícito.
2. **`seed_catalogs`** — 4 áreas (ID, CD, PM, UXUI), 4 niveles (JR, MID, SNR, LEAD), ponderaciones RN-19, periodo "2026-S1" (ABIERTO).
3. **`seed_questionnaires`** — carga los 16 templates de Ownership + 1 de Entrega de Valor desde fixtures generados de los Anexos A/B del KB (estructura: template → secciones → preguntas → opciones de escala con descriptores). Estado: PUBLICADO, versión 1.
4. **`seed_users`** — importa los 54 colaboradores del Anexo C del KB (email + nombre completo; contraseña de un solo uso o flujo de "establecer contraseña" por correo). Área/nivel quedan `null` hasta asignación por Talento (pendiente de mapeo).
5. **`seed_demo`** (solo dev) — proyectos de ejemplo, membresías y evaluaciones de prueba.

Los cuestionarios se mantienen como **fixtures YAML legibles** en `fixtures/questionnaires/` para revisión por Talento antes de cargar.

---

## 9. Fases de desarrollo

> **En cada fase:** cada feature se ejecuta invocando la **feature skill** (workflow completo + revisión al cierre); toda pantalla pasa por **UX UI Pro Max**; al cerrar la fase se corre **code simplifier** sobre el código nuevo; cada publicación a Vercel (preview o producción) se hace con la **skill de Vercel**.

### Fase 0 — Fundaciones (3 días)
Proyecto Django 6 (últimas versiones de todos los assets), settings por ambiente, proyecto conectado a **Vercel** desde el día 1 (deploy preview con la skill de Vercel), Postgres gestionado, Tailwind+Alpine+htmx integrados, `LANGUAGE_CODE es-mx`, páginas de error personalizadas en español, CI básico (lint + tests), layout base con navegación por rol (mock).

### Fase 1 — Identidad y catálogos (1 semana)
User custom (email), login/logout/reset, modelos de catalog, pantallas admin de áreas/niveles/usuarios/periodos/ponderaciones, `seed_superuser` + `seed_catalogs` + `seed_users`.
**Criterio de salida:** usuarios reales pueden hacer login; Talento asigna área/nivel.

### Fase 2 — Motor de cuestionarios (1.5 semanas)
Modelos questionnaires + versionado, editor administrable (CRUD secciones/preguntas/opciones), `seed_questionnaires` con los 17 cuestionarios, render genérico de un template.
**Criterio de salida:** los 16 checklists se ven exactamente como el KB; Talento puede editar una pregunta y publicar versión 2 sin tocar código.

### Fase 3 — Flujo Ownership (2 semanas)
Creación de evaluación (usuario × proyecto × periodo), wizard con autosave, cálculo en vivo, validación del líder, envío con candado RN-06, inmutabilidad post-envío, reapertura admin, correo de confirmación, `ownership_pillar_score`.
**Criterio de salida:** flujo E2E colaborador→líder→enviada→score, con tests de RN-03/04/05/06.

### Fase 4 — Entrega de Valor (1 semana)
Captura por líder, validación del director (estados y rechazo), propagación a miembros, promedio multi-proyecto.
**Criterio de salida:** RN-07/08/09 cubiertas con tests; criterio de tiempo condicionado al tipo de proyecto.

### Fase 5 — Impacto Arena + Calificación final (1 semana)
Captura masiva de Talento, `FinalScore` materializado con recálculo automático, bandas RN-20, vista integral de resultados, flag de completitud (KB §7.3).
**Criterio de salida:** un colaborador con los 3 pilares ve su calificación final correcta (verificación cruzada con casos calculados a mano).

### Fase 6 — Dashboards, reportes y cierre de periodo (1 semana)
Vista "Mi área" del Lead, dashboard de Talento (avance de llenado del periodo: % enviadas, % validadas, faltantes), exportes CSV/XLSX, cierre de periodo (solo lectura).

### Fase 7 — Endurecimiento y despliegue (1 semana)
Auditoría (`django-simple-history`), matriz completa de tests de permisos, pruebas de carga ligeras, backups de Postgres, **despliegue a producción en Vercel con la skill de Vercel** (dominio, variables de entorno, monitoreo), revisión final de error handling amigable en toda la app, pasada final de code simplifier, manual de usuario breve por rol (en español), sesión de capacitación a Talento.

**Total estimado: ~8–9 semanas** de un desarrollador full-time (o ~5 con apoyo de IA para scaffolding y tests).

---

## 10. Estrategia de pruebas

- **Unitarias (pytest-django):** servicios de scoring con casos límite — todo N/A, un solo ítem, redondeos .005, multi-proyecto, pesos por nivel. Objetivo: 100% de cobertura en `core/services/`.
- **De permisos:** parametrizadas rol × pantalla × objeto (propio/ajeno/otra área) — la matriz §6.1 completa.
- **De flujo (integration):** ciclo de vida de estados de ambas evaluaciones, candados de envío, inmutabilidad, cierre de periodo.
- **De seed:** idempotencia; conteo exacto de preguntas por cuestionario vs KB.
- **Smoke E2E (Playwright, opcional):** login → llenar checklist → validar → enviar → ver resultado.

---

## 11. Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|------------|
| Cambios al modelo de evaluación a mitad de desarrollo | Cuestionarios y ponderaciones como datos versionados, no código |
| Falta el mapeo persona→área/nivel/proyectos | Bloquea pilotaje, no desarrollo; pantalla de asignación masiva en Fase 1 |
| Impacto Arena sin definición interna | Diseñado como input manual; si luego se automatiza, se agrega un módulo de cálculo sin tocar el resto |
| Evaluaciones enviadas por error antes de la sesión | Candado de confirmación + banner + reapertura por Talento |
| Adopción (cambio desde Forms/SharePoint) | Replicar el flujo conocido (borrador→sesión→submit→correo) y vista integral equivalente |
| Django en Vercel (serverless): cold starts, sin filesystem persistente, límites de tiempo por request | Postgres gestionado externo, whitenoise/CDN para estáticos, correo vía proveedor SMTP/API externo, cálculos síncronos ligeros (volumen pequeño lo permite); validar en Fase 0 con deploy preview real |

---

## 12. Backlog v2 (fuera de alcance v1)

- SSO con Microsoft Entra ID (cuentas @arena-analytics.com).
- Automatización del cálculo de Impacto Arena (asistencias, capacitaciones).
- Comparativos históricos entre periodos y analítica de tendencias por área.
- Recordatorios automáticos programados (evaluaciones pendientes por vencer).
- Módulo de planes de desarrollo/acuerdos de mejora con seguimiento.
- Evaluación del Lead (hoy fuera del modelo).
- API REST para integraciones (Power BI).
- Importación masiva de proyectos/equipos desde Excel.
