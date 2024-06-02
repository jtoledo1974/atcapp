"""Verifica la lógica de los estadillos."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cambios.models import Estadillo
    from sqlalchemy.orm import Session


def test_identifica_grupos(estadillo: Estadillo, preloaded_session: Session) -> None:
    """Verifica que se identifiquen correctamente los grupos de controladores."""
    from cambios.estadillos import identifica_grupos

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
