"""Utility functions for the application."""

from __future__ import annotations

import unicodedata
from logging import getLogger
from typing import TYPE_CHECKING

from .models import ATC

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import scoped_session

logger = getLogger(__name__)


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
    apellidos_parts: list[str] = []
    i = 0

    # Identify the last names
    while i < len(parts) and len(apellidos_parts) < 2:  # noqa: PLR2004 Dos apellidos
        if parts[i].upper() in prepositions:
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


def normalize_string(s: str) -> str:
    """Normalize string by removing accents and converting to lowercase."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).lower()


def create_user(
    name: str | tuple[str, str],
    role: str,
    equipo: str | None,
    db_session: scoped_session,
    email: str | None = None,
) -> ATC:
    """Create a new user in the database.

    Args:
    ----
        name: The full name as a single string or a tuple of (nombre, apellidos).
              If a full name is provided it should be in the format "apellidos nombre".
        role: The role of the user. (CON, PDT, etc.)
        equipo: The equipo of the user (A, B, C, ...).
        db_session (scoped_session): The database session.
        email: The email of the user. If not provided, a fake email will be generated.

    Returns:
    -------
        User: The created user.

    """
    if isinstance(name, str):
        nombre, apellidos = parse_name(name)
    elif isinstance(name, tuple) and len(name) == 2:  # noqa: PLR2004
        nombre, apellidos = name
    else:
        _msg = "name either full name string or tuple of (nombre, apellidos)"
        raise ValueError(_msg)

    if not email:
        email = f"fixme{nombre.strip()}{apellidos.strip()}fixme@example.com"

    # Check first whether the user already exists
    existing_user = find_user(f"{apellidos} {nombre}", db_session)
    if existing_user:
        logger.warning(
            "Controlador existente: %s. No creamos uno nuevo con el mismo nombre.",
            existing_user,
        )
        return existing_user

    new_user = ATC(
        nombre=nombre,
        apellidos=apellidos,
        email=email,
        categoria=role,
        equipo=equipo.upper() if equipo else None,
        numero_de_licencia="",
    )
    db_session.add(new_user)
    return new_user


def update_user(user: ATC, role: str, equipo: str | None) -> ATC:
    """Update the user's equipo and role if they differ from the provided values."""
    if role and user.categoria != role:
        user.categoria = role
    if equipo and user.equipo != equipo.upper():
        user.equipo = equipo.upper()
    return user


def find_user(
    name: str,
    db_session: scoped_session,
) -> ATC | None:
    """Find a user in the database by name.

    The name is expected to be in the format "apellidos nombre".
    """
    nombre, apellidos = parse_name(name)
    normalized_nombre = normalize_string(nombre)
    normalized_apellidos = normalize_string(apellidos)
    normalized_full_name = normalize_string(f"{apellidos} {nombre}")

    # Fetch all users and normalize names for comparison
    users = db_session.query(ATC).all()

    for user in users:
        if (
            normalize_string(user.nombre) == normalized_nombre
            and normalize_string(user.apellidos) == normalized_apellidos
        ) or (
            normalize_string(f"{user.apellidos} {user.nombre}") == normalized_full_name
        ):
            return user

    return None
