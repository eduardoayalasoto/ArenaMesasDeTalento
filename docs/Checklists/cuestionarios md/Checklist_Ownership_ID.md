# Checklist de Ownership — Ingeniería de Datos (ID)

> Evalúa cada actividad con base en evidencia concreta del período: entregables, sesiones, documentación o retroalimentación del cliente y del equipo.

**Escala de calificación:**
- **1 — No cumple:** La actividad no se ejecutó o se ejecutó con deficiencias significativas que impactaron el proyecto o al equipo.
- **2 — Cumple parcial:** La actividad se ejecutó pero con omisiones, inconsistencias o calidad por debajo del estándar esperado para el nivel.
- **3 — Cumple:** La actividad se ejecutó de forma consistente y completa, cumpliendo el estándar esperado para el nivel.
- **4 — Excede:** La actividad se ejecutó por encima del estándar del nivel, con iniciativa, precisión o impacto adicional notable.
- **N/A:** La actividad no aplicó en este período por razones justificadas (tipo de proyecto, fase, etc.).

---

## ID Jr

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: ID Jr / ID Mid / ID Snr / ID Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Notas de alcance** — Ejecutar proceso de discovery para identificar fuentes principales, el flujo E2E de los datos y los primeros pasos a tomar una vez que el proyecto arranca. Levantar dudas antes de empezar a desarrollar, no solo durante.

6. **Documento de alcance técnico** — Contribuir en la definición de qué se construye y qué no en el proyecto, documentando los componentes asignados a su nivel con precisión. No asumir que algo está en scope si no está explícitamente documentado.

7. **Checklist de requerimientos** — Completar el checklist de requerimientos técnicos y funcionales para los componentes bajo su responsabilidad, verificando que cada ítem tiene un estado claro (cumple / no cumple / pendiente) y escalando los pendientes críticos antes del inicio del desarrollo.

8. **Propuesta de conectividad** — Documentar los conectores asignados a su nivel: el medio de acceso a la fuente, la frecuencia de actualización y el método de carga (append, overwrite, delta). Levantar dudas sobre accesos o permisos antes de comenzar el desarrollo.

9. **Reporte de calidad de datos** — Ejecutar los checks de calidad de datos asignados a su nivel para las fuentes o desarrollos bajo su responsabilidad. Documentar los resultados y comunicar anomalías detectadas de forma inmediata.

10. **Reportes de pruebas** — Ejecutar los casos de prueba asignados a su nivel, documentando resultados esperados vs obtenidos y registrando issues o errores detectados. No declarar un componente como 'done' sin haber ejecutado, documentado y presentado sus pruebas.

11. **Reporte técnico de calidad de datos** — Ejecutar y compartir los reportes de calidad de datos de los componentes bajo su responsabilidad, documentando las reglas aplicadas, los resultados obtenidos y las excepciones encontradas.

12. **Scripts de validación** — Ejecutar los scripts de validación automática pre y post carga asignados a su nivel. Comunicar de inmediato cuando un script de validación falla o genera resultados inesperados.

13. **Esquema preliminar de tablas** — Construir el esquema preliminar de tablas para los componentes asignados con base en los comentarios y mockups del DE Sr/Mid/Lead, aplicando correctamente las convenciones de nombres, tipos de datos y claves definidas.

14. **Notas técnicas** — Registrar las decisiones técnicas, supuestos, trade-offs y dudas relevantes de los componentes bajo su responsabilidad durante todo el proyecto. Externalizar dudas al DE Mid/Sr antes de tomar decisiones técnicas por cuenta propia.

15. **Scripts, Notebooks y pipelines** — Implementar las tareas de desarrollo asignadas a su nivel siguiendo los estándares de calidad y versionado del proyecto (SOLID, naming conventions, modularidad). No entregar código sin haber ejecutado pruebas básicas.

