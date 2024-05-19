"""Business logic for the cambios app."""

from __future__ import annotations

import locale
import re
from datetime import datetime
from typing import TYPE_CHECKING

import pdfplumber

from .models import User

if TYPE_CHECKING:
    from pdfplumber.page import Page
    from werkzeug.datastructures import FileStorage

BASIC_SHIFTS = ["M", "T", "N", "im", "it", "in"]

SHIFT_TYPES = {
    "SUP": "SUPERVISIÓN",
    "A1": "TRABAJO EN FRECUENCIA",
    "A2": "INSTRUCTOR IMPARTIENDO OJT O SIENDO EVALUADO",
    "A2e": "INSTRUCTOR EVALUANDO OJT",
    "A3": "CONTROLADOR EN OJT (FPT) I EVALUANDO",
    "A4": "CONTROLADOR SIENDO EVALUADO EN COMPETENCIA OPERACIONAL",
    "A5": "IMAGINARIAS",
    "B00": "AUSENCIA JUSTIFICADA POR ENFERMEDAD QUE NO DA LUGAR A IT",
    "B01": "MOTIVO MÉDICO: BAJA CON PARTE IT",
    "B01v": "VACUNACION COVID19",
    "B02": "MOTIVO MÉDICO: AVISA ENFERMO",
    "B03": "MOTIVO MÉDICO: ASISTE PERO NO PRESTA SERVICIO OPERATIVO",
    "B04": "SALIDA DE FRECUENCIA: EMBARAZO SEMANA 35",
    "B05": "CIMA: ACUDIR A REVISIÓN",
    "B06": "BAJA CIMA",
    "B07": "AUSENCIA CERTIFICADO CIMA",
    "B09": "PERMISOS DE CONVENIO",
    "B10": "LICENCIAS MATERNIDAD/PATERNIDAD/OTRAS",
    "B11": "REDUCCIÓN POR GUARDA LEGAL, POR CUIDADO DE FAMILIAR",
    "B12": "SUSPENSION DE EMPLEO POR CAUSAS DISCIPLINARIAS",
    "B13": "PÉRDIDA DE VALIDEZ DE UNIDAD POR ESTAR SIN CONTROLAR MÁS TIEMPO DEL ESTABLECIDO",  # noqa: E501
    "B14": "ACTIVIDAD SINDICAL",
    "C01": "INSTRUCTOR IMPARTIENDO FORMACIÓN TEÓRICA",
    "C02": "INSTRUCTOR EN SIMULADORES O SIENDO EVALUADO",
    "C03": "INSTRUIDO EN TEORÍA (PRE OJT)",
    "C04": "INSTRUIDO EN SIMULADOR (PRE OJT)",
    "C05": "EVALUADOR DE COMPETENCIA OPERACIONAL",
    "C06": "EVALUADOR DEL INSTRUCTOR OJT O SIENDO EVALUADO",
    "C07": "EVALUADOR DEL EVALUADOR",
    "CS1": "Desprogramación por Comisión de Servicio",
    "CS2": "Comisión de Servicio carácter Sindical",
    "CS3": "Compensación por días libres afectados por Comisión de Servicio",
    "CS4": "Compensación por días libres afectados por CS actividad sindical",
    "EX": "EXCEDENCIA",
    "FC03": "FORMACION ON LINE CONTINUA - INSTRUYENDO",
    "FCO1": "FORMACION TEORIA FC - INSTRUYENDO",
    "FCO2": "FORMACION SIMULADOR DE FC - INSTRUYENDO",
    "FCP1": "INSTRUYENDO EN CARRERA PROFESIONAL",
    "FCP2": "INSTRUYENDO EN CARRERA PROFESIONAL - ON LINE",
    "FCP3": "FORMACIÓN CARRERA PROFESIONAL INSTRUCTOR EN SIMULADOR",
    "FCP4": "FORMACION CARRERA PROFESIONAL EVALUADOR EN SIMULADOR",
    "BD1": "Desprogramación por reunión",
    "BD2": "Desprogramación por Asuntos Propios",
    "BD3": "Desprogramación por Formación",
    "BD4": "Desprogramación por Comisión de Servicio",
    "BD5": "Desprogramación por Tráfico",
    "BDZ": "Desprogramación por Zulú",
    "BDHE": "DESPROGRAMACION POR HE A COMPENSAR",
    "BDHEFM": "DESPROGRAMACION POR HEFM A COMPENSAR",
    "LP": "LICENCIA DE ASUNTOS PROPIOS",
    "P": "ASUNTOS PROPIOS CONVENIO CONTROL",
    "PJS": "ASUNTO PROPIO 12H",
    "PICGA": "ASUNTOS PROPIOS CONVENIO GRUPO AENA",
    "APANT": "ASUNTOS PROPIOS AÑO ANTERIOR CONVENIO GRUPO AENA",
    "OTROS": "OTROS CONVENIO GRUPO AENA",
    "V": "VACACIONES (anuales, del año anterior)",
    "Va": "VACACION DE ANTIGÜEDAD",
    "JM": "JORNADA MIXTA",
    "MSM": "MAÑANA SIMULADOR",
    "TSM": "TARDE SIMULADOR",
    "ME": "MAÑANA OFICINA TÉCNICA",
    "TE": "TARDE OFICINA TÉCNICA",
    "MR": "MAÑANA REUNION",
    "TR": "TARDE REUNION",
    "FORM": "FORMACION NO REALIZADA",
}

ATC_ROLES = {"TS", "IS", "TI", "INS", "PTD", "CON", "SUP", "N/A"}


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


def process_file(file: FileStorage) -> None:
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
            shifts = entry["shifts"]
            print(f"User: {first_name} {last_name}")
            for day, shift_code in enumerate(shifts, start=1):
                if shift_code:  # Skip empty shift codes
                    date_str = f"{day:02d} {month} {year}"
                    try:
                        shift_date = datetime.strptime(date_str, "%d %B %Y")
                    except ValueError:
                        continue
                    print(f"  Date: {shift_date}")
                    print(f"  Shift Code: {shift_code}")

        # Revert to the original locale
        locale.setlocale(locale.LC_TIME, original_locale)
