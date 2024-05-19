"""Configuration module."""

import secrets
from pathlib import Path

_admin_password: str = ""
"""The admin password."""


def load_key() -> str:
    """Load the secret key from the .key file.

    If there is no .key file, create one with a random secret key.
    """
    key_file = Path(".key")
    if key_file.exists():
        with key_file.open("r") as f:
            return f.read().strip()
    key = secrets.token_urlsafe(32)
    with key_file.open("w") as f:
        f.write(key)
    return key


def load_admin_password() -> str:
    """Load the admin password from the .admin_passwd file.

    If there is no .admin_passwd file, create one with a random password.
    """
    admin_passwd_file = Path(".admin_passwd")
    if admin_passwd_file.exists():
        with admin_passwd_file.open("r") as f:
            return f.read().strip()
    password = secrets.token_urlsafe(16)
    with admin_passwd_file.open("w") as f:
        f.write(password)
    return password


def get_admin_password() -> str:
    """Return the admin password."""
    return _admin_password
