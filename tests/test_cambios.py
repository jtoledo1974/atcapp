"""Test cases for the cambios module."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from cambios.cambios import (
    Dia,
    MonthCalGen,
    ShiftPeriod,
    Turno,
    description_from_code,
    period_from_code,
)

if TYPE_CHECKING:
    from cambios.models import ATC
    from sqlalchemy.orm import Session


def test_period_from_code() -> None:
    """Test the period_from_code function."""
    assert period_from_code("M") == ShiftPeriod.M
    assert period_from_code("T") == ShiftPeriod.T
    assert period_from_code("N") == ShiftPeriod.N
    assert period_from_code("im") == ShiftPeriod.M
    assert period_from_code("it") == ShiftPeriod.T
    assert period_from_code("in") == ShiftPeriod.N
    assert period_from_code("X") == ShiftPeriod.M  # Default case
    assert period_from_code("ME") == ShiftPeriod.M
    assert period_from_code("TR") == ShiftPeriod.T


def test_description_from_code() -> None:
    """Test the description_from_code function."""
    assert description_from_code("SUP") == "SUPERVISIÓN"
    assert description_from_code("A1") == "TRABAJO EN FRECUENCIA"
    assert description_from_code("B01") == "MOTIVO MÉDICO: BAJA CON PARTE IT"
    assert description_from_code("TB01") == "MOTIVO MÉDICO: BAJA CON PARTE IT"
    assert description_from_code("NB01") == "MOTIVO MÉDICO: BAJA CON PARTE IT"
    assert description_from_code("C01") == "INSTRUCTOR IMPARTIENDO FORMACIÓN TEÓRICA"
    assert description_from_code("B01v") == "VACUNACION COVID19"
    assert (
        description_from_code("M1") == "M1"
    )  # No matching description, return code itself
    assert (
        description_from_code("X") == "X"
    )  # No matching description, return code itself


def test_shift() -> None:
    """Test the Shift data class."""
    shift = Turno(period=ShiftPeriod.M, codigo="M01", start_time=None, end_time=None)
    assert shift.period == ShiftPeriod.M
    assert shift.codigo == "M01"
    assert shift.start_time is None
    assert shift.end_time is None


def test_day() -> None:
    """Test the Day data class."""
    day = Dia(
        fecha=date(2024, 5, 1),
        dia_de_la_semana="Miércoles",
        es_festivo_nacional=False,
    )
    assert day.fecha == date(2024, 5, 1)
    assert day.dia_de_la_semana == "Miércoles"
    assert not day.es_festivo_nacional
    assert day.turno is None


def test_month_calendar_days() -> None:
    """Test the generation of days in MonthCalendar."""
    calendar = MonthCalGen.generate(2024, 5)
    days = calendar.dias

    # Check the number of days including the days
    # from previous and next months to fill weeks
    weeks = calendar.semanas
    assert len(weeks) == 5

    # Check first and last days of the calendar view
    assert weeks[0][0].fecha == date(2024, 4, 29)
    assert weeks[-1][-1].fecha == date(2024, 6, 2)

    # Check specific day details
    assert days[0].fecha == date(2024, 5, 1)
    assert days[0].dia_de_la_semana == "miércoles"
    assert days[0].es_festivo_nacional

    assert days[30].fecha == date(2024, 5, 31)
    assert days[30].dia_de_la_semana == "viernes"
    assert not days[30].es_festivo_nacional


def test_month_calendar_holidays() -> None:
    """Test the identification of national holidays in MonthCalendar."""
    calendar = MonthCalGen.generate(2024, 1)
    holidays = [day for day in calendar.dias if day.es_festivo_nacional]

    # Check if the holidays are correctly identified
    assert len(holidays) == 1
    assert holidays[0].fecha == date(2024, 1, 1)


def test_month_calendar_weeks() -> None:
    """Test the week-wise iteration in MonthCalendar."""
    calendar = MonthCalGen.generate(2024, 5)
    weeks = calendar.semanas

    # Check the number of weeks
    assert len(weeks) == 5

    # Check the first week
    first_week = weeks[0]
    assert first_week[0].fecha == date(2024, 4, 29)
    assert first_week[-1].fecha == date(2024, 5, 5)

    # Check the last week
    last_week = weeks[-1]
    assert last_week[0].fecha == date(2024, 5, 27)
    assert last_week[-1].fecha == date(2024, 6, 2)


def test_load_weeks_from_user(atc: ATC, preloaded_session: Session) -> None:
    """Test loading weeks from user data."""
    calendar = MonthCalGen.generate(2024, 6, atc, preloaded_session)
    days = calendar.dias
    day = days[0]

    assert day.turno is not None
    assert day.turno.period == ShiftPeriod.M
    assert day.turno.codigo == "MB09"

    # Count shifts for the month
    shifts = [day for day in days if day.turno is not None]
    assert len(shifts) == 22
