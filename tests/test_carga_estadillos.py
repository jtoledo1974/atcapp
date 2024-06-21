"""Tests for the daily shifts upload module."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

import pytest
import pytz
from cambios import get_timezone
from cambios.carga_estadillo import (
    EstadilloTexto,
    extraer_datos_estadillo,
    extraer_periodos,
    guardar_datos_estadillo,
    procesa_estadillo,
    string_to_utc_datetime,
)
from cambios.models import (
    ATC,
    Estadillo,
    Periodo,
    Sector,
    Servicio,
)
from cambios.user_utils import find_user

if TYPE_CHECKING:
    from pathlib import Path

    from pdfplumber import PDF
    from sqlalchemy.orm import scoped_session


def test_extraer_datos_generales(pdf_estadillo: PDF) -> None:
    """Comprueba que se extraen los datos generales del estadillo."""
    data = extraer_datos_estadillo(pdf_estadillo.pages[0])

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


def test_extraer_periodos(pdf_estadillo: PDF) -> None:
    """Comprueba que se extraen los periodos de los controladores."""
    data = extraer_datos_estadillo(pdf_estadillo.pages[0])
    periodos = extraer_periodos(pdf_estadillo.pages[1])

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
    pdf_estadillo: PDF,
    session: scoped_session,
) -> None:
    """Comprobar que los datos del estadillo se guardan en la base de datos."""
    data = extraer_datos_estadillo(pdf_estadillo.pages[0])
    guardar_datos_estadillo(data, session, get_timezone())

    # Check the control room shift
    shift = session.query(Estadillo).first()
    assert shift
    assert shift.dependencia == data.dependencia
    assert shift.fecha.strftime("%d.%m.%Y") == data.fecha

    for nombre_controlador in data.jefes_de_sala:
        assert find_user(nombre_controlador, session) is not None

    for nombre_controlador in data.supervisores:
        assert find_user(nombre_controlador, session) is not None

    for nombre_controlador in data.tcas:
        assert find_user(nombre_controlador, session) is not None

    # Any controllers names mentioned on the first page should now exist
    # in the Users table
    for nombre_controlador in data.controladores:
        user = find_user(nombre_controlador, session)
        assert user
        assert user.categoria == data.controladores[nombre_controlador].puesto

    # Verificar sectores
    for sector in data.sectores:
        assert (
            session.query(Estadillo)
            .filter(Estadillo.sectores.any(nombre=sector))
            .first()
        )

    # Verificar que cada controlador mencionado tiene en el estadillo
    # los sectores que le tocan
    for nombre_controlador, controlador in data.controladores.items():
        user = find_user(nombre_controlador, session)
        assert user
        for sector_name in controlador.sectores:
            assert (
                session.query(Estadillo)
                .filter(Estadillo.sectores.any(nombre=sector_name))
                .first()
            )

    # Verificar que podemos encontrar este estadillo referenciado
    # en la tabla atcs_estadillos
    db_estadillo = session.query(Estadillo).first()
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

    # Verificar que horas de inicio y final de los periodos no son naif
    for servicio in controladores:
        for periodo in servicio.atc.periodos:
            assert periodo.hora_inicio.tzinfo
            assert periodo.hora_fin.tzinfo


def test_string_to_utc_datetime() -> None:
    """Comprobar que la función string_to_utc_datetime convierte correctamente."""
    # Test the conversion of a string to a datetime object
    date_str = "27.05.2024"
    time_str = "07:30"
    tz = pytz.timezone("Europe/Madrid")
    date = datetime.strptime(date_str, "%d.%m.%Y").date()  # noqa: DTZ007
    dt = string_to_utc_datetime(time_str, date, tz)
    assert dt.strftime("%d.%m.%Y") == date_str
    assert dt.strftime("%H:%M") == "05:30"

    # Test the conversion of a string to a datetime object
    date_str = "01.01.2024"
    time_str = "15:00"
    date = datetime.strptime(date_str, "%d.%m.%Y").date()  # noqa: DTZ007
    dt = string_to_utc_datetime(time_str, date, tz)
    assert dt.strftime("%d.%m.%Y") == date_str
    assert dt.strftime("%H:%M") == "14:00"


def test_periodos_a_db(
    pdf_estadillo: PDF,
    session: scoped_session,
    estadillo_path: Path,
) -> None:
    """Comprobar que los periodos de los controladores van a la base de datos."""
    with estadillo_path.open("rb") as file:
        estadillo_db = procesa_estadillo(file, session)

    periodos = extraer_periodos(pdf_estadillo.pages[1])

    atcs = [
        servicio.atc
        for servicio in estadillo_db.servicios
        if servicio.rol == "Controlador"
    ]

    assert len(atcs) == len(periodos)

    for atc in atcs:
        if atc.apellidos_nombre not in periodos:
            for nombre_controlador in periodos:
                if atc.apellidos_nombre.startswith(nombre_controlador):
                    break
            else:
                pytest.fail(f"Controlador {atc.apellidos_nombre} no encontrado")

    hora_inicio = atcs[0].periodos[0].hora_inicio
    hora_fin = atcs[-1].periodos[-1].hora_fin

    assert hora_inicio.strftime("%H:%M") == "05:30"
    assert hora_fin.strftime("%H:%M") == "13:00"

    # Check that everybody has the same start and end time
    for atc in atcs:
        assert atc.periodos[0].hora_inicio == hora_inicio
        assert atc.periodos[-1].hora_fin == hora_fin


def test_subir_dos_veces_lo_deja_igual(
    session: scoped_session,
    estadillo_path: Path,
) -> None:
    """Comprobar que subir un estadillo dos veces no cambia nada."""
    session = session()
    with estadillo_path.open("rb") as file:
        _estadillo_db = procesa_estadillo(file, session)
    n_estadillos = session.query(Estadillo).count()
    n_servicios = session.query(Servicio).count()
    n_periodos = session.query(Periodo).count()
    n_sectores = session.query(Sector).count()
    n_atcs = session.query(ATC).count()

    with estadillo_path.open("rb") as file:
        _estadillo_db2 = procesa_estadillo(file, session)
    n_estadillos2 = session.query(Estadillo).count()
    n_servicios2 = session.query(Servicio).count()
    n_periodos2 = session.query(Periodo).count()
    n_sectores2 = session.query(Sector).count()
    n_atcs2 = session.query(ATC).count()

    assert n_estadillos == n_estadillos2
    assert n_servicios == n_servicios2
    assert n_periodos == n_periodos2
    assert n_sectores == n_sectores2
    assert n_atcs == n_atcs2


def test_eliminacion_en_cascada(session: scoped_session) -> None:
    """Comprobar que se eliminan los servicios en cascada."""
    # Crear un nuevo estadillo con servicios
    estadillo = Estadillo(
        fecha=date.today(),  # noqa: DTZ011
        dependencia="TWR",
        turno="M",
    )
    servicio = Servicio(id_atc=1, id_estadillo=1, categoria="CAT1", rol="ROL1")
    estadillo.servicios.append(servicio)

    session.add(estadillo)
    session.commit()

    # Verificar que el servicio fue agregado
    assert session.query(Servicio).count() == 1

    # Eliminar el estadillo
    session.delete(estadillo)
    session.commit()

    # Verificar que el servicio fue eliminado en cascada
    assert session.query(Servicio).count() == 0


def test_horas_guardadas_en_utc(
    pdf_estadillo: PDF,
    session: scoped_session,
    estadillo_path: Path,
) -> None:
    """Comprobar que las horas de los periodos se guardan en UTC."""
    # Procesar el estadillo y guardar en la base de datos
    with estadillo_path.open("rb") as file:
        procesa_estadillo(file, session)

    # Obtener los periodos de la base de datos
    periodos = session.query(Periodo).all()

    assert periodos, "No se encontraron periodos en la base de datos."

    tz = get_timezone()

    for periodo in periodos:
        # Asumir que los datetime almacenados están en UTC
        hora_inicio_utc = datetime.combine(
            periodo.hora_inicio.date(),
            periodo.hora_inicio.time(),
        ).replace(tzinfo=timezone.utc)
        hora_fin_utc = datetime.combine(
            periodo.hora_fin.date(),
            periodo.hora_fin.time(),
        ).replace(tzinfo=timezone.utc)

        # Convertir las horas almacenadas en UTC a la zona horaria local para verificar
        hora_inicio_local = hora_inicio_utc.astimezone(tz)
        hora_fin_local = hora_fin_utc.astimezone(tz)

        # La base de datos tiene las fechas guardadas como UTC,
        # pero son datos naive. Para compararlas hay que convertirlas
        # a la zona horaria local
        assert (
            hora_inicio_local.time() == periodo.hora_inicio_utc.astimezone(tz).time()
        ), f"hora_inicio {hora_inicio_local} no coincide con la hora local esperada {hora_inicio_local}"
        assert (
            hora_fin_local.time() == periodo.hora_fin_utc.astimezone(tz).time()
        ), f"hora_fin {hora_fin_local} no coincide con la hora local esperada {hora_fin_local}"
