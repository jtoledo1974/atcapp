"""Processes the uploaded schedule file."""

from __future__ import annotations

import locale
import logging
import re
import unicodedata
from datetime import datetime
from typing import TYPE_CHECKING

import pdfplumber

from .cambios import ATC_ROLES, BASIC_SHIFTS, SHIFT_TYPES
from .models import Shift, User

if TYPE_CHECKING:
    from logging import Logger

    from pdfplumber.page import Page
    from sqlalchemy.orm import Session
    from werkzeug.datastructures import FileStorage

logger: Logger


def setup_logger(app_logger: Logger | None) -> None:
    """Set up the logger."""
    global logger  # noqa: PLW0603
    if app_logger:
        logger = app_logger
        return

    logger = logging.getLogger(__name__)


def is_valid_shift_code(shift_code: str) -> bool:
    """Check if the shift code is valid."""
    if not shift_code:
        return False
    if shift_code in BASIC_SHIFTS:
        return True
    if shift_code in SHIFT_TYPES:
        return True
    for prefix in BASIC_SHIFTS:
        if shift_code.startswith(prefix) and shift_code[1:] in SHIFT_TYPES:
            return True
    return False


def extract_month_year(text: str) -> tuple[str, str]:
    """Extract the month and year from the text."""
    month_year_pattern = re.compile(r"Mes:\s*(\w+)\s*Año:\s*(\d{4})")
    match = month_year_pattern.search(text)
    if match:
        return match.group(1), match.group(2)
    return None, None


MIN_SHIFT_COLUMNS = 3
"""Minimum number of columns required for a valid shift entry."""
MAX_DAYS_IN_MONTH = 31


