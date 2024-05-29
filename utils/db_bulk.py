"""Helper module to deal with bulk database operations.

Useful for testing.
"""

import locale
import pickle
from pathlib import Path

from cambios.carga_turnero import procesa_turnero
from cambios.database import db
from cambios.models import ATC, TipoTurno, Turno
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PICKLE_FILE = Path(__file__).parent.parent / "tests" / "resources" / "test_db.pickle"

locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")


def create_in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    db.metadata.create_all(engine)

    return sessionmaker(bind=engine)()


def create_test_data(session):
    test_file_path = (
        Path(__file__).parent.parent / "tests" / "resources" / "test_turnero.pdf"
    )
    with test_file_path.open("rb") as file:
        procesa_turnero(file, session, add_new=True)

    # Print the number of rows in the users and shifts tables
    print(
        f"Users {session.query(ATC).count()}, Shifts {session.query(Turno).count()}",
    )


def save_fixture(session):
    data = {
        "users": [user.__dict__ for user in session.query(ATC).all()],
        "shifts": [shift.__dict__ for shift in session.query(Turno).all()],
        "shift_types": [
            shift_type.__dict__ for shift_type in session.query(TipoTurno).all()
        ],
    }
    with open(PICKLE_FILE, "wb") as file:
        pickle.dump(
            {
                key: [dict(item, _sa_instance_state=None) for item in value]
                for key, value in data.items()
            },
            file,
        )


def load_fixture():
    with open(PICKLE_FILE, "rb") as file:
        data = pickle.load(file)

    session = create_in_memory_db()

    for table, data in (
        [ATC, data["users"]],
        [Turno, data["shifts"]],
        [TipoTurno, data["shift_types"]],
    ):
        for item in data:
            item.pop("_sa_instance_state", None)
            session.add(table(**item))

    session.commit()

    return session


def main():
    session = create_in_memory_db()
    create_test_data(session)
    save_fixture(session)

    # Load the fixture
    loaded_session = load_fixture()

    # Now you can query the loaded database using the session
    users = loaded_session.query(ATC).all()
    shifts = loaded_session.query(Turno).all()
    shift_types = loaded_session.query(TipoTurno).all()
    print(
        f"Users {loaded_session.query(ATC).count()}, Shifts {loaded_session.query(Turno).count()}",
    )

    # Do something with the data...


if __name__ == "__main__":
    main()
