"""Flask App for managing shifts."""

from __future__ import annotations

import locale
import logging
import os
import secrets
from pathlib import Path
from typing import TYPE_CHECKING, Any

from flask import Flask, redirect, session, url_for
from flask_admin import Admin  # type: ignore[import-untyped]
from flask_admin.contrib.sqla import ModelView  # type: ignore[import-untyped]

from .database import db, init_db
from .firebase import init_firebase
from .models import User
from .routes import register_routes

if TYPE_CHECKING:  # pragma: no cover
    from werkzeug import Response

LOGFILE = "logs/cambios.log"
LOGFORMAT = (
    "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d] %(name)s"
)


class Config:
    """Base configuration."""

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "SQLALCHEMY_DATABASE_URI",
        "sqlite:///shifts.db",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ["true", "1", "t"]
    HOST = os.getenv("HOST", "localhost")
    PORT = int(os.getenv("PORT", "80"))
    # Can't set this here, because we need to wait until the fixtures are loaded
    # Check below for ENABLE_LOGGING


class AdminModelView(ModelView):
    """Custom ModelView for the admin panel."""

    def is_accessible(self) -> bool:
        """Only allow access to the admin panel if the user is an admin."""
        return bool(session.get("is_admin"))

    def inaccessible_callback(self, _name: str, **_kwargs: dict[str, Any]) -> Response:
        """Redirect to the login page if the user is not an admin."""
        return redirect(url_for("main.login"))


def configure_logging(app: Flask, debug_level: int = logging.INFO) -> None:
    """Configure logging based on the environment variable."""
    # Configure logging
    # ENABLE_LOGGING forces logs to be written to a file
    enable_logging = os.getenv("ENABLE_LOGGING", "False").lower() in ["true", "1", "t"]

    if not enable_logging:
        return

    logs_dir = Path(LOGFILE).parent
    if not logs_dir.exists():
        logs_dir.mkdir()

    formatter = logging.Formatter(LOGFORMAT)
    file_handler = logging.FileHandler(LOGFILE)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(debug_level)

    # Crear un handler para sacar por pantalla
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(debug_level)

    logger = logging.getLogger("cambios")

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.setLevel(debug_level)
    logger.info("Cambios startup")


def create_app(config_class: type[Config] = Config) -> Flask:
    """Create the Flask app."""
    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")

    app = Flask("cambios.app")
    app.config.from_object(config_class)
    app.config.from_envvar("APP_SETTINGS", silent=True)

    configure_logging(app)

    db.init_app(app)
    with app.app_context():
        init_db()

    init_firebase()
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
    app.run(debug=True, port=app.config["PORT"], host=app.config["HOST"])
