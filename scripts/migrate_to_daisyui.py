"""Fases 3-4 de la migración a daisyUI (docs/PLAN_MIGRACION_DISENO.md): clases legadas `ui-*`
y paleta cruda (slate/gray, arena-*, emerald/amber/rose/sky) -> componentes daisyUI y tokens
semánticos del tema, como en arena-crm. Idempotente; preserva finales de línea (bytes).

No toca templates/components/ ni las plantillas copiadas tal cual de arena-crm.

Uso: python scripts/migrate_to_daisyui.py [--dry]
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"_navbar.html", "_auth_card.html"}

CARD = "bg-base-100 border border-base-300 rounded-2xl shadow-sm"
UI = {
    "ui-card": CARD,
    "ui-btn-primary": "btn btn-primary",
    "ui-btn-secondary": "btn btn-outline btn-primary",
    "ui-btn-ghost": "btn btn-ghost",
    "ui-btn-danger": "btn btn-error",
    "ui-btn-soft": "btn btn-sm btn-soft btn-primary",
    "ui-label": "fieldset-legend",
    "ui-badge": "badge",
}

STATE = {"emerald": "success", "green": "success", "amber": "warning", "yellow": "warning",
         "rose": "error", "red": "error", "sky": "info", "blue": "info"}
B = r"(?<![\w/-])"   # inicio de token (permite prefijos `hover:` antes)
E = r"(?![\w/-])"    # fin de token

TOKEN = re.compile(B + r"((?:[a-z-]+:)*)(text|bg|border|ring|divide|from|via|to|fill|stroke|outline)-"
                   r"(slate|gray|arena|emerald|green|amber|yellow|rose|red|sky|blue)-(\d+)(/\d+)?" + E)
DARK = re.compile(r"\s*" + B + r"dark:[^\s\"'{}]+")
WHITE = re.compile(B + r"((?:[a-z-]+:)*)bg-white" + E)
UI_RX = re.compile(B + r"(" + "|".join(map(re.escape, UI)) + r")" + E)
TAG_INPUT = re.compile(r"<(input|select|textarea)\b[^>]*>", re.S)


def _alpha(shade: int) -> str:
    return {50: "/10", 100: "/15", 200: "/25", 300: "/40", 400: "/70"}.get(shade, "")


def _neutral(util: str, shade: int, op: str) -> str | None:
    if util == "text":
        n = {900: "", 800: "", 700: "/80", 600: "/70", 500: "/60", 400: "/50", 300: "/40", 200: "/30"}
        return None if shade not in n else f"text-base-content{n[shade]}"
    if util == "bg":
        if shade >= 800:
            return f"bg-neutral{op}"
        return {50: "bg-base-200/50", 100: "bg-base-200", 200: "bg-base-300", 300: "bg-base-300"}.get(shade)
    if util in ("border", "divide", "ring", "outline"):
        return f"{util}-base-200" if shade <= 100 else f"{util}-base-300"
    return None


def _brand(util: str, shade: int, op: str, family: str) -> str:
    color = "primary" if family == "arena" else STATE[family]
    if util == "text":
        if family == "arena" and shade <= 300:
            return "text-primary-100"
        return f"text-{color}{op}"
    if op:
        return f"{util}-{color}{op}"
    if family == "arena" and shade >= 700:
        return f"{util}-primary-{800 if shade == 700 else 900}"
    return f"{util}-{color}{_alpha(shade)}"


def _token(m: re.Match) -> str:
    prefix, util, family, shade, op = m.group(1), m.group(2), m.group(3), int(m.group(4)), m.group(5) or ""
    if family in ("slate", "gray"):
        new = _neutral(util, shade, op)
    else:
        new = _brand(util, shade, op, family)
    return prefix + new if new else m.group(0)


def _fix_input_tag(m: re.Match) -> str:
    tag = m.group(0)
    base = {"input": "input", "select": "select", "textarea": "textarea"}[m.group(1)]
    return re.sub(B + r"ui-input" + E, f"{base} w-full", tag)


def convert(text: str) -> str:
    text = TAG_INPUT.sub(_fix_input_tag, text)
    text = re.sub(B + r"ui-input" + E, "input w-full", text)
    text = UI_RX.sub(lambda m: UI[m.group(1)], text)
    text = DARK.sub("", text)
    text = WHITE.sub(lambda m: m.group(1) + "bg-base-100", text)
    text = TOKEN.sub(_token, text)
    return text


def targets():
    for p in (ROOT / "templates").rglob("*.html"):
        if "components" in p.parts or p.name in SKIP:
            continue
        yield p
    for p in (ROOT / "apps").rglob("*.py"):
        if "tests" in p.parts or "migrations" in p.parts:
            continue
        yield p


def main(dry: bool) -> None:
    changed = 0
    for p in targets():
        raw = p.read_bytes().decode("utf-8")
        new = convert(raw)
        if new != raw:
            changed += 1
            if not dry:
                p.write_bytes(new.encode("utf-8"))
            print(p.relative_to(ROOT))
    print(f"{changed} archivos {'por cambiar' if dry else 'cambiados'}")


if __name__ == "__main__":
    main("--dry" in sys.argv)
