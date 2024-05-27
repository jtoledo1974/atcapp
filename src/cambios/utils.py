"""Utility functions for the application."""

import unicodedata


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
    prepositions = {"DE", "DEL", "DE LA", "DE LOS", "DE LAS"}
    last_name_parts: list[str] = []
    i = 0

    # Identify the last names
    while i < len(parts) and len(last_name_parts) < 2:  # noqa: PLR2004 Dos apellidos
        if parts[i].upper() in prepositions:
            # Handle multi-word prepositions (e.g., "DE LA", "DE LOS")
            if i + 1 < len(parts):
                if parts[i].upper() in {"DE", "DEL"}:
                    if i + 2 < len(parts) and parts[i + 1].upper() in {
                        "LA",
                        "LOS",
                        "LAS",
                    }:
                        last_name_parts.append(" ".join(parts[i : i + 3]))
                        i += 3
                    else:
                        last_name_parts.append(" ".join(parts[i : i + 2]))
                        i += 2
                else:
                    last_name_parts.append(" ".join(parts[i : i + 2]))
                    i += 2
            else:
                break
        else:
            last_name_parts.append(parts[i])
            i += 1

    # The rest is the first name
    first_name_parts = parts[i:]

    last_name = " ".join(last_name_parts)
    first_name = " ".join(first_name_parts)

    return first_name, last_name


def normalize_string(s: str) -> str:
    """Normalize string by removing accents and converting to lowercase."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).lower()
