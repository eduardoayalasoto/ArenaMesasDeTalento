#!/usr/bin/env python3
"""Stop hook: verificaciones baratas antes de que el agente dé un turno por terminado.

MISMO archivo en arena-talento y arena-crm (detecta en cuál corre). Revisa solo lo que cambió
en el working tree (git status) y BLOQUEA una vez por turno si encuentra:
  1. Un componente compartido distinto entre ambos repos (_nav_menu.html, _breadcrumb.html).
  2. Plantillas/CSS fuente editados después del último build del CSS compilado.
  3. Un models.py modificado sin ningún archivo de migración nuevo/modificado.
No corre pruebas (lentas contra Neon): la suite completa la corre CI en cada push.
Configurado en .claude/settings.json → hooks.Stop.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
IS_TALENTO = (ROOT / "build_css.ps1").exists()
CSS = ROOT / ("static/css/app.css" if IS_TALENTO else "static/css/tailwind.css")
BUILD_CMD = r".\build_css.ps1" if IS_TALENTO else "bash scripts/build_css.sh"
CSS_SOURCES = ("templates/", "static/src/", "styles/", "apps/core/templatetags/")
SIBLING = ROOT.parent / ("arena-crm" if IS_TALENTO else "arena-talento")
SHARED = ("templates/components/_nav_menu.html", "templates/components/_breadcrumb.html")
HOME_URLS = ("{% url 'dashboards:home' %}", "{% url 'core:home' %}")


def changed_files():
    out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    files = []
    for line in out.splitlines():
        if line[:2].strip() == "D":
            continue
        path = line[3:].strip().strip('"')
        files.append(path.split(" -> ")[-1].replace("\\", "/"))
    return files


def norm(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    for url in HOME_URLS:
        text = text.replace(url, "HOME")
    return text


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    if payload.get("stop_hook_active"):
        return  # ya se bloqueó una vez en este turno: no entrar en ciclo

    issues = []
    files = changed_files()

    if SIBLING.exists():
        for rel in SHARED:
            mine, theirs = ROOT / rel, SIBLING / rel
            if mine.exists() and theirs.exists() and norm(mine) != norm(theirs):
                issues.append(f"{rel} difiere de {SIBLING.name}: aplica el mismo cambio en ambos repos "
                              "(DESIGN_SYSTEM.md; prueba test_shared_components).")

    css_mtime = CSS.stat().st_mtime if CSS.exists() else 0
    stale = [f for f in files if f.startswith(CSS_SOURCES) and (ROOT / f).exists()
             and (ROOT / f).stat().st_mtime > css_mtime + 1]
    if stale:
        issues.append(f"CSS compilado desactualizado ({len(stale)} archivo(s) de plantillas/estilos más "
                      f"nuevos, p. ej. {stale[0]}): corre `{BUILD_CMD}` y versiona {CSS.relative_to(ROOT)}.")

    models = [f for f in files if f.endswith("models.py")]
    migrations = [f for f in files if "/migrations/" in f]
    if models and not migrations:
        issues.append(f"Cambiaste {', '.join(models)} sin migración: corre `manage.py makemigrations` "
                      "(o confirma que el cambio no la requiere).")

    if issues:
        print(json.dumps({"decision": "block",
                          "reason": "Verificaciones de cierre (.claude/hooks/stop_checks.py):\n- " + "\n- ".join(issues)},
                         ensure_ascii=True))


if __name__ == "__main__":
    main()
