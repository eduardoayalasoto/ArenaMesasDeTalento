# Spec 009 — Ponderación de pilares por posición y estándar CRUD con drawer

## Contexto
La ponderación de Ownership / Entrega de Valor / Impacto Arena solo existía por nivel (`PillarWeight`,
editable solo en el admin de Django). Los catálogos mezclan formularios en línea y no ofrecen siempre
crear, ver, editar y desactivar.

## Jerarquía de datos
**Área → Posición (nombre del cargo) → Nivel (Junior, Mid, Senior, Lead).** El nivel es la escalera
global; la posición es el cargo (p. ej. Project Manager); el área agrupa posiciones.

## Alcance
1. **Ponderación de pilares por posición** (área × posición × nivel) — **hecho (etapa 1)**
   - Modelo `PositionPillarWeight` (1:1 con `Position`); sin fila propia rige la ponderación del nivel.
   - Pantalla `Catálogos → Ponderación de pilares` (`weights.manage`): tabla + drawer de 3/4 de pantalla,
     total en vivo = 100%, "Volver a la ponderación del nivel".
   - **Bloqueo:** si ya existen `FinalScore` de personas con esa área × nivel, la ponderación no se edita.
   - `scoring.final_score` usa `pillar_weights.effective_weights(user)`.
2. **Estándar CRUD con drawer** — regla en `DESIGN_SYSTEM.md` (hecha); `_drawer.html` acepta `width_class`.
   Todo catálogo: índice informativo + Ver + Crear + Editar + Desactivar/Eliminar, en drawer.
   Excepción: **Cuestionarios y Proyectos** son pantallas completas.
3. **CRUD completo de Áreas, Posiciones y Categorías** con el estándar anterior — *etapa 2*.
4. **Cuestionarios publicados editables mientras no tengan respuestas** (pesos y preguntas); con una
   respuesta, solo vía nueva versión — *etapa 2*. Misma estructura para Ownership y Entrega de Valor
   en lo que aplique — *pendiente de definir*.

## Fuera de alcance
- No se modifican las ponderaciones por nivel (`PillarWeight`), ni los pesos de categorías/preguntas.
- No se recalcula nada histórico.

## Criterios de aceptación (etapa 1)
- Suma de pesos ≠ 100.0% → no se guarda (cliente y servidor).
- Posición con calificaciones finales → pantalla en solo lectura y el servicio rechaza el cambio.
- Posición sin ponderación propia → calificación idéntica a la actual (nivel).
- Clave `weights.manage` con ruta registrada; `test_access_coverage` en verde.