16. **Checklist de ejecución** — Completar el checklist de ejecución para los componentes bajo su responsabilidad antes del despliegue, verificando que todos los ítems están marcados como completos y que no existen bloqueadores críticos sin resolver.

17. **Documentación de scripts** — Documentar el código desarrollado explicando propósito, inputs, outputs, dependencias y consideraciones de uso. La documentación es parte del entregable, no un paso opcional al final.

18. **Inventario de fuentes** — Recopilar la información básica de las fuentes de datos asignadas a su nivel: nombre, owner, frecuencia de actualización, formato y calidad estimada. Escalar cuando una fuente no tiene owner claro o cuando su accesibilidad es incierta.

19. **Diagrama de arquitectura** — Entender completamente la arquitectura del proyecto y sus componentes. Identificar la posición de los desarrollos bajo su responsabilidad dentro del flujo end-to-end y comunicar al DE Mid/Sr/Lead cuando detecta que algo en su implementación se desvía del diseño arquitectónico.

20. **Modelado de datos** — Documentar los campos y tipos de datos de las tablas asignadas correctamente, siguiendo las convenciones del proyecto. Verificar con el DE Mid/Sr/Lead antes de implementar si hay dudas sobre granularidad o relaciones.

21. **Diseño de pipelines** — Entender el diseño lógico del pipeline y documentar los pasos correspondientes a los componentes bajo su responsabilidad. Comunicar al DE Mid/Sr/Lead cuando la implementación requiere ajustes al diseño definido.

22. **Desarrollo de pipelines** — Implementar las tareas de desarrollo de pipelines asignadas a su nivel: ingestión de datos, transformaciones simples y cargas bajo supervisión del DE Mid/Sr/Lead. No entregar componentes sin haber ejecutado una prueba end-to-end básica.

23. **Scripts de validación y calidad de datos** — Ejecutar los scripts de validación técnica y de negocio asignados a su nivel, verificando completitud, unicidad y consistencia básica. Analizar los resultados y comunicar al DE Mid/Sr/Lead cualquier incumplimiento detectado.

24. **Pruebas técnicas y de integración** — Ejecutar las pruebas unitarias asignadas a su nivel para los componentes bajo su responsabilidad. Documentar los resultados y escalar los defectos encontrados al DE Mid/Sr/Lead con evidencia.

25. **Documentación técnica integral** — Documentar correctamente los componentes bajo su responsabilidad como parte del proceso de desarrollo, asegurando que la documentación está actualizada con el código final antes de considerarlo terminado.

26. **Rutinas de gestión — Daily** — Asistir al daily preparado, comunicando claramente el avance de sus componentes, bloqueos activos y dependencias. No llegar al daily a descubrir sus propios bloqueos: deben estar identificados y comunicados antes de la sesión.

27. **Rutinas de gestión — Sprint Planning** — Asistir al sprint planning preparado con una propuesta de sus actividades y estimaciones de tiempo para el sprint. No llegar al planning sin haber revisado el backlog y sin saber qué puede comprometer.

28. **Rutinas de gestión — Sprint Review** — Asistir al sprint review preparado para exponer el resultado de sus componentes, explicar qué completó y qué no, y recibir retroalimentación técnica sin ponerse a la defensiva.

29. **Coordinación con DS y PM** — Alinear con el equipo de Ciencia de Datos los requerimientos de datos y las interfaces de entrega antes de cada fase de desarrollo. No comenzar a desarrollar una exposición de datos sin haber validado el formato y la granularidad esperada con el equipo.

30. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

31. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

32. **Fortalezas**
33. **Oportunidades**
34. **Comentarios** *(opcional)*

---

**Confirmación de envío**

35. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## ID Mid

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: ID Jr / ID Mid / ID Snr / ID Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Notas de alcance** — Liderar el proceso de discovery identificando posibles bloqueos durante la implementación, dependencias entre fuentes y riesgos técnicos. Documentar supuestos críticos y escalar al DE Sr/Lead los que requieran decisión de arquitectura.

