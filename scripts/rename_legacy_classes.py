"""Fase 0 de la migración a daisyUI (docs/PLAN_MIGRACION_DISENO.md §4).

Renombra las clases artesanales que chocan con daisyUI (`btn-primary`, `card`, `input`,
`label`, `badge`, `nav-link`, …) a su prefijo legado `ui-*`, SIN cambio visual: el CSS
(`static/src/input.css`) define las mismas reglas con el nombre nuevo. Solo toca valores de
atributos de clase (`class=`, `:class=`) en plantillas y cadenas de clase en Python.

Uso:  python scripts/rename_legacy_classes.py [--apply]
"""

import io
import re
import sys
from pathlib import Path

TOKENS = ("btn-primary", "btn-secondary", "btn-ghost", "btn-danger", "btn-soft", "btn",
          "card", "input", "label", "badge", "nav-link-active", "nav-link")
TOKEN_RX = re.compile(r"(?<![\w-])(" + "|".join(re.escape(t) for t in TOKENS) + r")(?![\w-])")

ATTR_RX = re.compile(r"""((?::class|\bclass)=)(["'])(.*?)\2""", re.S)          # templates + HTML en Python
PY_DICT_RX = re.compile(r"""("class"\s*:\s*)(["'])(.*?)\2""")                    # widgets: {"class": "input"}
PY_CONST_RX = re.compile(r"""^(\s*_?INPUT\s*=\s*)(["'])input\2""", re.M)         # _INPUT = "input"


def rename_tokens(value: str) -> str:
    return TOKEN_RX.sub(lambda m: "ui-" + m.group(1), value)


def process(text: str, is_py: bool) -> str:
    text = ATTR_RX.sub(lambda m: m.group(1) + m.group(2) + rename_tokens(m.group(3)) + m.group(2), text)
    if is_py:
        text = PY_DICT_RX.sub(lambda m: m.group(1) + m.group(2) + rename_tokens(m.group(3)) + m.group(2), text)
        text = PY_CONST_RX.sub(lambda m: m.group(1) + m.group(2) + "ui-input" + m.group(2), text)
    return text


def main(apply: bool) -> int:
    root = Path(__file__).resolve().parent.parent
    files = list((root / "templates").rglob("*.html")) + [
        p for p in (root / "apps").rglob("*.py") if "migrations" not in p.parts and "tests" not in p.parts
    ]
    changed = 0
    for path in files:
        if "components" in path.parts:  # los componentes nuevos ya usan daisyUI
            continue
        src = io.open(path, encoding="utf-8").read()
        out = process(src, path.suffix == ".py")
        if out != src:
            changed += 1
            n = sum(1 for a, b in zip(src.split(), out.split()) if a != b)
            print(f"{'escrito' if apply else 'cambiaría'}: {path.relative_to(root)} (~{n} tokens)")
            if apply:
                io.open(path, "w", encoding="utf-8", newline="").write(out)
    print(f"{changed} archivo(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))
