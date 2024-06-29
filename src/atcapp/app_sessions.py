"""Módulo para definir el modelo de la sesión de Flask."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from flask.sessions import SessionInterface, SessionMixin
from sqlalchemy import TIMESTAMP, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from werkzeug.datastructures import CallbackDict

from .database import db
from .models import Base

if TYPE_CHECKING:
    from flask import Flask, Request, Response

logger = logging.getLogger(__name__)

ID_ATC = "id_atc"


class Session(Base):
    """Modelo SQLAlchemy para representar las sesiones de Flask."""

    __tablename__ = "sessions"
    __table_args__ = (Index("idx_created_at", "created_at"),)
    id: Mapped[int] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        default=datetime.now(timezone.utc),
    )

    def __init__(self, session_id: str, data: str) -> None:
        """Inicializa una nueva sesión."""
        self.session_id = session_id
        self.data = data


class SqlAlchemySession(CallbackDict, SessionMixin):
    """Clase de sesión personalizada para almacenar datos de sesión."""

    def __init__(
        self,
        initial: dict | None = None,
        sid: str | None = None,
        *,
        new: bool = False,
    ) -> None:
        """Inicializa una nueva sesión."""
        super().__init__(initial)
        self.sid = sid
        self.new = new
        self.modified = False


class SqlAlchemySessionInterface(SessionInterface):
    """Interfaz de sesión que utiliza SQLAlchemy para almacenar datos de sesión."""

    def __init__(
        self,
        session_class: type[SqlAlchemySession] = SqlAlchemySession,
    ) -> None:
        """Inicializa la interfaz de sesión."""
        self.session_class = session_class

    def open_session(self, app: Flask, request: Request) -> SqlAlchemySession:
        """Abre una sesión existente o crea una nueva si no existe.

        :param app: La aplicación Flask.
        :param request: La solicitud HTTP.
        :return: Una instancia de SqlAlchemySession.
        """
        cookie_name = app.config["SESSION_COOKIE_NAME"]
        db_session = db.session
        session_id = request.cookies.get(cookie_name)
        logger.debug("Opening session. Request %s. Session id: %s", request, session_id)

        if session_id:
            stored_session = (
                db_session.query(Session).filter_by(session_id=session_id).first()
            )
            if stored_session:
                data = json.loads(stored_session.data)
                return self.session_class(data, sid=session_id)
        sid = str(uuid.uuid4())
        return self.session_class(sid=sid, new=True)

    def save_session(
        self,
        app: Flask,
        session: SqlAlchemySession,  # type: ignore[override]
        response: Response,
    ) -> None:
        """Guarda la sesión actual en la base de datos.

        :param app: La aplicación Flask.
        :param session: La sesión actual.
        :param response: La respuesta HTTP.
        """
        logger.debug("Saving session %s. Response %s", session, response)
        cookie_name = app.config["SESSION_COOKIE_NAME"]
        domain = self.get_cookie_domain(app)
        if not session or not session.sid:
            response.delete_cookie(cookie_name, domain=domain)
            return
        cookie_exp = self.get_expiration_time(app, session)
        session_data = json.dumps(dict(session))
        db_session = db.session
        stored_session = (
            db_session.query(Session).filter_by(session_id=session.sid).first()
        )
        logger.debug("Stored session: %s", stored_session)
        if stored_session:
            stored_session.data = session_data
        elif ID_ATC in session_data:
            stored_session = Session(session_id=session.sid, data=session_data)
            db_session.add(stored_session)
        db_session.commit()
        response.set_cookie(
            cookie_name,
            session.sid,
            expires=cookie_exp,
            httponly=True,
            domain=domain,
        )
