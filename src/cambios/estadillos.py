"""Procesado de estadillos.

Estas funciones deberían hacer más sencilla la presentación de los estadillos
por las plantillas.
"""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, scoped_session

from .models import ATC, Estadillo, Periodo, Sector


@dataclass
class Grupo:
    """Grupo de controladores que llevan juntos un grupo de sectores.

    Podrían ser un 8x3 (ocho controladres, tres sectores) o un 3x1,
    u otras combinaciones.
    """

    controladores: list[ATC]
    sectores: list[Sector]


def identifica_grupos(estadillo: Estadillo, session: Session) -> list[Grupo]:
    """Identifica los grupos de controladores y sectores en un estadillo.

    Args:
    ----
        estadillo: El estadillo a analizar.
        session: La sesión de SQLAlchemy.

    Returns:
    -------
        Una lista de grupos de controladores y sectores.

    """
    # Obtener todos los periodos del estadillo
    periodos = session.query(Periodo).filter_by(id_estadillo=estadillo.id).all()

    # Agrupar periodos por sector
    sector_controladores: dict[int, set[int | None]] = {}
    for periodo in periodos:
        if periodo.id_sector not in sector_controladores:
            sector_controladores[periodo.id_sector] = set()
        sector_controladores[periodo.id_sector].add(periodo.id_controlador)

    # Crear grupos de controladores y sectores
    grupos = []
    while sector_controladores:
        # Tomar un sector y sus controladores
        id_sector, controladores_ids = sector_controladores.popitem()

        # Crear un grupo inicial con este sector y sus controladores
        grupo_controladores = set(controladores_ids)
        grupo_sectores: set[int | None] = {id_sector}

        # Buscar otros sectores que compartan al menos un controlador
        found = True
        while found:
            found = False
            for sector, controladores in list(sector_controladores.items()):
                if grupo_controladores.intersection(controladores):
                    grupo_controladores.update(controladores)
                    grupo_sectores.add(sector)
                    del sector_controladores[sector]
                    found = True

        # Obtener las instancias de ATC y Sector
        res_controladores = (
            session.query(ATC).filter(ATC.id.in_(grupo_controladores)).all()
        )

        res_sectores = session.query(Sector).filter(Sector.id.in_(grupo_sectores)).all()

        grupos.append(Grupo(controladores=res_controladores, sectores=res_sectores))

    return grupos


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