6. **Documento de alcance técnico** — Redactar el alcance técnico del proyecto, definiendo explícitamente qué se construye y qué queda fuera. Alinear el alcance con las notas de discovery y obtener el sign-off del equipo y del cliente antes de comenzar el desarrollo.

7. **Checklist de requerimientos** — Validar técnicamente los requerimientos del proyecto, identificando ambigüedades, conflictos entre requerimientos y riesgos de implementación. Asegurar que todos los requerimientos críticos tienen estado definido antes del inicio del desarrollo.

8. **Propuesta de conectividad** — Definir los métodos de carga, frecuencias y características técnicas de los conectores del proyecto. Evaluar opciones de conectividad considerando restricciones de acceso, seguridad y volumen de datos.

9. **Reporte de calidad de datos** — Ejecutar y analizar los resultados de los reportes de calidad de datos, identificar tendencias, priorizar las acciones de mejora y comunicar hallazgos al equipo con recomendaciones concretas.

10. **Reportes de pruebas** — Ejecutar y analizar los resultados de las pruebas del equipo, validar que los defectos detectados están correctamente clasificados y tomar la decisión de si un componente está listo para producción.

11. **Reporte técnico de calidad de datos** — Ejecutar y analizar los resultados de calidad, dar seguimiento al incremento de los indicadores entre períodos y asegurar que las recomendaciones del reporte anterior se implementaron.

12. **Scripts de validación** — Desarrollar los scripts de validación automática pre y post carga, asegurando que las fallas generan alertas o logs claros y que los scripts están integrados al flujo de ejecución.

13. **Esquema preliminar de tablas** — Revisar el esquema de tablas constantemente, dar retroalimentación al equipo sobre inconsistencias detectadas y asegurar que el esquema está alineado con el modelo lógico antes del inicio del desarrollo.

14. **Notas técnicas** — Concentrar las notas técnicas del equipo, aclarar las dudas levantadas por el equipo y el cliente y convertir las notas en tareas o metas claras en el backlog del proyecto.

15. **Scripts, Notebooks y pipelines** — Orquestar los pipelines del equipo, asegurando la correcta integración de los componentes del flujo completo. Identificar y corregir problemas de modularidad o reutilización antes del sprint review.

16. **Checklist de ejecución** — Revisar el checklist de ejecución del equipo, dar retroalimentación al equipo sobre ítems incompletos y asegurar que no existen bloqueadores críticos antes de aprobar el despliegue.

17. **Documentación de scripts** — Revisar la documentación del equipo y dar retroalimentación sobre completitud y claridad antes de considerarla como entregable. Documentar la integración de los pipelines orquestados.

18. **Inventario de fuentes** — Analizar la estructura, frecuencia, volumen y calidad de las fuentes de datos del proyecto. Identificar riesgos y limitaciones de cada fuente y documentarlos con propuestas de mitigación.

19. **Diagrama de arquitectura** — Entender la arquitectura definida para el proyecto y comunicarla con precisión al equipo y al cliente. Detectar desviaciones de implementación del equipo respecto al diseño durante el sprint, antes del roll-out.

20. **Modelado de datos** — Diseñar las tablas del proyecto y validar la granularidad correcta con el equipo. Asegurar que el modelo de datos es coherente con las métricas y entidades de negocio definidas.

21. **Diseño de pipelines** — Diseñar los pipelines estándar del proyecto: pasos, dependencias, manejo de errores, reintentos y ventanas de tiempo. Asegurar que el diseño es consistente con la arquitectura definida y aprobado antes del desarrollo.

22. **Desarrollo de pipelines** — Implementar pipelines completos: ingestión, transformaciones, cargas incrementales e historificación. Asegurar que los pipelines del desarrollo están correctamente integrados en el flujo completo.

23. **Scripts de validación y calidad de datos** — Desarrollar los scripts de validación técnica y de negocio del proyecto. Asegurar que los resultados son auditables y que las alertas son accionables por cualquier miembro del equipo.

