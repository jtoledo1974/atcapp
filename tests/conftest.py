"""Configuration for pytest."""

import os
import secrets
from typing import Any, Generator

import pytest
from cambios.app import Config, create_app
from cambios.models import User
from flask import Flask
from flask.testing import FlaskClient
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import scoped_session, sessionmaker


@pytest.fixture()
def app() -> Flask:
    """Create and configure a new app instance for each test."""
    config = Config()
    config.SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
    app = create_app(config_class=Config)
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
    Session = scoped_session(session_factory)
    db.session = Session

    yield Session

    Session.remove()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    """A test client for the app."""
    return app.test_client()


@pytest.fixture()
def runner(app: Flask) -> Any:
    """A test runner for the app's Click commands."""
    return app.test_cli_runner()


@pytest.fixture()
def init_firebase_mock(mocker: Any) -> None:
    """Mock the init_firebase function."""
    mocker.patch("src.cambios.firebase.init_firebase", return_value=None)


@pytest.fixture()
def verify_id_token_mock(mocker: Any) -> None:
    """Mock the verify_id_token function."""
    mocker.patch(
        "src.cambios.firebase.auth.verify_id_token",
        return_value={"uid": "test_uid"},
    )


@pytest.fixture()
def admin_user(session: scoped_session) -> User:
    """Create an admin user for testing."""
    admin = User(
        email="admin@example.com",
        firebase_uid="admin_uid",
        first_name="Admin",
        last_name="User",
        category="Admin",
        team=None,
        license_number="123456",
        is_admin=True,
    )
    session.add(admin)
    session.commit()
    return admin


@pytest.fixture()
def regular_user(session: scoped_session) -> User:
    """Create a regular user for testing."""
    user = User(
        email="user@example.com",
        firebase_uid="user_uid",
        first_name="Regular",
        last_name="User",
        category="User",
        team=None,
        license_number="654321",
        is_admin=False,
    )
    session.add(user)
    session.commit()
    return user
