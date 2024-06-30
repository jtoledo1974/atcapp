"""Utilities for working with users in the database."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from logging import getLogger
from typing import TYPE_CHECKING

from .models import ATC
from .name_utils import (
    capitaliza_nombre,
    fix_encoding,
    no_extraneous_spaces,
    parse_name,
)

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import scoped_session

logger = getLogger(__name__)


class UpdateResult(Enum):
    """The result of updating a user."""

    NO_CHANGE = auto()
    UPDATED = auto()


@dataclass
class AtcTexto:
    """Datos en texto de un controlador.

    Para ser utilizada con funciones del módulo user_utils.
    """

    apellidos_nombre: str
    dependencia: str
    """LECS, LECM, etc."""
    categoria: str
    """CON, PTD, IS, TIN, etc."""
    equipo: str | None = None
    "A a H, o None."
    email: str | None = None


def create_user(
    atc_texto: AtcTexto,
    db_session: scoped_session,
) -> ATC:
    """Create a new user in the database.

    Args:
    ----
        atc_texto (AtcTexto): The user's data in text form.
        db_session (scoped_session): The database session.

    Returns:
    -------
        User: The created user.

    """
    apellidos_nombre = no_extraneous_spaces(atc_texto.apellidos_nombre)
    apellidos_nombre = fix_encoding(apellidos_nombre)
    dependencia = no_extraneous_spaces(atc_texto.dependencia)
    role = no_extraneous_spaces(atc_texto.categoria)
    equipo = no_extraneous_spaces(atc_texto.equipo) if atc_texto.equipo else None

    nombre, apellidos = parse_name(apellidos_nombre)
    nombre, apellidos = capitaliza_nombre(nombre, apellidos)

    email = atc_texto.email
    if not email:
        # Substitute spaces for dots and remove accents
        email_name = (
            apellidos_nombre.replace(" ", ".")
            .encode("ascii", "ignore")
            .decode("utf-8")
            .lower()
        )
        email = f"{email_name}@example.com"

    # Check first whether the user already exists
    existing_user = find_user(apellidos_nombre, db_session)
    if existing_user:
        logger.warning(
            "Controlador existente: %s. No creamos uno nuevo con el mismo nombre.",
            existing_user,
        )
        return existing_user

    new_user = ATC(
        apellidos_nombre=apellidos_nombre,
        nombre=nombre,
        apellidos=apellidos,
        dependencia=dependencia.upper(),
        email=email,
        categoria=role,
        equipo=equipo.upper() if equipo else None,
    )
    logger.debug("Creando nuevo controlador: %s", new_user)
    db_session.add(new_user)
    return new_user


def update_user(user: ATC, role: str, equipo: str | None) -> UpdateResult:
    """Update the user's equipo and role if they differ from the provided values."""
    res = UpdateResult.NO_CHANGE
    if role and user.categoria != role:
        user.categoria = role
        res = UpdateResult.UPDATED
    if equipo and user.equipo != equipo.upper():
        user.equipo = equipo.upper()
        res = UpdateResult.UPDATED
    return res


def find_user(
    apellidos_nombre: str,
    db_session: scoped_session,
) -> ATC | None:
    """Find a user in the database by name.

    The name is expected to be in the format "apellidos nombre".
    """
    # Find the user in the database by name
    query = db_session.query(ATC).filter(
        ATC.apellidos_nombre == fix_encoding(apellidos_nombre),
    )
    if query.count() > 0:
        return query.first()
    return None
