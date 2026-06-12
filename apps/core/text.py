"""Utilidades de texto en español."""

import unicodedata

# Partículas que van en minúscula dentro de un nombre propio.
_LOWER_PARTICLES = {"de", "del", "la", "las", "los", "y", "e"}


def titlecase_name(raw: str) -> str:
    """Convierte 'EDUARDO DE LA CRUZ' → 'Eduardo de la Cruz'."""
    words = raw.strip().split()
    out: list[str] = []
    for i, word in enumerate(words):
        lower = word.lower()
        if i != 0 and lower in _LOWER_PARTICLES:
            out.append(lower)
        else:
            out.append(lower.capitalize())
    return " ".join(out)


def normalize_name(raw) -> str:
    """Minúsculas, sin acentos y espacios colapsados, para emparejar nombres."""
    if not raw:
        return ""
    s = unicodedata.normalize("NFKD", str(raw))
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().split())
