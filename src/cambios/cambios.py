"""Business logic for the cambios app."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from sqlalchemy.orm import Session

from .models import ATC
from .models import Turno as DBShift


class TipoTurno(Enum):
    """Enum que indica si el turno es de mañana, tarde o noche."""

    M = "Mañana"
    T = "Tarde"
    N = "Noche"


TURNOS_BASICOS = ["M", "T", "N", "im", "it", "in"]
"""Turnos básicos según definidos en la última página
del turnero mensual de controladores aéreos.
Estos turnos pueden aparecer solos o con un código adicional.
"""

CODIGOS_DE_TURNO = {
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
"""Códigos de turno y descripciones según definidas en la última página
del turnero mensual de controladores aéreos."""

PUESTOS_CARRERA = {"TS", "IS", "TI", "INS", "PTD", "CON", "SUP", "N/A"}

MESES_EN_UN_AÑO = 12
NUMERO_DIA_DOMINGO = 6


def period_from_code(code: str) -> TipoTurno:
    """Get the period from a shift code."""
    if code in TURNOS_BASICOS and len(code) > 1 and code[1].upper() in TURNOS_BASICOS:
        return TipoTurno[code[1].upper()]

    if code in ("MSM", "TSM", "ME", "TE", "MR", "TR"):
        return TipoTurno[code[0]]

    if code[0] in TURNOS_BASICOS:
        return TipoTurno[code[0].upper()]

    return TipoTurno["M"]


def description_from_code(code: str) -> str:
    """Get the description from a shift code."""
    if code in CODIGOS_DE_TURNO:
        return CODIGOS_DE_TURNO[code]
    if code[1:] in CODIGOS_DE_TURNO:
        return CODIGOS_DE_TURNO[code[1:]]
    return code


def es_admin(email: str) -> bool:
    """Check if the user is an admin.

    Checks the es_admin column in Users.
    If no users have the es_admin flag set, the first user to log in becomes the admin.

    """
    user = ATC.query.filter_by(email=email).first()
    if user:
        # The user was found
        return user.es_admin

    # User is not an admin. Check whether anyone is an admin.
    return not ATC.query.filter_by(es_admin=True).first()


@dataclass
class Turno:
    """Shift information."""

    period: TipoTurno
    codigo: str
    descripcion: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


@dataclass
class Dia:
    """Day information."""

    fecha: date
    dia_de_la_semana: str
    es_festivo_nacional: bool
    turno: Turno | None = None


@dataclass
class CalendarioMensual:
    """Calendario mensual de un ATC.

    El objetivo de esta clase es facilitar la presentación de un calendario
    mensual en una plantilla HTML.
    """

    año: int
    mes: int
    _dias: list[Dia] = field(default_factory=list)

    @property
    def dias(self) -> list[Dia]:
        """Return the days in the month.

        But only those in the actual month.
        """
        return [day for day in self._dias if day.fecha.month == self.mes]

    @property
    def semanas(self) -> list[list[Dia]]:
        """Return the days in the month grouped by weeks."""
        weeks = []
        week = []
        for day in self._dias:
            week.append(day)
            if day.fecha.weekday() == NUMERO_DIA_DOMINGO:
                weeks.append(week)
                week = []
        if week:
            weeks.append(week)  # Add the last week if it wasn't added
        return weeks

    @property
    def nombre_mes(self) -> str:
        """Return the name of the month."""
        return self.dias[0].fecha.strftime("%B").capitalize()


class GenCalMensual:
    """Generate a calendar for a month and year and user."""

    @staticmethod
    def generate(
        año: int,
        mes: int,
        atc: ATC | None = None,
        session: Session | None = None,
    ) -> CalendarioMensual:
        """Generate a calendar for a month and year."""
        dias: list[Dia] = []
        first_day = date(año, mes, 1)
        last_day = GenCalMensual._ultimo_dia_del_mes(año, mes)

        # Determine the start of the calendar
        # (possibly including days from the previous month)
        start_date = first_day - timedelta(days=first_day.weekday())

        # Determine the end of the calendar
        # (possibly including days from the next month)
        end_date = last_day + timedelta(days=(6 - last_day.weekday()))

        current_date = start_date
        while current_date <= end_date:
            day_of_week = current_date.strftime("%A")
            is_national_holiday = GenCalMensual._verifica_fiesta_nacional(current_date)
            dias.append(
                Dia(
                    fecha=current_date,
                    dia_de_la_semana=day_of_week,
                    es_festivo_nacional=is_national_holiday,
                ),
            )
            current_date += timedelta(days=1)

        if not atc or not session:
            return CalendarioMensual(año=año, mes=mes, _dias=dias)

        # Go through every shift in the database matching the user id
        # and the date within the dates of the calendar
        min_date, max_date = dias[0].fecha, dias[-1].fecha
        user_shifts = (
            session.query(DBShift)
            .filter(
                DBShift.id_atc == atc.id,
                DBShift.fecha.between(min_date, max_date),
            )
            .all()
        )

        # Add a Shift dataclass for each day that has a shift
        turnos_por_fecha = {dbshift.fecha: dbshift for dbshift in user_shifts}

        for dia in (dia for dia in dias if dia.fecha in turnos_por_fecha):
            dbshift = turnos_por_fecha[dia.fecha]
            dia.turno = Turno(
                period=period_from_code(dbshift.turno),
                codigo=dbshift.turno,
                descripcion=description_from_code(dbshift.turno),
            )

        return CalendarioMensual(año=año, mes=mes, _dias=dias)

    @staticmethod
    def _ultimo_dia_del_mes(año: int, mes: int) -> date:
        if mes == MESES_EN_UN_AÑO:
            return date(año, 12, 31)
        return date(año, mes + 1, 1) - timedelta(days=1)

    @staticmethod
    def _verifica_fiesta_nacional(date_to_check: date) -> bool:
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
