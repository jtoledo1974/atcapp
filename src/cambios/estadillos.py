from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .models import ATC, Estadillo, Periodo


def get_user_estadillo(user: ATC, session: Session) -> list[dict[str, Any]]:
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
            if p.actividad == "E":
                periodo_data["ejecutivo"] = f"{atc.nombre} {atc.apellidos}"
            elif p.actividad == "P":
                periodo_data["planificador"] = f"{atc.nombre} {atc.apellidos}"

        estadillo_data.append(periodo_data)

    return estadillo_data


def get_general_estadillo(
    latest_estadillo: Estadillo,
    session: Session,
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
