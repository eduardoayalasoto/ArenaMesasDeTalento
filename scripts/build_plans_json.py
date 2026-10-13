"""Arma `apps/learning/data/planes_2026.json` (spec 006, T025) a partir de:

1. El Excel `Catalogo_Cursos_Plataforma_Capacitacion.xlsx` (catálogo por área).
2. El volcado crudo de los 4 HTML (`scripts/extract_plans_html.py`).
3. El criterio técnico documentado en la spec (FR-026a) para los huecos del material, con los
   ajustes por curso de `scripts/plans_overrides.py`.

Uso:  python -I scripts/build_plans_json.py <excel.xlsx> <raw_plans.json> <salida.json> [<reporte.md>]

Reglas (spec 006, R7/R12):
- Tipo de aprendizaje y enfoque son dimensiones independientes. "Aprendizaje Horizontal/Vertical"
  del material es ENFOQUE; "Aprendizaje Estructurado/Certificado/Puntual/Contextual" y
  "Habilidades Blandas" son TIPO. Ninguno se deriva del otro.
- Lo que el material no dice se asigna con criterio técnico y queda marcado `proposed`.
- Hoja ID: "Ingeniería de IA" -> plan CD; "Ingeniería de Datos" -> plan ID.
- KO solo es etiqueta. Los cursos solo-KO del plan PM son tipo Puntual; nivel por fase KO.
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from plans_overrides import COURSE_OVERRIDES  # noqa: E402

YEAR = 2026
TRACKING = {"t", "si", "ref", "trk", "source", "referralcode", "feature"}

KIND_ALIASES = {
    "aprendizaje estructurado": "ESTRUCTURADO", "aprendizaje certificado": "CERTIFICACION",
    "aprendizaje puntual": "PUNTUAL", "aprendizaje contextual": "CONTEXTUAL", "habilidades blandas": "SOFT_SKILLS",
}
FOCUS_ALIASES = {"aprendizaje horizontal": "HORIZONTAL", "aprendizaje vertical": "VERTICAL"}
KIND_ORDER = ["ESTRUCTURADO", "CERTIFICACION", "PUNTUAL", "CONTEXTUAL", "SOFT_SKILLS", "EVENTO"]
KO_PHASE_LEVELS = {"F": ["JR"], "I": ["MID"], "A": ["SNR"]}
LEVEL_CODES = {"jr": "JR", "mid": "MID", "snr": "SNR", "senior": "SNR", "lead": "LEAD"}
SHEET_AREA = {"PM": "PM", "UX-UI": "UXUI", "CD": "CD"}

PLAN_META = {
    "PM": {"title": "Plan de Capacitación PM 2026",
           "intro": "Catálogo sugerido, no currícula obligatoria: cada PM elige según su nivel, la brecha "
                    "identificada en su evaluación y sus proyectos actuales. Las etiquetas Jr, Mid y Snr indican "
                    "el nivel para el que el curso es prioritario; un curso sin nivel es para todos."},
    "UXUI": {"title": "Plan de Capacitación UX/UI 2026",
             "intro": "Catálogo sugerido, no currícula obligatoria: cada diseñador elige según su nivel, su rol "
                      "en los proyectos y las áreas de oportunidad identificadas."},
    "CD": {"title": "Plan de Capacitación Ingeniería de IA 2026",
           "intro": "Catálogo sugerido, no currícula rígida: cada persona elige sus cursos según su rol en "
                    "proyectos, sus fortalezas y su tiempo disponible. Stack: Azure + Claude. Microsoft Learn y "
                    "Anthropic Academy son gratuitos; el costo principal son los exámenes de certificación."},
    "ID": {"title": "Plan de Capacitación Ingeniería de Datos 2026",
           "intro": "Catálogo sugerido, no currícula rígida: cada persona elige sus cursos según su rol en "
                    "proyectos, sus fortalezas y su tiempo disponible."},
}

# Certificaciones (no están en el Excel). Clave = examen; AI-900 del plan PM es el mismo examen
# que AI-901 (su liga apunta al curso AI-901T00). Sin liga propia en el material -> url vacía
# (cuando la guía enlaza al curso de preparación, ese curso ya está en el catálogo).
CERTS = {
    "PMP": {"name": "PMP · Project Management Professional", "provider": "PMI",
            "url": "https://www.pmi.org/certifications/project-management-pmp", "cost": 405},
    "PL-300": {"name": "PL-300 · Microsoft Power BI Data Analyst Associate", "provider": "Microsoft",
               "url": "", "cost": 165},  # su liga es la del curso de preparación "Power BI Data Analyst"
    "DP-900": {"name": "DP-900 · Microsoft Azure Data Fundamentals", "provider": "Microsoft", "url": "", "cost": 165},
    "AI-901": {"name": "AI-901 · Azure AI Fundamentals", "provider": "Microsoft", "url": "", "cost": 165},
    "AI-103": {"name": "AI-103 · Azure AI App & Agent Developer Associate", "provider": "Microsoft", "url": "",
               "cost": 165},
    "AI-300": {"name": "AI-300 · MLOps Engineer Associate", "provider": "Microsoft", "url": "", "cost": 165},
    "CCA": {"name": "Claude Certified Architect", "provider": "Anthropic Academy", "url": "", "cost": 0},
    "DP-700": {"name": "DP-700 · Fabric Data Engineer Associate", "provider": "Microsoft", "url": "", "cost": 165},
    "DP-203": {"name": "DP-203 · Azure Data Engineer Associate", "provider": "Microsoft", "url": "", "cost": 165},
    "DBX": {"name": "Databricks Certified Data Engineer Associate", "provider": "Databricks", "url": "", "cost": 200},
    "AZ-400": {"name": "AZ-400 · DevOps Engineer Expert", "provider": "Microsoft", "url": "", "cost": 165},
}
CERT_ALIASES = {"AI-900": "AI-901"}
# Niveles de certificación que el material indica en el texto ("Recomendado para ...").
CERT_LEVELS = {"PMP": ["SNR"], "PL-300": ["MID"], "DP-900": ["MID"], "GUX": ["JR", "MID"],
               "DP-700": ["MID", "SNR", "LEAD"], "DP-203": ["SNR", "LEAD"], "AZ-400": ["SNR", "LEAD"]}

DOMAIN_PROVIDERS = {
    "learn.microsoft.com": "Microsoft Learn", "coursera.org": "Coursera", "linkedin.com": "LinkedIn Learning",
    "datacamp.com": "DataCamp", "deeplearning.ai": "DeepLearning.AI", "udemy.com": "Udemy", "alison.com": "Alison",
    "youtube.com": "YouTube", "anthropic.skilljar.com": "Anthropic Academy", "nngroup.com": "Nielsen Norman Group",
    "interaction-design.org": "Interaction Design Foundation", "mckinsey.com": "McKinsey",
}


def norm_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    p = urlsplit(url if "://" in url else f"https://{url}")
    host = (p.hostname or "").lower().removeprefix("www.")
    params = sorted((k, v) for k, v in parse_qsl(p.query)
                    if not (k.lower() in TRACKING or k.lower().startswith(("utm", "coupon"))))
    return f"{host}{p.path.rstrip('/').lower()}" + (f"?{urlencode(params)}" if params else "")


def clean_url(url: str) -> str:
    """Liga para guardar: sin parámetros de rastreo ni posición (`&t=285s`)."""
    p = urlsplit(url.strip())
    params = [(k, v) for k, v in parse_qsl(p.query)
              if not (k.lower() in TRACKING or k.lower().startswith(("utm", "coupon")))]
    return p._replace(query=urlencode(params), fragment="").geturl()


def provider_from(url, *candidates):
    for c in candidates:
        c = (c or "").strip()
        if c:
            return c
    host = (urlsplit(url).hostname or "").lower().removeprefix("www.")
    for dom, name in DOMAIN_PROVIDERS.items():
        if host.endswith(dom):
            return name
    return "Sin especificar"


def parse_plat(plat: str):
    """'~10 h · Coursera · LearnQuest' -> (10.0, 'Coursera · LearnQuest', gratis?)."""
    parts = [x.strip() for x in (plat or "").split("·") if x.strip()]
    hours, rest, free = None, [], False
    for x in parts:
        m = re.fullmatch(r"~?\s*(\d+(?:\.\d+)?)\s*(?:[-–]\s*(\d+(?:\.\d+)?))?\s*h", x)
        if m and hours is None:
            a, b = float(m.group(1)), float(m.group(2) or m.group(1))
            hours = round((a + b) / 2 * 2) / 2
        elif x.lower() in ("gratis", "gratuito"):
            free = True
        elif x and not x.startswith(("⚠", "💳")):
            rest.append(x)
    return hours, " · ".join(rest), free


def parse_levels(text: str) -> list[str]:
    t = (text or "").strip().lower()
    if not t or t.startswith("todo"):
        return []
    out = []
    for part in re.split(r"[-–/ ]+", t):
        code = LEVEL_CODES.get(part)
        if code and code not in out:
            out.append(code)
    return out


def stack_kind(name: str):
    return KIND_ALIASES.get(" ".join(name.lower().replace("aprendizaje", "aprendizaje ").split()))


def stack_focus(stack) -> str | None:
    name = " ".join(stack["name"].lower().replace("aprendizaje", "aprendizaje ").split())
    if name in FOCUS_ALIASES:
        return FOCUS_ALIASES[name]
    enf = stack["enfoque"].lower()
    if "horizontal" in enf or "amplitud" in enf:
        return "HORIZONTAL"
    if "vertical" in enf or "profundidad" in enf:
        return "VERTICAL"
    return None


# --- Criterio técnico para huecos (FR-026a) ----------------------------------------------

VERTICAL_HINTS = re.compile(
    r"\b(advanced|intermediate|deep|fine-?tun|rag\b|langchain|langgraph|llamaindex|haystack|vector|embedding|"
    r"kusto|kql|dax|power query|spacy|pyspark|spark|databricks|delta|dbt|airflow|kafka|terraform|docker|"
    r"kubernetes|mlops|llmops|function-calling|agents?\b|agentic|mcp|prompt|eval|debug|anomaly|time series|"
    r"nlp|computer vision|forecast|serving|quantiz|copilot in|copilot en|with (?:the )?claude|claude code|"
    r"api|sql|python|fabric|synapse|purview|devops|ci/cd|testing|security|governance of|figma|prototyp|"
    r"accessibility|accesibilidad|usability testing|design system)", re.I)
HORIZONTAL_HINTS = re.compile(
    r"\b(introduction|intro\b|fundamentals|foundations|basics|for everyone|for business|for leaders|"
    r"for managers|for product managers|overview|strategy|strategic|leadership|thinking|storytelling|"
    r"communicat|retail|supply chain|industry|cpg|consumer|business|crash course|what is|essentials|"
    r"principles|concepts|literacy|ethics|responsible|governance|career|productivity|time management|"
    r"negotiat|stakeholder|presentation|feedback|ownership|research cheat sheet|ux research)", re.I)
SOFT_HINTS = re.compile(r"\b(communicat|leadership|negotiat|feedback|emotional|presentation|storytelling|"
                        r"time management|productivity|critical thinking|problem solving|career|teamwork|"
                        r"stakeholder|influence|resilien|pressure|ownership|executive)", re.I)


def propose_kind(c) -> tuple[str, str]:
    url, name, hours = c["url"].lower(), c["name"], c.get("duration_hours")
    if any(k in url for k in ("/paths/", "/specializations/", "/professional-certificates/", "/certificates/")):
        return "ESTRUCTURADO", "ruta o programa de varios módulos"
    if "/modules/" in url or "nngroup.com/articles" in url or "youtube.com" in url:
        return "PUNTUAL", "módulo, artículo o video de un solo tema"
    if SOFT_HINTS.search(name) and not VERTICAL_HINTS.search(name):
        return "SOFT_SKILLS", "habilidad interpersonal"
    if hours is not None and hours <= 4:
        return "PUNTUAL", f"curso corto ({hours:g} h) de un solo tema"
    if "skilljar.com" in url or "coursera.org/learn" in url or "udemy.com" in url or (hours or 0) >= 6:
        return "ESTRUCTURADO", "curso completo con varios módulos"
    return "PUNTUAL", "curso corto de un solo tema"


def propose_focus(c, kind) -> tuple[str, str]:
    name = c["name"]
    v, h = VERTICAL_HINTS.search(name), HORIZONTAL_HINTS.search(name)
    if v and not h:
        return "VERTICAL", f"profundiza en una herramienta o técnica («{v.group(0)}»)"
    if h and not v:
        return "HORIZONTAL", f"cubre fundamentos o varios temas («{h.group(0)}»)"
    if kind == "CERTIFICACION":
        return "VERTICAL", "certificación: valida profundidad en un dominio"
    if kind in ("CONTEXTUAL", "SOFT_SKILLS"):
        return "HORIZONTAL", "contexto o habilidad transversal"
    if kind == "PUNTUAL":
        return "VERTICAL", "skill específico"
    return "HORIZONTAL", "curso amplio de varios temas"


# --- Construcción --------------------------------------------------------------------------


def read_excel(path):
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True)
    rows = []
    for ws in wb:
        for i, r in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            name, url, plat, d = (r + (None,) * 5)[:4]
            if not name and not url:
                continue
            rows.append({"sheet": ws.title, "row": i, "name": str(name or "").strip(), "url": str(url or "").strip(),
                         "platform": str(plat or "").strip(), "types": str(d or "")})
    return rows


def build(xlsx, raw_path):
    courses: dict[str, dict] = {}
    plans: dict[str, dict] = {}
    unprocessed, aliases = [], []

    def course_for(url, name, provider=""):
        key = norm_url(url)
        c = courses.get(key)
        if c is None:
            c = courses[key] = {"url": clean_url(url), "name": name, "provider": provider, "kinds": [], "focuses": [],
                                "ko": False, "duration_hours": None, "free": False, "aliases": []}
        elif name and name != c["name"] and name not in c["aliases"]:
            c["aliases"].append(name)
        if provider and not c["provider"]:
            c["provider"] = provider
        return c

    def plan_for(area):
        return plans.setdefault(area, {"area": area, "items": {}, "type_notes": {}})

    def add_item(area, c, levels=None, note=""):
        p = plan_for(area)
        key = norm_url(c["url"]) or c["name"]
        it = p["items"].get(key)
        if it is None:
            it = p["items"][key] = {"course": key, "levels": [], "note": note, "order": len(p["items"]) + 1}
        for lv in levels or ():
            if lv not in it["levels"]:
                it["levels"].append(lv)
        if note and not it["note"]:
            it["note"] = note
        return it

    # 1) HTML: orden de la guía, niveles, KO, fase, duración, enfoque y tipo por stack.
    raw = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    meta_by_area = {}
    for plan in raw:
        area = plan["area"]
        meta_by_area.setdefault(area, {k: plan.get(k) for k in ("start_month", "end_month", "hours_min", "hours_max")})
        for st in plan["stacks"]:
            kind = stack_kind(st["name"])
            focus = stack_focus(st)
            is_ko_stack = "ko upskilling" in st["name"].lower()
            if kind and st["desc"]:
                plan_for(area)["type_notes"].setdefault(kind, st["desc"])
            for it in st["courses"]:
                hours, prov, free = parse_plat(it["plat"])
                c = course_for(it["url"], it["name"], "")
                c["html_provider"] = c.get("html_provider") or prov
                c["duration_hours"] = c["duration_hours"] or hours
                c["free"] = c["free"] or free
                if kind:
                    c["kinds"].append(kind)
                if focus:
                    c["focuses"].append(focus)
                levels = parse_levels(it["level"])
                if is_ko_stack or it["ko"]:
                    c["ko"] = True
                if is_ko_stack:
                    c["ko_only_pm"] = True
                    phase = it["phase"].strip().upper() or next(
                        (code for word, code in (("foundations", "F"), ("intermediate", "I"), ("advanced", "A"))
                         if word in it.get("row", "").lower()), "")
                    if not levels and phase and not c.get("regular"):  # FR-028a: el nivel regular manda
                        levels = KO_PHASE_LEVELS.get(phase, [])
                elif not is_ko_stack:
                    c["regular"] = True
                add_item(area, c, levels)
            for ce in st["certs"]:
                code = CERT_ALIASES.get(ce["exam"], ce["exam"])
                if code == "GUX":
                    c = course_for(ce["url"], ce["name"], "Google / Coursera")
                    c["kinds"].append("CERTIFICACION")
                    c["focuses"].append(focus or "VERTICAL")
                    add_item(area, c, CERT_LEVELS.get(code, []), ce["detail"])
                    continue
                spec = CERTS[code]
                key = f"cert:{code}"  # el examen es un elemento propio, aparte de su curso de preparación
                c = courses.get(key)
                if c is None:
                    c = courses[key] = {"url": spec["url"], "name": spec["name"], "provider": spec["provider"],
                                        "kinds": ["CERTIFICACION"], "focuses": [focus or "VERTICAL"], "ko": False,
                                        "duration_hours": None, "free": False, "aliases": [],
                                        "reference_cost": spec["cost"], "currency": "USD", "cert": code}
                p = plan_for(area)
                note = ce["detail"]
                it = p["items"].get(key)
                if it is None:
                    p["items"][key] = {"course": key, "levels": list(CERT_LEVELS.get(code, [])), "note": note,
                                       "order": len(p["items"]) + 1}

    # 2) Excel: catálogo por área, plataforma y tipo (y ruta de la hoja ID).
    for r in read_excel(xlsx):
        if not r["url"]:
            unprocessed.append(f"{r['sheet']} fila {r['row']}: «{r['name']}» sin liga")
            continue
        for entry in [e.strip() for e in r["types"].split(";") if e.strip()] or [""]:
            route, _, label = entry.rpartition("—")
            route, label = route.strip().lower(), label.strip().lower()
            if r["sheet"] == "ID":
                area = "CD" if "ia" in route.split() or "inteligencia" in route or route.endswith(" ia") else "ID"
                if "datos" in route:
                    area = "ID"
            else:
                area = SHEET_AREA.get(r["sheet"])
            if area is None:
                unprocessed.append(f"{r['sheet']} fila {r['row']}: hoja desconocida")
                continue
            c = course_for(r["url"], r["name"], r["platform"])
            if label in KIND_ALIASES:
                c["kinds"].append(KIND_ALIASES[label])
            elif label in FOCUS_ALIASES:
                c["focuses"].append(FOCUS_ALIASES[label])
            elif "ko upskilling" in label:
                c["ko"] = True
            elif label:
                unprocessed.append(f"{r['sheet']} fila {r['row']}: tipo desconocido «{label}»")
            add_item(area, c)

    # 3) Tipo, enfoque y huecos con criterio técnico.
    report = []
    for key, c in courses.items():
        c["provider"] = provider_from(c["url"], c.get("provider"), c.get("html_provider"))
        kinds = list(dict.fromkeys(c["kinds"]))
        focuses = list(dict.fromkeys(c["focuses"]))
        proposed, why = [], []
        if c.get("ko_only_pm") and not c.get("regular") and not kinds:
            kinds = ["PUNTUAL"]
            why.append("tipo: solo en el bloque KO de PM → Puntual (decisión de la spec)")
        ov = COURSE_OVERRIDES.get(key) or COURSE_OVERRIDES.get(c["name"], {})
        if "kind" in ov and len(kinds) != 1:
            kind, reason = ov["kind"], ov.get("why_kind", "criterio por nombre")
            proposed.append("kind")
            why.append(f"tipo: {reason}")
        elif len(kinds) == 1:
            kind = kinds[0]
        elif len(kinds) > 1:
            kind = sorted(kinds, key=KIND_ORDER.index)[0]
            proposed.append("kind")
            why.append(f"tipo: el material dice {' y '.join(kinds)}; se toma {kind} (curso completo)")
        else:
            kind, reason = propose_kind(c)
            proposed.append("kind")
            why.append(f"tipo: {reason}")
        if "focus" in ov and len(focuses) != 1:
            focus, reason = ov["focus"], ov.get("why_focus", "criterio por nombre")
            proposed.append("focus")
            why.append(f"enfoque: {reason}")
        elif len(focuses) == 1:
            focus = focuses[0]
        else:
            focus, reason = propose_focus(c, kind)
            proposed.append("focus")
            why.append(("enfoque: el material dice ambos; " if len(focuses) > 1 else "enfoque: ") + reason)
        c.update(kind=kind, focus=focus, proposed=proposed, why="; ".join(why))
        if c["aliases"]:
            aliases.append(f"«{c['name']}» también aparece como: " + ", ".join(f"«{a}»" for a in c["aliases"]))
        report.append(c)

    out_courses = []
    for key, c in courses.items():
        out_courses.append({
            "key": key, "url": c["url"], "name": c["name"][:160], "provider": c["provider"][:120],
            "kind": c["kind"], "focus": c["focus"], "duration_hours": c["duration_hours"],
            "reference_cost": c.get("reference_cost", 0 if c["free"] else None),
            "currency": c.get("currency", "USD" if c.get("reference_cost") is not None or c["free"] else "MXN"),
            "ko": c["ko"], "proposed": c["proposed"], "why": c["why"], "aliases": c["aliases"],
        })
    out_plans = []
    for area in ("PM", "UXUI", "CD", "ID"):
        p = plans[area]
        meta = meta_by_area.get(area, {})
        out_plans.append({
            "area": area, "year": YEAR, **PLAN_META[area], **meta,
            "type_notes": p["type_notes"],
            "items": sorted(p["items"].values(), key=lambda i: i["order"]),
        })
    return {"year": YEAR, "plans": out_plans, "courses": out_courses}, unprocessed, aliases


def write_report(data, unprocessed, aliases, path):
    kinds = {"ESTRUCTURADO": "Estructurado", "CERTIFICACION": "Certificación", "PUNTUAL": "Puntual",
             "CONTEXTUAL": "Contextual", "SOFT_SKILLS": "Soft Skills", "EVENTO": "Evento"}
    lines = ["# Revisión de datos propuestos · planes 2026", "",
             f"- Cursos en el catálogo: **{len(data['courses'])}**",
             f"- Con etiqueta KO: **{sum(c['ko'] for c in data['courses'])}**",
             f"- Con tipo propuesto: **{sum('kind' in c['proposed'] for c in data['courses'])}** · con enfoque "
             f"propuesto: **{sum('focus' in c['proposed'] for c in data['courses'])}**", ""]
    for p in data["plans"]:
        lines.append(f"- Plan {p['area']}: {len(p['items'])} cursos")
    lines += ["", "## Datos propuestos (curso · tipo · enfoque · motivo)", "",
              "| Curso | Tipo | Enfoque | Motivo |", "|---|---|---|---|"]
    for c in sorted(data["courses"], key=lambda c: c["name"].lower()):
        if c["proposed"]:
            t = kinds[c["kind"]] + (" *" if "kind" in c["proposed"] else "")
            f = c["focus"].capitalize() + (" *" if "focus" in c["proposed"] else "")
            lines.append(f"| {c['name']} | {t} | {f} | {c['why']} |")
    lines += ["", "\\* = propuesto con criterio técnico (el resto viene del material).", ""]
    if aliases:
        lines += ["## Misma liga con nombres distintos (se conserva el primero)", ""] + [f"- {a}" for a in aliases] + [""]
    if unprocessed:
        lines += ["## Filas no procesadas", ""] + [f"- {u}" for u in unprocessed] + [""]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    xlsx, raw, out = sys.argv[1:4]
    data, unprocessed, aliases = build(xlsx, raw)
    Path(out).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    if len(sys.argv) > 4:
        write_report(data, unprocessed, aliases, sys.argv[4])
    print(f"cursos={len(data['courses'])} ko={sum(c['ko'] for c in data['courses'])} "
          f"tipo_prop={sum('kind' in c['proposed'] for c in data['courses'])} "
          f"enfoque_prop={sum('focus' in c['proposed'] for c in data['courses'])} "
          f"planes={[(p['area'], len(p['items'])) for p in data['plans']]} no_proc={len(unprocessed)} alias={len(aliases)}")
