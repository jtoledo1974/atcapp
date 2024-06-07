"""Funciones para manejar nombres."""

from __future__ import annotations

import unicodedata
from logging import getLogger

logger = getLogger(__name__)

PREPOSITIONS = {
    "DE",
    "DEL",
    "DA",
    "DAS",
    "DO",
    "DOS",
}
ARTICLES = {
    "LA",
    "EL",
    "LOS",
    "LAS",
}

MIN_N_APELLIDOS = 2
MAX_N_NOMBRE = 2
"""Limitar a dos nombres para evitar problemas con nombres compuestos."""


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
    n_parts = len(parts)
    while i < n_parts and (
        len(apellidos_parts) < MIN_N_APELLIDOS or i < n_parts - MAX_N_NOMBRE
    ):  # Dos apellidos
        if parts[i].upper() in PREPOSITIONS.union(ARTICLES):
            # Handle multi-word prepositions (e.g., "DE LA", "DE LOS")
            if i + 1 < n_parts:
                if parts[i].upper() in PREPOSITIONS:
                    if i + 2 < n_parts and parts[i + 1].upper() in ARTICLES:
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

    # Join the components into full names
    apellidos = " ".join(apellidos_parts)
    nombre = " ".join(nombre_parts)

    return nombre, apellidos


def capitaliza_nombre(nombre: str, apellidos: str) -> tuple[str, str]:
    """Capitaliza el nombre, manteniendo las preposiciones como minúsculas."""
    nombre_parts = nombre.split()
    apellidos_parts = apellidos.split()

    for i, part in enumerate(nombre_parts):
        if part.upper() not in PREPOSITIONS:
            nombre_parts[i] = part.capitalize()
        else:
            nombre_parts[i] = part.lower()

    for i, part in enumerate(apellidos_parts):
        if part.upper() not in PREPOSITIONS.union(ARTICLES) or (
            part.upper() in ARTICLES
            and (
                i == 0 or (i > 0 and apellidos_parts[i - 1].upper() not in PREPOSITIONS)
            )
        ):
            apellidos_parts[i] = part.capitalize()
        else:
            apellidos_parts[i] = part.lower()

    n = " ".join(nombre_parts)
    a = " ".join(apellidos_parts)
    return n, a


def to_lower_no_accents(s: str) -> str:
    """Normalize string by removing accents and converting to lowercase."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).lower()


def to_no_accents(s: str) -> str:
    """Normalize string by removing accents."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )
