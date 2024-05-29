"""Configuration for pytest."""

from __future__ import annotations

import locale
import logging
import os
import pickle
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Generator

import pytest
from cambios.app import Config, configure_logging, create_app
from cambios.database import db as _db
from cambios.models import ATC, TipoTurno, Turno
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

if TYPE_CHECKING:
    from flask import Flask
    from flask.testing import FlaskClient
    from flask_sqlalchemy import SQLAlchemy
    from pytest_mock import MockerFixture
    from sqlalchemy.orm import Session

PICKLE_FILE = Path(__file__).parent / "resources" / "test_db.pickle"


@pytest.fixture(scope="session", autouse=True)
def _set_env() -> None:
    """Set up logging using the environment variable."""
    configure_logging(log_level=logging.INFO, enable_logging=True)
    locale.setlocale(locale.LC_ALL, "es_ES.UTF-8")


@pytest.fixture()
def app() -> Flask:
    """Create and configure a new app instance for each test."""
    config = Config()
    config.SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
    app = create_app(config_class=Config)
    app.config.update({"TESTING": True})
    return app


@pytest.fixture()
def db(app: Flask) -> Generator[SQLAlchemy, None, None]:
    """Provide a database session for tests."""
    from cambios.database import db as _db

    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def session(db: SQLAlchemy) -> Generator[scoped_session, None, None]:
    """Create a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)
    db.session = session  # type: ignore[assignment]

    yield session

    session.remove()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(app: Flask, session: scoped_session) -> FlaskClient:
    """Create a test client for the app."""
    return app.test_client()


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


@pytest.fixture()
def preloaded_session() -> Generator[Session, None, None]:
    """Load the database with test data."""
    engine = create_engine("sqlite:///:memory:")
    _db.metadata.create_all(engine)

    session = sessionmaker(bind=engine)()

    with Path.open(PICKLE_FILE, "rb") as file:
        pickle_data = pickle.load(file)  # noqa: S301

    for table, data in (
        [ATC, pickle_data["users"]],
        [Turno, pickle_data["shifts"]],
        [TipoTurno, pickle_data["shift_types"]],
    ):
        for item in data:
            item.pop("_sa_instance_state", None)
            session.add(table(**item))

    yield session

    _db.metadata.drop_all(engine)


@pytest.fixture()
def atc(preloaded_session: Session) -> ATC:
    """Return an atc from a preloaded database."""
    # Get the first user from the Users table
    user = preloaded_session.query(ATC).first()
    if not user:
        _msg = "No users in the database."
        raise ValueError(_msg)
    return user
