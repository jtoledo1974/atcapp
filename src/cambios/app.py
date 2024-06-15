"""Flask App for managing shifts."""

from __future__ import annotations

import locale
import logging
import os
import secrets
import sys
from datetime import timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from flask import Flask, flash, redirect, render_template, session, url_for
from flask_admin import Admin  # type: ignore[import-untyped]
from flask_admin.contrib.sqla import ModelView  # type: ignore[import-untyped]
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from . import configure_timezone
from .database import db
from .firebase import init_firebase
from .models import ATC
from .routes import register_routes

if TYPE_CHECKING:  # pragma: no cover
    from werkzeug import Response

LOGFILE = "logs/cambios.log"
SQLLOGFILE = "logs/cambios-sql.log"
LOGFORMAT = "%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]"


class Config:
    """Configuración por defecto."""

    ENABLE_LOGGING = False
    LOG_LEVEL = logging.WARNING

    SQLALCHEMY_DATABASE_URI = "sqlite:///shifts.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = secrets.token_urlsafe(32)
    DEBUG = False
    HOST = "localhost"
    PORT = 80
    PERMANENT_SESSION_LIFETIME = timedelta(days=90)
    SESSION_TYPE = "filesystem"


def configure_logging(
    log_level: int = Config.LOG_LEVEL,
    *,
    enable_logging: bool = Config.ENABLE_LOGGING,
) -> None:
    """Configure logging based on the environment variable.

    enable_logging forces logs to be written to a file,
    and a log_level of at least INFO.

    """
    # Configure logging
    # ENABLE_LOGGING forces logs to be written to a file

    env_log_level = os.getenv("LOG_LEVEL")
    if env_log_level:
        log_level = logging.getLevelName(env_log_level)

    env_enable_logging = os.getenv("ENABLE_LOGGING")
    if env_enable_logging:
        enable_logging = env_enable_logging.lower() in ["true", "1", "t"]
        if log_level > logging.INFO:
            log_level = logging.INFO

    logger = logging.getLogger()
    logger.debug("Setting log level to %s", log_level)

    if not enable_logging:
        return

    logger.debug("Logging to %s", LOGFILE)

    logs_dir = Path(LOGFILE).parent
    logs_dir.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(LOGFORMAT)
    file_handler = logging.FileHandler(LOGFILE)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    sql_file_handler = logging.FileHandler(SQLLOGFILE)
    sql_file_handler.setFormatter(formatter)
    sql_file_handler.setLevel(log_level)

    # Crear un handler para sacar por pantalla
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)

    logger = logging.getLogger("cambios")

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    logger.addHandler(sql_file_handler)
    logger.setLevel(log_level)
    logger.info("Cambios startup")

    sqllogger = logging.getLogger("sqlalchemy.engine")
    sqllogger.setLevel(logging.INFO)
    sqllogger.addHandler(file_handler)


class AdminModelView(ModelView):
    """Custom ModelView for the admin panel."""

    def is_accessible(self) -> bool:
        """Only allow access to the admin panel if the user is an admin."""
        return bool(session.get("es_admin"))

    def inaccessible_callback(self, _name: str, **_kwargs: dict[str, Any]) -> Response:
        """Redirect to the login page if the user is not an admin."""
        return redirect(url_for("main.login"))


def check_db_connection() -> None | str:
    """Check if a database connection can be established."""
    try:
        # Intenta realizar una consulta simple para verificar la conexión

        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # Maneja el error de conexión a la base de datos
        app.logger.exception("Error al conectar a la base de datos.")
        flash("Error: No se puede conectar a la base de datos.", "danger")
        return render_template("error.html")
    else:
        # Continúa con la solicitud normal
        return None


def create_app() -> Flask:
    """Create the Flask app."""
    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")

    app = Flask("cambios.app")
    app.config.from_object(Config)
    app.config.from_prefixed_env()

    configure_logging()
    configure_timezone()

    app.logger.info("DB_URI: %s", app.config["SQLALCHEMY_DATABASE_URI"])

    db.init_app(app)
    with app.app_context():
        try:
            db.init_db()
        except SQLAlchemyError:
            app.logger.exception("Error al inicializar la base de datos.")
            sys.exit(1)

    init_firebase()
    register_routes(app)

    admin = Admin(app, name="Admin Panel", template_mode="bootstrap4")
    admin.add_view(AdminModelView(ATC, db.session))

    # Registrar la función de verificación de la base de datos
    app.before_request(check_db_connection)

    # Context processor to make user info available in templates
    @app.context_processor
    def inject_user() -> dict[str, str | None]:
        try:
            user = db.session.query(ATC).filter_by(id=session.get("id_atc")).first()  # type: ignore[attr-defined]
        except SQLAlchemyError:
            return {"current_user": None}
        else:
            return {"current_user": user}

    @app.before_request
    def make_session_permanent() -> None:
        session.permanent = True

    # Manejador de error 404
    @app.errorhandler(404)
    def page_not_found(_e: Exception) -> str:
        msg = "Página no encontrada (404)"
        app.logger.exception(msg)
        return render_template("error.html", message=msg)

    # Manejador de error 500
    @app.errorhandler(500)
    def internal_server_error(_e: Exception) -> str:
        msg = "Error de servidor (500)"
        app.logger.exception(msg)
        return render_template("error.html", message=msg)

    # Otros errores
    @app.errorhandler(Exception)
    def handle_exception(_e: Exception) -> tuple[str, int]:
        # Para manejar otros errores de forma general
        msg = "Error desconocido"
        app.logger.exception(msg)
        return render_template("error.html", message=msg), 500

    return app


if __name__ == "__main__":  # pragma: no cover
    app = create_app()
    app.run(debug=True, port=app.config["PORT"], host=app.config["HOST"])
