"""Processes the uploaded daily schedule file.

process_file is the main function that processes the uploaded daily schedule file.
It extracts the schedule data from the file, parses the data, and inserts it
into the database. The function uses the extract_schedule_data function to
extract the schedule data from each page of the uploaded file. The extracted
data is then parsed using the parse_and_insert_data function, which inserts
the data into the database.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pdfplumber

if TYPE_CHECKING:  # pragma: no cover
    from logging import Logger


logger: Logger


def setup_logger(app_logger: Logger | None) -> None:
    """Set up the logger."""
    global logger  # noqa: PLW0603
    if app_logger:
        logger = app_logger
        return

    logger = logging.getLogger(__name__)


@dataclass
class Controller:
    """Text data for controllers extracted from the first page of the daily shift."""

    name: str
    role: str
    sectors: set[str] = field(default_factory=set)
    comments: str = ""


@dataclass
class TextShiftData:
    """Text data extracted from the first page of the daily shift."""

    dependencia: str = ""
    fecha: str = ""
    turno: str = ""
    jefes_de_sala: list[str] = field(default_factory=list)
    supervisores: list[str] = field(default_factory=list)
    tcas: list[str] = field(default_factory=list)
    controladores: dict[str, Controller] = field(default_factory=dict)
    sectores: set[str] = field(default_factory=set)


def extract_shift_data(page: pdfplumber.page.Page) -> TextShiftData:
    """Extract the schedule data from the first page.

    Mainly the people working and the sectors they are working in.
    """
    table = page.extract_table()
    if table is None:
        return TextShiftData()

    data = TextShiftData()

    # Extract dependencia, fecha, and turno from the first row
    header = table[0][0].split()  # type: ignore[union-attr]
    data.dependencia = header[0]
    data.fecha = header[1]
    data.turno = header[2]

    for row in table:
        if row[0] == "JEFES DE SALA":
            data.jefes_de_sala = [
                item  # type: ignore[misc]
                for item in row
                if item not in (None, "JEFES DE SALA")
            ]
        elif row[0] == "SUPERVISORES":
            data.supervisores = [
                item  # type: ignore[misc]
                for item in row
                if item not in (None, "SUPERVISORES")
            ]
        elif row[0] == "TCA":
            data.tcas = [
                item  # type: ignore[misc]
                for item in row
                if item not in (None, "TCA")
            ]
        elif row[1] and row[1].startswith("C"):
            controller_name = row[2]
            controller_role = row[3]
            if not controller_name:
                continue
            controller = Controller(
                name=controller_name,
                role=controller_role,  # type: ignore[arg-type]
            )
            data.controladores[controller_name] = controller
            sectors = [row[5], row[6], row[7]]
            for sector in sectors:
                if sector:
                    data.sectores.add(sector)
                    controller.sectors.add(sector)
            controller.comments = row[8]

    return data
