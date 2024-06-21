"""Processes the uploaded schedule file.

process_file is the main function that processes the uploaded schedule file.
It extracts the schedule data from the file, parses the data, and inserts it
into the database. The function uses the extract_schedule_data function to
extract the schedule data from each page of the uploaded file. The extracted
data is then parsed using the parse_and_insert_data function, which inserts
the data into the database.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from io import BufferedReader, BytesIO
from logging import getLogger
from typing import TYPE_CHECKING

import pdfplumber
from pdfminer.pdfparser import PDFSyntaxError

from . import get_timezone
from .cambios import CODIGOS_DE_TURNO, PUESTOS_CARRERA, TURNOS_BASICOS
from .models import ATC, Turno
from .user_utils import AtcTexto, UpdateResult, create_user, find_user, update_user

logger = getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from pdfplumber.page import Page
    from sqlalchemy.orm.scoping import scoped_session
    from werkzeug.datastructures import FileStorage


@dataclass
class DatosTurnero:
    """Datos globales de un archivo pdf de turnero mensual."""

    mes: str
    año: str
    dependencia: str


@dataclass
class ScheduleEntry:
    """Data for a single schedule entry."""

    name: str
    role: str
    equipo: str | None = None
    shifts: list[str] = field(default_factory=list)


@dataclass
class ResultadoProcesadoTurnos:
    """Resultado del procesamiento de los turnos."""

    existing_shifts: set[Turno] = field(default_factory=set)
    updated_shifts: set[Turno] = field(default_factory=set)
    created_shifts: set[Turno] = field(default_factory=set)

    @property
    def n_existing_shifts(self) -> int:
        """Number of identified shifts."""
        return len(self.existing_shifts)

    @property
    def n_updated_shifts(self) -> int:
        """Number of updated shifts."""
        return len(self.updated_shifts)

    @property
    def n_created_shifts(self) -> int:
        """Number of created shifts."""
        return len(self.created_shifts)

    @property
    def n_total_shifts(self) -> int:
        """Total number of shifts."""
        return self.n_existing_shifts + self.n_updated_shifts + self.n_created_shifts


@dataclass
class ResultadoProcesadoTurnero(ResultadoProcesadoTurnos):
    """Resultado del procesamiento del turnero."""

    existing_users: set[ATC] = field(default_factory=set)
    updated_users: set[ATC] = field(default_factory=set)
    created_users: set[ATC] = field(default_factory=set)

    @property
    def n_existing_users(self) -> int:
        """Number of identified users."""
        return len(self.existing_users)

    @property
    def n_updated_users(self) -> int:
        """Number of updated users."""
        return len(self.updated_users)

    @property
    def n_created_users(self) -> int:
        """Number of created users."""
        return len(self.created_users)

    @property
    def n_total_users(self) -> int:
        """Total number of users."""
        return self.n_existing_users + self.n_updated_users + self.n_created_users

    def incluye(self, other: ResultadoProcesadoTurnero) -> ResultadoProcesadoTurnero:
        """Incluye los resultados de otro procesamiento.

        Se suman los creados.
        Se suman los actualizados.
        De los identificados se restan los creados y los actualizados.
        Devuelve un nuevo objeto con los resultados combinados.
        """
        return ResultadoProcesadoTurnero(
            created_users=self.created_users.union(other.created_users),
            updated_users=self.updated_users.union(other.updated_users),
            existing_users=self.existing_users.union(other.existing_users)
            - self.created_users
            - self.updated_users,
            created_shifts=self.created_shifts.union(other.created_shifts),
            updated_shifts=self.updated_shifts.union(other.updated_shifts),
            existing_shifts=self.existing_shifts.union(other.existing_shifts)
            - self.created_shifts
            - self.updated_shifts,
        )


def is_valid_shift_code(shift_code: str) -> bool:
    """Check if the shift code is valid."""
    if not shift_code:
        return False
    if shift_code in TURNOS_BASICOS:
        return True
    if shift_code in CODIGOS_DE_TURNO:
        return True
    for prefix in TURNOS_BASICOS:
        if shift_code.startswith(prefix) and shift_code[1:] in CODIGOS_DE_TURNO:
            return True
    return False


MAX_DAYS_IN_MONTH = 31


def extract_schedule_data(page: Page) -> list[ScheduleEntry]:
    """Extract the schedule data from the page."""
    table = page.extract_table()
    if table is None:
        return []

    data = []
    equipo: str | None = None

    # Regular expression to find the equipo
    equipo_pattern = re.compile(r"EQUIPO: (\w+)")

    for row in table:
        if row and any(row):
            parts = [cell.strip() if cell else "" for cell in row]

            if not equipo:
                equipo_match = equipo_pattern.search(parts[0])
                equipo = equipo_match.group(1) if equipo_match else None
                equipo = equipo if equipo != "NA" else None

            # Identify role by finding the first occurrence of a known role
            role_index = next(
                (i for i, part in enumerate(parts) if part in PUESTOS_CARRERA),
                None,
            )
            if role_index is None:
                continue  # Skip rows without a valid role

            name = " ".join(parts[:role_index])
            role = parts[role_index]
            shifts = parts[role_index + 1 :]

            # Make sure at least one shift code is valid
            if not any(is_valid_shift_code(shift) for shift in shifts):
                continue

            # Handle incomplete shift rows by padding with empty strings
            if len(shifts) < MAX_DAYS_IN_MONTH:
                shifts.extend([""] * (MAX_DAYS_IN_MONTH - len(shifts)))

            data.append(
                ScheduleEntry(
                    name=name.strip(),
                    role=role.strip(),
                    equipo=equipo.strip() if equipo else None,
                    shifts=shifts,
                ),
            )

    return data


def is_valid_user_entry(entry: ScheduleEntry) -> bool:
    """Check if the user entry is valid."""
    days_of_week = {"S", "D", "L", "M", "X", "J", "V"}
    if not entry.name or all(day in days_of_week for day in entry.shifts):
        return False
    return True


def extraer_mes_año(text: str) -> tuple[str, str]:
    """Extract the month and year from the text."""
    month_year_pattern = re.compile(r"Mes:\s*(\w+)\s*Año:\s*(\d{4})")
    match = month_year_pattern.search(text)
    if match:
        return match.group(1), match.group(2)
    _msg = "Couldn't extract month and year from the text"
    raise ValueError(_msg)


def extraer_dependencia(text: str) -> str:
    """Extraer la dependencia del texto."""
    dependencia_pattern = re.compile(r"(\w+) - CONTROLADORES")
    match = dependencia_pattern.search(text)
    if match:
        return match.group(1)
    _msg = "Couldn't extract dependency from the text"
    raise ValueError(_msg)


def extraer_datos_turnero_de_primera_pagina(page: Page) -> DatosTurnero:
    """Extrae los datos del turnero de la primera página."""
    text = page.extract_text()
    mes, año = extraer_mes_año(text)
    dependencia = extraer_dependencia(text)
    return DatosTurnero(mes=mes, año=año, dependencia=dependencia)


def insert_shift_data(
    shifts: list[str],
    month: str,
    year: str,
    user: ATC,
    db_session: scoped_session,
) -> ResultadoProcesadoTurnos:
    """Insert shift data into the database.

    The shifts list contains the shift codes for each day of the month.
    Returns the number of shifts inserted.
    """
    tz = get_timezone()
    logger.info("Inserting shifts for %s %s", user.nombre, user.apellidos)
    res = ResultadoProcesadoTurnos()
    for day, shift_code in enumerate(shifts, start=1):
        if shift_code:  # Skip empty shift codes
            date_str = f"{day:02d} {month} {year}"
            try:
                shift_date = (
                    datetime.strptime(date_str, "%d %B %Y").astimezone(tz).date()
                )
            except ValueError:
                continue

            # Check if shift already exists for the user on this date
            servicio = (
                db_session.query(Turno)
                .filter_by(id_atc=user.id, fecha=shift_date)
                .first()
            )
            if servicio:
                if servicio.turno == shift_code:
                    res.existing_shifts.add(servicio)
                else:
                    servicio.turno = shift_code
                    res.updated_shifts.add(servicio)
                continue

            new_shift = Turno(
                fecha=shift_date,
                turno=shift_code,
                id_atc=user.id,
            )
            db_session.add(new_shift)
            res.created_shifts.add(new_shift)

    return res


def parse_and_insert_data(
    all_data: list[ScheduleEntry],
    datos_turnero: DatosTurnero,
    db_session: scoped_session,
) -> ResultadoProcesadoTurnero:
    """Parse extracted data and insert it into the database.

    The data is a list of ScheduleEntry instances, each containing the name, role,
    equipo, and shifts for a user. The function parses the data, finds or creates the
    user in the database, and inserts the shift data for each user.

    Returns the number of identified users and shifts inserted, along with sets of
    identified users, updated users, created users, identified shifts,
    and created shifts.
    """
    res = ResultadoProcesadoTurnero()

    try:
        for entry in all_data:
            if not is_valid_user_entry(entry):
                continue

            user = find_user(
                entry.name,
                db_session,
            )

            if user:
                update_res = update_user(user, entry.role, entry.equipo)
                if update_res == UpdateResult.UPDATED:
                    res.updated_users.add(user)
                else:
                    res.existing_users.add(user)
            else:
                atc_texto = AtcTexto(
                    apellidos_nombre=entry.name,
                    dependencia=datos_turnero.dependencia,
                    categoria=entry.role,
                    equipo=entry.equipo,
                )
                user = create_user(atc_texto, db_session)
                db_session.flush()
                res.created_users.add(user)

            res_turnos = insert_shift_data(
                entry.shifts,
                datos_turnero.mes,
                datos_turnero.año,
                user,
                db_session,
            )
            res.created_shifts.update(res_turnos.created_shifts)
            res.existing_shifts.update(res_turnos.existing_shifts)

            db_session.flush()

        db_session.commit()
    except Exception:
        logger.exception("Error processing schedule data")
        db_session.rollback()
        raise

    logger.info(
        "Inserted %d users and %d shifts",
        len(res.created_users),
        len(res.created_shifts),
    )
    return res


def procesa_turnero(
    file: FileStorage | BufferedReader,
    db_session: scoped_session,
) -> ResultadoProcesadoTurnero:
    """Process the uploaded file and insert data into the database.

    The function extracts the schedule data from the uploaded file, parses the data,
    and inserts it into the database.
    Usuarios desconocidos se añaden a la base de datos.
    The app_logger parameter can be used to
    pass a logger instance to the function.

    Returns the number of users and shifts inserted, along with sets of
    identified users, updated users, created users, identified shifts,
    and created shifts.
    """
    try:
        with pdfplumber.open(BytesIO(file.read())) as pdf:
            all_data = []
            datos_turnero = extraer_datos_turnero_de_primera_pagina(pdf.pages[0])

            for page in pdf.pages:
                page_data = extract_schedule_data(page)
                all_data.extend(page_data)

            res = parse_and_insert_data(
                all_data,
                datos_turnero,
                db_session,
            )

    except PDFSyntaxError as e:
        logger.exception("Error parsing PDF file")
        _msg = "Error parsing PDF file"
        raise ValueError(_msg) from e

    logger.info("Processed %d pages", len(pdf.pages))
    logger.info(
        "Inserted %d users and %d shifts",
        len(res.created_users),
        len(res.created_shifts),
    )

    return res
