"""Business logic for the cambios app."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum

from .models import User


class ShiftType(Enum):
    """Shift types."""

    M = "Mañana"
    T = "Tarde"
    N = "Noche"


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

MONTHS_IN_A_YEAR = 12
SUNDAY_DAY_NUMBER = 6


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


@dataclass
class Shift:
    type: ShiftType
    code: str
    start_time: datetime | None = None
    end_time: datetime | None = None


@dataclass
class Day:
    date: date
    day_of_week: str
    is_national_holiday: bool
    shift: Shift | None = None


@dataclass
class MonthCalendar:
    year: int
    month: int
    days: list[Day] = field(init=False)

    def __post_init__(self) -> None:
        """Generate the days for the month."""
        self.days = self._generate_days(self.year, self.month)

    def _generate_days(self, year: int, month: int) -> list[Day]:
        days = []
        first_day = date(year, month, 1)
        last_day = self._last_day_of_month(year, month)

        # Determine the start of the calendar (possibly including days from the previous month)
        start_date = first_day - timedelta(days=first_day.weekday())

        # Determine the end of the calendar (possibly including days from the next month)
        end_date = last_day + timedelta(days=(6 - last_day.weekday()))

        current_date = start_date
        while current_date <= end_date:
            day_of_week = current_date.strftime("%A")
            is_national_holiday = self._check_national_holiday(current_date)
            days.append(
                Day(
                    date=current_date,
                    day_of_week=day_of_week,
                    is_national_holiday=is_national_holiday,
                ),
            )
            current_date += timedelta(days=1)

        return days

    def _last_day_of_month(self, year: int, month: int) -> date:
        if month == MONTHS_IN_A_YEAR:
            return date(year, 12, 31)
        return date(year, month + 1, 1) - timedelta(days=1)

    def _check_national_holiday(self, date_to_check: date) -> bool:
        # Placeholder for actual holiday checking logic
        # TODO #2 Implement a real holiday checking mechanism
        national_holidays = [
            date(date_to_check.year, 1, 1),  # New Year's Day
            date(date_to_check.year, 12, 25),  # Christmas Day
            date(date_to_check.year, 12, 6),  # Constitution Day
            date(date_to_check.year, 10, 12),  # Hispanic Day
            date(date_to_check.year, 5, 1),  # Labour Day
            date(date_to_check.year, 8, 15),  # Assumption of Mary
            date(date_to_check.year, 11, 1),  # All Saints' Day
            date(date_to_check.year, 12, 8),  # Immaculate Conception
        ]
        return date_to_check in national_holidays

    def get_weeks(self) -> list[list[Day]]:
        weeks = []
        week = []
        for day in self.days:
            week.append(day)
            if day.date.weekday() == SUNDAY_DAY_NUMBER:  # Sunday is the end of the week
                weeks.append(week)
                week = []
        if week:
            weeks.append(week)  # Add the last week if it wasn't added
        return weeks
