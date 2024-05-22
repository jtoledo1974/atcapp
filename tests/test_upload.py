"""Tests for the shifts upload module."""

from pathlib import Path

import pytest
from cambios.models import User
from flask.testing import FlaskClient

# Assuming your fixtures are in conftest.py as shown before


@pytest.mark.usefixtures("_verify_admin_id_token_mock")
def test_upload_admin_post(client: FlaskClient, admin_user: User) -> None:
    """Test that the upload route processes a valid PDF file."""
    # Log in as admin user
    client.post("/login", data={"idToken": "test_token"})

    # Path to the test PDF file
    test_file_path = Path(__file__).parent / "resources" / "test_schedule.pdf"

    with test_file_path.open("rb") as file:
        response = client.post(
            "/upload",
            data={"file": file},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert "Archivo cargado con éxito".encode() in response.data


@pytest.mark.usefixtures("_verify_admin_id_token_mock")
def test_upload_post_invalid_file(client: FlaskClient, admin_user: User) -> None:
    """Test that the upload route fails if an invalid file is uploaded."""
    # Log in as admin user
    client.post("/login", data={"idToken": "test_token"})

    # Path to an invalid test file
    test_file_path = Path(__file__).parent / "resources" / "invalid_file.txt"

    with test_file_path.open("rb") as file:
        response = client.post(
            "/upload",
            data={"file": file},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert "Formato de archivo no válido".encode() in response.data