24. **Pruebas técnicas y de integración** — Ejecutar las pruebas de integración del proyecto, verificando que los pipelines funcionan correctamente de forma conjunta. Asegurar que los casos críticos y los escenarios de error están cubiertos.

25. **Optimización de pipelines** — Analizar el desempeño de los pipelines e identificar oportunidades de optimización en tiempo de ejecución, consumo de recursos y costos. Implementar optimizaciones conocidas y documentar el impacto con métricas comparativas.

26. **Runbooks** — Actualizar y mantener los runbooks operativos del proyecto, asegurando que los procedimientos ante fallas son claros y utilizables por personal no desarrollador.

27. **Documentación técnica integral** — Mantener la documentación técnica del proyecto actualizada a lo largo del desarrollo. Revisar la documentación del equipo y asegurar que la documentación del proyecto está lista para auditoría o handover en cualquier momento.

28. **Informe de transición** — Ejecutar la transición formal del producto de datos a operación o al equipo receptor. Asegurar que el conocimiento técnico, los riesgos conocidos y las responsabilidades están claramente documentados y aceptados por el receptor.

29. **Rutinas de gestión — Daily** — Asistir al daily preparado, reportando el avance propio y el del equipo a su cargo. Identificar bloqueos del equipo antes de que impacten entregables y gestionarlos activamente.

30. **Rutinas de gestión — Sprint Planning** — Asistir al sprint planning preparado con propuesta de actividades propias y del equipo a su cargo, incluyendo estimaciones, definitions of completeness y dependencias inter-equipo.

31. **Rutinas de gestión — Sprint Review** — Asistir al sprint review exponiendo resultados propios, identificando qué se completó y qué no. Dar retroalimentación técnica honesta y documentada al equipo.

32. **Coordinación con DS y PM** — Alinear con el equipo de Ciencia de Datos los requerimientos de datos, interfaces y formatos de entrega antes de cada fase. Comunicar al PM cuando un cambio técnico en las fuentes impacta el plan de entrega.

33. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

34. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

35. **Fortalezas**
36. **Oportunidades**
37. **Comentarios** *(opcional)*

---

**Confirmación de envío**

38. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## ID Snr

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: ID Jr / ID Mid / ID Snr / ID Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

**Actividades evaluadas** *(escala 1–4 / N/A)*

5. **Notas de alcance** — Liderar el discovery identificando fuentes críticas a nivel de negocio, diseñando la estrategia de implementación escalable y mapeando fuentes legacy y dependencias entre fuentes. Anticipar riesgos de implementación que no son visibles para el DE Mid.

6. **Esquemas de Bases de datos** — Realizar el diagrama entidad-relación de las tablas fuente y de las tablas destino, con campos tipificados, formatos y relaciones (PK/FK) claramente definidas. Asegurar que las reglas de negocio están correctamente interpretadas, modeladas y alineadas con la arquitectura.

7. **Matriz de trazabilidad** — Construir y mantener la matriz de trazabilidad que mapea las reglas de transformación entre fuentes y destinos. Compartirla con el equipo y explicar su funcionamiento para que el DE Mid y DE Jr puedan utilizarla como referencia durante el desarrollo.

8. **Documento de alcance técnico** — Definir los límites técnicos del proyecto con criterio, identificar riesgos de alcance y alinear el documento con todos los stakeholders técnicos y de negocio antes del inicio del desarrollo.

9. **Checklist de requerimientos** — Identificar riesgos técnicos en los requerimientos y asegurar que la alineación entre negocio y el equipo técnico es completa antes del inicio del desarrollo. Escalar al cliente los requerimientos que son técnicamente inviables tal como están definidos.

10. **Propuesta de conectividad** — Evaluar las opciones de conectividad considerando costos, performance, seguridad y escalabilidad. Aprobar la propuesta final y asegurar su alineación con la arquitectura definida.

