"""Database models for the application."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TCH003. Por el mapping.
from typing import TYPE_CHECKING

import pytz
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.decl_api import DeclarativeBase
from sqlalchemy.schema import MetaData

from . import get_timezone

if TYPE_CHECKING:
    from typing import ClassVar

    from sqlalchemy.orm import Query

# Naming conventions for Alembic migrations
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)

UTC = pytz.utc


# Define a base using the declarative base
class Base(DeclarativeBase):
    """Base class for declarative models."""

    metadata = metadata
    query: ClassVar[Query]


sectores_estadillo = Table(
    "sectores_estadillo",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("id_sector", Integer, ForeignKey("sectores.id"), nullable=False),
    Column("id_estadillo", Integer, ForeignKey("estadillos.id"), nullable=False),
)


class ATC(Base):
    """Modelo de la tabla controladores."""

    __tablename__ = "atcs"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    apellidos_nombre: Mapped[str] = mapped_column(
        String(70),
        unique=True,
        nullable=False,
    )
    """Nombre completo del controlador según lo presenta enaire."""
    nombre: Mapped[str] = mapped_column(String(40), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(40), nullable=False)
    dependencia: Mapped[str] = mapped_column(String(4), nullable=False)
    """Unidad a la que pertenece el controlador. LECS, LECM, etc."""
    categoria: Mapped[str] = mapped_column(String(50), nullable=True)
    """Categoría del controlador. PTD, CON, TIN, etc."""
    equipo: Mapped[str | None] = mapped_column(String(1), nullable=True)
    """Equipo al que pertenece el controlador. Típicamente del A al H."""
    numero_de_licencia: Mapped[str] = mapped_column(String(50), nullable=True)
    es_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    politica_aceptada: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (Index("idx_apellidos_nombre", "apellidos_nombre"),)

    servicios: Mapped[list[Servicio]] = relationship("Servicio", back_populates="atc")
    estadillos: Mapped[list[Estadillo]] = relationship(
        "Estadillo",
        secondary="servicios",
        back_populates="atcs",
        overlaps="servicios",
    )
    periodos: Mapped[list[Periodo]] = relationship(
        "Periodo",
        back_populates="controlador",
    )

    @property
    def nombre_apellidos(self) -> str:
        """Nombre completo del controlador capitalizado correctamente."""
        return f"{self.nombre} {self.apellidos}"

    def __repr__(self) -> str:
        """Representación de un controlador."""
        return f"<ATC {self.apellidos_nombre}>"


class Turno(Base):
    """Turnos son los publicados en el turnero mensual y actualizados con cambios.

    Se distinguen de los servicios porque esos son los que se utilizan para
    asociar a los controladores con el estadillo diario.
    """

    __tablename__ = "turnos"
    __table_args__ = (UniqueConstraint("fecha", "id_atc"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    turno: Mapped[str] = mapped_column(String(10), nullable=False)
    id_atc: Mapped[int] = mapped_column(Integer, ForeignKey("atcs.id"), nullable=False)

    atc: Mapped[ATC] = relationship("ATC", backref="turnos")


class TipoTurno(Base):
    """Modelo de la tabla "tipos_de_turno."""

    __tablename__ = "tipos_de_turno"

    codigo: Mapped[str] = mapped_column(String(10), primary_key=True, nullable=False)
    descripcion: Mapped[str] = mapped_column(String(50), nullable=False)


class Estadillo(Base):
    """Modelo de la tabla estadillos.

    Datos generales del estadillo diario:
    Fecha, Unidad, Tipo de turno (M, T, N).
    """

    __tablename__ = "estadillos"
    __table_args__ = (UniqueConstraint("fecha", "dependencia", "turno"),)

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
    servicios: Mapped[list[Servicio]] = relationship(
        "Servicio",
        back_populates="estadillo",
        cascade="all, delete-orphan",
    )
    sectores: Mapped[list[Sector]] = relationship(
        "Sector",
        secondary=sectores_estadillo,
        back_populates="estadillos",
    )
    periodos: Mapped[list[Periodo]] = relationship(
        "Periodo",
        back_populates="turno_sala_control",
        cascade="all, delete-orphan",
    )

    @property
    def hora_inicio(self) -> datetime:
        """Hora de inicio del estadillo."""
        hora_min = min(periodo.hora_inicio for periodo in self.periodos)
        return hora_min.astimezone(get_timezone())

    @property
    def hora_fin(self) -> datetime:
        """Hora de fin del estadillo."""
        hora_max = max(periodo.hora_fin for periodo in self.periodos)
        return hora_max.astimezone(get_timezone())


