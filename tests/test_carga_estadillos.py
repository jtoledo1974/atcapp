"""Tests for the daily shifts upload module."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Generator

import pdfplumber
import pytest
from cambios.carga_estadillo import (
    EstadilloTexto,
    extraer_datos_estadillo,
    extraer_periodos,
    guardar_datos_estadillo,
    procesa_estadillo,
)
from cambios.models import (
    Estadillo,
)
from cambios.utils import find_user
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

if TYPE_CHECKING:
    from typing import Any, Generator

    from pdfplumber import PDF
    from sqlalchemy.orm import Session

TEST_ESTADILLO_PATH = Path(__file__).parent / "resources" / "test_estadillo.pdf"

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
    test_file_path = TEST_ESTADILLO_PATH
    with pdfplumber.open(test_file_path):
        yield pdfplumber.open(test_file_path)


def test_extraer_datos_generales(pdf: PDF) -> None:
    """Comprueba que se extraen los datos generales del estadillo."""
    data = extraer_datos_estadillo(pdf.pages[0])

    assert data
    assert isinstance(data, EstadilloTexto)
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
    assert data.controladores["ASENSIO GONZALEZ JUAN CARLOS"].puesto == "CON"
    assert data.controladores["ASENSIO GONZALEZ JUAN CARLOS"].sectores == {"TPR1"}
    assert data.controladores["TRUJILLO GUERRA RAFAEL"].sectores == {"SUR", "SEV"}

    expected_sectors = {"TPR1", "ASN", "ASV", "CEN", "MAR", "NO1", "SEV", "SUR"}
    assert data.sectores == expected_sectors

    assert (
        data.controladores["SEGURA OCAMPO CARLOS"].comentarios
        == "BASELGA VICENTE FERNANDO"
    )
    # Only two controllers have comments for them
    assert (
        len([c.comentarios for c in data.controladores.values() if c.comentarios]) == 2
    )

    assert len(data.controladores) == 21


def test_extraer_periodos(pdf: PDF) -> None:
    """Comprueba que se extraen los periodos de los controladores."""
    data = extraer_datos_estadillo(pdf.pages[0])
    periodos = extraer_periodos(pdf.pages[1])

    assert isinstance(data, EstadilloTexto)

    # Comprobar que los los controladores en los datos
    # son los mismos que en los periodos
    c = set(data.controladores.keys())
    p = set(periodos.keys())

    # ESCUDERO MOUTIHNO DE FREITAS es caso particular,
    # porque no cabe en los detalles y se le quitó el nombre
    # los quitamos de los sets
    nombre_completo = "ESCUDERO MOUTINHO DE FREITAS CATARINA"
    assert (nombre_completo) in c
    c.remove(nombre_completo)
    apellidos = "ESCUDERO MOUTINHO DE FREITAS"
    assert (apellidos) in p
    p.remove(apellidos)

    assert set(c) == set(p)

    # comprobar que todo el mundo tiene o bien uno, o bien seis o más periodos
    for nombre_controlador in periodos:
        n_periodos = len(periodos[nombre_controlador])
        assert n_periodos == 1 or n_periodos >= 6

    # Comprobar que todo el mundo tiene un periodo que comienza bien a las
    # 07:30, a las 8:07 a las 8:20
    for nombre_controlador in periodos:
        assert any(
            periodo.hora_inicio in ("07:30", "08:07", "08:20")
            for periodo in periodos[nombre_controlador]
        )


def test_datos_generales_estadillo_a_db(
    pdf: PDF,
    db_session: scoped_session,
) -> None:
    """Comprobar que los datos del estadillo se guardan en la base de datos."""
    data = extraer_datos_estadillo(pdf.pages[0])
    guardar_datos_estadillo(data, db_session)

    # Check the control room shift
    shift = db_session.query(Estadillo).first()
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
    for nombre_controlador in data.controladores:
        user = find_user(nombre_controlador, db_session)
        assert user
        assert user.categoria == data.controladores[nombre_controlador].puesto

    # Verificar sectores
    for sector in data.sectores:
        assert (
            db_session.query(Estadillo)
            .filter(Estadillo.sectores.any(nombre=sector))
            .first()
        )

    # Verificar que cada controlador mencionado tiene en el estadillo
    # los sectores que le tocan
    for nombre_controlador, controlador in data.controladores.items():
        user = find_user(nombre_controlador, db_session)
        assert user
        for sector_name in controlador.sectores:
            assert (
                db_session.query(Estadillo)
                .filter(Estadillo.sectores.any(nombre=sector_name))
                .first()
            )

    # Verificar que podemos encontrar este estadillo referenciado
    # en la tabla atcs_estadillos
    db_estadillo = db_session.query(Estadillo).first()
    assert db_estadillo
    assert db_estadillo.atcs

    # Contar los servicios asociados a este estadillo cuyo
    # rol es de Controlador
    controladores = [
        servicio for servicio in db_estadillo.servicios if servicio.rol == "Controlador"
    ]
    assert len(controladores) == len(data.controladores)

    for servicio in db_estadillo.servicios:
        if servicio.rol != "Controlador":
            continue
        assert servicio.atc.apellidos_nombre in data.controladores


def test_periodos_a_db(pdf: PDF, db_session: scoped_session) -> None:
    """Comprobar que los periodos de los controladores van a la base de datos."""
    with TEST_ESTADILLO_PATH.open("rb") as file:
        procesa_estadillo(file, db_session)

    periodos = extraer_periodos(pdf.pages[1])

    for nombre_controlador, periodos_controlador in periodos.items():
        user = find_user(nombre_controlador, db_session)
        assert user
        assert len(periodos_controlador) == len(user.periodos)
            
