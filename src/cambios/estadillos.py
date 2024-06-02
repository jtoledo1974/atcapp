"""Procesado de estadillos.

Estas funciones deberían hacer más sencilla la presentación de los estadillos
por las plantillas.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, scoped_session

from .models import ATC, Estadillo, Periodo, Sector


@dataclass
class Grupo:
    """Grupo de controladores que llevan juntos un grupo de sectores.

    Podrían ser un 8x3 (ocho controladores, tres sectores) o un 3x1,
    u otras combinaciones.
    """

    controladores: set[ATC]
    sectores: set[Sector]


def identifica_grupos(estadillo: Estadillo, session: Session) -> list[Grupo]:
    """Identifica los grupos de controladores y sectores en un estadillo."""
    res: list[Grupo] = []

    # Obtener todos los periodos del estadillo
    periodos = session.query(Periodo).filter_by(id_estadillo=estadillo.id).all()

    # Crear un diccionario que mapea cada controlador a los sectores en los que trabaja
    sectores_por_controlador: dict[ATC, set[Sector]] = defaultdict(set)
    for periodo in periodos:
        if periodo.sector:
            sectores_por_controlador[periodo.controlador].add(periodo.sector)

    controladores_sin_asignar = set(sectores_por_controlador.keys())

    # Mientras haya controladores sin asignar, buscamos grupos
    while controladores_sin_asignar:
        controlador = controladores_sin_asignar.pop()
        sectores_asociados = sectores_por_controlador[controlador]

        # Inicializar el nuevo grupo con el controlador actual
        grupo_controladores = {controlador}
        grupo_sectores = set(sectores_asociados)

        # Buscar controladores que compartan sectores con el controlador actual
        for otro_controlador in controladores_sin_asignar.copy():
            if sectores_asociados & sectores_por_controlador[otro_controlador]:
                grupo_controladores.add(otro_controlador)
                grupo_sectores.update(sectores_por_controlador[otro_controlador])
                controladores_sin_asignar.remove(otro_controlador)

        res.append(Grupo(controladores=grupo_controladores, sectores=grupo_sectores))

    return res


def get_user_estadillo(user: ATC, session: scoped_session) -> list[dict[str, Any]]:
    """Get the latest estadillo for the user."""
    latest_estadillo = (
        session.query(Estadillo)
        .join(Estadillo.atcs)
        .filter(ATC.id == user.id)
        .order_by(Estadillo.fecha.desc())
        .first()
    )

    if not latest_estadillo:
        return []

    user_periodos = (
        session.query(Periodo)
        .filter(
            Periodo.id_controlador == user.id,
            Periodo.id_estadillo == latest_estadillo.id,
        )
        .order_by(Periodo.hora_inicio)
        .all()
    )

    estadillo_data = []
    for periodo in user_periodos:
        sector = periodo.sector.nombre if periodo.sector else "DESCANSO"
        periodo_data = {
            "hora_inicio": periodo.hora_inicio,
            "hora_fin": periodo.hora_fin,
            "sector": sector,
            "actividad": periodo.actividad,
            "ejecutivo": None,
            "planificador": None,
        }

        # Find partners in the same sector at the same time
        same_sector_periodos = (
            session.query(Periodo)
            .filter(
                Periodo.id_estadillo == latest_estadillo.id,
                Periodo.id_sector == periodo.id_sector,
                Periodo.hora_inicio == periodo.hora_inicio,
                Periodo.id_controlador != user.id,
            )
            .all()
        )

        for p in same_sector_periodos:
            atc = session.query(ATC).get(p.id_controlador)
            if not atc:
                continue
            if p.actividad == "E":
                periodo_data["ejecutivo"] = f"{atc.nombre} {atc.apellidos}"
            elif p.actividad == "P":
                periodo_data["planificador"] = f"{atc.nombre} {atc.apellidos}"

        estadillo_data.append(periodo_data)

    return estadillo_data


def get_general_estadillo(
    latest_estadillo: Estadillo,
    session: scoped_session,
) -> list[dict[str, Any]]:
    """Get the general estadillo for the control room."""
    all_periodos = (
        session.query(Periodo)
        .filter(Periodo.id_estadillo == latest_estadillo.id)
        .order_by(Periodo.hora_inicio)
        .all()
    )

    estadillo_general = []
    for atc in latest_estadillo.atcs:
        atc_periodos = [p for p in all_periodos if p.id_controlador == atc.id]
        atc_data = {"nombre": f"{atc.nombre} {atc.apellidos}", "periodos": []}

        for periodo in atc_periodos:
            sector = periodo.sector.nombre if periodo.sector else "DESCANSO"
            periodo_data = {
                "hora_inicio": periodo.hora_inicio,
                "hora_fin": periodo.hora_fin,
                "sector": sector,
                "actividad": periodo.actividad,
            }
            atc_data["periodos"].append(periodo_data)
        estadillo_general.append(atc_data)

    return estadillo_general
