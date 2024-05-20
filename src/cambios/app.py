"""Flask App for managing shifts."""

import os
import secrets
from pathlib import Path
from typing import Any

from flask import Flask, Response, redirect, session, url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from .database import db, init_db
from .firebase import init_firebase
from .models import User
from .routes import register_routes


class Config:
    """Base configuration."""

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "sqlite:///shifts.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ["true", "1", "t"]
    PORT = int(os.getenv("PORT", "5005"))

    @staticmethod
    def load_key() -> str:
        """Load the secret key from the environment or .key file."""
        if "SECRET_KEY" in os.environ:
            return os.environ["SECRET_KEY"]
        key_file = Path(".key")
        if key_file.exists():
            with key_file.open("r") as f:
                return f.read().strip()
        key = secrets.token_urlsafe(32)
        with key_file.open("w") as f:
            f.write(key)
        return key


class AdminModelView(ModelView):
    """Custom ModelView for the admin panel."""

    def is_accessible(self) -> bool:
        """Only allow access to the admin panel if the user is an admin."""
        return session.get("is_admin")

    def inaccessible_callback(self, _name: str, **_kwargs: dict[str, Any]) -> Response:
        """Redirect to the login page if the user is not an admin."""
        return redirect(url_for("login"))


def create_app(config_class: Config = Config) -> Flask:
    """Create the Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config.from_envvar("APP_SETTINGS", silent=True)

    db.init_app(app)
    with app.app_context():
        init_db()

    init_firebase(app.logger)
    register_routes(app)

    admin = Admin(
        app,
        name="Admin Panel",
        template_mode="bootstrap4",
    )
    admin.add_view(AdminModelView(User, db.session))

    # Context processor to make user info available in templates
    @app.context_processor
    def inject_user() -> dict[str, str]:
        user = User.query.filter_by(id=session.get("user_id")).first()
        return {
            "current_user": user,
        }

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5005)
