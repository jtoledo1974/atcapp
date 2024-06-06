"""Funciones para manejar nombres."""

from __future__ import annotations

import unicodedata
from logging import getLogger

logger = getLogger(__name__)

PREPOSITIONS = {"DE", "DEL", "DE LA", "DE LOS", "DE LAS", "DA", "DAS", "DO", "DOS"}


def parse_name(name: str) -> tuple[str, str]:
    """Parse the name into first and last name.

    El archivo tiene los dos apellidos primero y luego el nombre, pero
    no identifica las partes. Tanto los apellidos como el nombre pueden
    ser compuestos.

    El algoritmo a seguir será identificar dos apellidos, lo que reste
    será el nombre.

    Entendemos como un apellido bien una única palabra, o bien:
      - DE APELLIDO
      - DEL APELLIDO
      - DE LA APELLIDO
      - DE LOS APELLIDOS
      - DE LAS APELLIDOS

    Ejemplos:
    CASTILLO PINTO JAIME -> Nombre: JAIME, Apellidos: CASTILLO PINTO
    MARTINEZ MORALES MARIA VIRGINIA: Nombre: MARIA VIRGINIA, Apellidos: MARTINEZ MORALES
    DE ANDRES RICO MARIO -> Nombre: MARIO, Apellidos: DE ANDRES RICO
    """
    parts = name.split()
    apellidos_parts: list[str] = []
    i = 0

    # Identify the last names
    while i < len(parts) and len(apellidos_parts) < 2:  # noqa: PLR2004 Dos apellidos
        if parts[i].upper() in PREPOSITIONS:
            # Handle multi-word prepositions (e.g., "DE LA", "DE LOS")
            if i + 1 < len(parts):
                if parts[i].upper() in {"DE", "DEL"}:
                    if i + 2 < len(parts) and parts[i + 1].upper() in {
                        "LA",
                        "LOS",
                        "LAS",
                    }:
                        apellidos_parts.append(" ".join(parts[i : i + 3]))
                        i += 3
                    else:
                        apellidos_parts.append(" ".join(parts[i : i + 2]))
                        i += 2
                else:
                    apellidos_parts.append(" ".join(parts[i : i + 2]))
                    i += 2
            else:
                break
        else:
            apellidos_parts.append(parts[i])
            i += 1

    # The rest is the first name
    nombre_parts = parts[i:]

    apellidos = " ".join(apellidos_parts)
    nombre = " ".join(nombre_parts)

    return nombre, apellidos


def capitaliza_nombre(nombre: str, apellidos: str) -> str:
    """Capitaliza el nombre, manteniendo las preposiciones como minúsculas."""
    nombre_parts = nombre.split()
    apellidos_parts = apellidos.split()

    for i, part in enumerate(nombre_parts):
        if part.upper() not in PREPOSITIONS:
            nombre_parts[i] = part.capitalize()
        else:
            nombre_parts[i] = part.lower()

    for i, part in enumerate(apellidos_parts):
        if part.upper() not in PREPOSITIONS:
            apellidos_parts[i] = part.capitalize()
        else:
            apellidos_parts[i] = part.lower()

    n = " ".join(nombre_parts)
    a = " ".join(apellidos_parts)
    return f"{n} {a}"


def normalize_string(s: str) -> str:
    """Normalize string by removing accents and converting to lowercase."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).lower()