def extract_schedule_data(page: Page) -> list[dict]:
    """Extract the schedule data from the page."""
    table = page.extract_table()
    if table is None:
        return []

    data = []

    for row in table:
        if row and any(row):
            parts = [cell.strip() if cell else "" for cell in row]
            if (
                len(parts) < MIN_SHIFT_COLUMNS
            ):  # Skip rows that do not have enough parts to be valid entries
                continue

            # Identify role by finding the first occurrence of a known role
            role_index = next(
                (i for i, part in enumerate(parts) if part in ATC_ROLES),
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

            data.append({"name": name, "role": role, "shifts": shifts})

    return data


def parse_name(name: str) -> tuple[str, str]:
    """Parse the name into first and last name.

    El archivo tiene los dos apellidos primero y luego el nombre, pero
    no identifica las partes. Tanto los apellidos como el nombre pueden
    ser compuestos.

    El algoritmo a seguir será identificar dos apellidos, lo que reste
    será el nombre.

    Entendemos como un apellido bien una única palabra, o bien:
      - DE APELLIDO
      - DEL APELLIDO
      - DE LA APELLIDO
      - DE LOS APELLIDOS
      - DE LAS APELLIDOS

    Ejemplos:
    CASTILLO PINTO JAIME -> Nombre: JAIME, Apellidos: CASTILLO PINTO
    MARTINEZ MORALES MARIA VIRGINIA: Nombre: MARIA VIRGINIA, Apellidos: MARTINEZ MORALES
    DE ANDRES RICO MARIO -> Nombre: MARIO, Apellidos: DE ANDRES RICO
    """
    parts = name.split()
    prepositions = {"DE", "DEL", "DE LA", "DE LOS", "DE LAS"}
    last_name_parts = []
    i = 0

    # Identify the last names
    while i < len(parts) and len(last_name_parts) < 2:  # noqa: PLR2004 Dos apellidos
        if parts[i].upper() in prepositions:
            # Handle multi-word prepositions (e.g., "DE LA", "DE LOS")
            if i + 1 < len(parts):
                if parts[i].upper() in {"DE", "DEL"}:
                    if i + 2 < len(parts) and parts[i + 1].upper() in {
                        "LA",
                        "LOS",
                        "LAS",
                    }:
                        last_name_parts.append(" ".join(parts[i : i + 3]))
                        i += 3
                    else:
                        last_name_parts.append(" ".join(parts[i : i + 2]))
                        i += 2
                else:
                    last_name_parts.append(" ".join(parts[i : i + 2]))
                    i += 2
            else:
                break
        else:
            last_name_parts.append(parts[i])
            i += 1

    # The rest is the first name
    first_name_parts = parts[i:]

    last_name = " ".join(last_name_parts)
    first_name = " ".join(first_name_parts)

    return first_name, last_name


def is_valid_user_entry(entry: dict) -> bool:
    """Check if the user entry is valid."""
    days_of_week = {"S", "D", "L", "M", "X", "J", "V"}
    if not entry["name"] or all(day in days_of_week for day in entry["shifts"]):
        return False
    return True


def extract_month_year_from_first_page(page: Page) -> tuple[str, str]:
    """Extract month and year from the first page."""
    text = page.extract_text()
    return extract_month_year(text)


_original_locale = None


def set_locale(locale_name: str) -> None:
    """Set the locale to the specified locale name."""
    global _original_locale  # noqa: PLW0603
    _original_locale = locale.getlocale(locale.LC_TIME)
    try:
        locale.setlocale(locale.LC_TIME, locale_name)
    except locale.Error:
        logger.exception(
            "Locale %s not available. Please ensure it's installed.",
            locale_name,
        )
        raise


def reset_locale() -> None:
    """Reset the locale to the original locale."""
    if _original_locale:
        locale.setlocale(locale.LC_TIME, _original_locale)


def insert_shift_data(
    shifts: list[str],
    month: str,
    year: str,
    user: User,
    db_session: Session,
) -> None:
    """Insert shift data into the database."""
    logger.info("Inserting shifts for %s %s", user.first_name, user.last_name)
    for day, shift_code in enumerate(shifts, start=1):
        if shift_code:  # Skip empty shift codes
            date_str = f"{day:02d} {month} {year}"
            try:
                shift_date = datetime.strptime(date_str, "%d %B %Y")  # noqa: DTZ007
            except ValueError:
                continue

            # Check if shift already exists for the user on this date
            existing_shift = (
                db_session.query(Shift)
                .filter_by(user_id=user.id, date=shift_date)
                .first()
            )
            if existing_shift:
                continue

            new_shift = Shift(
                date=shift_date,
                shift_type=shift_code,
                user_id=user.id,
            )
            db_session.add(new_shift)
            db_session.commit()


def normalize_string(s: str) -> str:
    """Normalize string by removing accents and converting to lowercase."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    ).lower()


def find_user(name: str, db_session: Session) -> User | None:
    """Find a user in the database by name.

    First attempt is to find the user by first and last name.
    If we fail, we take a look at all users in the database in the form
    'LAST_NAME FIRST_NAME' and try to match the name that way.
    """
    first_name, last_name = parse_name(name)
    normalized_first_name = normalize_string(first_name)
    normalized_last_name = normalize_string(last_name)

    # Fetch all users and normalize names for comparison
    users = db_session.query(User).all()
    for user in users:
        if (
            normalize_string(user.first_name) == normalized_first_name
            and normalize_string(user.last_name) == normalized_last_name
        ):
            return user

    # Attempt to match the full name
    normalized_name = normalize_string(name)
    for user in users:
        if normalize_string(f"{user.last_name} {user.first_name}") == normalized_name:
            return user

    return None


def parse_and_insert_data(
    all_data: list[dict],
    month: str,
    year: str,
    db_session: Session,
) -> None:
    """Parse extracted data and insert it into the database."""
    for entry in all_data:
        if not is_valid_user_entry(entry):
            continue

        user = find_user(entry["name"], db_session)

        if not user:
            logger.warning("User not found for entry: %s", entry["name"])
            continue

        insert_shift_data(entry["shifts"], month, year, user, db_session)


def process_file(
    file: FileStorage,
    db_session: Session,
    /,
    app_logger: Logger | None = None,
) -> None:
    """Process the uploaded file and insert data into the database."""
    setup_logger(app_logger)
    with pdfplumber.open(file) as pdf:
        all_data = []
        month, year = extract_month_year_from_first_page(pdf.pages[0])

        for page in pdf.pages:
            page_data = extract_schedule_data(page)
            all_data.extend(page_data)

        set_locale("es_ES")
        try:
            parse_and_insert_data(all_data, month, year, db_session)
        finally:
            reset_locale()
