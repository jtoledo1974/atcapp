"""Helper module to deal with bulk database operations.

Useful for testing.
"""

from __future__ import annotations

import locale
import logging
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

from cambios.carga_estadillo import procesa_estadillo
from cambios.carga_turnero import procesa_turnero
from cambios.database import db
from cambios.models import ATC, Estadillo, Periodo, Sector, Servicio, TipoTurno, Turno
from cambios.models import __file__ as models_file
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

PICKLE_FILE = Path(__file__).parent.parent / "tests" / "resources" / "test_db.pickle"
# No usar estos paths. Usar los fixtures estadillo_path y turnero_path
__TEST_ESTADILLO_PATH = Path(__file__).parent / "resources" / "test_estadillo.pdf"
__TEST_TURNERO_PATH = Path(__file__).parent / "resources" / "test_turnero.pdf"

locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def create_in_memory_db() -> Session:
    """Crea una base de datos en memoria para pruebas."""
    engine = create_engine("sqlite:///:memory:")
    db.metadata.create_all(engine)

    return sessionmaker(bind=engine)()


def create_test_data(session: Session) -> None:
    """Crea datos de prueba en la base de datos."""
    with __TEST_TURNERO_PATH.open("rb") as file:
        procesa_turnero(file, session, add_new=True)  # type: ignore[arg-type]
    with __TEST_ESTADILLO_PATH.open("rb") as file:
        procesa_estadillo(file, session)  # type: ignore[arg-type]

    # Print the number of rows in the users and shifts tables
    _msg = f"Users {session.query(ATC).count()}, Shifts {session.query(Turno).count()}"
    logger.info(_msg)


def save_fixture(session: Session) -> None:
    """Guarda los datos de la base de datos en un archivo pickle.

    El objetivo es que los tests puedan usar una base de datos precargada.
    """
    data = {
        "users": [user.__dict__ for user in session.query(ATC).all()],
        "shifts": [shift.__dict__ for shift in session.query(Turno).all()],
        "shift_types": [
            shift_type.__dict__ for shift_type in session.query(TipoTurno).all()
        ],
        "estadillos": [
            estadillo.__dict__ for estadillo in session.query(Estadillo).all()
        ],
        "periodos": [periodo.__dict__ for periodo in session.query(Periodo).all()],
        "sectores": [sector.__dict__ for sector in session.query(Sector).all()],
        "servicios": [servicio.__dict__ for servicio in session.query(Servicio).all()],
    }
    with PICKLE_FILE.open("wb") as file:
        pickle.dump(
            {
                key: [dict(item, _sa_instance_state=None) for item in value]
                for key, value in data.items()
            },
            file,
        )


def load_fixture() -> Session:
    """Carga los datos de un archivo pickle en una base de datos en memoria."""
    with PICKLE_FILE.open("rb") as file:
        data = pickle.load(file)  # noqa: S301

    session = create_in_memory_db()

    for table, table_data in (
        [ATC, data["users"]],
        [Turno, data["shifts"]],
        [TipoTurno, data["shift_types"]],
        [Estadillo, data["estadillos"]],
        [Periodo, data["periodos"]],
        [Sector, data["sectores"]],
        [Servicio, data["servicios"]],
    ):
        for item in table_data:
            item.pop("_sa_instance_state", None)
            session.add(table(**item))

    session.commit()
    return session


def should_regenerate_pickle() -> bool:
    """Determina si es necesario regenerar el archivo pickle."""
    if not PICKLE_FILE.exists():
        return True

    pickle_mtime = PICKLE_FILE.stat().st_mtime
    models_mtime = Path(models_file).stat().st_mtime
    save_fixture_mtime = Path(__file__).stat().st_mtime
    turnero_mtime = __TEST_TURNERO_PATH.stat().st_mtime
    estadillo_mtime = __TEST_ESTADILLO_PATH.stat().st_mtime

    # Regenerar si el archivo de modelos es más reciente que el pickle
    if models_mtime > pickle_mtime:
        logger.info("Módulo Models ha cambiado. Regenerando pickle.")
        return True

    if save_fixture_mtime > pickle_mtime:
        logger.info("Módulo pickled_db ha cambiado. Regenerando pickle.")
        return True

    if turnero_mtime > pickle_mtime:
        logger.info("Archivo de turnero ha cambiado. Regenerando pickle.")
        return True

    if estadillo_mtime > pickle_mtime:
        logger.info("Archivo de estadillo ha cambiado. Regenerando pickle.")
        return True

    return False
