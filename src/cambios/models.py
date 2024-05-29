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
    """Tipo de turno: M, T, N."""


class Sector(db.Model):  # type: ignore[name-defined]
    """Modelo de la tabla sectores."""

    __tablename__ = "sectores"
    id = Column(Integer, primary_key=True)
    nombre: str = Column(String(20), nullable=False)  # type: ignore[assignment]


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


# Relaciones de muchos a muchos entre tablas

atcs_estadillos = Table(
    "atcs_estadillos",
    db.Model.metadata,
    Column("id_estadillo", Integer, ForeignKey("estadillos.id")),
    Column("id_atc", Integer, ForeignKey("atcs.id")),
)

jefes_estadillos = Table(
    "jefes_estadillos",
    db.Model.metadata,
    Column("id_estadillo", Integer, ForeignKey("estadillos.id")),
    Column("id_atc", Integer, ForeignKey("atcs.id")),
)

supervisores_estadillos = Table(
    "supervisores_estadillos",
    db.Model.metadata,
    Column("id_estadillo", Integer, ForeignKey("estadillos.id")),
    Column("id_atc", Integer, ForeignKey("atcs.id")),
)

tcas_estadillos = Table(
    "tcas_estadillos",
    db.Model.metadata,
    Column("id_estadillo", Integer, ForeignKey("estadillos.id")),
    Column("id_atc", Integer, ForeignKey("atcs.id")),
)

sectores_estadillos = Table(
    "sectores_estadillos",
    db.Model.metadata,
    Column("id_estadillo", Integer, ForeignKey("estadillos.id")),
    Column("id_sector", Integer, ForeignKey("sectores.id")),
)

# Actualizar relaciones en los modelos
Estadillo.atcs = relationship(
    "ATC",
    secondary=atcs_estadillos,
    backref="servicios",
)

Estadillo.jefes = relationship(
    "ATC",
    secondary=jefes_estadillos,
    backref="servicios_de_jefe",
)
Estadillo.supervisores = relationship(
    "ATC",
    secondary=supervisores_estadillos,
    backref="servicios_de_supervisor",
)
Estadillo.tcas = relationship(
    "ATC",
    secondary=tcas_estadillos,
    backref="servicios_de_tca",
)
Estadillo.sectores = relationship(
    "Sector",
    secondary=sectores_estadillos,
    backref="estadillos",
)
