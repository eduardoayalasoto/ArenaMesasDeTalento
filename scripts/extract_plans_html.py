"""Extrae los datos de los 4 planes HTML de capacitación 2026 (spec 006, T002).

Uso (una sola vez, fuera de la app):
    python -I scripts/extract_plans_html.py <carpeta_con_los_html> <salida.json>

Genera un volcado CRUDO por plan: metadatos (periodo, horas), stacks (nombre, descripción,
enfoque) y, por curso, liga, nombre, nivel, marca KO, fase KO, plataforma/duración; más las
certificaciones (clave de examen, nombre, liga, detalle con costo). El archivo curado
`apps/learning/data/planes_2026.json` se arma a partir de este volcado y del Excel con
`scripts/build_plans_json.py`.
"""

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

FILES = {
    "Plan_Capacitacion_PM_CORREGIDO.html": ["PM"],
    "Plan_Capacitacion_UXUI_CORREGIDO.html": ["UXUI"],
    "Plan_Capacitacion_DS_2026_CORREGIDO.html": ["CD"],
    "Plan_Capacitacion_IS_CORREGIDO.html": ["CD", "ID"],  # IA v2 y luego Ingeniería de Datos
}
VOID = {"br", "img", "input", "meta", "link", "hr", "source", "wbr"}


class PlanParser(HTMLParser):
    def __init__(self, areas):
        super().__init__(convert_charrefs=True)
        self.areas = list(areas)
        self.area_idx = 0
        self.plans = {a: {"area": a, "texts": [], "stacks": []} for a in self.areas}
        self.stack_tags = []  # pila de (tag, clases)
        self.stack = None
        self.item = None
        self.cert = None
        self.capture = None  # (clave, nivel de pila en que empezó)
        self.buf = []
        self.in_h1 = False
        self.h1 = []
        self.sublabel = ""
        self.row_name = ""

    @property
    def plan(self):
        return self.plans[self.areas[self.area_idx]]

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = set((a.get("class") or "").split())
        if tag not in VOID:
            self.stack_tags.append((tag, cls))
        depth = len(self.stack_tags)
        if tag == "h1":
            self.in_h1, self.h1 = True, []
        if "stack-card" in cls:
            self.stack = {"badge": "", "name": "", "desc": "", "enfoque": "", "courses": [], "certs": [], "_depth": depth}
            self.plan["stacks"].append(self.stack)
        for key in ("stack-badge", "stack-name", "stack-desc", "stack-enfoque", "pilar-sublabel", "pilar-row-name"):
            if key in cls and self.capture is None:
                self.capture, self.buf = (key, depth), []
        if "course-item" in cls and self.stack is not None:
            self.item = {"url": "", "name": "", "level": "", "ko": False, "phase": "", "plat": "",
                         "group": self.sublabel, "row": self.row_name, "_depth": depth}
        if self.item is not None:
            if tag == "a" and not self.item["url"]:
                self.item["url"] = a.get("href", "")
                self.capture, self.buf = ("item-name", depth), []
            elif "level-tag" in cls:
                self.capture, self.buf = ("item-level", depth), []
            elif "ko-badge" in cls or "ko-tag" in cls:
                self.item["ko"] = True
            elif "phase-pill" in cls:
                self.capture, self.buf = ("item-phase", depth), []
            elif "course-item-plat" in cls:
                self.capture, self.buf = ("item-plat", depth), []
        if "cert-item" in cls and self.stack is not None:
            self.cert = {"exam": "", "name": "", "url": "", "detail": "", "info": [], "_depth": depth}
        if self.cert is not None:
            if "cert-exam" in cls:
                self.capture, self.buf = ("cert-exam", depth), []
            elif "cert-name" in cls:
                self.capture, self.buf = ("cert-name", depth), []
            elif tag == "a" and not self.cert["url"]:
                self.cert["url"] = a.get("href", "")
            elif "cert-detail" in cls:
                self.capture, self.buf = ("cert-detail", depth), []

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        depth = len(self.stack_tags)
        if self.capture and self.capture[1] == depth:
            self._flush()
        if tag == "h1" and self.in_h1:
            self.in_h1 = False
            title = " ".join("".join(self.h1).split())
            if "Datos" in title and len(self.areas) > 1:
                self.area_idx = 1
            self.plan["h1"] = title
        if self.item is not None and self.item["_depth"] == depth:
            it = self.item
            self.item = None
            it.pop("_depth")
            if it["url"]:
                self.stack["courses"].append(it)
        if self.cert is not None and self.cert["_depth"] == depth:
            c = self.cert
            self.cert = None
            c.pop("_depth")
            c["info"] = " ".join("".join(c["info"]).split())
            self.stack["certs"].append(c)
        if self.stack is not None and self.stack["_depth"] == depth:
            self.stack.pop("_depth")
            self.stack = None
        if self.stack_tags:
            self.stack_tags.pop()

    def handle_data(self, data):
        if self.in_h1:
            self.h1.append(data)
        if self.capture:
            self.buf.append(data)
        if self.cert is not None:
            self.cert["info"].append(data)
        self.plan["texts"].append(data)

    def _flush(self):
        key, _ = self.capture
        text = " ".join("".join(self.buf).split())
        self.capture = None
        if key.startswith("stack-") and self.stack is not None:
            self.stack[key.removeprefix("stack-")] = text
        elif key == "pilar-sublabel":
            self.sublabel = text
        elif key == "pilar-row-name":
            self.row_name, self.sublabel = text, ""
        elif key == "item-name" and self.item is not None:
            self.item["name"] = text
        elif key == "item-level" and self.item is not None:
            self.item["level"] = text
        elif key == "item-phase" and self.item is not None:
            self.item["phase"] = text
        elif key == "item-plat" and self.item is not None:
            self.item["plat"] = text
        elif key.startswith("cert-") and self.cert is not None:
            self.cert[key.removeprefix("cert-")] = text


MONTHS = {m: i for i, m in enumerate(
    ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
     "noviembre", "diciembre"], start=1)}


def plan_meta(text: str) -> dict:
    meta = {}
    m = re.search(r"(\d+)\s*[–-]\s*(\d+)\s*hrs?\s*/\s*semana", text)
    if m:
        meta["hours_min"], meta["hours_max"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)"
                  r"\s*[–-]\s*(Enero|Febrero|Marzo|Abril|Mayo|Junio|Julio|Agosto|Septiembre|Octubre|Noviembre|Diciembre)"
                  r"\s*(\d{4})", text)
    if m:
        meta["start_month"], meta["end_month"] = MONTHS[m.group(1).lower()], MONTHS[m.group(2).lower()]
        meta["year"] = int(m.group(3))
    return meta


def main(folder: str, out: str):
    result = []
    for fname, areas in FILES.items():
        parser = PlanParser(areas)
        parser.feed((Path(folder) / fname).read_text(encoding="utf-8"))
        for area in areas:
            plan = parser.plans[area]
            text = " ".join(" ".join(plan.pop("texts")).split())
            plan.update(plan_meta(text))
            plan["source"] = fname
            result.append(plan)
    Path(out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for p in result:
        n = sum(len(s["courses"]) for s in p["stacks"])
        c = sum(len(s["certs"]) for s in p["stacks"])
        print(f"{p['source']:45} {p['area']:5} stacks={len(p['stacks'])} cursos={n} certs={c} "
              f"meta={ {k: p.get(k) for k in ('start_month', 'end_month', 'year', 'hours_min', 'hours_max')} }")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
