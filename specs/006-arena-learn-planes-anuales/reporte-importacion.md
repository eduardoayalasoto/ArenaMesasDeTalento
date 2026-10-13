# Reporte de importación · Arena Learn 006

## Ensayo en rama de Neon (2026-10-12)

**Rama usada:** `dryrun-006-arena-learn` (`br-green-cloud-ap05yoie`), copia de producción tomada el 2026-10-12 a las 23:13 UTC. Producción no se tocó.

| Paso | Resultado |
|---|---|
| `migrate` | `access.0003_learn_planes_grants` y `learning.0004_tags_planes` aplicadas sin error |
| `reset_learning_data --before 2026-10-13` (simulación) | 5 pasos de aprobación · 0 evidencias · 0 reseñas · 4 solicitudes · 7 filas de historial · 5 cursos · 0 etiquetas. **Coincide con FR-039.** |
| `reset_learning_data … --confirm` | Borrado; la configuración de Arena Learn se conserva |
| `import_learning_plans` (1.ª corrida, 79 s) | 260 cursos creados · 4 planes creados (publicados) · 279 cursos en planes · KO en 34 cursos · 221 cursos con algún dato propuesto |
| `import_learning_plans` (2.ª corrida) | **0 creados**, 260 sin cambio, 279 ya estaban (SC-003) |
| Prueba de humo HTTP (colaborador y Talento) | Planes, filtro KO (htmx), catálogo, Mi plan, Mis cursos, Etiquetas, Avance de planes y alta de plan responden 200. Al colaborador se le niegan (403) Etiquetas, Avance de planes y alta de plan. Las páginas de plan hacen 30 consultas fijas, sin N+1 |

## Contenido importado

| Plan | Cursos | Tipos | Con nivel | KO |
|---|---|---|---|---|
| PM 2026 (may–dic, 3–10 h/sem) | 87 | Estructurado 24 · Certificación 4 · Puntual 52 · Contextual 7 | 77 | 26 |
| UX/UI 2026 (may–dic, 3–10 h/sem) | 41 | Estructurado 8 · Certificación 1 · Puntual 23 · Soft Skills 9 | 1 | 0 |
| Ingeniería de IA 2026 · área CD (abr–dic, 5–10 h/sem) | 100 | Estructurado 10 · Certificación 4 · Puntual 75 · Contextual 11 | 0 | 10 |
| Ingeniería de Datos 2026 · área ID (abr–dic, 5–10 h/sem) | 51 | Estructurado 11 · Certificación 4 · Puntual 30 · Contextual 6 | 3 | 0 |

Las guías de IA y Datos no traen nivel por curso: sus cursos quedan en "Todos los niveles", salvo las certificaciones cuya guía sí indica "Recomendado para…".

**Misma liga con nombres distintos** (se conserva el primer nombre):
- Critical Thinking & Problem Solving
- Fundamentals of Generative AI
- Introduction to AI in Azure
- GenAI for Product Managers
- Supply Chain Analytics for Professionals
- Mastering Supply Chain and Logistics Management
- Google UX Design Certificate
- Write your first query with KQL

**Datos propuestos con criterio técnico:** ver `revision-datos-propuestos.md` (42 tipos y 182 enfoques, cada uno con su motivo).

## Pendiente: corrida en producción

Se hará solo con autorización explícita y en este orden:
1. Rama de respaldo `backup-pre-006`.
2. `migrate`.
3. `reset_learning_data --confirm`.
4. `import_learning_plans`.
5. Push a `main`.