11. **Reporte de calidad de datos** — Proponer las reglas de calidad del proyecto y definir el framework de data quality que el equipo implementará. Asegurar que el framework es adoptado consistentemente por el DE Mid y DE Jr.

12. **Reportes de pruebas** — Proponer las reglas de calidad y monitorear los resultados de las pruebas del equipo. Tomar la decisión final de liberar o no liberar a producción basado en la evidencia del reporte del DE Mid.

13. **Reporte técnico de calidad de datos** — Analizar los resultados de calidad del período, dar retroalimentación constante al equipo y asegurar que las métricas mejoran entre períodos. Escalar a Negocio cuando los problemas de calidad tienen impacto en los modelos del DS.

14. **Scripts de validación** — Optimizar y estandarizar los scripts de validación del proyecto. Definir las librerías comunes de validación que el equipo reutilizará en futuros desarrollos.

15. **Esquema preliminar de tablas** — Construir el mockup del esquema inicial, compartirlo con el equipo y dar seguimiento constante al cumplimiento de las convenciones durante el desarrollo. Realizar la revisión final del esquema antes del deployment.

16. **Notas técnicas** — Concentrar las notas técnicas del equipo, esclarecer las dudas levantadas y convertir las decisiones técnicas en tareas o metas claras en el backlog. Asegurar que ninguna decisión técnica relevante queda sin documentar.

17. **Scripts, Notebooks y pipelines** — Optimizar y escalar los desarrollos del equipo. Definir los patrones de desarrollo que el DE Mid y DE Jr seguirán para asegurar modularidad, reutilización y cumplimiento de estándares.

18. **Checklist de ejecución** — Revisar el cumplimiento del checklist de ejecución y dar retroalimentación al equipo sobre desviaciones detectadas. Aprobar el despliegue solo cuando todos los ítems están verificados.

19. **Documentación de scripts** — Revisar la documentación del equipo y dar retroalimentación sobre completitud y calidad técnica. Asegurar que la documentación del proyecto está lista para auditoría o handover en cualquier momento.

20. **Inventario de fuentes** — Evaluar la calidad, estabilidad y riesgos técnicos de las fuentes del proyecto. Identificar fuentes con historial de inestabilidad o problemas de calidad y proponer estrategias de mitigación.

21. **Diagrama de arquitectura** — Refinar el diseño de arquitectura para escalabilidad y operación en producción. Aprobar la arquitectura final y comunicarla al equipo con suficiente detalle para que el DE Mid pueda implementar sin ambigüedades.

22. **Modelado de datos** — Definir el modelo de datos completo y la granularidad correcta para las métricas del negocio. Validar la alineación del modelo con el negocio y con la arquitectura definida.

23. **Diseño de pipelines** — Validar el diseño de pipelines del DE Mid considerando fallos, escalabilidad y escenarios de error. Aprobar el diseño final antes del inicio del desarrollo.

24. **Desarrollo de pipelines** — Refactorizar, optimizar y asegurar la calidad de los pipelines del equipo. Definir los estándares de desarrollo que el DE Mid y DE Jr seguirán durante el proyecto.

25. **Scripts de validación y calidad de datos** — Diseñar las reglas de calidad robustas del proyecto y aprobar el enfoque y cobertura de los scripts del DE Mid. Asegurar que las reglas cubren los escenarios de negocio más críticos.

26. **Pruebas técnicas y de integración** — Diseñar la estrategia de testing del proyecto y aprobar los resultados finales antes del pase a producción. Asegurar que los casos críticos y los escenarios de error están cubiertos.

27. **Optimización de pipelines** — Optimizar el performance y los costos de los pipelines del proyecto. Validar el impacto técnico y financiero de las optimizaciones del DE Mid.

