# Reporte de revisión y publicación — checklists 2027 (Ownership v2)

**Fecha**: 2026-10-28 · **Revisó**: equipo técnico (criterio delegado por el usuario) · **Producción**: Neon `"talento-app"`

## Criterios de revisión (research.md)

1. Mismo número de reactivos que la hoja del Excel.
2. Títulos únicos dentro del cuestionario.
3. Descripción y criterio de aceptación presentes (salvo celda vacía en el Excel).
4. Sin columnas de respaldo ni leyendas de escala importadas.
5. Escala (5 opciones) y nota de escala copiadas de la v1.

## Resultado por cuestionario

| Puesto | Reactivos (Excel = v2) | Con criterio | Títulos ajustados («Categoría — Subtema» o conservados de v1) | Estado |
|---|---|---|---|---|
| CD/JR | 21 | 21 | 4 (rutinas) | **Publicado** (v1 y v3 archivadas) |
| CD/MID | 24 | 24 | 7 (rutinas) | **Publicado** |
| CD/SNR | 24 | 24 | 7 (rutinas) | **Publicado** |
| CD/LEAD | 24 | 24 | 20 (categorías Lead) | **Publicado** |
| ID/JR | 29 | 29 | 3 (rutinas, de v1) | **Publicado** |
| ID/MID | 32 | 32 | 3 (rutinas, de v1) | **Publicado** |
| ID/SNR | 34 | 34 | 3 (rutinas, de v1) | **Publicado** |
| ID/LEAD | 25 | 25 | 25 (columna Categoría; 19 títulos de v1 conservados) | **Publicado** |
| PM/JR | 25 | 25 | 23 (categorías) | **Publicado** |
| PM/MID | 32 | 32 | 23 (categorías) | **Publicado** |
| PM/SNR | 39 | 38 | 23 (categorías) | **Publicado** — «Posicionamiento como asesor de confianza con stakeholder» no trae criterio en el Excel |
| PM/LEAD | 25 | 25 | 23 (títulos de UX/UI Lead v1) | **Publicado** |
| UXUI/JR | 18 | 18 | 0 | **Publicado** |
| UXUI/MID | 23 | 23 | 0 | **Publicado** |
| UXUI/SNR | 27 | 27 | 0 | **Publicado** |
| UXUI/LEAD | 25 | 25 | 23 (de v1, conservados) | **Publicado** |
| **Total** | **427** | **426** | | 16/16 publicados |

Entrega de Valor v1: sin cambios (Publicado).

## Verificación en producción

| Métrica | Antes | Después |
|---|---|---|
| Respuestas de Ownership | 2.116 | 2.116 |
| Evaluaciones | 75 | 75 |
| Borradores 2026-S1 (PM Snr, cuestionario v1) | #82: 39 resp. · #81: 11 resp. | #82: 39 resp. · #81: 11 resp. (siguen en v1) |
| Ownership v1 | 16 Publicado | 16 Archivado |
| Ownership v2 | 1 Borrador (copia de v1) | 16 Publicado |
| CD/JR v3 (borrador de prueba) | Borrador | Archivado |

Orden aplicado (analyze F1): migración → push (`b2b8272`) → deploy de Vercel "success" → importación con `--publish`.
Simulación previa (`--dry-run`) contra producción: 16/16 válidos.

## Observaciones de contenido para Talento (no bloquean)

- PM/SNR: el reactivo «Posicionamiento como asesor de confianza con stakeholder» no tiene criterio de aceptación en el Excel; se puede completar desde el editor creando una versión nueva.
- Los textos se importaron tal como vienen (incluidos errores menores de redacción del Excel, p. ej. "suspuestos", "buenas práctica"); su corrección es de contenido y se hace en el editor.
- La versión 2025 (CD Mid con textos de Jr) queda corregida por la v2.
