"""Tests for the daily shifts upload module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

import pdfplumber
import pytest
from cambios.daily_shift_upload import (
    TextShiftData,
    extract_shift_data,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Database setup for testing
@pytest.fixture(scope="module")
def db_session() -> Generator[scoped_session[Session], Any, Any]:
    """Create a new database session for testing."""
    engine = create_engine("sqlite:///:memory:")
    session_factory = sessionmaker(bind=engine)
    session = scoped_session(session_factory)

    # Create all tables
    from cambios.models import db

    db.metadata.create_all(engine)
    yield session
    session.close()
    engine.dispose()


def test_extract_shift_data() -> None:
    """Test extracting the people data from the first page."""
    test_file_path = Path(__file__).parent / "resources" / "test_daily_schedule.pdf"

    with pdfplumber.open(test_file_path) as pdf:
        first_page = pdf.pages[0]
        data = extract_shift_data(first_page)

    assert data
    assert isinstance(data, TextShiftData)
    assert data.dependencia == "LECS"
    assert data.fecha == "27.05.2024"
    assert data.turno == "M"
    assert data.jefes_de_sala
    assert data.supervisores
    assert data.tcas
    assert data.controladores
    assert data.sectores

    assert "OLMEDO JIMENEZ JOSE ANTONIO" in data.jefes_de_sala
    assert "SANZ LLORENTE MIGUEL ANGEL" in data.supervisores
    assert "GALLEGO PAGAN ANTONIO GINES" in data.tcas

    assert "ASENSIO GONZALEZ JUAN CARLOS" in data.controladores
    assert data.controladores["ASENSIO GONZALEZ JUAN CARLOS"].role == "CON"
    assert data.controladores["ASENSIO GONZALEZ JUAN CARLOS"].sectors == {"TPR1"}
    assert data.controladores["TRUJILLO GUERRA RAFAEL"].sectors == {"SUR", "SEV"}

    expected_sectors = {"TPR1", "ASN", "ASV", "CEN", "MAR", "NO1", "SEV", "SUR"}
    assert data.sectores == expected_sectors

    assert (
        data.controladores["SEGURA OCAMPO CARLOS"].comments
        == "BASELGA VICENTE FERNANDO"
    )
    # Only two controllers have comments for them
    assert len([c.comments for c in data.controladores.values() if c.comments]) == 2

    assert len(data.controladores) == 21
