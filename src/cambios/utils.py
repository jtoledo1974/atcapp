"""Utility functions for the application."""

from __future__ import annotations

import unicodedata
from typing import TYPE_CHECKING

from .models import User

if TYPE_CHECKING:
    from sqlalchemy.orm import scoped_session


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


def create_user(
    name: str | tuple[str, str],
    role: str,
    team: str | None,
    db_session: scoped_session,
    email: str | None = None,
) -> User:
    """Create a new user in the database.

    Args:
    ----
        name: The full name as a single string or a tuple of (first_name, last_name).
        role: The role of the user. (CON, PDT, etc.)
        team: The team of the user (A, B, C, ...).
        db_session (scoped_session): The database session.
        email: The email of the user. If not provided, a fake email will be generated.

    Returns:
    -------
        User: The created user.

    """
    if isinstance(name, str):
        first_name, last_name = parse_name(name)
    elif isinstance(name, tuple) and len(name) == 2:  # noqa: PLR2004
        first_name, last_name = name
    else:
        _msg = "name either full name string or tuple of (first_name, last_name)"
        raise ValueError(_msg)

    if not email:
        email = f"fixme{first_name.strip()}{last_name.strip()}fixme@example.com"

    new_user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        category=role,
        team=team.upper() if team else None,
        license_number="",
    )
    db_session.add(new_user)
    return new_user


def update_user(user: User, role: str, team: str | None) -> User:
    """Update the user's team and role if they differ from the provided values."""
    if user.category != role:
        user.category = role
    if team and user.team != team.upper():
        user.team = team.upper()
    return user


def find_user(
    name: str,
    db_session: scoped_session,
) -> User | None:
    """Find a user in the database by name.

    The name is expected to be in the format "LAST_NAME FIRST_NAME".
    """
    first_name, last_name = parse_name(name)
    normalized_first_name = normalize_string(first_name)
    normalized_last_name = normalize_string(last_name)
    normalized_full_name = normalize_string(f"{last_name} {first_name}")

    # Fetch all users and normalize names for comparison
    users = db_session.query(User).all()

    for user in users:
        if (
            normalize_string(user.first_name) == normalized_first_name
            and normalize_string(user.last_name) == normalized_last_name
        ) or (
            normalize_string(f"{user.last_name} {user.first_name}")
            == normalized_full_name
        ):
            return user

    return None
