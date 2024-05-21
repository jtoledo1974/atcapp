"""Firebase Admin SDK initialization."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import firebase_admin  # type: ignore[import-untyped]
from firebase_admin import auth, credentials

if TYPE_CHECKING:
    from logging import Logger

CRED_FILE = "cambios-76578-firebase-adminsdk-sude0-7d233cd189.json"

logger: Logger


def init_firebase(app_logger: Logger) -> None:
    """Initialize Firebase Admin SDK."""
    try:
        cred = credentials.Certificate(CRED_FILE)
    except FileNotFoundError:
        # Report error and shutdown
        app_logger.critical(
            "Firebase Admin SDK credentials file not found: %s"
            "\nPlease download from Firebase Console and place in the project root.",
            CRED_FILE,
        )
        sys.exit(1)
    firebase_admin.initialize_app(cred)
    global logger  # noqa: PLW0603
    logger = app_logger


def verify_id_token(id_token: str) -> dict[str, str]:
    """Verify the Firebase ID token.

    Returns the decoded token if verification is successful.

    """
    try:
        decoded_token = auth.verify_id_token(id_token)
    except Exception:
        _msg = "Token verification failed"
        logger.exception(_msg)
        raise ValueError(_msg) from None
    else:
        return decoded_token
