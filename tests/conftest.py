"""Configuration for pytest."""

from __future__ import annotations

import locale
import os
from pathlib import Path
from typing import TYPE_CHECKING, Generator
from unittest.mock import MagicMock, patch

import pdfplumber
import pytest
from cambios.app import create_app
from cambios.database import db as _db
from cambios.models import ATC, Estadillo
from sqlalchemy.orm import scoped_session, sessionmaker

from .pickled_db import (
    __TEST_ESTADILLO_PATH,
    __TEST_TURNERO_PATH,
    create_in_memory_db,
    create_test_data,
    load_fixture,
    save_fixture,
    should_regenerate_pickle,
)

if TYPE_CHECKING:
    from typing import Any, Generator

    from cambios.database import DB
    from flask import Flask
    from flask.testing import FlaskClient
    from pdfplumber import PDF
    from pytest_mock import MockerFixture
    from sqlalchemy.orm import Session


PICKLE_FILE = Path(__file__).parent / "resources" / "test_db.pickle"


@pytest.fixture(scope="session", autouse=True)
def _set_env() -> None:
    """Set up logging using the environment variable."""
    os.environ["ENABLE_LOGGING"] = "true"
    os.environ["LOG_LEVEL"] = "INFO"

    locale.setlocale(locale.LC_ALL, "es_ES.UTF-8")
    os.environ["FLASK_SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    # Usar  "sqlite:///testing.db" para ver la base de datos de prueba


@pytest.fixture(scope="session")
def app() -> Flask:
    """Create and configure a new app instance."""
    app = create_app()
    app.config.update({"TESTING": True})
    return app


@pytest.fixture(scope="session")
def preloaded_app(
    app: Flask,
    preloaded_session: Session,
) -> Generator[Flask, None, None]:
    """Create and configure a new app instance with preloaded data."""
    with app.app_context():
        saved_session = _db.session
        _db.session = scoped_session(lambda: preloaded_session)  # type: ignore[arg-type]
        yield app
        _db.session.remove()
        _db.drop_all()
        _db.session.remove()
        _db.session = saved_session


@pytest.fixture(scope="session")
def db(preloaded_app: Flask) -> Generator[DB, None, None]:
    """Provide a database session for tests."""
    with preloaded_app.app_context():
        yield _db


@pytest.fixture()
def session(db: DB) -> Generator[scoped_session, None, None]:
    """Create a new database session for a test."""
    if not db.engine:
        pytest.fail("No database engine.")
    connection = db.engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)
    saved_session = db.session
    db.session = session  # type: ignore[assignment]

    yield session

    session.remove()
    transaction.rollback()
    db.session = saved_session


@pytest.fixture(scope="session")
def pdf_estadillo() -> Generator[PDF, Any, Any]:
    """Precarga el pdf de estadillo para pruebas.

    Se precargan las tablas de las páginas para evitar volver a procesar el
    pdf en cada test.
    """
    test_file_path = __TEST_ESTADILLO_PATH
    with pdfplumber.open(test_file_path) as pdf:
        # precarga las páginas del pdf
        table = pdf.pages[0].extract_table()
        pdf.pages[0].extract_table = MagicMock(return_value=table)  # type: ignore[method-assign]
        tables = pdf.pages[1].extract_tables()
        pdf.pages[1].extract_tables = MagicMock(return_value=tables)  # type: ignore[method-assign]
        yield pdf


@pytest.fixture()
def estadillo_path(pdf_estadillo: pdfplumber.pdf.PDF) -> Generator[Path, Any, Any]:
    """Return the path to the test PDF file.

    Hacemos un mock de pdfplumber.open para que su uso con un context manager
    devuelva el pdf precargado.
    """
    with patch("pdfplumber.open") as pdf_open_mock:
        mock = MagicMock()
        mock.__enter__.return_value = pdf_estadillo
        pdf_open_mock.return_value = mock

        yield __TEST_ESTADILLO_PATH


@pytest.fixture()
def estadillo(preloaded_session: Session) -> Estadillo:
    """Return an estadillo from a preloaded database."""
    # Get the first user from the Users table
    estadillo = preloaded_session.query(Estadillo).first()
    if not estadillo:
        _msg = "No estadillos in the database."
        raise ValueError(_msg)
    return estadillo


