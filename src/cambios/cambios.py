"""Business logic for the cambios app."""

from __future__ import annotations

import locale
import re
from datetime import datetime

import pdfplumber

from .models import User

SHIFT_TYPES = {
    "A1": "TRABAJO EN FRECUENCIA",
    "A2": "INSTRUCTOR IMPARTIENDO OJT O SIENDO EVALUADO",
    "A3": "INSTRUCTOR EVALUADOR OJT",
    "A4": "CONTROLADOR EN DT (FPT) EVALUANDO",
    "A5": "CONTROLADOR SIENDO EVALUADO EN COMPETENCIA OPERACIONAL",
    "AM": "ASAMBLEARIAS",
    "B01": "BAJA JUSTIFICADA POR ENFERMEDAD QUE NO DA LUGAR A IT",
    "B02": "MOTIVO MEDICO: BAJA POR PARTES IT",
    "B03": "MOTIVO MEDICO: AVISA ENFERMO",
    "B04": "MOTIVO MEDICO: ASTE PREV NO PRESTA SERVICIO OPERATIVO",
    "B05": "SALIDA DE FRECUENCIA: EMBARAZO SEMANA 33",
    "B06": "CIMA: CURA Y REVISIÓN",
    "B08": "BAJA CIMA",
    "B09": "AUSENCIA CERTIFICADO CIMA",
    "C01": "PERMISOS DE CONVENIO",
    "B10": "LICENCIAS MATERNIDAD/PATERNIDAD/OTRAS",
    "B11": "REDUCCIÓN POR GUARDIA LEGAL, POR CUIDADO DE FAMILIAR",
    "B12": "SUSPENSIÓN DE EMPLEO POR CAUSAS DISCIPLINARIAS",
    "B13": "PÉRDIDA DE VALIDEZ DE UNIDAD POR ESTAR SIN CONTROLAR MÁS TIEMPO DEL ESTABLECIDO",
    "B14": "ACTIVIDAD SINDICAL",
    "B15": "EXCEDENCIA",
    "P": "LICENCIA DE ASUNTOS PROPIOS",
    "P0": "ASUNTOS PROPIOS CONVENIO CONTROL",
    "P1": "ASUNTO PROPIO 12H",
    "P2": "ASUNTO PROPIO 12HS",
    "P3": "ASUNTOS PROPIOS CONVENIO GRUPO AENA",
    "P4": "APART: ASUNTOS PROPIOS AÑO ANTERIOR CONVENIO GRUPO AENA",
    "V": "VACACIONES (Anuales, el año anterior)",
    "VA": "VACACION DE ANTIGÜEDAD",
    "1": "COMPENSACIÓN DESPROGRAMACIÓN POR FORMACIÓN",
    "BD1": "Desprogramación por reunión",
    "BD2": "Desprogramación por Asuntos Propios",
    "BD3": "Desprogramación por Formación",
    "BD4": "Desprogramación por Comisión de Servicio",
    "BD5": "Desprogramación por Salud",
    "BD6": "Desprogramación por Faltas",
    "BD7": "Desprogramación por Turno",
    "BD8": "Desprogramación por Comisión de Servicio",
    "BDHE": "Desprogramación por HE A Compensar",
    "C3": "Comisión de Servicio de carácter Sindical",
    "C5": "Compensación por turnos afectados por actividades sindicales",
    "CS3": "Comisión de Servicio de carácter Sindical",
    "C9": "Compensación por turnos afectados por actividades sindicales",
    "C10": "INSTRUCTOR IMPARTIENDO FORMACIÓN TÉCNICA",
    "C11": "INSTRUCTOR EN SIMULADORES O SIENDO EVALUADO",
    "C03": "INSTRUIDO EN SIMULADOR (FTE) (OT)",
    "C05": "EVALUADOR DE COMPETENCIA OPERACIONAL",
    "C07": "EVALUADOR DE INSTRUCTOR OJT O SIENDO EVALUADO",
    "C08": "EVALUADOR DEL EVALUADOR",
    "C09": "FORMACIÓN ON LINE CONTINUA – INSTRUYENDO",
    "FC01": "FORMACIÓN TÉCNICA FC – INSTRUYENDO",
    "FCO2": "INSTRUYENDO EN CARRERA PROFESIONAL",
    "FCP1": "INSTRUYENDO EN CARRERA PROFESIONAL – ON LINE",
    "FCP3": "FORMACIÓN TÉCNICA Y EVALUADOR DE INSTRUCTOR EN SIMULADOR",
    "FCP4": "FORMACIÓN TÉCNICA PROFESIONAL EVALUADOR EN SIMULADOR",
    "MR": "MAÑANA REUNIÓN",
    "TE": "Tarde Onírica Técnica",
    "JX": "Jornada Mixta",
    "MSM": "Mañana Simulador",
    "TSM": "Tarde Simulador",
    "FORM": "FORMACIÓN NO REALIZADA",
}

ATC_ROLES = {"TS", "IS", "TI", "INS", "PTD", "CON", "SUP"}  # Add all ATC roles here


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
                        print(f"Failed to parse date: {date_str}")
                        continue
                    print(f"  Date: {shift_date}")
                    print(f"  Shift Code: {shift_code}")

        # Revert to the original locale
        locale.setlocale(locale.LC_TIME, original_locale)
