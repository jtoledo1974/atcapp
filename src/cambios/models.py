"""Database models for the application."""

from __future__ import annotations

from datetime import date, time  # noqa: TCH003  # Necesario para el mapping

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Table,
    Time,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import db

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

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(100), nullable=False)
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)
    equipo: Mapped[str | None] = mapped_column(String(1), nullable=True)
    numero_de_licencia: Mapped[str] = mapped_column(String(50), nullable=False)
    es_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    politica_aceptada: Mapped[bool] = mapped_column(Boolean, default=False)

    servicios: Mapped[list[Servicio]] = relationship("Servicio", back_populates="atc")
    estadillos: Mapped[list[Estadillo]] = relationship(
        "Estadillo",
        secondary="servicios",
        back_populates="atcs",
        overlaps="servicios",
    )
    periodos: Mapped[list[Periodo]] = relationship("Periodo", back_populates="controlador")

    @property
    def apellidos_nombre(self) -> str:
        """Nombre completo del controlador."""
        return f"{self.apellidos} {self.nombre}"


class Turno(db.Model):  # type: ignore[name-defined]
    """Modelo de la tabla Turno."""

    __tablename__ = "turnos"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    turno: Mapped[str] = mapped_column(String(10), nullable=False)
    id_atc: Mapped[int] = mapped_column(Integer, ForeignKey("atcs.id"), nullable=False)

    atc: Mapped[ATC] = relationship("ATC", backref="turnos")


class TipoTurno(db.Model):  # type: ignore[name-defined]
    """Modelo de la tabla "tipos_de_turno."""

    __tablename__ = "tipos_de_turno"

    codigo: Mapped[str] = mapped_column(String(10), primary_key=True, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(50), nullable=False)


class Estadillo(db.Model):  # type: ignore[name-defined]
    """Modelo de la tabla estadillos.

    Datos generales del estadillo diario:
    Fecha, Unidad, Tipo de turno (M, T, N).
    """

    __tablename__ = "estadillos"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    dependencia: Mapped[str] = mapped_column(String(4), nullable=False)
    turno: Mapped[str] = mapped_column(String(1), nullable=False)

    atcs: Mapped[list[ATC]] = relationship(
        "ATC",
        secondary="servicios",
        back_populates="estadillos",
        overlaps="servicios",
    )
    servicios: Mapped[list[Servicio]] = relationship("Servicio", back_populates="estadillo")
    sectores: Mapped[list[Sector]] = relationship(
        "Sector",
        secondary=sectores_estadillo,
        back_populates="estadillos",
    )


class Sector(db.Model):  # type: ignore[name-defined]
    """Modelo de la tabla sectores."""

    __tablename__ = "sectores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(20), nullable=False)

    estadillos: Mapped[list[Estadillo]] = relationship(
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

    id: Mapped[int] = mapped_column(primary_key=True)
    id_controlador: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("atcs.id"),
        nullable=False,
    )
    id_estadillo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("estadillos.id"),
        nullable=False,
    )
    id_sector: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sectores.id"),
        nullable=False,
    )
    hora_inicio: Mapped[time] = mapped_column(Time, nullable=False)
    hora_fin: Mapped[time] = mapped_column(Time, nullable=False)
    actividad: Mapped[str] = mapped_column(String(20), nullable=False)

    controlador: Mapped[ATC] = relationship("ATC", back_populates="periodos")
    turno_sala_control: Mapped[Estadillo] = relationship("Estadillo", backref="periodos")
    sector: Mapped[Sector] = relationship("Sector", backref="periodos")


class Servicio(db.Model):  # type: ignore[name-defined]
    """Modelo intermedio para gestionar la relación entre ATC y Estadillo."""

    __tablename__ = "servicios"

    id: Mapped[int] = mapped_column(primary_key=True)
    id_atc: Mapped[int] = mapped_column(Integer, ForeignKey("atcs.id"), nullable=False)
    id_estadillo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("estadillos.id"),
        nullable=False,
    )
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)
    rol: Mapped[str] = mapped_column(String(50), nullable=False)

    atc: Mapped[ATC] = relationship(
        "ATC",
        back_populates="servicios",
        overlaps="atcs,estadillos",
    )
    estadillo: Mapped[Estadillo] = relationship(
        "Estadillo",
        back_populates="servicios",
        overlaps="atcs,estadillos",
    )