@pytest.fixture(scope="session")
def pdf_turnero() -> Generator[PDF, Any, Any]:
    """Precarga el pdf de turnero para pruebas.

    Se precargan las tablas de las páginas para evitar volver a procesar el
    pdf en cada test.
    """
    test_file_path = __TEST_TURNERO_PATH
    with pdfplumber.open(test_file_path) as pdf:
        table = pdf.pages[0].extract_table()
        pdf.pages[0].extract_table = MagicMock(return_value=table)  # type: ignore[method-assign]
        yield pdf


@pytest.fixture()
def turnero_path(pdf_turnero: pdfplumber.pdf.PDF) -> Generator[Path, Any, Any]:
    """Return the path to the test PDF file.

    Hacemos un mock de pdfplumber.open para que su uso con un context manager
    devuelva el pdf precargado.
    """
    with patch("pdfplumber.open") as pdf_open_mock:
        mock = MagicMock()
        mock.__enter__.return_value = pdf_turnero
        pdf_open_mock.return_value = mock

        yield __TEST_TURNERO_PATH


@pytest.fixture()
def client(preloaded_app: Flask, session: scoped_session) -> FlaskClient:
    """Create a test client for the app with preloaded data."""
    return preloaded_app.test_client()


@pytest.fixture()
def _init_firebase_mock(mocker: MockerFixture) -> None:
    """Mock the init_firebase function."""
    mocker.patch("src.cambios.firebase.init_firebase", return_value=None)


@pytest.fixture()
def _verify_id_token_mock(mocker: MockerFixture) -> None:
    """Mock the verify_id_token function from firebase."""
    mocker.patch(
        "src.cambios.firebase.auth.verify_id_token",
        return_value={"uid": "user_uid", "email": "user@example.com"},
    )


@pytest.fixture()
def _verify_admin_id_token_mock(mocker: MockerFixture) -> None:
    """Mock the verify_id_token function from firebase."""
    mocker.patch(
        "src.cambios.firebase.auth.verify_id_token",
        return_value={"uid": "admin_uid", "email": "admin@example.com"},
    )


@pytest.fixture()
def regular_user(session: scoped_session) -> ATC:
    """Create a regular user for testing."""
    user = ATC(
        apellidos_nombre="User Regular",
        email="user@example.com",
        nombre="Regular",
        apellidos="User",
        categoria="User",
        equipo=None,
        numero_de_licencia="654321",
        es_admin=False,
        politica_aceptada=True,
    )
    session.add(user)
    session.commit()
    return user


@pytest.fixture()
def admin_user(regular_user: ATC, session: scoped_session) -> ATC:
    """Create an admin user for testing."""
    session.delete(regular_user)
    admin = regular_user
    admin.email = "admin@example.com"
    admin.es_admin = True
    session.add(admin)
    session.commit()
    return admin


@pytest.fixture()
def new_user(regular_user: ATC, session: scoped_session) -> ATC:
    """Create a new regular user for testing."""
    session.delete(regular_user)
    regular_user.politica_aceptada = False
    session.add(regular_user)
    session.commit()
    return regular_user


@pytest.fixture(scope="session")
def preloaded_session() -> Generator[Session, None, None]:
    """Load the database with test data."""
    if should_regenerate_pickle():
        session = create_in_memory_db()
        create_test_data(session)
        save_fixture(session)
    else:
        session = load_fixture()

    yield session
    session.close()


@pytest.fixture()
def preloaded_client(
    preloaded_app: Flask,
    preloaded_session: scoped_session,
) -> FlaskClient:
    """Create a test client for the app with preloaded data."""
    return preloaded_app.test_client()


@pytest.fixture()
def atc(preloaded_session: Session, mocker: MockerFixture) -> ATC:
    """Return an ATC from a preloaded database and mock verify_id_token."""
    user = preloaded_session.query(ATC).first()
    if not user:
        msg = "No users in the database."
        raise ValueError(msg)

    mocker.patch(
        "cambios.firebase.auth.verify_id_token",
        return_value={"uid": "admin_uid", "email": user.email},
    )
    user.politica_aceptada = True
    preloaded_session.commit()

    return user
