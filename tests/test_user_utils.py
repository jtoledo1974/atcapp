"""Verifica la funcionalidad del módulo user_utils.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

from cambios.user_utils import create_user, find_user

if TYPE_CHECKING:
    from sqlalchemy.orm import scoped_session


def test_duplicados_con_caracteres_mal_codificados(
    preloaded_session: scoped_session,
) -> None:
    """Comprobar que no se producen duplicados usando nombres con eñes."""
    # Log in as admin user
    create_user("PEPA NUÃ‘EZ", "CON", "A", preloaded_session)  # noqa: RUF001
    user = find_user("PEPA NUÃ‘EZ", preloaded_session)  # noqa: RUF001
    assert user is not None

    user2 = create_user("PEPA NUÑEZ", "CON", "A", preloaded_session)
    assert user is not None
    assert user == user2
