"""Tests for the commands module."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator
from unittest import mock

import pytest
from atcapp.commands import (
    ATTR_APELLIDOS,
    ATTR_APELLIDOS_NOMBRE,
    ATTR_EMAIL,
    ATTR_ES_ADMIN,
    ATTR_NOMBRE,
    ATTR_POLITICA_ACEPTADA,
    export_atcs,
    get_session,
    import_atcs,
    set_verbose_level,
)
from atcapp.models import ATC
from click.testing import CliRunner
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture()
def session_mock() -> Generator[Session, Any, Any]:
    """src/atcapp/test_commands.py: Fixture for a SQLAlchemy session mock."""
    with mock.patch("sqlalchemy.create_engine"), mock.patch(
        "sqlalchemy.orm.sessionmaker",
    ) as sessionmaker_mock:
        session_mock = mock.Mock()
        sessionmaker_mock.return_value = session_mock
        yield session_mock


ATCS: list[dict[str, str | bool]] = [
    {
        ATTR_APELLIDOS_NOMBRE: "John Doe",
        ATTR_NOMBRE: "John",
        ATTR_APELLIDOS: "Doe",
        ATTR_EMAIL: "john.doe@example.com",
        ATTR_ES_ADMIN: True,
        ATTR_POLITICA_ACEPTADA: True,
    },
    {
        ATTR_APELLIDOS_NOMBRE: "Jane Smith",
        ATTR_NOMBRE: "Jane",
        ATTR_APELLIDOS: "Smith",
        ATTR_EMAIL: "jane.smith@example.com",
        ATTR_ES_ADMIN: False,
        ATTR_POLITICA_ACEPTADA: True,
    },
]


@pytest.fixture()
def atcs() -> list[dict[str, str | bool]]:
    """Fixture for a list of ATC dictionaries."""
    return ATCS.copy()


def test_get_session() -> None:
    """Test getting a SQLAlchemy session."""
    db_uri = "sqlite:///test.db"
    session = get_session(db_uri)
    assert isinstance(session, Session)


def test_set_verbose_level() -> None:
    """Test setting the logger verbosity level."""
    logger_mock = mock.Mock()
    with mock.patch("atcapp.commands.logger", logger_mock):
        set_verbose_level(0)
        logger_mock.setLevel.assert_called_once_with(logging.INFO)

        logger_mock.reset_mock()
        set_verbose_level(1)
        logger_mock.setLevel.assert_called_once_with(logging.DEBUG)

        logger_mock.reset_mock()
        set_verbose_level(2)
        logger_mock.setLevel.assert_called_once_with(logging.DEBUG)

        logger_mock.reset_mock()
        set_verbose_level(3)
        logger_mock.setLevel.assert_called_once_with(logging.DEBUG)


def test_export_atcs(
    session_mock: Session,
    atcs: list[dict[str, str | bool]],
    tmp_path: Path,
) -> None:
    """Test exporting ATCs to a JSON file."""
    output_file = tmp_path / "output.json"
    session_mock.query.return_value.filter.return_value.all.return_value = [  # type: ignore[attr-defined]
        ATC(**atc) for atc in atcs
    ]

    runner = CliRunner()
    with mock.patch("atcapp.commands.get_session", return_value=session_mock):
        runner.invoke(export_atcs, ["-v", str(output_file), "sqlite:///test.db"])
    assert output_file.exists()

    with output_file.open("r") as f:
        exported_atcs = json.load(f)

    assert exported_atcs == atcs


def mock_filter_by(*args, **kwargs) -> mock.Mock:  # noqa:ANN002, ANN003
    """Return an ATC object based on the filter_by parameters.

    Para probar las funcionalidaddes de añadir y editar
    retiramos el primer ATC, y al resto le ponemos otro email.
    """
    apellidos_nombre = kwargs.get("apellidos_nombre")
    for atc in ATCS[1:]:
        if atc[ATTR_APELLIDOS_NOMBRE] == apellidos_nombre:
            atc[ATTR_EMAIL] = "modified_by_mock_filter@example.com"
            return mock.Mock(first=mock.Mock(return_value=ATC(**atc)))
    return mock.Mock(first=mock.Mock(return_value=None))


def test_import_atcs(
    session_mock: mock.Mock,
    atcs: list[dict[str, str | bool]],
    tmp_path: Path,
) -> None:
    """Test importing ATCs from a JSON file."""
    input_file = tmp_path / "input.json"
    input_file.write_text(json.dumps(atcs))

    session_mock.query.return_value.filter_by.side_effect = mock_filter_by

    runner = CliRunner()
    with mock.patch("atcapp.commands.get_session", return_value=session_mock):
        runner.invoke(import_atcs, [str(input_file), "sqlite:///test.db"])

    assert session_mock.query.return_value.filter_by.call_count == len(atcs)
    assert session_mock.add.call_count == 1
    assert session_mock.commit.call_count == 1
