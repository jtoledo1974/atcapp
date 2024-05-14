"""Flask App for managing shifts."""

import collections

import firebase_admin
from firebase_admin import credentials
from flask import Response, flash, redirect, render_template, request, session, url_for
from flask_admin.contrib.sqla import ModelView

from .config import admin, admin_password, app, db
from .models import Shift, User

# Initialize Firebase Admin SDK
cred = credentials.Certificate("path/to/your/firebase-adminsdk.json")
firebase_admin.initialize_app(cred)


@app.route("/")
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
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login() -> str:
    """Render the login page."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # Check for admin user.
        if username == "admin" and password == admin_password:
            session["user_id"] = 0
            return redirect(url_for("admin.index"))

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            session["user_id"] = user.id
            flash("Login successful!", "success")
            return redirect(url_for("index"))
        flash("Login failed. Please check your username and password.", "danger")
        return redirect(url_for("login"))
    return render_template("login.html")


@app.route("/logout")
def logout() -> Response:
    """Logout the user."""
    session.pop("user_id", None)
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register() -> Response:
    """Render the register page."""
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for("login"))
    return render_template("register.html")


class AdminModelView(ModelView):
    """Custom ModelView for the admin panel."""

    def is_accessible(self) -> bool:
        """Only allow access to the admin panel if the user is an admin."""
        return session.get("user_id") == 0

    def inaccessible_callback(self, name, **kwargs) -> Response:
        """Redirect to the login page if the user is not an admin."""
        return redirect(url_for("login"))


admin.add_view(AdminModelView(User, db.session))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
