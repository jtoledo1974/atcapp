"""Routes for the Cambios app."""

from __future__ import annotations

import contextlib
from datetime import datetime
from functools import wraps
from logging import getLogger
from typing import TYPE_CHECKING, Callable

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import IntegrityError

from . import get_timezone
from .cambios import GenCalMensual
from .carga_estadillo import procesa_estadillo
from .carga_turnero import ResultadoProcesadoTurnero, procesa_turnero
from .database import db
from .estadillos import genera_datos_estadillo
from .firebase import get_recognized_emails, invalidate_token, verify_id_token
from .models import ATC, Estadillo

if TYPE_CHECKING:  # pragma: no cover
    from flask import Flask
    from werkzeug import Response

logger = getLogger(__name__)

main = Blueprint("main", __name__)


def privacy_policy_accepted(f: Callable) -> Callable:
    """Decorate a route to check if the user has accepted the privacy policy."""

    @wraps(f)
    def decorated_function(*args, **kwargs) -> Response | str:  # noqa: ANN002, ANN003
        """Check if the user has accepted the privacy policy."""
        id_atc = session.get("id_atc")
        if not id_atc:
            # This decorator is meant for logged in users.
            # Do nothing if the user is not logged in.
            return f(*args, **kwargs)

        user = db.session.get(ATC, id_atc)
        if user and not user.politica_aceptada:
            flash("Debes aceptar la política de privacidad para continuar.", "warning")
            return redirect(url_for("main.privacy_policy"))

        return f(*args, **kwargs)

    return decorated_function


def es_admin(f: Callable) -> Callable:
    """Check if the user is an admin dectorator."""

    @wraps(f)
    def decorated_function(*args, **kwargs) -> Response | str:  # noqa: ANN002, ANN003
        """Check if the user is an admin."""
        id_atc = session.get("id_atc")
        if not id_atc:
            # User is not logged in, redirect to login
            return redirect(url_for("main.login"))

        user = db.session.get(ATC, id_atc)
        if user and user.es_admin:
            # User is an admin, proceed with the original function
            return f(*args, **kwargs)

        # User is not an admin, redirect to index with a warning
        flash("Debes ser administrador para acceder a esta página.", "warning")
        return redirect(url_for("main.index"))

    return decorated_function


@main.route("/")
@privacy_policy_accepted
def index() -> Response | str:
    """Render the index page."""
    if "id_atc" not in session:
        return redirect(url_for("main.login"))

    user = db.session.get(ATC, session["id_atc"])
    if not user:
        return redirect(url_for("main.logout"))

    # Check if the user has a latest estadillo and redirect to it
    estadillo = (
        db.session.query(Estadillo)
        .join(Estadillo.atcs)
        .filter(ATC.id == user.id)
        .order_by(Estadillo.fecha.desc())
        .first()
    )

    now = datetime.now(tz=get_timezone())
    if estadillo and estadillo.hora_inicio <= now <= estadillo.hora_fin:
        return redirect(url_for("main.estadillo"))

    # TODO #3 It would be better to use the user's timezone here
    # Currently forcing continental Spain using pytz
    tz = get_timezone()
    today = datetime.now(tz=tz)

    # Get month and year from query parameters or use current month and year
    month = request.args.get("month", type=int, default=today.month)
    year = request.args.get("year", type=int, default=today.year)

    logger.debug("Generando calendario para %s %s", month, year)
    calendar = GenCalMensual.generate(year, month, user, db.session)  # type: ignore[arg-type]

    # Check the session for the toggleDescriptions state
    if "toggleDescriptions" not in session:
        session["toggleDescriptions"] = request.user_agent.platform not in [
            "android",
            "iphone",
        ]

    return render_template(
        "index.html",
        user=user,
        calendar=calendar,
        toggle_descriptions=session["toggleDescriptions"],
    )


@main.route("/toggle_descriptions")
def toggle_descriptions() -> Response:
    """Toggle the descriptions on or off and save the state in the session."""
    session["toggleDescriptions"] = not session.get("toggleDescriptions", False)
    return redirect(url_for("main.index"))


