"""Igualar tamaños de texto con arena-crm (DESIGN_SYSTEM.md del CRM: `text-base` es el tamaño
estándar de todo el texto de UI). Las plantillas legadas se escribieron con la escala de Tailwind
por defecto (`text-sm` = 14 px, `text-xs` = 12 px); con la escala del CRM quedaban en 11/10 px.

Reemplaza `text-xs`/`text-sm` (con o sin variante `sm:`, `md:`, `dark:`...) por `text-base` en
templates/ (salvo components/, que es copia literal del CRM), en el HTML generado desde Python y
en la capa `ui-*` de static/src/input.css. Idempotente.

Uso: python scripts/normalize_text_size.py [--dry-run]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RX = re.compile(r"(?<![\w-])((?:[a-z0-9-]+:)*)text-(?:xs|sm)(?![\w-])")
UI_LAYER = "PROPIO DE ARENA-TALENTO"


def targets():
    for p in (ROOT / "templates").rglob("*.html"):
        if "components" not in p.relative_to(ROOT / "templates").parts:
            yield p
    for p in (ROOT / "apps").rglob("*.py"):
        if "tests" not in p.parts and "migrations" not in p.parts:
            yield p
    yield ROOT / "static" / "src" / "input.css"


def convert(path, text):
    if path.suffix == ".css":  # solo la capa propia; la escala --text-* del CRM no se toca
        head, sep, tail = text.partition(UI_LAYER)
        return head + sep + RX.sub(r"\1text-base", tail) if sep else text
    return RX.sub(r"\1text-base", text)


def main():
    dry = "--dry-run" in sys.argv
    total = 0
    for p in targets():
        text = p.read_bytes().decode("utf-8")  # sin traducir CRLF
        new = convert(p, text)
        if new != text:
            n = len(RX.findall(text)) if p.suffix != ".css" else len(RX.findall(text.partition(UI_LAYER)[2]))
            total += n
            print(f"{n:4d}  {p.relative_to(ROOT)}")
            if not dry:
                p.write_bytes(new.encode("utf-8"))
    print(f"Total: {total} reemplazos{' (dry-run)' if dry else ''}")


if __name__ == "__main__":
    main()
