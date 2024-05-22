"""Business logic for the cambios app."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from .models import Shift as DBShift
from .models import User


class ShiftPeriod(Enum):
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


def period_from_code(code: str) -> ShiftPeriod:
    """Get the period from a shift code."""
    if code in BASIC_SHIFTS and code[1].upper() in BASIC_SHIFTS:
        return ShiftPeriod[code[1].upper()]

    if code[0] in BASIC_SHIFTS:
        return ShiftPeriod[code[0].upper()]

    return ShiftPeriod["M"]


def description_from_code(code: str) -> str:
    """Get the description from a shift code."""
    if code in SHIFT_TYPES:
        return SHIFT_TYPES[code]
    if code[1:] in SHIFT_TYPES:
        return SHIFT_TYPES[code[1:]]
    return code


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
    """Shift information."""

    period: ShiftPeriod
    code: str
    description: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


@dataclass
class Day:
    """Day information."""

    date: date
    day_of_week: str
    is_national_holiday: bool
    shift: Shift | None = None


@dataclass
class MonthCalendar:
    """Calendar for a month."""

    year: int
    month: int
    _days: list[Day] = field(default_factory=list)

    @property
    def days(self) -> list[Day]:
        """Return the days in the month.

        But only those in the actual month.
        """
        return [day for day in self._days if day.date.month == self.month]

    @property
    def weeks(self) -> list[list[Day]]:
        """Return the days in the month grouped by weeks."""
        weeks = []
        week = []
        for day in self._days:
            week.append(day)
            if day.date.weekday() == SUNDAY_DAY_NUMBER:  # Sunday is the end of the week
                weeks.append(week)
                week = []
        if week:
            weeks.append(week)  # Add the last week if it wasn't added
        return weeks

    @property
    def month_name(self) -> str:
        """Return the name of the month."""
        return self.days[0].date.strftime("%B").capitalize()


class MonthCalGen:
    """Generate a calendar for a month and year and user."""

    @staticmethod
    def generate(
        year: int,
        month: int,
        user: User | None = None,
        session: Session | None = None,
    ) -> MonthCalendar:
        """Generate a calendar for a month and year."""
        days = []
        first_day = date(year, month, 1)
        last_day = MonthCalGen._last_day_of_month(year, month)

        # Determine the start of the calendar
        # (possibly including days from the previous month)
        start_date = first_day - timedelta(days=first_day.weekday())

        # Determine the end of the calendar
        # (possibly including days from the next month)
        end_date = last_day + timedelta(days=(6 - last_day.weekday()))

        current_date = start_date
        while current_date <= end_date:
            day_of_week = current_date.strftime("%A")
            is_national_holiday = MonthCalGen._check_national_holiday(current_date)
            days.append(
                Day(
                    date=current_date,
                    day_of_week=day_of_week,
                    is_national_holiday=is_national_holiday,
                ),
            )
            current_date += timedelta(days=1)

        if not user or not session:
            return MonthCalendar(year=year, month=month, _days=days)

        # Go through every shift in the database matching the user id
        # and the date within the dates of the calendar
        min_date, max_date = days[0].date, days[-1].date
        user_shifts = (
            session.query(DBShift)
            .filter(
                DBShift.user_id == user.id,
                DBShift.date.between(min_date, max_date),
            )
            .all()
        )

        # Add a Shift dataclass for each day that has a shift
        shifts_by_date = {dbshift.date.date(): dbshift for dbshift in user_shifts}

        for day in (day for day in days if day.date in shifts_by_date):
            dbshift = shifts_by_date[day.date]
            day.shift = Shift(
                period=period_from_code(dbshift.shift_type),
                code=dbshift.shift_type,
                description=description_from_code(dbshift.shift_type),
            )

        return MonthCalendar(year=year, month=month, _days=days)

    @staticmethod
    def _last_day_of_month(year: int, month: int) -> date:
        if month == MONTHS_IN_A_YEAR:
            return date(year, 12, 31)
        return date(year, month + 1, 1) - timedelta(days=1)

    @staticmethod
    def _check_national_holiday(date_to_check: date) -> bool:
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
