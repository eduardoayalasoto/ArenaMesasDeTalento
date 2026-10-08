#!/usr/bin/env python3
"""PreToolUse hook (Write|Edit): recordatorio no-bloqueante de DESIGN_SYSTEM.md (y docs/PLAN_MIGRACION_DISENO.md).

Se dispara cuando Claude escribe/edita un archivo bajo `templates/` o
`static/css/` (cualquier vista nueva o layout visual). Inyecta contexto
adicional al modelo -- nunca bloquea la operacion ni pide confirmacion.

Ver CLAUDE.md ("Skills obligatorios para todo cambio visual") y
DESIGN_SYSTEM.md (y docs/PLAN_MIGRACION_DISENO.md). Configurado en .claude/settings.json bajo hooks.PreToolUse.
"""
import json
import sys

REMINDER = (
    "Recordatorio DESIGN_SYSTEM (no bloqueante): estas por escribir/editar un archivo visual ({path}).\n"
    "1) DESIGN_SYSTEM.md es ley (daisyUI 5 + tema arena, tokens semanticos, marca arenatalento); plan y fase vigente en docs/PLAN_MIGRACION_DISENO.md.\n"
    "2) Busca primero en templates/components/ antes de inventar markup; nada de clases legadas ui-* ni de la escala arena-* en codigo nuevo.\n"
    "3) Menu = apps/core/navigation.py (nunca condiciones de menu en plantillas); permisos con request.user|can:'clave' (spec 005).\n"
    "4) Iconos solo con window.renderIcons(); sin style= inline, emojis ni confirm()/alert().\n"
    "5) Si tocas navbar, layout o cards, invoca los skills daisyui y frontend-design; corre build_css.ps1 tras cambiar clases."
)

# Rutas (relativas a la raiz del repo) que disparan el recordatorio.
WATCHED_PREFIXES = ("templates/", "static/css/")


def should_remind(file_path: str) -> bool:
    if not file_path:
        return False
    normalized = file_path.replace("\\", "/")
    # Busca el prefijo en cualquier punto de la ruta (funciona con rutas
    # absolutas de Windows y con rutas relativas al repo).
    return any(prefix in normalized for prefix in WATCHED_PREFIXES) and normalized.endswith(
        (".html", ".css")
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path", "")

    if not should_remind(file_path):
        return 0

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": REMINDER.format(path=file_path),
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
