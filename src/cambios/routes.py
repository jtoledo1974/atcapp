"""Routes for the Cambios app."""

from __future__ import annotations

import collections
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
    if "user_id" in session:
        user = User.query.get(session["user_id"])
        shifts = Shift.query.order_by(Shift.date).all()
        shift_data = collections.defaultdict(
            lambda: {"M": "Open", "T": "Open", "N": "Open"},
        )
        for shift in shifts:
            date_str = shift.date.strftime("%Y-%m-%d")
            shift_data[date_str][shift.shift_type] = shift.user.username
        return render_template("index.html", user=user, shift_data=shift_data)
    return redirect(url_for("main.login"))


@main.route("/login", methods=["GET", "POST"])
def login() -> str:
    """Render the login page."""
    if request.method == "POST":
        try:
            email = verify_id_token(request.form["idToken"])["email"]
        except ValueError:
            flash("Login failed. Please try again.", "danger")
            return redirect(url_for("main.login"))

        # Check for admin user.
        if is_admin(email):
            return redirect(url_for("admin.index"))

        user = User.query.filter_by(email=email).first()
        if user:
            session["user_id"] = user.id

            flash("Login successful!", "success")
            return redirect(url_for("main.index"))
        flash("Login failed. Please check your username and password.", "danger")
        return redirect(url_for("main.login"))
    return render_template("login.html")


@main.route("/logout")
def logout() -> Response:
    """Logout the user."""
    session.clear()

    return redirect(url_for("main.login"))


@main.route("/register", methods=["GET", "POST"])
def register() -> Response:
    """Render the register page."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("main.login"))
    return render_template("main.register.html")


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
