"""Verifica la lógica de los estadillos."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import pytz
from cambios.estadillos import ColorManager, genera_datos_grupo, identifica_grupos

if TYPE_CHECKING:
    from cambios.models import Estadillo
    from sqlalchemy.orm import Session


@pytest.fixture()
def color_manager() -> ColorManager:
    """Fixture para el ColorManager."""
    return ColorManager()


def test_identifica_grupos(estadillo: Estadillo, preloaded_session: Session) -> None:
    """Verifica que se identifiquen correctamente los grupos de controladores."""
    grupos = identifica_grupos(estadillo, preloaded_session)
    assert len(grupos) == 4
    # Verifica que hay dos grupos de 8x3, uno de 3x1 y uno de 2x1
    assert len(grupos[0].controladores) == 2
    assert len(grupos[1].controladores) == 3
    assert len(grupos[2].controladores) == 8
    assert len(grupos[3].controladores) == 8

    # Comprobar que cada controlador del estadillo está en un grupo o ninguno
    controladores = {periodo.controlador for periodo in estadillo.periodos}
    controladores_en_grupos = {
        controlador for grupo in grupos for controlador in grupo.controladores
    }
    assert controladores == controladores_en_grupos


def test_genera_datos_grupo(
    estadillo: Estadillo,
    preloaded_session: Session,
    color_manager: ColorManager,
) -> None:
    """Verifica que se generen correctamente los datos de un grupo."""
    grupos = identifica_grupos(estadillo, preloaded_session)
    tz = pytz.timezone("Europe/Madrid")
    dg = genera_datos_grupo(grupos[2], color_manager, tz)
    assert dg
    assert set(dg.sectores) == {"ASV", "CEN", "MAR"}
    assert dg.atcs[0].nombre == "Francisco Victoria Alberdi"

    periodo_0 = dg.atcs[0].periodos[0]
    assert periodo_0.hora_inicio == "07:30"
    assert periodo_0.hora_fin == "08:45"
    assert periodo_0.actividad == "P-ASV"

    periodo_1 = dg.atcs[7].periodos[-1]
    assert periodo_1.hora_inicio == "13:45"
    assert periodo_1.hora_fin == "15:00"
    assert periodo_1.actividad == "P-CEN"

    duracion_atc = sum(periodo.duracion for periodo in dg.atcs[0].periodos)
    duracion_horas = sum(periodo.duracion for periodo in dg.horas_inicio)
    assert duracion_atc == duracion_horas
    assert duracion_atc == 450


def test_comprueba_duraciones_grupo(
    estadillo: Estadillo,
    preloaded_session: Session,
    color_manager: ColorManager,
) -> None:
    grupos = identifica_grupos(estadillo, preloaded_session)
    tz = pytz.timezone("Europe/Madrid")
    datos_grupos = [genera_datos_grupo(grupo, color_manager, tz) for grupo in grupos]

    # Comprobar las duraciones:
    duraciones = {
        periodo.duracion
        for dg in datos_grupos
        for atc in dg.atcs
        for periodo in atc.periodos
    }

    assert duraciones == {37, 38, 50, 75, 450}


def test_mismas_duraciones(estadillo: Estadillo, preloaded_session: Session) -> None:
    """Verifica que la duración_total de la jornada es igual para todos.

    Tienen que coincicidr entre todos los controladores de un grupo y con
    la duración total del grupo.
    """
    grupos = identifica_grupos(estadillo, preloaded_session)

    for grupo in grupos:
        duracion_total = grupo.duracion
        # Verificar que la duración total es de 7h30m en minutos
        assert duracion_total == 450
        for periodos in grupo.controladores.values():
            duracion_controlador = sum(periodo.duracion for periodo in periodos)
            assert duracion_total == duracion_controlador
