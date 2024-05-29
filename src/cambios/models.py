"""Database models for the application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Time,
)
from sqlalchemy.orm import relationship

from .database import db

if TYPE_CHECKING:  # pragma: no cover
    from datetime import date, time

# This is a hack due to flask_sqlalchemy seeming incompatible with mypy
# It is explained in https://github.com/pallets-eco/flask-sqlalchemy/issues/1327
# I've tried all approaches and this seems to me the simplest hack
# to get mypy happy.
# We don't get autocomplete for model methods like query, but at least
# we do get type checking of columns.


sectores_estadillo = Table(
    "sectores_estadillo",
    db.Model.metadata,
    Column("id", Integer, primary_key=True),
    Column("id_sector", Integer, ForeignKey("sectores.id"), nullable=False),
    Column("id_estadillo", Integer, ForeignKey("estadillos.id"), nullable=False),
)


class ATC(db.Model):  # type: ignore[name-defined]
    """Modelo de la tabla controladores."""

    __tablename__ = "atcs"
    id = Column(Integer, primary_key=True)
    firebase_uid = Column(String, unique=True)
    email: str = Column(String(80), unique=True, nullable=False)  # type: ignore[assignment]
    nombre: str = Column(String(100), nullable=False)  # type: ignore[assignment]
    apellidos: str = Column(String(100), nullable=False)  # type: ignore[assignment]
    categoria: str = Column(String(50), nullable=False)  # type: ignore[assignment]
    """Categoría profesional: CON, PTD, IS, etc."""
    equipo: str = Column(String(1))  # type: ignore[assignment]
    numero_de_licencia: str = Column(String(50), nullable=False)  # type: ignore[assignment]
    es_admin: bool = Column(Boolean, default=False)  # type: ignore[assignment]
    politica_aceptada: bool = Column(Boolean, default=False)  # type: ignore[assignment]
    """Indica que el usuario ha aceptado la política de privacidad."""

    servicios = relationship("Servicio", back_populates="atc")
    estadillos = relationship(
        "Estadillo",
        secondary="servicios",
        back_populates="atcs",
    )

    @property
    def apellidos_nombre(self) -> str:
        """Nombre completo del controlador."""
        return f"{self.apellidos} {self.nombre}"


class Turno(db.Model):  # type: ignore[name-defined]
    """Modelo de la tabla Turno."""

    __tablename__ = "turnos"
    id = Column(Integer, primary_key=True)
    fecha = Column(DateTime, nullable=False)
    turno: str = Column(String(10), nullable=False)  # type: ignore[assignment]
    """Es el código completo del servicio, como aparece en el turnero mensual.
       Puede ser M,T, o N más o código, o sólo un código."""
    id_atc = Column(Integer, ForeignKey("atcs.id"), nullable=False)
    atc = relationship("ATC", backref="turnos")


class TipoTurno(db.Model):  # type: ignore[name-defined]
    """Modelo de la tabla "tipos_de_turno."""

    __tablename__ = "tipos_de_turno"
    codigo: str = Column(String(10), primary_key=True, nullable=False)  # type: ignore[assignment]
    descripcion: str = Column(String(50), nullable=False)  # type: ignore[assignment]


class Estadillo(db.Model):  # type: ignore[name-defined]
    """Modelo de la tabla estadillos.

    Datos generales del estadillo diario:
    Fecha, Unidad, Tipo de turno (M, T, N).
    """

    __tablename__ = "estadillos"
    id = Column(Integer, primary_key=True)
    fecha: date = Column(DateTime, nullable=False)  # type: ignore[assignment]
    dependencia: str = Column(String(4), nullable=False)  # type: ignore[assignment]
    """Dependencia de control: LECS, LECM, etc."""
    turno: str = Column(
        String(1),
        nullable=False,
    )  # type: ignore[assignment]
    atcs = relationship("ATC", secondary="servicios", back_populates="estadillos")
    servicios = relationship("Servicio", back_populates="estadillo")
    sectores = relationship(
        "Sector",
        secondary=sectores_estadillo,
        back_populates="estadillos",
    )


class Sector(db.Model):  # type: ignore[name-defined]
    """Modelo de la tabla sectores."""

    __tablename__ = "sectores"
    id = Column(Integer, primary_key=True)
    nombre: str = Column(String(20), nullable=False)  # type: ignore[assignment]
    estadillos = relationship(
        "Estadillo",
        secondary=sectores_estadillo,
        back_populates="sectores",
    )


class Periodo(db.Model):  # type: ignore[name-defined]
    """Modelo de la tabla periodos.

    Periodos es cada uno de los tramos en que un controlador
    ejecuta una única tarea en un sector. Esto es, el tiempo
    que está de ejecutivo en un sector o de plani en otro.
    """

    __tablename__ = "periodos"
    id = Column(Integer, primary_key=True)
    id_controlador = Column(Integer, ForeignKey("atcs.id"), nullable=False)
    id_estadillo = Column(
        Integer,
        ForeignKey("estadillos.id"),
        nullable=False,
    )
    id_sector: int = Column(Integer, ForeignKey("sectores.id"), nullable=False)  # type: ignore[assignment]
    hora_inicio: time = Column(Time, nullable=False)  # type: ignore[assignment]
    hora_fin: time = Column(Time, nullable=False)  # type: ignore[assignment]
    actividad = Column(String(20), nullable=False)
    controlador = relationship("ATC", backref="periodos")
    turno_sala_control = relationship("Estadillo", backref="periodos")
    sector = relationship("Sector", backref="periodos")


class Servicio(db.Model):  # type: ignore[name-defined]
    """Modelo intermedio para gestionar la relación entre ATC y Estadillo."""

    __tablename__ = "servicios"
    id = Column(Integer, primary_key=True)
    id_atc = Column(Integer, ForeignKey("atcs.id"), nullable=False)
    id_estadillo = Column(Integer, ForeignKey("estadillos.id"), nullable=False)
    categoria = Column(String(50), nullable=False)
    """Categoría profesional del ATC en el momento del servicio."""
    rol = Column(String(50), nullable=False)
    """Rol del ATC durante el servicio: Controlador, Supervisor, 
    Jefe de Sala, Evaluador, etc."""

    atc = relationship("ATC", back_populates="servicios")
    estadillo = relationship("Estadillo", back_populates="servicios")
