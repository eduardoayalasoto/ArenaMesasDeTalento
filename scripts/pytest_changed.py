"""Pruebas locales rápidas: solo los archivos de prueba del cambio + las guardas del sistema.

Uso:  .\.venv\Scripts\python.exe scripts/pytest_changed.py [archivos de prueba extra...]

Local corre contra el Postgres de pruebas en Neon (lento, --reuse-db, nunca en paralelo): aquí se
eligen solo los test_*.py modificados en git (más los que se pasen como argumento) y las guardas
que deben quedar siempre en verde. La suite completa la corre CI en cada push
(.github/workflows/tests.yml). Objetivo: corrida ≤ 3 min.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUARDS = [
    "apps/core/tests/test_access_coverage.py",   # toda ruta con permiso registrado (spec 005)
    "apps/core/tests/test_navigation.py",        # menú y breadcrumb
    "apps/core/tests/test_shared_components.py", # paridad con arena-crm
]

status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT,
                        capture_output=True, text=True, encoding="utf-8").stdout
changed = [l[3:].strip().strip('"').split(" -> ")[-1] for l in status.splitlines() if l[:2].strip() != "D"]
tests = [f for f in changed if Path(f).name.startswith("test_") and f.endswith(".py")]
targets = list(dict.fromkeys(tests + sys.argv[1:] + GUARDS))
print("Pruebas:", *targets, sep="\n  ")
sys.exit(subprocess.call([sys.executable, "-m", "pytest", "--reuse-db", "-p", "no:warnings", *targets], cwd=ROOT))
