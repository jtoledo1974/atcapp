"""Firebase Admin SDK initialization."""

from __future__ import annotations

import json
import os
import sys
from typing import TYPE_CHECKING

import firebase_admin  # type: ignore[import-untyped]
from firebase_admin import auth, credentials

if TYPE_CHECKING:
    from logging import Logger

CRED_FILE = os.getenv(
    "FIREBASE_CRED_FILE",
    "cambios-firebase.json",
)
CRED_JSON = os.getenv("FIREBASE_CRED_JSON")

logger: Logger
firebase_initialized = False


def init_firebase(app_logger: Logger) -> None:
    """Initialize Firebase Admin SDK."""
    global firebase_initialized  # noqa: PLW0603
    if firebase_initialized:
        return

    try:
        if CRED_JSON:
            cred_dict = json.loads(CRED_JSON)
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate(CRED_FILE)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # Report error and shutdown
        app_logger.critical(
            "Firebase Admin SDK credentials not found or invalid: %s\n"
            "Please set FIREBASE_CRED_FILE or FIREBASE_CRED_JSON "
            "environment variables.\n"
            "Firebase credentials can be downloaded from Firebase Console.\n\n"
            "%s",
            CRED_FILE,
            str(e),
        )
        sys.exit(1)
    firebase_admin.initialize_app(cred)
    global logger  # noqa: PLW0603
    logger = app_logger
    firebase_initialized = True


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
