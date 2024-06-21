"""Cambios package."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pytz import timezone as tzinfo

if TYPE_CHECKING:  # pragma: no cover
    from pytz import _UTCclass
    from pytz.tzinfo import DstTzInfo, StaticTzInfo

logger = logging.getLogger(__name__)


def get_timezone(unit: str) -> _UTCclass | StaticTzInfo | DstTzInfo:
    """Get the timezone the ATC unit."""
    if unit.upper() in ("LECM", "LECS", "LECB"):
        return tzinfo("Europe/Madrid")
    if unit.upper() == "GCCC":
        return tzinfo("Atlantic/Canary")
    logger.warning("Dependencia desconocida %s. Usando zona horaria de Madrid.", unit)
    return tzinfo("Europe/Madrid")
