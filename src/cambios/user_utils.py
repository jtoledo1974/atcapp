"""Utilities for working with users in the database."""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from .models import ATC
from .name_utils import parse_name, to_lower_no_accents

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import scoped_session

logger = getLogger(__name__)


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
    normalized_nombre = to_lower_no_accents(nombre)
    normalized_apellidos = to_lower_no_accents(apellidos)
    normalized_full_name = to_lower_no_accents(f"{apellidos} {nombre}")

    # Fetch all users and normalize names for comparison
    users = db_session.query(ATC).all()

    for user in users:
        if (
            to_lower_no_accents(user.nombre) == normalized_nombre
            and to_lower_no_accents(user.apellidos) == normalized_apellidos
        ) or (
            to_lower_no_accents(f"{user.apellidos} {user.nombre}")
            == normalized_full_name
        ):
            return user

    return None
