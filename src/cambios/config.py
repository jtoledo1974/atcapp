"""Configuration for the Flask app."""

import secrets
from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy


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


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shifts.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = load_key()

db = SQLAlchemy(app)