28. **Runbooks** — Diseñar los flujos de soporte y definir los SLAs y niveles de soporte del proyecto. Asegurar que los runbooks son suficientemente completos para que el equipo de operaciones del cliente pueda operar sin apoyo de Arena.

29. **Documentación técnica integral** — Validar la coherencia técnica de la documentación del proyecto y garantizar su completitud y calidad antes del cierre. Asegurar que la documentación es suficiente para una auditoría o handover sin apoyo del equipo.

30. **Informe de transición** — Asegurar que la transferencia de conocimiento técnico está completa y aprobar el cierre del proyecto. Garantizar que el equipo receptor puede operar sin apoyo de Arena.

31. **Rutinas de gestión — Daily** — Asistir al daily reportando avance propio en definición, coordinación y validación. Identificar y anticipar riesgos técnicos del equipo como principal responsable de la gestión de riesgos técnicos del proyecto.

32. **Rutinas de gestión — Sprint Planning** — Asistir al sprint planning liderando la definición de actividades técnicas del equipo. Hacer challenge de estimaciones no realistas y asegurar que todas las tareas tienen definition of completeness antes de comprometerse.

33. **Rutinas de gestión — Sprint Review** — Exponer resultados técnicos del equipo en el sprint review, identificar áreas de mejora propias y del equipo, y dar retroalimentación técnica profunda al DE Mid.

34. **Coordinación con DS y PM** — Liderar la alineación técnica con el equipo de Ciencia de Datos definiendo las interfaces de datos, formatos y granularidades que el pipeline proveerá. Comunicar al PM impactos técnicos que afecten el plan con suficiente anticipación para renegociar con el cliente.

35. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

36. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

37. **Fortalezas**
38. **Oportunidades**
39. **Comentarios** *(opcional)*

---

**Confirmación de envío**

40. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*

---
---

## ID Lead

> **Escala para nivel Lead:** 1 — No cumple (impacto negativo) / 2 — Cumple parcial (incompleto o tardío) / 3 — Cumple (consistente y proactivo) / 4 — Excede (impacto diferencial) / N/A

**Preguntas de identificación**

1. **Nombre del evaluado** *(texto libre)*
2. **Área** *(selección única)*: Ingeniería de Datos / Ciencia de Datos / Product Manager / UX/UI
3. **Puesto del evaluado** *(selección única)*: ID Jr / ID Mid / ID Snr / ID Lead
4. **Nombre del evaluador(es)** *(texto libre)*

---

### Aseguramiento de calidad técnica del equipo

5. Realizar seguimiento a los DE Sr/Mid de sus proyectos para evaluar el cumplimiento de sus checklists correspondientes. Documentar hallazgos y dar retro directa en sesión 1:1.

6. Asegurar que los proyectos a su cargo cumplen con las actividades de la Oficina de PMO y con los estándares de arquitectura de datos de Arena. Identificar brechas técnicas y escalarlas al director de Analítica cuando no puedan resolverse a nivel de proyecto.

7. Hacer equipo con los leads técnicos de DS, Producto y UX para asegurar que los proyectos cuentan con los diseños de integración de datos correctos y que no hay brechas entre lo que el pipeline entrega y lo que el DS necesita.

### Guía y soporte al equipo de proyecto

8. Asistir y participar activamente en los dailys al inicio del proyecto, en fases de entregables críticos y en el cierre. Evaluar en cada asistencia la preparación del equipo, el foco técnico y el cumplimiento de agenda y tiempos.

9. Asistir y participar activamente en los sprint planning y sprint review. Hacer challenge técnico de estimaciones de pipeline, diseños de arquitectura comprometidos y consistencia entre lo que se planea construir y la propuesta original.

10. Ayudar al equipo a mapear y entender todos los stakeholders técnicos y de negocio involucrados en el proyecto, incluyendo sus motivaciones, nivel de influencia y postura hacia las decisiones de arquitectura.

