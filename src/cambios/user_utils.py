"""Utilities for working with users in the database."""

from __future__ import annotations

from logging import getLogger
from typing import TYPE_CHECKING

from .models import ATC
from .name_utils import parse_name

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import scoped_session

logger = getLogger(__name__)


def create_user(
    name: str,
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
    name = name.strip()
    if isinstance(name, str):
        nombre, apellidos = parse_name(name)
    elif isinstance(name, tuple) and len(name) == 2:  # noqa: PLR2004
        nombre, apellidos = name
    else:
        _msg = "name either full name string or tuple of (nombre, apellidos)"
        raise ValueError(_msg)

    if not email:
        # Substitute spaces for dots and remove accents
        email_name = (
            f"{name.replace(' ', '.').encode('ascii', 'ignore').decode('utf-8')}"
        )
        email = f"{email_name}@example.com"

    # Check first whether the user already exists
    existing_user = find_user(f"{apellidos} {nombre}", db_session)
    if existing_user:
        logger.warning(
            "Controlador existente: %s. No creamos uno nuevo con el mismo nombre.",
            existing_user,
        )
        return existing_user

    new_user = ATC(
        apellidos_nombre=name,
        nombre=nombre,
        apellidos=apellidos,
        email=email,
        categoria=role,
        equipo=equipo.upper() if equipo else None,
        numero_de_licencia="",
    )
    logger.debug("Creando nuevo controlador: %s", new_user)
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
    # Find the user in the database by name
    user = db_session.query(ATC).filter(ATC.apellidos_nombre == name).first()
    users = db_session.query(ATC).all()

    for user in users:
        if user.apellidos_nombre == name:
            return user

    return None
