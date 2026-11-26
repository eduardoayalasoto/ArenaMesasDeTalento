# Spec 011 — Centro de ayuda contextual (por perfil y por lo que cada persona puede hacer)

**Estado:** implementado junto con el spec 010; se despliega a producción cuando terminan ambos.

## 1. Pedido del usuario (2026-11-26)
1. El botón del **Centro de ayuda** sale del menú de usuario y va **directo en la barra, junto a la campana**.
2. El contenido se **actualiza con todo lo que existe hoy** y se **muestra solo lo que le toca a cada persona**:
   - por **perfil/organigrama** (Área › Posición › Nivel, marcas Lead/Director): p. ej. un Lead de Ingeniería ve la
     **ponderación de pilares de un Lead de Ingeniería**; un Analista de Consultoría ve la de un Analista;
   - por **lo que puede hacer** (permisos y relaciones): quien da retroalimentación de Mesa ve cómo hacerla; quien
     contesta Ownership ve cómo; quien es evaluador, owner con 360, Responsable/Validador de Entrega de Valor, etc.
3. Narrativa **según el rol en el flujo**: quien se autoevalúa lee «haz tu cuestionario → avisa a tu evaluador y agenden la
   sesión de validación → recuérdale tener abierta la evaluación para revisar tus calificaciones»; quien es evaluador lee
   «cuando te agenden una sesión de validación, ten abierta esa evaluación y revísenla juntos».
4. **Talento** no ve la guía personal (autoevaluación, evaluador, líder…); ve **cómo organizar y mantener los catálogos**
   (crear Área, Posición, Nivel, Posición × nivel, cuestionarios, periodos…), con un **diagrama** de quién contiene a
   quién (relación de pertenencia, tipo Venn).
5. Las pestañas están **siempre visibles** y actualizadas; solo aparecen las que aplican a la persona.

## 2. Diseño
- **Servicio** `apps/core/services/help_center.py`: `build(user)` devuelve `{perfil, pestañas, datos}`. Las pestañas se deciden
  por **reglas sobre permisos y relaciones**, nunca por el rol «a mano»; el contenido no se oculta con CSS: lo que no aplica
  **no se renderiza**.
- **Datos reales, no copiados:** ponderación de pilares (`pillar_weights.effective_weights`), cuestionario de Ownership que le
  corresponde (categorías y ponderaciones), evaluadores de la persona, evaluaciones pendientes como evaluador, proyectos
  donde es owner/responsable/validador, 360 pendientes, y el organigrama vivo (Áreas › Posiciones › Niveles) para Talento.
- **Pestañas y regla de aparición**
  | Pestaña | Aparece para |
  |---|---|
  | El modelo | todos (con **sus** ponderaciones; Talento ve la tabla de todas las posiciones) |
  | Mi evaluación | quien tiene `ownership.self.manage` y no es Talento |
  | Soy evaluador | quien es evaluador de alguien (o es Lead/Director con `ownership.validate`) y no es Talento |
  | Liderazgo y proyectos | marca Lead, o owner/responsable/validador de algún proyecto |
  | Evaluación 360 | owner de un proyecto con 360, o quien debe responder alguna, o Talento/Dirección |
  | Mesa y retroalimentación | `talent_table.view`, `feedback.view` con relación, o Talento |
  | Dirección | marca Director |
  | Arena Learn | `learn.self` |
  | Organización y catálogos · Cuestionarios y ponderaciones · Ciclo del periodo | solo Talento |
- **Barra:** botón `circle-help` con tooltip «Centro de ayuda», a la izquierda de la campana; se quita del menú de usuario.
- Estilo: guías con pasos numerados (`help_step`), callouts del Design System, sin emojis ni `style=` inline.

## 3. Criterios de aceptación
1. El botón está en la barra y ya no en el menú de usuario.
2. Un Analista de Consultoría ve **su** ponderación (la de su Posición × nivel) y no la de otro nivel.
3. Un Lead ve «Liderazgo y proyectos» y su ponderación de Lead; un colaborador no ve esa pestaña.
4. El evaluador ve la narrativa de evaluador; el autoevaluado, la de «avisa a tu evaluador y agenden la sesión».
5. Talento no ve «Mi evaluación», «Soy evaluador» ni «Liderazgo»; ve el diagrama del organigrama y las recetas de catálogo.
6. Pruebas por perfil que verifican qué pestañas aparecen y los números mostrados.
