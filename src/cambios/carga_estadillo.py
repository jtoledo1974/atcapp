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
from datetime import date, datetime, timezone
from io import BytesIO
from logging import getLogger
from typing import TYPE_CHECKING

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import scoped_session

from . import get_timezone
from .models import Estadillo, Periodo, Sector, Servicio
from .user_utils import create_user, find_user, update_user

logger = getLogger(__name__)


if TYPE_CHECKING:  # pragma: no cover
    from io import BufferedReader

    import pytz
    from sqlalchemy.orm import scoped_session
    from werkzeug.datastructures import FileStorage

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


def guardar_atc_en_estadillo(
    name: str,
    role: str,
    estadillo: Estadillo,
    categoria: str,
    db_session: scoped_session,
) -> ATC:
    """Incluye a un atc en un estadillo.

    El atc se almacena con su categoría profesional y rol
    en función de la relación que se pase como argumento.

    Si el atc no existe en la base de datos, se crea.
    """
    if not name:
        _msg = "El nombre del controlador no puede estar vacío"
        raise ValueError(_msg)

    user = find_user(name, db_session)
    if not user:
        logger.debug("Controlador %s no encontrado en la base de datos", name)
        user = create_user(name, role, None, db_session)

    servicio = (
        db_session.query(Servicio)
        .filter_by(id_atc=user.id, id_estadillo=estadillo.id)
        .first()
    )
    if not servicio:
        servicio = Servicio(
            id_atc=user.id,
            id_estadillo=estadillo.id,
            categoria=categoria,
            rol=role,
        )
        db_session.add(servicio)
    return user


def extrae_actividad_y_sector(funcion: str) -> tuple[str, str]:
    """Extrae el rol y el sector de una cadena de texto.

    La cadena de texto tiene el formato "P-ASN" o "E-ASN" donde
    "P" es el rol y "ASN" es el sector.
    """
    if funcion == "CAS":
        return "CAS", "CAS"
    res = funcion.split("-")
    if len(res) != 2:  # noqa: PLR2004
        _msg = f"Fallo al extraer actividad y sector de {funcion}"
        logger.error(_msg)
        raise ValueError(_msg)
    return res[0], res[1]


def string_to_utc_datetime(
    time: str,
    fecha: datetime.date,
    tz: pytz.timezone,
) -> datetime:
    """Convierte una cadena HH:MM en un datetime UTC.

    Para ellos se requiere la fecha y la zona horaria.
    """
    naive_dt = datetime.strptime(time, "%H:%M")  # noqa: DTZ007
    naive_dt_date = datetime.combine(fecha, naive_dt.time())
    local_dt = tz.localize(naive_dt_date)  # type: ignore[attr-defined]
    return local_dt.astimezone(timezone.utc)


def calcula_horas_inicio_y_fin(
    periodos: list[PeriodosTexto],
    fecha: date,
    fin_mañana: datetime,
    fin_tarde: datetime,
    tz: pytz.timezone,
) -> list[tuple[datetime, datetime]]:
    """Recoge la lista de horas de inicio en texto y calcula las horas de fin.

    Devuelve una lista de tuplas con las horas de inicio y fin en UTC.
    """
    horas = []
    for i, periodo in enumerate(periodos):
        hora_inicio = string_to_utc_datetime(periodo.hora_inicio, fecha, tz)
        if i + 1 < len(periodos):
            hora_fin = string_to_utc_datetime(periodos[i + 1].hora_inicio, fecha, tz)
        elif hora_inicio < fin_mañana:
            hora_fin = fin_mañana
        else:
            hora_fin = fin_tarde

        horas.append((hora_inicio, hora_fin))
    return horas


def guardar_periodos(
    user: ATC,
    periodos: list[PeriodosTexto],
    estadillo: Estadillo,
    db_session: scoped_session,
    tz: pytz.timezone,
) -> None:
    """Guardar los periodos de los controladores en la base de datos."""
    fin_mañana = string_to_utc_datetime("15:00", estadillo.fecha, tz)
    fin_tarde = string_to_utc_datetime("22:30", estadillo.fecha, tz)

    horas = calcula_horas_inicio_y_fin(
        periodos,
        estadillo.fecha,
        fin_mañana,
        fin_tarde,
        tz=tz,
    )

    for i, periodo_texto in enumerate(periodos):
        sector = None
        if periodo_texto.funcion == "DESCANSO":
            actividad, sector_name = "D", None
        else:
            actividad, sector_name = extrae_actividad_y_sector(periodo_texto.funcion)

            sector = db_session.query(Sector).filter_by(nombre=sector_name).first()
            if not sector:
                logger.warning(
                    "Sector %s no encontrado en la base de datos",
                    sector_name,
                )
                continue

        # Convertir a naive datetime en UTC
        hora_inicio = horas[i][0].replace(tzinfo=None)
        hora_fin = horas[i][1].replace(tzinfo=None)

        periodo = Periodo(
            id_controlador=user.id,
            id_estadillo=estadillo.id,
            hora_inicio=hora_inicio,
            hora_fin=hora_fin,
            actividad=actividad,
        )
        if sector:
            periodo.id_sector = sector.id

        db_session.add(periodo)
    db_session.commit()


