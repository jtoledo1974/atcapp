"""Database models for the application."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TCH003  # Necesario para el mapping
from enum import Enum
from typing import TYPE_CHECKING

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
from sqlalchemy import (
    Enum as EnumType,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm.decl_api import DeclarativeBase
from sqlalchemy.schema import MetaData

from . import get_timezone

if TYPE_CHECKING:
    from typing import ClassVar

    from sqlalchemy.orm import Query

class TipoFuente(Enum):
    """Enum para indicar el tipo de fuente de un turno."""

    TURNERO = "turnero"
    MANUAL = "manual"
    OTRO = "otro"


# Naming conventions for Alembic migrations
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)


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
    categoria: Mapped[str] = mapped_column(String(50), nullable=False)
    equipo: Mapped[str | None] = mapped_column(String(1), nullable=True)
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
    archivos: Mapped[list[Archivo]] = relationship("Archivo", back_populates="atc")
    """Archivos subidos por el controlador."""

    cambios_manuales: Mapped[list[TurnoManual]] = relationship(
        "TurnoManual",
        back_populates="atc",
    )
    """Cambios de turno manuales realizados por el controlador."""

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
    """Código del turno: p.ej. MB09 ."""
    id_atc: Mapped[int] = mapped_column(Integer, ForeignKey("atcs.id"), nullable=False)
    tipo_fuente: Mapped[TipoFuente] = mapped_column(
        EnumType(TipoFuente),
        nullable=False,
    )
    """Tipo de fuente del turno (turnero, manual, otro)."""

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
    hora_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actividad: Mapped[str] = mapped_column(String(20), nullable=False)
    """E, P o D: ejecutivo, planificador o descanso."""

    controlador: Mapped[ATC] = relationship("ATC", back_populates="periodos")
    turno_sala_control: Mapped[Estadillo] = relationship(
        "Estadillo",
        back_populates="periodos",
    )
    sector: Mapped[Sector] = relationship("Sector", backref="periodos")

    @property
    def hora_inicio_tz(self) -> datetime:
        """Hora de inicio del periodo en la zona horaria del controlador."""
        return self.hora_inicio.astimezone(get_timezone())

    @property
    def hora_fin_tz(self) -> datetime:
        """Hora de fin del periodo en la zona horaria del controlador."""
        return self.hora_fin.astimezone(get_timezone())

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


class Archivo(db.Model):  # type: ignore[name-defined]
    """Tabla para almacenar información general sobre archivos subidos.

    La tabla Archivo se utiliza para mantener un registro de todos los archivos
    que se suben al sistema, independientemente de su tipo. Esto incluye turneros,
    estadillos y otros tipos de archivos que    puedan ser introducidos en el futuro.
    Cada registro contiene metadatos sobre el archivo subido, como su hash para evitar
    duplicados, la URI para su localización, el tipo de archivo y la información
    del usuario que lo subió.
    """

    __tablename__ = "archivos"

    id: Mapped[int] = mapped_column(primary_key=True)
    """Identificador único del archivo."""

    hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    """Hash del archivo para identificar duplicados."""

    uri: Mapped[str] = mapped_column(String(256), nullable=False)
    """URI del archivo (local o en la nube)."""

    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    """Tipo de archivo (turnero, estadillo, etc.)."""

    fecha_subida: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    """Fecha y hora de la subida del archivo."""

    id_atc: Mapped[int] = mapped_column(Integer, ForeignKey("atcs.id"), nullable=False)
    """Identificador del ATC que subió el archivo."""

    nombre_apellidos_subidor: Mapped[str] = mapped_column(String(80), nullable=False)
    """Nombre y apellidos del ATC que subió el archivo en el momento de la subida."""

    atc: Mapped[ATC] = relationship("ATC", back_populates="archivos")

    __table_args__ = (UniqueConstraint("hash"),)


class Turnero(db.Model):  # type: ignore[name-defined]
    """Tabla para almacenar metadatos específicos de archivos de turnero.

    La tabla Turnero se utiliza para guardar información específica sobre los
    archivos de turnero que se suben al sistema. Cada registro de turnero está
    asociado a un archivo en la tabla Archivo y contiene detalles adicionales como
    el año y el mes del turnero, así como la dependencia correspondiente. Esto
    permite una mejor organización y búsqueda de los turneros subidos.

    """

    __tablename__ = "turneros"

    id: Mapped[int] = mapped_column(primary_key=True)
    """Identificador único del turnero."""

    id_archivo: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("archivos.id"),
        nullable=False,
    )
    """Identificador del archivo relacionado."""

    year: Mapped[int] = mapped_column(Integer, nullable=False)
    """Año del turnero."""

    month: Mapped[int] = mapped_column(Integer, nullable=False)
    """Mes del turnero."""

    dependencia: Mapped[str] = mapped_column(String(4), nullable=False)
    """Dependencia a la que pertenece el turnero."""

    archivo: Mapped[Archivo] = relationship("Archivo", back_populates="turnero")


class TurnoTurnero(db.Model):  # type: ignore[name-defined]
    """Tabla intermedia para asociar turnos con archivos de turnero.

    Esta tabla se utiliza para mantener una relación entre los turnos y los
    archivos de turnero que los originaron. Cada registro en esta tabla indica
    que un turno específico proviene de un archivo de turnero particular.

    """

    __tablename__ = "turnos_turneros"

    id: Mapped[int] = mapped_column(primary_key=True)
    """Identificador único de la relación."""

    id_turno: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("turnos.id"),
        nullable=False,
    )
    """Identificador del turno."""

    id_turnero: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("turneros.id"),
        nullable=False,
    )
    """Identificador del turnero."""

    turno: Mapped[Turno] = relationship("Turno", backref="turno_turnero")
    turnero: Mapped[Turnero] = relationship("Turnero", backref="turno_turnero")


class TurnoManual(db.Model):  # type: ignore[name-defined]
    """Tabla intermedia para asociar turnos con cambios manuales.

    Esta tabla se utiliza para mantener una relación entre los turnos y los cambios
    manuales realizados por los usuarios. Cada registro en esta tabla indica que
    un turno específico fue modificado manualmente por un usuario en una fecha
    particular.

    """

    __tablename__ = "turnos_manuales"

    id: Mapped[int] = mapped_column(primary_key=True)
    """Identificador único de la relación."""

    id_turno: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("turnos.id"),
        nullable=False,
    )
    """Identificador del turno."""

    fecha_cambio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    """Fecha y hora del cambio manual."""

    id_atc: Mapped[int] = mapped_column(Integer, ForeignKey("atcs.id"), nullable=False)
    """Identificador del ATC que realizó el cambio manual."""

    turno: Mapped[Turno] = relationship("Turno", backref="turno_manual")
    atc: Mapped[ATC] = relationship("ATC", backref="cambios_manuales")
