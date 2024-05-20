"""Routes for the Cambios app."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from flask import (
    Blueprint,
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .cambios import is_admin
from .database import db
from .firebase import verify_id_token
from .models import Shift, User
from .upload import process_file

if TYPE_CHECKING:
    from flask import Flask

main = Blueprint("main", __name__)


@main.route("/")
def index() -> Response:
    """Render the index page."""
    if "user_id" not in session:
        return redirect(url_for("main.login"))

    user = User.query.get(session["user_id"])
    shifts = Shift.query.order_by(Shift.date).all()
    shift_data = defaultdict(lambda: {"M": "Open", "T": "Open", "N": "Open"})
    for shift in shifts:
        date_str = shift.date.strftime("%Y-%m-%d")
        shift_data[date_str][shift.shift_type] = (
            f"{shift.user.first_name} {shift.user.last_name}"
        )
    return render_template("index.html", user=user, shift_data=shift_data)


@main.route("/login", methods=["GET", "POST"])
def login() -> str:
    """Render the login page."""
    if request.method != "POST":
        return render_template("login.html")

    try:
        email = verify_id_token(request.form["idToken"])["email"]
    except ValueError:
        flash("Login failed. Please try again.", "danger")
        return redirect(url_for("main.login"))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash("Usuario no reconocido. Hable con el administrador.", "danger")
        return redirect(url_for("main.logout"))

    session["user_id"] = user.id
    flash("Login successful!", "success")

    # Check for admin user.
    if is_admin(email):
        session["is_admin"] = True
        return redirect(url_for("admin.index"))

    return redirect(url_for("main.index"))


@main.route("/logout")
def logout() -> Response:
    """Logout the user."""
    session.clear()

    return redirect(url_for("main.login"))


@main.route("/upload", methods=["GET", "POST"])
def upload() -> Response:
    """Upload shift data to the server.

    For GET requests, render the upload page.
    For POST requests, upload the shift data to the server.
    """
    if request.method == "POST":
        file = request.files["file"]
        if file.filename:
            process_file(file, db.session)
            return redirect(url_for("main.index"))
    return render_template("upload.html")


def register_routes(app: Flask) -> Blueprint:
    """Register the routes with the app."""
    app.register_blueprint(main)
    return main
