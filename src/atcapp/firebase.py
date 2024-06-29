"""Firebase Admin SDK initialization."""

from __future__ import annotations

import base64
import binascii
import json
import os
import sys
from logging import getLogger

from firebase_admin import auth, credentials, initialize_app

logger = getLogger(__name__)

CRED_FILE = os.getenv(
    "FIREBASE_CRED_FILE",
    "atcapp.json",
)
CRED_JSON_BASE64 = os.getenv("FIREBASE_CRED_JSON")

firebase_initialized = False


def init_firebase() -> None:
    """Initialize Firebase Admin SDK."""
    global firebase_initialized  # noqa: PLW0603
    if firebase_initialized:
        return

    have_credentials = False
    cred = None

    # Try to load credentials from base64 encoded JSON
    if CRED_JSON_BASE64:
        try:
            cred_json = base64.b64decode(CRED_JSON_BASE64).decode("utf-8")
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            have_credentials = True
        except (binascii.Error, json.JSONDecodeError):
            logger.warning(
                "Failed to decode Firebase credentials from environment variable: %s",
            )

    # If loading from base64 failed, try to load from file
    if not have_credentials:
        try:
            cred = credentials.Certificate(CRED_FILE)
            have_credentials = True
        except FileNotFoundError:
            logger.exception(
                "Firebase Admin SDK credentials file not found: %s. "
                "Please set the FIREBASE_CRED_FILE environment variable correctly.",
                CRED_FILE,
            )
        except Exception:
            logger.exception(
                "An unexpected error loading Firebase credentials from file: %s",
                CRED_FILE,
            )

    if not have_credentials:
        sys.exit(1)

    try:
        initialize_app(cred)
        firebase_initialized = True
        logger.info("Firebase Admin SDK initialized.")
    except Exception:
        logger.exception("An unexpected error occurred while initializing Firebase: %s")
        sys.exit(1)


def verify_id_token(id_token: str) -> dict[str, str]:
    """Verify the Firebase ID token.

    Returns the decoded token if verification is successful.

    """
    try:
        decoded_token = auth.verify_id_token(id_token, clock_skew_seconds=2)
    except Exception:
        _msg = "Token verification failed"
        logger.exception(_msg)
        raise ValueError(_msg) from None
    else:
        return decoded_token


def invalidate_token(id_token: str) -> None:
    """Invalidate the Firebase ID token."""
    try:
        auth.revoke_refresh_tokens(id_token)
    except Exception:
        _msg = "Token invalidation failed"
        logger.exception(_msg)
        raise ValueError(_msg) from None


def get_recognized_emails() -> list[str]:
    """Retrieve the list of recognized user emails from Firebase."""
    users = auth.list_users().users
    return [user.email for user in users if user.email is not None]
