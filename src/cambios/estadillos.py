"""Procesado de estadillos.

Estas funciones deberían hacer más sencilla la presentación de los estadillos
por las plantillas.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from .models import ATC, Estadillo, Periodo

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, scoped_session

    from .models import Sector


@dataclass
class Grupo:
    """Grupo de controladores que llevan juntos un grupo de sectores.

    Podrían ser un 8x3 (ocho controladores, tres sectores) o un 3x1,
    u otras combinaciones.

    Esta estrucutra de datos es útil para poder generar luego otra
    estructura de texto que se pueda presentar en una plantilla.
    """

    estadillo: Estadillo
    sectores: set[Sector]
    controladores: dict[ATC, list[Periodo]]
    duracion: int
    """Duración total del grupo en minutos."""


@dataclass
class PeriodoData:
    """Datos de un periodo en un estadillo.

    La finalidad es preparar la información para presentarla en una plantilla.
    """

    hora_inicio: str
    hora_fin: str
    actividad: str
    color: str
    duracion: int
    """Duracion en minutos"""
    porcentaje: float
    """Fracción de la jornada que ocupa este periodo."""


@dataclass
class EstadilloPersonalData:
    """Datos de estadillo individual.

    La finalidad es preparar la información para presentarla en una plantilla.
    """

    nombre: str
    periodos: list[PeriodoData]


@dataclass
class GrupoDatos:
    """Datos de grupo de estadillo listo para presentar en plantilla HTML."""

    sectores: list[str]
    atcs: list[EstadilloPersonalData] = field(default_factory=list)
    """Datos de los controladores en el grupo: nombre y periodos."""


def identifica_grupos(
    estadillo: Estadillo,
    session: Session | scoped_session,
) -> list[Grupo]:
    """Identifica los grupos de controladores y sectores en un estadillo.

    La base de datos solo guarda periodos individuales asociados a un controlador
    y a un estadillo. Esta función identifica los grupos de controladores que
    trabajan juntos en los mismos sectores.
    """
    res: list[Grupo] = []

    # Obtener todos los periodos del estadillo
    periodos = session.query(Periodo).filter_by(id_estadillo=estadillo.id).all()

    # Crear un diccionario que mapea cada controlador a los sectores en los que trabaja
    sectores_por_controlador: dict[ATC, set[Sector]] = defaultdict(set)
    periodos_por_controlador: dict[ATC, list[Periodo]] = defaultdict(list)
    for periodo in periodos:
        if periodo.sector:
            sectores_por_controlador[periodo.controlador].add(periodo.sector)
        periodos_por_controlador[periodo.controlador].append(periodo)

    controladores_sin_asignar = list(sectores_por_controlador.keys())

    # Mientras haya controladores sin asignar, buscamos grupos
    while controladores_sin_asignar:
        controlador = controladores_sin_asignar.pop(0)
        sectores_asociados = sectores_por_controlador[controlador]

        # Inicializar el nuevo grupo con el controlador actual
        grupo_controladores = {controlador: periodos_por_controlador[controlador]}
        grupo_sectores = set(sectores_asociados)

        # Buscar controladores que compartan sectores con el controlador actual
        for otro_controlador in controladores_sin_asignar[:]:
            if sectores_asociados & sectores_por_controlador[otro_controlador]:
                grupo_controladores[otro_controlador] = periodos_por_controlador[
                    otro_controlador
                ]
                grupo_sectores.update(sectores_por_controlador[otro_controlador])
                controladores_sin_asignar.remove(otro_controlador)

        # Calcular la duración total del grupo
        inicio = grupo_controladores[controlador][0].hora_inicio
        fin = grupo_controladores[controlador][-1].hora_fin
        duracion = (fin - inicio).seconds // 60

        res.append(Grupo(estadillo, grupo_sectores, grupo_controladores, duracion))

    return res


def _genera_actividad(per: Periodo) -> str:
    """Genera la actividad de un periodo para presentar en una plantilla."""
    return f"{per.actividad}-{per.sector.nombre}" if per.actividad != "D" else ""


def _genera_color(per: Periodo) -> str:
    """Genera el color de un periodo para presentar en una plantilla."""
    return "red" if per.actividad == "E" else "blue"


def genera_datos_grupo(grupo: Grupo) -> GrupoDatos:
    """Genera los datos de un grupo de controladores para presentar en una plantilla."""
    sectores = [sector.nombre for sector in grupo.sectores]
    atcs = []
    for controlador, periodos in grupo.controladores.items():
        atc_data = EstadilloPersonalData(
            nombre=f"{controlador.apellidos_nombre}",
            periodos=[
                PeriodoData(
                    hora_inicio=datetime.strftime(p.hora_inicio, "%H:%M"),
                    hora_fin=datetime.strftime(p.hora_fin, "%H:%M"),
                    actividad=_genera_actividad(p),
                    color=_genera_color(p),
                    duracion=(p.hora_fin - p.hora_inicio).seconds // 60,
                    porcentaje=(p.hora_fin - p.hora_inicio).seconds
                    / grupo.duracion
                    * 100,
                )
                for p in periodos
            ],
        )
        atcs.append(atc_data)

    return GrupoDatos(sectores=sectores, atcs=atcs)


def genera_datos_estadillo(
    estadillo: Estadillo,
    session: Session | scoped_session,
) -> list[GrupoDatos]:
    """Genera los datos de un estadillo para presentar en una plantilla."""
    grupos = identifica_grupos(estadillo, session)
    return [genera_datos_grupo(grupo) for grupo in grupos]
