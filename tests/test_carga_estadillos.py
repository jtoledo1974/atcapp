"""Tests for the daily shifts upload module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

import pdfplumber
import pytest
from cambios.carga_estadillo import (
    DatosEstadilloTexto,
    extraer_datos_estadillo,
    guardar_datos_estadillo,
)
from cambios.models import (
    EstadilloDiario,
)
from cambios.utils import find_user
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

if TYPE_CHECKING:
    from typing import Any, Generator

    from pdfplumber import PDF
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


@pytest.fixture(scope="session")
def pdf() -> Generator[PDF, Any, Any]:
    """Open the test PDF file."""
    test_file_path = Path(__file__).parent / "resources" / "test_estadillo.pdf"
    with pdfplumber.open(test_file_path):
        yield pdfplumber.open(test_file_path)


def test_extract_shift_data(pdf: PDF) -> None:
    """Test extracting the people data from the first page."""
    data = extraer_datos_estadillo(pdf.pages[0])

    assert data
    assert isinstance(data, DatosEstadilloTexto)
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


def test_shift_data_to_tables(
    pdf: PDF,
    db_session: scoped_session,
) -> None:
    """Test populating the model tables with the data extracted."""
    data = extraer_datos_estadillo(pdf.pages[0])
    guardar_datos_estadillo(data, db_session)

    # Check the control room shift
    shift = db_session.query(EstadilloDiario).first()
    assert shift
    assert shift.dependencia == data.dependencia
    assert shift.fecha.strftime("%d.%m.%Y") == data.fecha

    for nombre_controlador in data.jefes_de_sala:
        assert find_user(nombre_controlador, db_session) is not None

    for nombre_controlador in data.supervisores:
        assert find_user(nombre_controlador, db_session) is not None

    for nombre_controlador in data.tcas:
        assert find_user(nombre_controlador, db_session) is not None

    # Any controllers names mentioned on the first page should now exist
    # in the Users table
    for controller in data.controladores:
        user = find_user(controller, db_session)
        assert user
        assert user.categoria == data.controladores[controller].role
