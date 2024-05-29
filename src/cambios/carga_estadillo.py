"""Procesa la carga del archivo de estadillo diario.

procesa_estadillo es la función principal que procesa el archivo de estadillo diario.
Extrae los datos del estadillo del archivo, analiza los datos e inserta los datos
en la base de datos. La función utiliza la función extraer_datos_estadillo para
extraer los datos del estadillo de cada página del archivo cargado. Los datos
extraídos se analizan utilizando la función parse_and_insert_data, que inserta
los datos en la base de datos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from logging import getLogger
from typing import TYPE_CHECKING

import pdfplumber

from .models import EstadilloDiario
from .utils import create_user, find_user, update_user

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import scoped_session

logger = getLogger(__name__)


@dataclass
class Controller:
    """Text data for controllers extracted from the first page of the daily shift."""

    name: str
    role: str
    sectors: set[str] = field(default_factory=set)
    comments: str = ""


@dataclass
class DatosEstadilloTexto:
    """Datos en texto extraídos de la primera página del estadillo."""

    dependencia: str = ""
    fecha: str = ""
    turno: str = ""
    jefes_de_sala: list[str] = field(default_factory=list)
    supervisores: list[str] = field(default_factory=list)
    tcas: list[str] = field(default_factory=list)
    controladores: dict[str, Controller] = field(default_factory=dict)
    """Diccionario de controladores extraídos de la primera página del turno diario.
    
    La clave es el nombre del controlador."""
    sectores: set[str] = field(default_factory=set)


def extraer_datos_estadillo(page: pdfplumber.page.Page) -> DatosEstadilloTexto:
    """Extraer los datos del la primera página del estadillo.

    Principalmente las personas que trabajan y los sectores en los que trabajan.
    """
    table = page.extract_table()
    if table is None:
        return DatosEstadilloTexto()

    data = DatosEstadilloTexto()

    # Extract dependencia, fecha, and turno from the first row
    header = table[0][0].split()  # type: ignore[union-attr]
    data.dependencia = header[0]
    data.fecha = header[1]
    data.turno = header[2]

    for row in table:
        if row[0] == "JEFES DE SALA":
            data.jefes_de_sala = [
                item  # type: ignore[misc]
                for item in row
                if item not in (None, "JEFES DE SALA")
            ]
        elif row[0] == "SUPERVISORES":
            data.supervisores = [
                item  # type: ignore[misc]
                for item in row
                if item not in (None, "SUPERVISORES")
            ]
        elif row[0] == "TCA":
            data.tcas = [
                item  # type: ignore[misc]
                for item in row
                if item not in (None, "TCA")
            ]
        elif row[1] and row[1].startswith("C"):
            controller_name = row[2]
            controller_role = row[3]
            if not controller_name:
                continue
            controller = Controller(
                name=controller_name,
                role=controller_role,  # type: ignore[arg-type]
            )
            data.controladores[controller_name] = controller
            sectors = [row[5], row[6], row[7]]
            for sector in sectors:
                if sector:
                    data.sectores.add(sector)
                    controller.sectors.add(sector)
            controller.comments = row[8] if row[8] else ""

    return data


def guardar_datos_estadillo(
    data: DatosEstadilloTexto,
    db_session: scoped_session,
) -> None:
    """Guardar los datos generales del estadillo en la base de datos."""
    logger.info("Saving shift data to the database")
    # 27.05.2024 to python date
    date = datetime.strptime(data.fecha, "%d.%m.%Y")  # noqa: DTZ007

    control_room_shift = EstadilloDiario(
        fecha=date,
        dependencia=data.dependencia,
        turno=data.turno,
    )
    db_session.add(control_room_shift)

    for nombre_jefe_de_sala in data.jefes_de_sala:
        if find_user(nombre_jefe_de_sala, db_session):
            continue
        create_user(nombre_jefe_de_sala, "JDS", None, db_session)

    for nombre_supervisor in data.supervisores:
        if find_user(nombre_supervisor, db_session):
            continue
        create_user(nombre_supervisor, "SUP", None, db_session)

    for nombre_tca in data.tcas:
        if find_user(nombre_tca, db_session):
            continue
        create_user(nombre_tca, "TCA", None, db_session)

    for nombre_controlador, controller in data.controladores.items():
        if user := find_user(nombre_controlador, db_session):
            update_user(user, controller.role, None)
        create_user(
            nombre_controlador,
            controller.role,
            None,
            db_session,
        )

    logger.info("Shift data saved to the database")
