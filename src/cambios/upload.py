"""Processes the uploaded schedule file."""

from __future__ import annotations

import locale
import re
from datetime import datetime
from typing import TYPE_CHECKING

import pdfplumber

from .cambios import ATC_ROLES, BASIC_SHIFTS, SHIFT_TYPES
from .models import Shift, ShiftTypes, User

if TYPE_CHECKING:
    from pdfplumber.page import Page
    from sqlalchemy.orm import Session
    from werkzeug.datastructures import FileStorage


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
                len(parts) < 3
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
            if len(shifts) < 31:
                shifts.extend([""] * (31 - len(shifts)))

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
    while i < len(parts) and len(last_name_parts) < 2:
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


def is_valid_user_entry(entry) -> bool:
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
        print(f"Locale '{locale_name}' not available. Please ensure it's installed.")
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
    for day, shift_code in enumerate(shifts, start=1):
        if shift_code:  # Skip empty shift codes
            date_str = f"{day:02d} {month} {year}"
            try:
                shift_date = datetime.strptime(date_str, "%d %B %Y")
            except ValueError:
                continue

            # Check if shift already exists for the user on this date
            existing_shift = (
                db_session.query(Shift)
                .filter_by(user_id=user.id, date=shift_date)
                .first()
            )
            if not existing_shift:
                shift_type = (
                    db_session.query(ShiftTypes).filter_by(code=shift_code).first()
                )
                if shift_type:
                    new_shift = Shift(
                        date=shift_date,
                        shift_type=shift_code,
                        user_id=user.id,
                    )
                    db_session.add(new_shift)
                    db_session.commit()


def find_user(name: str, db_session: Session) -> User | None:
    """Find a user in the database by name.

    First attempt is to find the user by first and last name.
    If we fail, we take a look at all users in the database in the form
    'LAST_NAME FIRST_NAME' and try to match the name that way.
    """
    first_name, last_name = parse_name(name)
    user = (
        db_session.query(User)
        .filter_by(first_name=first_name, last_name=last_name)
        .first()
    )
    if user:
        return user

    for user in db_session.query(User).all():
        if f"{user.last_name} {user.first_name}" == name:
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
            print(f"User not found for entry: {entry['name']}")
            continue

        insert_shift_data(entry["shifts"], month, year, user, db_session)


def process_file(file: FileStorage, db_session: Session) -> None:
    """Process the uploaded file and insert data into the database."""
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


# Example usage:
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from .database import Base

# engine = create_engine('sqlite:///yourdatabase.db')
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# db_session = SessionLocal()
# with open("schedule.pdf", "rb") as f:
#     process_file(f, db_session)
