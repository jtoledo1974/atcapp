"""Flask App for managing shifts."""

from typing import Any

from flask import Flask, Response, redirect, session, url_for
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from .config import load_admin_password, load_key
from .database import db, init_db
from .firebase import init_firebase
from .models import User
from .routes import register_routes


class AdminModelView(ModelView):
    """Custom ModelView for the admin panel."""

    def is_accessible(self) -> bool:
        """Only allow access to the admin panel if the user is an admin."""
        return session.get("user_id") == 0

    def inaccessible_callback(self, _name: str, **_kwargs: dict[str, Any]) -> Response:
        """Redirect to the login page if the user is not an admin."""
        return redirect(url_for("login"))


def create_app() -> Flask:
    """Create the Flask app."""
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shifts.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = load_key()
    db.init_app(app)
    with app.app_context():
        init_db()

    init_firebase(app.logger)
    register_routes(app)

    _admin_password = load_admin_password()
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