@main.route("/login", methods=["GET", "POST"])
def login() -> Response | str:
    """Render the login page."""
    if request.method == "GET":
        if request.args.get("verify_email"):
            flash(
                "Se ha enviado un correo de verificación."
                " Por favor, verifica tu correo electrónico e inicia sesión de nuevo.",
                "info",
            )
        if request.args.get("logged_out"):
            flash("Has cerrado sesión.", "info")
        error = request.args.get("error")
        if error and isinstance(error, str):
            flash(error, "danger")
        return render_template("login.html")

    try:
        firebase_data = verify_id_token(request.form["idToken"])
        email = firebase_data["email"]
        session["firebase_uid"] = firebase_data["uid"]
    except ValueError:
        logger.exception(
            "Error verifying ID token %s",
            request.form["idToken"],
        )
        return redirect(url_for("main.logout", error="Autenticación fallida"))

    user = ATC.query.filter_by(email=email).first()
    if not user:
        # If the user database is empty we assume the first user is an admin.
        if not ATC.query.all():
            logger.info(
                "No hay usuarios en la base de datos."
                " Se asume que el primer usuario es un administrador.",
            )
            user = ATC(
                apellidos_nombre="Admin User",
                email=email,
                nombre="Admin",
                apellidos="User",
                categoria="Admin",
                numero_de_licencia=0,
                es_admin=True,
            )
            db.session.add(user)
            db.session.commit()
            session["es_admin"] = True
            flash("Usuario administrador creado.", "success")
            return redirect(url_for("admin.index"))

        logger.error("User not recognized. email=%s", email)
        return redirect(
            url_for(
                "main.logout",
                error="Usuario no reconocido. Hable con el administrador.",
            ),
        )

    session["id_atc"] = user.id
    logger.info(
        "User %s logged in. email=%s",
        user.nombre + " " + user.apellidos,
        email,
    )
    flash("Bienvenido, " + user.nombre + " " + user.apellidos, "success")

    # Check for admin user.
    if user.es_admin:
        session["es_admin"] = True

    # Verificar si el usuario ha aceptado la política de privacidad
    if not user.politica_aceptada:
        return redirect(url_for("main.privacy_policy"))

    return redirect(url_for("main.index"))


@main.route("/logout")
def logout() -> Response:
    """Logout the user."""
    firebase_id_token = session.get("firebase_uid")
    if firebase_id_token:
        with contextlib.suppress(Exception):
            invalidate_token(firebase_id_token)

    session.clear()
    error = request.args.get("error")
    if error:
        return redirect(url_for("main.login", logged_out=True, error=error))
    return redirect(url_for("main.login", logged_out=True))


@main.route("/privacy_policy", methods=["GET", "POST"])
def privacy_policy() -> Response | str:
    """Render the privacy policy page and handle acceptance."""
    if request.method == "POST":
        if "accept_policy" in request.form:
            user = db.session.get(ATC, session["id_atc"])
            if user:
                user.politica_aceptada = True
                db.session.commit()
                return redirect(url_for("main.index"))
        flash("Debe aceptar la política de privacidad para continuar.", "danger")

    return render_template("privacy_policy.html")


@main.route("/upload", methods=["GET", "POST"])
@privacy_policy_accepted
@es_admin
def upload() -> Response | str:
    """Upload shift data to the server.

    For GET requests, render the upload page.
    For POST requests, upload the shift data to the server.
    """
    if request.method != "POST":
        return render_template("upload.html")

    files = request.files.getlist("files")

    if not files or any(not file.filename for file in files):
        flash(
            "No se han seleccionado archivos o algunos archivos no tienen nombre",
            "danger",
        )
        return redirect(url_for("main.upload"))

    total = ResultadoProcesadoTurnero()
    for file in files:
        try:
            res = procesa_turnero(
                file,
                db.session,
            )
            total = total.incluye(res)
        except ValueError:
            flash(f"Formato de archivo no válido: {file.filename}", "danger")
            return redirect(url_for("main.upload"))

    plural = "s" if len(files) > 1 else ""
    flash(
        f"Archivo{plural} cargado{plural} con éxito. "
        f"Usuarios reconocidos: {total.n_total_users}, "
        f"turnos agregados: {total.n_created_shifts}",
        "success",
    )
    return redirect(url_for("main.index"))


