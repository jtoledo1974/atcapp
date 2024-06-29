"""Verifica la funcionalidad del módulo user_utils.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from atcapp.user_utils import AtcTexto, create_user, find_user

if TYPE_CHECKING:
    from sqlalchemy.orm import scoped_session


def test_duplicados_con_caracteres_mal_codificados(
    preloaded_session: scoped_session,
) -> None:
    """Comprobar que no se producen duplicados usando nombres con eñes."""
    # Log in as admin user
    atc_texto = AtcTexto(
        apellidos_nombre="PEPA NUÑEZ",
        dependencia="LECS",
        categoria="PTD",
        equipo=None,
        email=None,
    )
    create_user(atc_texto, preloaded_session)
    user = find_user("PEPA NUÃ‘EZ", preloaded_session)  # noqa: RUF001
    assert user is not None

    atc_texto.categoria = "PTD"
    atc_texto.equipo = "A"
    user2 = create_user(atc_texto, preloaded_session)
    assert user is not None
    assert user == user2


def test_no_duplicates(session: scoped_session) -> None:
    """Comprobar que no se producen duplicados."""
    atc_texto = AtcTexto(
        apellidos_nombre="PEPA NUÑEZ",
        dependencia="LECS",
        categoria="PTD",
        equipo="A",
        email=None,
    )
    user = create_user(atc_texto, session)
    user2 = create_user(atc_texto, session)
    assert user == user2


def test_no_carriage_return(session: scoped_session) -> None:
    """Comprobar que no se producen duplicados."""
    atc_texto = AtcTexto(
        apellidos_nombre="PEPA NUÑEZ",
        dependencia="LECS",
        categoria="PTD",
        equipo="A",
        email=None,
    )
    user = create_user(atc_texto, session)
    atc_texto.apellidos_nombre = "PEPA \nNUÑEZ"
    user2 = create_user(atc_texto, session)
    assert user == user2
