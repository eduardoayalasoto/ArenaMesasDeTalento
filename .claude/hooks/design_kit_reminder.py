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
    "Recordatorio DESIGN_SYSTEM (no bloqueante): estas por escribir/editar un "
    "archivo visual ({path}).\n"
    "1) Revisa DESIGN_SYSTEM.md (y docs/PLAN_MIGRACION_DISENO.md) antes de introducir layout, tarjetas o "
    "composicion nueva -- es ley para todo cambio visual.\n"
    "2) Busca primero en templates/components/ y en los patrones ya "
    "establecidos (p.ej. _daily_objective.html / _daily_deliverable_card.html "
    "para cards anidadas) antes de inventar un estilo nuevo; si ya existe un "
    "componente o patron equivalente, reusalo en vez de crear uno paralelo.\n"
    "3) Si esto toca navbar, fondo de pagina, cards o cualquier composicion "
    "de layout nueva, invoca los skills `ui-ux-pro-max` y `frontend-design` "
    "antes de finalizar -- no opcional."
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
            "permissionDecision": "allow",
            "permissionDecisionReason": "Recordatorio informativo, no bloquea la escritura.",
            "additionalContext": REMINDER.format(path=file_path),
        }
    }
    print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
