"""Ajustes por curso del criterio técnico de FR-026a (spec 006), tras revisar el nombre de cada curso.

Clave: nombre exacto del curso (como viene en el material). Solo aplica a datos que el material no
define o define dos veces; nunca contradice un tipo o enfoque que el material da una sola vez.
"""

_EST_FULL = {"kind": "ESTRUCTURADO", "why_kind": "curso completo de varias semanas, con módulos"}
_PUN = {"kind": "PUNTUAL", "why_kind": "curso corto (≈2 h) de un solo tema"}
_H_INTRO = {"focus": "HORIZONTAL", "why_focus": "introducción o panorama general de varios temas"}
_H_ROLE = {"focus": "HORIZONTAL", "why_focus": "aplica la IA de forma amplia al rol o a la gestión"}
_H_MGMT = {"focus": "HORIZONTAL", "why_focus": "habilidad de gestión transversal"}
_V_TOOL = {"focus": "VERTICAL", "why_focus": "profundiza en una sola herramienta o técnica"}

COURSE_OVERRIDES: dict[str, dict] = {
    # --- Tipo ------------------------------------------------------------------------------
    "Communicating Data Insights": _PUN,
    "Accessibility in Practice": _EST_FULL,
    "Agile Methods for UX Design": _EST_FULL,
    "Data-Driven Design: Quantitative Research for UX": _EST_FULL,
    "Information Visualization: Getting Dashboards Right": _EST_FULL,
    "UI Design Patterns for Successful Software": _EST_FULL,
    "User Research — Methods and Best Practices": _EST_FULL,
    "AI-103T00-A: Develop AI apps and agents on Azure": {
        "kind": "ESTRUCTURADO", "why_kind": "curso oficial de Microsoft de varios días (preparación AI-103)"},
    "AI-300T00-A: Operationalize ML and generative AI solutions": {
        "kind": "ESTRUCTURADO", "why_kind": "curso oficial de Microsoft de varios días (preparación AI-300)"},
    "DP-700T00: Implement Data Engineering in Microsoft Fabric": {
        "kind": "ESTRUCTURADO", "why_kind": "curso oficial de Microsoft de varios días (preparación DP-700)"},
    # --- Enfoque ---------------------------------------------------------------------------
    "Google UX Design Certificate": {
        "focus": "HORIZONTAL", "why_focus": "programa amplio: research, wireframes, prototipos y handoff"},
    "A Beginner's Guide to Data Engineering — Part I": _H_INTRO,
    "Artificial Intelligence for PM": _H_ROLE,
    "Azure Well-Architected Framework": {
        "focus": "HORIZONTAL", "why_focus": "marco general que cubre todos los pilares de arquitectura"},
    "Chart Guide — Storytelling with Data": {"focus": "VERTICAL", "why_focus": "guía específica para elegir gráficas"},
    "Design Critiques: Encourage a Positive Culture to Improve Products": {
        "focus": "HORIZONTAL", "why_focus": "práctica de equipo transversal"},
    "Explore Microsoft 365 Copilot and agents": {
        "focus": "HORIZONTAL", "why_focus": "panorama de toda la suite de Copilot"},
    "Fostering appropriate reliance on GenAI": {"focus": "HORIZONTAL", "why_focus": "criterio general de uso de IA"},
    "Getting Started with Generative AI in Azure": _H_INTRO,
    "How Business Thinkers Can Start Building AI Plugins with Semantic Kernel": {
        "focus": "VERTICAL", "why_focus": "se centra en un SDK específico (Semantic Kernel)"},
    "Integrating GenAI Into the Creative Process": _H_ROLE,
    "Introduction to AI Agents": _H_INTRO,
    "Introduction to MongoDB": _V_TOOL,
    "Introduction to NLP and LLM: Principles and Practical Applications": _H_INTRO,
    "Introduction to On-Device AI": _V_TOOL,
    "Introduction to Power BI": _V_TOOL,
    "Leverage Generative AI to Streamline Processes and Increase Efficiency as a Manager": _H_ROLE,
    "Machine Learning for Everybody – Full Course": _H_INTRO,
    "Manager of Managers: Coaching and Mentoring People Managers": _H_MGMT,
    "Managing as a Coach": _H_MGMT,
    "Microsoft AI Product Manager Professional Certificate": {
        "focus": "HORIZONTAL", "why_focus": "programa profesional amplio (60 h) para el rol de PM"},
    "MLOps Concept": _H_INTRO,
    "Python for Everybody Specialization": _H_INTRO,
    "Reinforcement Learning from Human Feedback": _V_TOOL,
    "Strengthen your Decision Making with GenAI": _H_ROLE,
    "The AI-Driven Product Designer": _H_ROLE,
    "Understanding Data Engineering": _H_INTRO,
    "Understanding Machine Learning": _H_INTRO,
    "Using AI for Data-Driven Insights": _H_ROLE,
    "UX Writing Study Guide": {"focus": "VERTICAL", "why_focus": "profundiza en una sola práctica (UX writing)"},
}
