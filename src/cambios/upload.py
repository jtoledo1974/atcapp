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
    """Parse the name into first and last name."""
    parts = name.split()
    first_name = parts[0]
    last_name = " ".join(parts[1:])
    return first_name, last_name


def is_valid_user_entry(entry) -> bool:
    """Check if the user entry is valid."""
    days_of_week = {"S", "D", "L", "M", "X", "J", "V"}
    if not entry["name"] or all(day in days_of_week for day in entry["shifts"]):
        return False
    return True


def process_file(file: FileStorage, db_session: Session) -> None:
    """Process the uploaded file and insert data into the database."""
    with pdfplumber.open(file) as pdf:
        all_data = []
        month = None
        year = None

        for page_num in range(len(pdf.pages)):
            page = pdf.pages[page_num]
            if page_num == 0:
                # Extract month and year from the first page
                text = page.extract_text()
                month, year = extract_month_year(text)

            # Extract schedule data from each page
            page_data = extract_schedule_data(page)
            all_data.extend(page_data)

        # Set the locale to Spanish
        original_locale = locale.getlocale(locale.LC_TIME)
        try:
            locale.setlocale(locale.LC_TIME, "es_ES")
        except locale.Error:
            print("Locale 'es_ES' not available. Please ensure it's installed.")
            return

        for entry in all_data:
            if not is_valid_user_entry(entry):
                continue

            first_name, last_name = parse_name(entry["name"])
            user = (
                db_session.query(User)
                .filter_by(first_name=first_name, last_name=last_name)
                .first()
            )

            if not user:
                print(f"User {first_name} {last_name} not found in the database.")
                continue

            shifts = entry["shifts"]
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
                            db_session.query(ShiftTypes)
                            .filter_by(code=shift_code)
                            .first()
                        )
                        if shift_type:
                            new_shift = Shift(
                                date=shift_date,
                                shift_type=shift_code,
                                user_id=user.id,
                            )
                            db_session.add(new_shift)
                            db_session.commit()

        # Revert to the original locale
        locale.setlocale(locale.LC_TIME, original_locale)


# Example usage:
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from .database import Base

# engine = create_engine('sqlite:///yourdatabase.db')
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# db_session = SessionLocal()
# with open("schedule.pdf", "rb") as f:
#     process_file(f, db_session)
