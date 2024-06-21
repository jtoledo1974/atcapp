"""Cambios package."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from pytz import timezone as tzinfo

if TYPE_CHECKING:  # pragma: no cover
    from pytz import _UTCclass
    from pytz.tzinfo import DstTzInfo, StaticTzInfo

_DEFAULT_TIMEZONE = "Europe/Madrid"
_TZ = tzinfo(_DEFAULT_TIMEZONE)


def get_timezone() -> _UTCclass | StaticTzInfo | DstTzInfo:
    """Get the timezone for the app."""
    return _TZ


def configure_timezone(timezone: str | None = None) -> None:
    """Configure the timezone for the app.

    if no argument is passed, the timezone is set to environment variable TZ.
    Else the hardcoded default stays.
    """
    if not timezone:
        timezone = os.getenv("TZ", _DEFAULT_TIMEZONE)
    global _TZ  # noqa: PLW0603
    _TZ = tzinfo(timezone)