def procesar_controladores_y_sectores(
    controladores: dict[str, Controller],
    estadillo: Estadillo,
    db_session: scoped_session,
    tz: pytz.timezone,
) -> None:
    """Procesar los controladores y sus sectores.

    Añade a la base de datos a los controladores y sectores que no existan.
    """
    for nombre_controlador, controller in controladores.items():
        try:
            user = guardar_atc_en_estadillo(
                nombre_controlador,
                "Controlador",
                estadillo,
                controller.puesto,
                db_session,
            )
            update_user(user, controller.puesto, None)
        except ValueError:
            logger.exception("Error al guardar controlador %s", nombre_controlador)
            continue

        for sector_name in controller.sectores:
            sector = db_session.query(Sector).filter_by(nombre=sector_name).first()
            if not sector:
                sector = Sector(nombre=sector_name)
                db_session.add(sector)
            if sector not in estadillo.sectores:
                estadillo.sectores.append(sector)

        guardar_periodos(user, controller.periodos, estadillo, db_session, tz)


def guardar_datos_estadillo(
    data: EstadilloTexto,
    db_session: scoped_session,
    tz: pytz.timezone,
) -> Estadillo:
    """Guardar los datos generales del estadillo en la base de datos."""
    logger.info("Guardando datos del estadillo en la base de datos")
    # Convertir la fecha "27.05.2024" a un objeto date de Python
    fecha = datetime.strptime(data.fecha, "%d.%m.%Y").astimezone(tz).date()

    # Iniciar transacción
    transaction = db_session.begin_nested()

    # Crear el objeto Estadillo
    estadillo = Estadillo(
        fecha=fecha,
        dependencia=data.dependencia,
        turno=data.turno,
    )

    try:
        # Añadir y confirmar la sesión para asegurar que estadillo.id esté disponible
        db_session.add(estadillo)
        db_session.commit()
    except IntegrityError:
        transaction.rollback()  # Deshacer la transacción en caso de error
        # Manejar la excepción específicamente
        # Ya existía un estadillo así. Hay que borrar los datos anteriores
        logger.warning("Estadillo para la fecha %s ya existe. Se sustituye.", fecha)

        # Obtener y eliminar el estadillo existente y sus dependencias en cascada
        estadillo_existente = (
            db_session.query(Estadillo)
            .filter_by(fecha=fecha, dependencia=data.dependencia, turno=data.turno)
            .one()
        )

        db_session.delete(estadillo_existente)
        db_session.commit()  # Asegurarse de que se elimine antes de añadir el nuevo

        # Reintentar la inserción del nuevo estadillo
        db_session.add(estadillo)
        db_session.commit()

    roles = {
        "jefes_de_sala": ("Jefe de Sala", "JDS"),
        "supervisores": ("Supervisor", "SUP"),
        "tcas": ("TCA", "TCA"),
    }

    for rol, (titulo, identificador) in roles.items():
        for nombre in (nombre for nombre in getattr(data, rol) if nombre):
            try:
                guardar_atc_en_estadillo(
                    nombre,
                    titulo,
                    estadillo,
                    identificador,
                    db_session,
                )
            except ValueError:
                logger.exception("Error al guardar %s %s", titulo, nombre)
                continue

    # Procesar controladores y sus sectores
    procesar_controladores_y_sectores(data.controladores, estadillo, db_session, tz)

    logger.info("Datos del estadillo guardados en la base de datos")
    db_session.commit()
    return estadillo


def incorporar_periodos(
    estadillo_texto: EstadilloTexto,
    periodos_por_controlador: dict[str, list[PeriodosTexto]],
) -> None:
    """Incorpora los periodos de los controladores en el estadillo.

    Los periodos se añaden a los controladores en el estadillo.
    Si los nombres de los controladores están truncados, se verifican
    y se asocian correctamente.
    """
    # Inicializar un conjunto con los nombres de controladores del estadillo
    controladores_sin_periodos = set(estadillo_texto.controladores.keys())

    for nombre, periodos in periodos_por_controlador.items():
        # Intentar encontrar el nombre del controlador en el estadillo
        controlador_encontrado = nombre

        if nombre not in estadillo_texto.controladores:
            # Si el nombre no se encuentra, verificar si está truncado
            for nombre_estadillo in controladores_sin_periodos:
                if nombre_estadillo.startswith(nombre):
                    controlador_encontrado = nombre_estadillo
                    break
            else:
                continue

        estadillo_texto.controladores[controlador_encontrado].periodos = periodos
        controladores_sin_periodos.discard(controlador_encontrado)

    # Reportar cualquier controlador de la página 2 que no se pudo encontrar
    for nombre in controladores_sin_periodos:
        logger.warning(
            "Controlador %s en la página 2 no encontrado en la página 1",
            nombre,
        )


def procesa_estadillo(
    file: FileStorage | BufferedReader,
    db_session: scoped_session,
) -> Estadillo:
    """Procesa el archivo de estadillo diario.

    Extrae los datos del estadillo del archivo, analiza los datos e inserta los datos
    en la base de datos.
    """
    logger.info("Procesando archivo de estadillo diario")
    try:
        with pdfplumber.open(BytesIO(file.read())) as pdf:
            page1 = pdf.pages[0]
            page2 = pdf.pages[1]
    except PDFSyntaxError:
        logger.exception("Error al procesar el archivo PDF de estadillo")
        _msg = "Error al procesar el archivo PDF de estadillo"
        raise ValueError(_msg) from None

    estadillo_texto = extraer_datos_estadillo(page1)
    periodos_por_atc = extraer_periodos(page2)
    incorporar_periodos(estadillo_texto, periodos_por_atc)

    tz = get_timezone()
    estadillo_db = guardar_datos_estadillo(estadillo_texto, db_session, tz)

    logger.info("Archivo de estadillo diario procesado")
    db_session.commit()
    return estadillo_db
