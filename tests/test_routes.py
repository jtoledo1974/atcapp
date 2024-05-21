"""Tests for the routes module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from flask import session

if TYPE_CHECKING:
    from cambios.models import User
    from flask.testing import FlaskClient
    from pytest_mock import MockerFixture


def test_index_redirect(client: FlaskClient) -> None:
    """Test that the index page redirects to the login page."""
    response = client.get("/")
    assert response.status_code == 302
    assert response.location == "/login"


@pytest.mark.usefixtures("_verify_id_token_mock")
def test_login_success(client: FlaskClient, regular_user: User) -> None:
    """Test that the login route logs in a user."""
    response = client.post(
        "/login",
        data={"idToken": "test_token"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.location == "/"
    with client.session_transaction() as sess:
        assert sess["user_id"] == regular_user.id


def test_login_failure(client: FlaskClient, mocker: MockerFixture) -> None:
    """Test that the login route fails with an invalid token."""
    mocker.patch("src.cambios.firebase.auth.verify_id_token", side_effect=ValueError)
    response = client.post(
        "/login",
        data={"idToken": "invalid_token"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Login failed. Please try again." in response.data


@pytest.mark.usefixtures("_verify_id_token_mock")
def test_logout(client: FlaskClient, regular_user: User) -> None:
    """Test that the logout route logs out a user."""
    client.post("/login", data={"idToken": "test_token"})
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"Login" in response.data
    assert "user_id" not in session


@pytest.mark.usefixtures("_verify_id_token_mock")
def test_upload_get(client: FlaskClient, regular_user: User) -> None:
    """Test that the upload route renders the upload page."""
    client.post("/login", data={"idToken": "test_token"})
    response = client.get("/upload")
    assert response.status_code == 200
    assert b"Carga de Turnero" in response.data


@pytest.mark.usefixtures("_verify_id_token_mock")
def test_upload_post_no_file(client: FlaskClient, regular_user: User) -> None:
    """Test that the upload route fails if no file is selected."""
    client.post("/login", data={"idToken": "test_token"})
    response = client.post("/upload", data={}, follow_redirects=True)
    assert response.status_code == 200
    assert b"No file selected" in response.data
