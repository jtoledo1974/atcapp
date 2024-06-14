"""Tests for the routes module."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from cambios.models import ATC
    from flask.testing import FlaskClient
    from pytest_mock import MockerFixture


def test_index_redirect(client: FlaskClient) -> None:
    """Test that the index page redirects to the login page."""
    response = client.get("/")
    assert response.status_code == 302
    assert response.location == "/login"


@pytest.mark.usefixtures("_verify_id_token_mock")
def test_login_success(client: FlaskClient, regular_user: ATC) -> None:
    """Test that the login route logs in a user."""
    response = client.post(
        "/login",
        data={"idToken": "test_token"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.location == "/"
    with client.session_transaction() as sess:
        assert sess["id_atc"] == regular_user.id


def test_login_failure(client: FlaskClient, mocker: MockerFixture) -> None:
    """Test that the login route fails with an invalid token."""
    mocker.patch("src.cambios.firebase.auth.verify_id_token", side_effect=ValueError)
    response = client.post(
        "/login",
        data={"idToken": "invalid_token"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Autenticación fallida".encode() in response.data


@pytest.mark.usefixtures("_verify_id_token_mock")
def test_logout(client: FlaskClient, regular_user: ATC) -> None:
    """Test that the logout route logs out a user."""
    client.post("/login", data={"idToken": "test_token"})
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert "Has cerrado sesión" in response.data.decode()
    with client.session_transaction() as sess:
        assert "id_atc" not in sess


@pytest.mark.usefixtures("_verify_id_token_mock")
def test_upload_get(client: FlaskClient, regular_user: ATC) -> None:
    """Test that the upload route redirects regular users to /."""
    client.post("/login", data={"idToken": "test_token"})
    response = client.get("/upload")
    assert response.status_code == 302
    assert response.location == "/"


@pytest.mark.usefixtures("_verify_admin_id_token_mock")
def test_upload_admin_get(client: FlaskClient, admin_user: ATC) -> None:
    """Test that the upload route renders the upload page."""
    client.post("/login", data={"idToken": "test_token"})
    response = client.get("/upload")
    assert response.status_code == 200
    assert b"Carga de Turnero" in response.data


@pytest.mark.usefixtures("_verify_admin_id_token_mock")
def test_upload_post_no_file(client: FlaskClient, admin_user: ATC) -> None:
    """Test that the upload route fails if no file is selected."""
    client.post("/login", data={"idToken": "test_token"})
    # Submit the upload form with an empty file field
    response = client.post("/upload", data={"files": (None, "")}, follow_redirects=True)
    assert response.status_code == 200
    assert (
        b"No se han seleccionado archivos o algunos archivos no tienen nombre"
        in response.data
    )


@pytest.mark.usefixtures("_verify_id_token_mock")
def test_privacy_policy_redirect(client: FlaskClient, new_user: ATC) -> None:
    """Test that a user is redirected to the privacy policy page if they have not accepted the policy."""  # noqa: E501
    # Log in the user
    response = client.post("/login", data={"idToken": "test_token"})
    # Ensure the user has not accepted the policy
    assert response.status_code == 302
    assert response.location == "/privacy_policy"


@pytest.mark.usefixtures("_verify_id_token_mock")
def test_privacy_policy_accept(client: FlaskClient, new_user: ATC) -> None:
    """Test that accepting the privacy policy updates the database and redirects to the main page."""  # noqa: E501
    # Log in the user
    client.post("/login", data={"idToken": "test_token"})
    # Accept the privacy policy
    response = client.post(
        "/privacy_policy",
        data={"accept_policy": "true"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Turnero" in response.data


@pytest.mark.usefixtures("_verify_id_token_mock")
def test_login_redirect_to_privacy_policy(
    client: FlaskClient,
    new_user: ATC,
) -> None:
    """Test that a user is redirected to the privacy policy page after login if they have not accepted the policy."""  # noqa: E501
    # Log in the user
    response = client.post("/login", data={"idToken": "test_token"})
    # Ensure the user has not accepted the policy
    assert response.status_code == 302
    assert response.location == "/privacy_policy"
    # Try to access the main page
    response = client.get("/")
    assert response.status_code == 302
    assert response.location == "/privacy_policy"


@pytest.mark.usefixtures("_verify_admin_id_token_mock")
def test_upload_estadillo_get(client: FlaskClient, admin_user: ATC) -> None:
    """Test that the upload_estadillo route renders the upload page."""
    client.post("/login", data={"idToken": "test_token"})
    response = client.get("/upload_estadillo")
    assert response.status_code == 200
    assert b"Carga de Estadillo" in response.data


@pytest.mark.usefixtures("_verify_admin_id_token_mock")
def test_upload_estadillo_post_no_file(client: FlaskClient, admin_user: ATC) -> None:
    """Test that the upload_estadillo route fails if no file is selected."""
    client.post("/login", data={"idToken": "test_token"})
    response = client.post(
        "/upload_estadillo",
        data={"file": (None, "")},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"No se ha seleccionado un archivo" in response.data


@pytest.mark.usefixtures("_verify_admin_id_token_mock")
def test_upload_estadillo_post(
    client: FlaskClient,
    admin_user: ATC,
    estadillo_path: Path,
) -> None:
    """Test that the upload_estadillo route processes a valid PDF file."""
    client.post("/login", data={"idToken": "test_token"})

    with estadillo_path.open("rb") as file:
        response = client.post(
            "/upload_estadillo",
            data={"file": file},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert "Archivo cargado con éxito".encode() in response.data


def test_plantilla_estadillo(preloaded_client: FlaskClient, atc: ATC) -> None:
    """Verificar que la plantilla de estadillo se renderiza correctamente."""
    preloaded_client.post("/login", data={"idToken": "test_token"})
    response = preloaded_client.get("/estadillo")
    assert response.status_code == 200
    assert b"Plantilla de Estadillo" in response.data