class Sector(Base):
    """Modelo de la tabla sectores."""

    __tablename__ = "sectores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(20), nullable=False)

    estadillos: Mapped[list[Estadillo]] = relationship(
        "Estadillo",
        secondary=sectores_estadillo,
        back_populates="sectores",
    )

    def __repr__(self) -> str:
        """Representación de un sector."""
        return f"<Sector {self.nombre}>"


class Periodo(Base):
    """Modelo de la tabla periodos.

    Periodos es cada uno de los tramos en que un controlador
    ejecuta una única tarea en un sector. Esto es, el tiempo
    que está de ejecutivo en un sector o de plani en otro.
    """

    __tablename__ = "periodos"
    __table_args__ = (UniqueConstraint("id_controlador", "hora_inicio"),)

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
        nullable=True,
    )
    """Sector en el que se realiza la actividad. Puede ser nulo en caso de descanso."""
    hora_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    """Hora de inicio del periodo en la zona horaria del controlador.
    
    Ni SQLite ni Mariadb tratan zonas horarias. Así que no nos fiamos
    y utilizamos la propiedad hora_inicio_utc para asegurarnos de que
    estamos trabajando con horas en UTC.
    """
    hora_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    """Hora de fin del periodo en la zona horaria del controlador.
    
    Ni SQLite ni Mariadb tratan zonas horarias. Así que no nos fiamos
    y utilizamos la propiedad hora_fin_utc para asegurarnos de que
    estamos trabajando con horas en UTC.
    """

    actividad: Mapped[str] = mapped_column(String(20), nullable=False)
    """E, P o D: ejecutivo, planificador o descanso."""

    controlador: Mapped[ATC] = relationship("ATC", back_populates="periodos")
    turno_sala_control: Mapped[Estadillo] = relationship(
        "Estadillo",
        back_populates="periodos",
    )
    sector: Mapped[Sector] = relationship("Sector", backref="periodos")

    @property
    def hora_inicio_utc(self) -> datetime:
        """Hora de inicio del periodo en UTC.

        La hora de inicio guardada debería ser bien UTC o bien
        naif en UTC. Nos aseguramos que en ambos casos
        devolvemos una hora en UTC.
        """
        if self.hora_inicio.tzinfo is None:
            return UTC.localize(self.hora_inicio)
        return self.hora_inicio.astimezone(UTC)

    @property
    def hora_fin_utc(self) -> datetime:
        """Hora de fin del periodo en UTC.

        La hora de fin guardada debería ser bien UTC o bien
        naif en UTC. Nos aseguramos que en ambos casos
        devolvemos una hora en UTC.
        """
        if self.hora_fin.tzinfo is None:
            return UTC.localize(self.hora_fin)
        return self.hora_fin.astimezone(UTC)

    @property
    def duracion(self) -> int:
        """Duración del periodo en minutos."""
        return (self.hora_fin - self.hora_inicio).seconds // 60

    def __repr__(self) -> str:
        """Representación de un periodo."""
        return f"<Per. {self.hora_inicio.strftime('%H:%M')} {self.duracion}'>"


class Servicio(Base):
    """Modelo intermedio para gestionar la relación entre ATC y Estadillo.

    Un concepto similar es el de Turno, pero usaremos servicios para
    referirnos a aquellos para los que hay estadillo, y turnos como
    cualquier otro trabajo que pueda realizar un controlador,
    incluyendo los servicios de sala.
    """

    __tablename__ = "servicios"
    __table_args__ = (UniqueConstraint("id_atc", "id_estadillo"),)

    __mapper_args__ = {"confirm_deleted_rows": False}  # noqa: RUF012 Creo que es FP

    id: Mapped[int] = mapped_column(primary_key=True)
    id_atc: Mapped[int] = mapped_column(Integer, ForeignKey("atcs.id"), nullable=False)
    id_estadillo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("estadillos.id"),
        nullable=False,
    )
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)
    """Puesto que ejerce un controlador en un servicio: CON, PTD, IS, TIN, etc."""
    rol: Mapped[str] = mapped_column(String(50), nullable=False)
    """Rol de ATC para un servicio: Controlador, Jefe de Sala, Supervicsor, TCA."""

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
