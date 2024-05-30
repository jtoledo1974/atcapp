"""Tests for the app module."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from cambios import configure_timezone, get_timezone
from cambios.app import create_app

if TYPE_CHECKING:
    from cambios.models import ATC
    from flask.testing import FlaskClient


# Ensure the fixtures are defined in conftest.py
@pytest.mark.usefixtures("_verify_id_token_mock")
def test_admin_access(client: FlaskClient, admin_user: ATC) -> None:
    """Test that an admin user can access the admin panel."""
    # Log in as admin user
    client.post("/login", data={"idToken": "test_token"})

    # Access the admin panel
    response = client.get("/admin/")
    assert response.status_code == 200
    assert b"Admin Panel" in response.data


@pytest.mark.usefixtures("_verify_id_token_mock")
def test_non_admin_access(client: FlaskClient, regular_user: ATC) -> None:
    """Test that a non-admin user cannot access the admin panel."""
    # Log in as regular user
    client.post("/login", data={"idToken": "test_token"})

    # Try to access the admin panel
    response = client.get("/admin/", follow_redirects=True)
    assert response.status_code == 200
    assert b"Bienvenido" in response.data  # Check if redirected to login


def test_logging_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that logging is enabled if the environment variable is set."""
    # Set the environment variable to enable logging
    monkeypatch.setenv("ENABLE_LOGGING", "true")

    app = create_app()

    assert app.logger.parent
    assert app.logger.parent.level == logging.INFO

    monkeypatch.delenv("ENABLE_LOGGING", raising=False)
    app.logger.parent.setLevel(logging.WARNING)  # manually set to warning again
    app.logger.handlers.clear()  # remove all handlers


def test_logging_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that logging is disabled if the environment variable is not set."""
    # Unset the environment variable to disable logging
    monkeypatch.delenv("ENABLE_LOGGING", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)

    app = create_app()
    assert app.logger.parent
    assert app.logger.parent.level != logging.INFO


@pytest.mark.usefixtures("_verify_admin_id_token_mock")
def test_admin_sees_users_link(client: FlaskClient, admin_user: ATC) -> None:
    """Test that an admin user sees the Users link in the admin panel."""
    # Log in as admin user
    client.post("/login", data={"idToken": "test_token"})

    # Access the admin panel
    response = client.get("/admin/")

    # Check that the response contains the "Users" link
    assert response.status_code == 200
    assert b"User" in response.data


def test_default_timezone() -> None:
    """Verifica que la zona horaria por defecto es 'Europe/Madrid'."""
    tz = get_timezone()
    assert tz.zone == "Europe/Madrid"


def test_env_timezone() -> None:
    """Verifica que la zona horaria se puede configurar mediante una variable de entorno."""
    # Set the environment variable to change the timezone
    with pytest.MonkeyPatch.context() as mp:
        mp.setenv("TZ", "America/New_York")
        configure_timezone()

        tz = get_timezone()
        assert tz.zone == "America/New_York"

    # Unset the environment variable
    configure_timezone()
    tz = get_timezone()
    assert tz.zone == "Europe/Madrid"
