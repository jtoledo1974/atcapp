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

from .models import Estadillo, Sector
from .utils import create_user, find_user, update_user

if TYPE_CHECKING:  # pragma: no cover
    import pdfplumber
    from sqlalchemy.orm import scoped_session
    from sqlalchemy.orm.collections import InstrumentedList

    from .models import ATC


logger = getLogger(__name__)


@dataclass
class PeriodosTexto:
    """Datos en texto de todos los periodos presentes en el estadillo."""

    hora_inicio: str
    """Hora en format HH:MM."""
    funcion: str
    """Tarea y sector, por ejemplo "E-ASV"."""


@dataclass
class Controller:
    """Datos de un controlador extraídos de la primera página del estadillo."""

    nombre: str
    puesto: str
    """Puesto del controlador, como aparece en el estadillo (CON, PTD, IS, etc.)."""
    sectores: set[str] = field(default_factory=set)
    """Conjunto de sectores en los que trabaja el controlador en un turno."""
    comentarios: str = ""
    """Comentarios adicionales. Puede ser el instruyendo."""
    periodos: list[PeriodosTexto] = field(default_factory=list)
    """Lista de periodos en los que trabaja el controlador en un turno."""


@dataclass
class EstadilloTexto:
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


def extraer_datos_estadillo(page: pdfplumber.page.Page) -> EstadilloTexto:
    """Extraer los datos del la primera página del estadillo.

    Principalmente las personas que trabajan y los sectores en los que trabajan.
    """
    table = page.extract_table()
    if table is None:
        return EstadilloTexto()

    data = EstadilloTexto()

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
                nombre=controller_name,
                puesto=controller_role,  # type: ignore[arg-type]
            )
            data.controladores[controller_name] = controller
            sectors = [row[5], row[6], row[7]]
            for sector in sectors:
                if sector:
                    data.sectores.add(sector)
                    controller.sectores.add(sector)
            controller.comentarios = row[8] if row[8] else ""

    return data


def extraer_periodos_de_tabla(
    table: list[list[str | None]],
) -> dict[str, list[PeriodosTexto]]:
    """Extraer los periodos de los controladores de una tabla."""
    # Cada tabla tiene dos filas por controlador con este formato:
    # 'CASTILLO RUIZ\nM PILAR', 'P-ASN', 'E-ASN', '', 'P-ASN', 'E-ASN'
    # None, '07:30', '08:20', '09:10', '10:00', '10:50
    # Donde la primera fila tiene el nombre del controlador y los sectores
    # donde trabaja, o en blanco donde descansa
    # La segunda fila tiene en la primera celda None, y en las siguientes
    # las horas de inicio de cada periodo

    periodos: dict[str, list[PeriodosTexto]] = {}

    for i in range(0, len(table), 2):
        row_controlador = table[i]
        row_horas = table[i + 1]

        if not row_controlador[0]:
            continue
        nombre_controlador = row_controlador[0].replace("\n", " ")
        periodos_controlador = []

        for j in range(1, len(row_controlador)):
            funcion = row_controlador[j]
            hora_inicio = row_horas[j]

            if funcion and hora_inicio:
                periodos_controlador.append(
                    PeriodosTexto(hora_inicio=hora_inicio, funcion=funcion),
                )
            elif hora_inicio:
                periodos_controlador.append(
                    PeriodosTexto(hora_inicio=hora_inicio, funcion="DESCANSO"),
                )

        periodos[nombre_controlador] = periodos_controlador

    return periodos


def extraer_periodos(page: pdfplumber.page.Page) -> dict[str, list[PeriodosTexto]]:
    """Extraer los periodos de los controladores de la segunda página del estadillo.

    La clave es el nombre del controlador.
    """
    tables = page.extract_tables()
    if tables is None:
        return {}

    periodos = {}
    for table in tables:
        data = extraer_periodos_de_tabla(table)
        periodos.update(data)

    return periodos


def guardar_datos_estadillo(  # noqa: C901
    data: EstadilloTexto,
    db_session: scoped_session,
) -> None:
    """Guardar los datos generales del estadillo en la base de datos."""
    logger.info("Saving shift data to the database")
    # 27.05.2024 to python date
    date = datetime.strptime(data.fecha, "%d.%m.%Y")  # noqa: DTZ007

    estadillo = Estadillo(
        fecha=date,
        dependencia=data.dependencia,
        turno=data.turno,
    )
    db_session.add(estadillo)

    def procesar_atc(
        name: str,
        role: str,
        relationship_list: InstrumentedList | list,
    ) -> ATC:
        """Procesar un ATC y añadirlo a la lista de relación si no está ya."""
        user = find_user(name, db_session)
        if not user:
            user = create_user(name, role, None, db_session)
        if user not in relationship_list:
            relationship_list.append(user)
        return user

    # Procesar jefes de sala
    for nombre_jefe_de_sala in data.jefes_de_sala:
        procesar_atc(nombre_jefe_de_sala, "JDS", estadillo.jefes)

    # Procesar supervisores
    for nombre_supervisor in data.supervisores:
        procesar_atc(nombre_supervisor, "SUP", estadillo.supervisores)

    # Procesar TCAs
    for nombre_tca in data.tcas:
        procesar_atc(nombre_tca, "TCA", estadillo.tcas)

    # Procesar controladores y sus sectores
    for nombre_controlador, controller in data.controladores.items():
        user = procesar_atc(nombre_controlador, controller.puesto, [])
        update_user(user, controller.puesto, None)

        for sector_name in controller.sectores:
            sector = db_session.query(Sector).filter_by(nombre=sector_name).first()
            if not sector:
                sector = Sector(nombre=sector_name)
                db_session.add(sector)
            if sector not in estadillo.sectores:
                estadillo.sectores.append(sector)

    logger.info("Shift data saved to the database")
    db_session.commit()
