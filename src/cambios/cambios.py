"""Business logic for the cambios app."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pypdf

from .models import User

if TYPE_CHECKING:
    from werkzeug.datastructures import FileStorage


def is_admin(email: str) -> bool:
    """Check if the user is an admin.

    Checks the is_admin column in Users.
    If no users have the is_admin flag set, the first user to log in becomes the admin.

    """
    user = User.query.filter_by(email=email).first()
    if user:
        # The user was found
        return user.is_admin

    # User is not an admin. Check whether anyone is an admin.
    return not User.query.filter_by(is_admin=True).first()


def process_file(file: FileStorage) -> None:
    """Process the uploaded file."""
    pdf = pypdf.PdfReader(file)
    for page_num in range(len(pdf.pages)):
        page = pdf.pages[page_num]
        text = page.extract_text()
        # Process text
        print(text)
