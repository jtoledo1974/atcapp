"""Test cases for the cambios module."""

from datetime import date

from cambios.cambios import Day, MonthCalendar, Shift, ShiftType


def test_shift() -> None:
    """Test the Shift data class."""
    shift = Shift(type=ShiftType.M, code="M01", start_time=None, end_time=None)
    assert shift.type == ShiftType.M
    assert shift.code == "M01"
    assert shift.start_time is None
    assert shift.end_time is None


def test_day() -> None:
    """Test the Day data class."""
    day = Day(date=date(2024, 5, 1), day_of_week="Wednesday", is_national_holiday=False)
    assert day.date == date(2024, 5, 1)
    assert day.day_of_week == "Wednesday"
    assert not day.is_national_holiday
    assert day.shift is None


def test_month_calendar_days() -> None:
    """Test the generation of days in MonthCalendar."""
    calendar = MonthCalendar(2024, 5)
    days = calendar.days

    # Check the number of days including the days
    # from previous and next months to fill weeks
    assert len(days) == 35

    # Check first and last days of the calendar view
    assert days[0].date == date(2024, 4, 29)
    assert days[-1].date == date(2024, 6, 2)

    # Check specific day details
    assert days[2].date == date(2024, 5, 1)
    assert days[2].day_of_week == "Wednesday"
    assert days[2].is_national_holiday

    assert days[32].date == date(2024, 5, 31)
    assert days[32].day_of_week == "Friday"
    assert not days[32].is_national_holiday


def test_month_calendar_holidays() -> None:
    """Test the identification of national holidays in MonthCalendar."""
    calendar = MonthCalendar(2024, 1)
    holidays = [day for day in calendar.days if day.is_national_holiday]

    # Check if the holidays are correctly identified
    assert len(holidays) == 1
    assert holidays[0].date == date(2024, 1, 1)


def test_month_calendar_weeks() -> None:
    """Test the week-wise iteration in MonthCalendar."""
    calendar = MonthCalendar(2024, 5)
    weeks = calendar.get_weeks()

    # Check the number of weeks
    assert len(weeks) == 5

    # Check the first week
    first_week = weeks[0]
    assert first_week[0].date == date(2024, 4, 29)
    assert first_week[-1].date == date(2024, 5, 5)

    # Check the last week
    last_week = weeks[-1]
    assert last_week[0].date == date(2024, 5, 27)
    assert last_week[-1].date == date(2024, 6, 2)