@main.route("/upload_estadillo", methods=["GET", "POST"])
@privacy_policy_accepted
@es_admin
def upload_estadillo() -> Response | str:
    """Upload estadillo data to the server.

    For GET requests, render the upload page.
    For POST requests, upload the estadillo data to the server.
    """
    if request.method != "POST":
        return render_template("upload_estadillo.html")
    file = request.files["file"]
    if not file.filename:
        flash("No se ha seleccionado un archivo", "danger")
        return redirect(url_for("main.upload_estadillo"))

    try:
        estadillo_db = procesa_estadillo(file, db.session)
        n_controladores = len(estadillo_db.servicios)
        n_periodos = sum(len(atc.periodos) for atc in estadillo_db.atcs)
    except ValueError:
        flash("Formato de archivo no válido", "danger")
        return redirect(url_for("main.upload_estadillo"))

    flash(
        "Archivo cargado con éxito. "
        f"Controladores reconocidos: {n_controladores},"
        f" periodos agregados: {n_periodos}",
        "success",
    )
    return redirect(url_for("main.index"))


@main.route("/estadillo", methods=["GET", "POST"])
@privacy_policy_accepted
def estadillo() -> Response | str:
    """Show the latest estadillo for the logged-in user."""
    if "id_atc" not in session:
        return redirect(url_for("main.login"))

    user = db.session.get(ATC, session["id_atc"])
    if not user:
        return redirect(url_for("main.logout"))

    # Get the latest estadillo for the user
    latest_estadillo = (
        db.session.query(Estadillo)
        .join(Estadillo.atcs)
        .order_by(Estadillo.fecha.desc())
        .first()
    )

    if not latest_estadillo:
        flash("No hay estadillos disponibles.", "info")
        return redirect(url_for("main.index"))

    grupos = genera_datos_estadillo(latest_estadillo, db.session)

    return render_template(
        "estadillo.html",
        grupos=grupos,
    )


@main.route("/admin/user_list")
@es_admin
def admin_user_list() -> Response | str:
    """Render a page with a list of users in a copy-friendly format."""
    filter_by_recognized = (
        request.args.get("filter_recognized", default="false").lower() == "true"
    )

    users_query = ATC.query.order_by(ATC.apellidos_nombre)

    if filter_by_recognized:
        recognized_emails = get_recognized_emails()
        users_query = users_query.filter(ATC.email.in_(recognized_emails))

    users = users_query.all()

    user_list = [
        f"{user.id}, {user.nombre}, {user.apellidos}, "
        f"{user.apellidos_nombre}, {user.email}"
        for user in users
    ]

    return render_template("admin_user_list.html", user_list=user_list)


@main.route("/admin/update_users", methods=["POST"])
@es_admin
def admin_update_users() -> Response:
    """Update users in the database based on provided corrected data."""
    corrected_data = request.form.get("corrected_data")
    if not corrected_data:
        flash("No data provided", "danger")
        return redirect(url_for("main.admin_user_list"))

    try:
        updated_users = 0
        for line in corrected_data.splitlines():
            try:
                user_id, nombre, apellidos, _, email = line.split(",")
            except ValueError:
                flash(f"valores inválidos en: {line}", "danger")
                logger.warning("Vaores inválidos en: %s", line)
                continue
            user = ATC.query.get(user_id)
            if user:
                user.nombre = nombre.strip()
                user.apellidos = apellidos.strip()
                user.email = email.strip()
                db.session.commit()
                updated_users += 1

        flash(f"Successfully updated {updated_users} users", "success")
    except IntegrityError as e:
        flash(f"Error updating users: {e}", "danger")

    return redirect(url_for("main.admin_user_list"))


def register_routes(app: Flask) -> Blueprint:
    """Register the routes with the app."""
    app.register_blueprint(main)
    return main
