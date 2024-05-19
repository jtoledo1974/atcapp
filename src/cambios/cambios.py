"""Business logic for the cambios app."""

from __future__ import annotations

from .models import User


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
