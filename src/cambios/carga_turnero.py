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
from .user_utils import create_user, find_user, update_user

logger = getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover
    from pdfplumber.page import Page
    from sqlalchemy.orm.scoping import scoped_session
    from werkzeug.datastructures import FileStorage


@dataclass
class ScheduleEntry:
    """Data for a single schedule entry."""

    name: str
    role: str
    equipo: str | None = None
    shifts: list[str] = field(default_factory=list)


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


def extract_month_year(text: str) -> tuple[str, str]:
    """Extract the month and year from the text."""
    month_year_pattern = re.compile(r"Mes:\s*(\w+)\s*Año:\s*(\d{4})")
    match = month_year_pattern.search(text)
    if match:
        return match.group(1), match.group(2)
    _msg = "Couldn't extract month and year from the text"
    raise ValueError(_msg)


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


def extract_month_year_from_first_page(page: Page) -> tuple[str, str]:
    """Extract month and year from the first page."""
    text = page.extract_text()
    return extract_month_year(text)


def insert_shift_data(
    shifts: list[str],
    month: str,
    year: str,
    user: ATC,
    db_session: scoped_session,
) -> int:
    """Insert shift data into the database.

    The shifts list contains the shift codes for each day of the month.
    Returns the number of shifts inserted.
    """
    tz = get_timezone()
    n_shifts = 0
    logger.info("Inserting shifts for %s %s", user.nombre, user.apellidos)
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
                servicio.turno = shift_code
                continue

            new_shift = Turno(
                fecha=shift_date,
                turno=shift_code,
                id_atc=user.id,
            )
            db_session.add(new_shift)
            n_shifts += 1

    return n_shifts


def parse_and_insert_data(
    all_data: list[ScheduleEntry],
    month: str,
    year: str,
    db_session: scoped_session,
) -> tuple[int, int]:
    """Parse extracted data and insert it into the database.

    The data is a list of ScheduleEntry instances, each containing the name, role,
    equipo, and shifts for a user. The function parses the data, finds or creates the
    user in the database, and inserts the shift data for each user.

    Returns the number of identified users and shifts inserted.
    """
    n_users = 0
    n_shifts = 0

    try:
        for entry in all_data:
            if not is_valid_user_entry(entry):
                continue

            user = find_user(
                entry.name,
                db_session,
            )

            if user:
                user = update_user(user, entry.role, entry.equipo)
            else:
                user = create_user(
                    entry.name,
                    entry.role,
                    entry.equipo,
                    db_session,
                )
                db_session.flush()

            n_users += 1
            n_shifts += insert_shift_data(entry.shifts, month, year, user, db_session)
            db_session.flush()

        db_session.commit()
    except Exception:
        logger.exception("Error processing schedule data")
        db_session.rollback()
        raise

    logger.info("Inserted %d users and %d shifts", n_users, n_shifts)
    return n_users, n_shifts


def procesa_turnero(
    file: FileStorage | BufferedReader,
    db_session: scoped_session,
) -> tuple[int, int]:
    """Process the uploaded file and insert data into the database.

    The function extracts the schedule data from the uploaded file, parses the data,
    and inserts it into the database.
    Usuarios desconocidos se añaden a la base de datos.
    The app_logger parameter can be used to
    pass a logger instance to the function.

    Returns the number of users and shifts inserted.
    """
    try:
        with pdfplumber.open(BytesIO(file.read())) as pdf:
            all_data = []
            month, year = extract_month_year_from_first_page(pdf.pages[0])

            for page in pdf.pages:
                page_data = extract_schedule_data(page)
                all_data.extend(page_data)

            n_users, n_shifts = parse_and_insert_data(
                all_data,
                month,
                year,
                db_session,
            )

    except PDFSyntaxError as e:
        logger.exception("Error parsing PDF file")
        _msg = "Error parsing PDF file"
        raise ValueError(_msg) from e

    logger.info("Processed %d pages", len(pdf.pages))
    logger.info("Inserted %d users and %d shifts", n_users, n_shifts)

    return n_users, n_shifts
