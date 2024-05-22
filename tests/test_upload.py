"""Tests for the shifts upload module."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from cambios.models import Shift, User

if TYPE_CHECKING:
    from flask.testing import FlaskClient
    from sqlalchemy import SQLAlchemy

# Assuming your fixtures are in conftest.py as shown before

users_shifts_pattern = re.compile(
    rb"Usuarios reconocidos: (\d+), turnos agregados: (\d+)",
)


def extract_users_and_shifts_inserted(response: bytes) -> tuple[int, int]:
    """Extract the number of users and shifts inserted from the response."""
    match = re.search(
        rb"(\d+) users and (\d+) shifts inserted",
        response,
        re.IGNORECASE,
    )
    match = users_shifts_pattern.search(response)

    assert match is not None, "Expected flash message not found"
    return int(match.group(1)), int(match.group(2))


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
    users, shifts = extract_users_and_shifts_inserted(response.data)
    # We never checked the add_new checkbox, so no users or shifts should be added
    assert users == 0
    assert shifts == 0


@pytest.mark.usefixtures("_verify_admin_id_token_mock")
def test_upload_admin_post_add_new(
    client: FlaskClient,
    admin_user: User,
    db: SQLAlchemy,
) -> None:
    """Test that the upload route processes a valid PDF file."""
    # Log in as admin user
    client.post("/login", data={"idToken": "test_token"})

    # Path to the test PDF file
    test_file_path = Path(__file__).parent / "resources" / "test_schedule.pdf"

    with test_file_path.open("rb") as file:
        response = client.post(
            "/upload",
            data={"file": file, "add_new": "on"},
            content_type="multipart/form-data",
            follow_redirects=True,
        )

    assert response.status_code == 200
    users, shifts = extract_users_and_shifts_inserted(response.data)
    # We checked the add_new checkbox, so users and shifts should be added
    assert users == 20
    assert shifts == 445

    # Skip the first user (Admin) and get the second user
    user = User.query.offset(1).first()
    assert user.first_name == "MANUEL"
    assert user.last_name == "GIL ROMERO"
    assert user.email == "fixmeMANUELGIL ROMEROfixme@example.com"
    assert user.category == "TS"
    assert user.team == "A"
    assert user.license_number == ""

    # Checking that we don't touch existing shifts
    # and that roles and teams are updated
    shift_to_delete = Shift.query.first()
    db.session.delete(shift_to_delete)
    user.team = "X"
    user.category = "CON"

    with test_file_path.open("rb") as file:
        response = client.post(
            "/upload",
            data={"file": file},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    users, shifts = extract_users_and_shifts_inserted(response.data)
    assert shifts == 1
    assert user.team == "A"
    assert user.category == "TS"


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
