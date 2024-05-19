"""Business logic for the cambios app."""

from __future__ import annotations

import re
from datetime import datetime

import pdfplumber

from .models import User


def is_admin(email: str) -> bool:
    """Check if the user is an admin.

    Checks the is_admin column in Users.
    If no users have the is_admin flag set, the first user to log in becomes the admin.

    """
    user = User.query.filter_by(email=email).first()
    if user:
        # The user was found
        return user.is_admin

    # User is not an admin. Check whether anyone is an admin.
    return not User.query.filter_by(is_admin=True).first()


def extract_month_year(text):
    month_year_pattern = re.compile(r"Mes:\s*(\w+)\s*Año:\s*(\d{4})")
    match = month_year_pattern.search(text)
    if match:
        return match.group(1), match.group(2)
    return None, None


def extract_schedule_data(page):
    lines = page.extract_text().split("\n")
    data = []
    name_shift_pattern = re.compile(r"([A-Z\s]+)\s+(\w+)(?:\s+(\w+))*")

    for line in lines:
        if name_shift_pattern.match(line):
            parts = line.split()
            name = " ".join(parts[:-31])
            shifts = parts[-31:]
            data.append({"name": name, "shifts": shifts})

    return data


def parse_name(name):
    parts = name.split()
    first_name = parts[0]
    last_name = " ".join(parts[1:])
    return first_name, last_name


def is_valid_user_entry(entry):
    # Check if the name is empty or the shifts array contains only day abbreviations
    days_of_week = {"S", "D", "L", "M", "X", "J", "V"}
    if not entry["name"] or all(day in days_of_week for day in entry["shifts"]):
        return False
    return True


def process_file(file):
    """Process the uploaded file."""
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

        # Print the extracted data in a structured format
        if month and year:
            print(f"Month: {month}")
            print(f"Year: {year}")

        for entry in all_data:
            if not is_valid_user_entry(entry):
                continue
            first_name, last_name = parse_name(entry["name"])
            shifts = entry["shifts"]
            print(f"User: {first_name} {last_name}")
            for day, shift_code in enumerate(shifts, start=1):
                if shift_code:  # Skip empty shift codes
                    date_str = f"{day:02d} {month} {year}"
                    shift_date = datetime.strptime(date_str, "%d %B %Y")
                    print(f"  Date: {shift_date}")
                    print(f"  Shift Code: {shift_code}")