11. Identificar, validar el material técnico y participar en sesiones críticas con stakeholders senior del cliente o de tecnología del cliente que requieran el criterio del DE Lead. Asegurar que el equipo tiene clara la agenda y el objetivo técnico antes de construir el material.

12. Agendar y ejecutar one-on-ones con stakeholders técnicos senior del cliente (CTO, arquitectos, equipo de infraestructura) para alinear expectativas técnicas, anticipar restricciones de ambiente y construir una relación de confianza técnica.

13. Anticipar y coordinar la participación del director de Analítica en momentos críticos del proyecto (revisiones de arquitectura, escalamientos de cliente, decisiones de alcance técnico), comunicando con claridad el contexto y el tipo de apoyo requerido.

14. Crear y ejecutar un plan de transición, onboarding técnico, KT y seguimiento al staffing del proyecto al inicio, durante y al final, considerando riesgos de pérdida de conocimiento de arquitectura ante cambios de equipo.

### Guía y soporte al equipo interno

15. Asegurar que los proyectos a su cargo cumplen con las actividades de la Mesa de Talento, incluyendo evaluaciones de desempeño cerradas antes de que el equipo se reasigne a otros proyectos.

16. Monitorear el avance de los planes de capacitación técnica del equipo de Ingeniería en sus proyectos. Identificar quién no puede avanzar por carga de trabajo y escalar al director de Analítica con propuesta de solución.

17. Monitorear la ejecución y calidad de las sesiones de mentoring de los DE Sr/Mid en sus proyectos. Actuar sobre el mentoring que no está generando desarrollo real en el mentee.

18. Dar seguimiento a la planeación y anticipación de vacaciones y ausencias del equipo de DE en sus proyectos, gestionándolas como riesgo de continuidad de pipeline, no como trámite administrativo.

19. Ser el punto de referencia del equipo de DE para resolver dudas sobre procedimientos internos de Arena (PMO, Odoo, Mesa de Talento, vacaciones, etc.) sin necesidad de intermediación de RH o PMO.

20. Planear y ejecutar sesiones de aprendizaje técnico con el equipo de DE. Las sesiones deben desarrollar capacidades de arquitectura, ingeniería de datos o consultoría técnica que el equipo pueda aplicar en proyectos.

21. Identificar y gestionar la implementación de mejoras a las metodologías, estándares de arquitectura y herramientas del equipo de DE, en coordinación con los demás leads y el director de Analítica.

### Soporte comercial

22. Identificar oportunidades de expansión del trabajo de DE en los proyectos: nuevas fuentes de datos, modernización de arquitecturas legacy, automatización de procesos manuales del cliente o expansión de la cobertura del pipeline actual.

23. Dar soporte en la construcción y validación técnica de propuestas de ingeniería de datos: viabilidad de arquitectura, estimaciones de esfuerzo de pipeline, alcance técnico y dependencias con el cliente.

24. Dar soporte en el seguimiento a facturación y temas administrativos del proyecto cuando sea requerido por el director.

25. Coordinar y tener sesiones presenciales en las oficinas del cliente o de Arena para fortalecer la relación técnica y mantener una presencia activa de Arena con el equipo de tecnología del cliente.

### Cumplimiento de lineamientos de trabajo remoto

26. **Cumplimiento de lineamientos de trabajo remoto 1** — Confirmar asistencia a reuniones, conectarse de forma puntual, prender cámara y mantenerse atento y participativo durante toda la sesión.

27. **Cumplimiento de lineamientos de trabajo remoto 2** — Responder correos y mensajes de Teams dentro de las 24 horas hábiles. Si no puede dar respuesta completa, confirmar recepción dentro de las 4 horas y estimar cuándo la tendrá.

---

**Conclusión** *(texto libre)*

28. **Fortalezas**
29. **Oportunidades**
30. **Comentarios** *(opcional)*

---

**Confirmación de envío**

31. **Confirmo que ya revisé esta autoevaluación con mi líder y cuento con su validación** *(Sí / No)*
