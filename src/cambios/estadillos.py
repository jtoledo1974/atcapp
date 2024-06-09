"""Procesado de estadillos.

Estas funciones deberían hacer más sencilla la presentación de los estadillos
por las plantillas.
"""

from __future__ import annotations

import colorsys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from . import get_timezone
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
    anchor: Periodo | None = None


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
    activo: str = field(default="FUT")
    """Indica si el periodo está activo, está pasado o es futuro. PAS, ACT, FUT."""
    scroll_anchor: bool = False
    "Indica si es este periodo el que se debe mostrar en la pantalla al cargar la página."


@dataclass
class EstadilloPersonalData:
    """Datos de estadillo individual.

    La finalidad es preparar la información para presentarla en una plantilla.
    """

    nombre: str
    periodos: list[PeriodoData]
    usuario_actual: bool = False


@dataclass
class GrupoDatos:
    """Datos de grupo de estadillo listo para presentar en plantilla HTML."""

    sectores: list[str]
    atcs: list[EstadilloPersonalData] = field(default_factory=list)
    """Datos de los controladores en el grupo: nombre y periodos."""
    horas_inicio: list[PeriodoData] = field(default_factory=list)
    """Horas de inicio de todos los periodos para la cabecera."""


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
        if not sectores_asociados:
            continue

        # Inicializar el nuevo grupo con el controlador actual
        grupo_controladores = {controlador: periodos_por_controlador[controlador]}
        grupo_sectores = set(sectores_asociados)

        # Buscar controladores que compartan sectores con el controlador actual
        for otro_controlador in controladores_sin_asignar[:]:
            if sectores_por_controlador[otro_controlador] & grupo_sectores:
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


def marca_anchor(grupos: list[Grupo], user: ATC | None) -> None:
    """Marca el periodo activo en el grupo de controladores.

    El periodo activo es el que está en curso en el momento de la consulta.
    Primero se identifican todos los periodos que estén activos.
    Si user no es None y alguno de los periodos activos está asociado a user,
    se marca como el group anchor.
    Si no, se marca el periodo que pertenezca a un grupo con más controladores.
    """
    now = datetime.now(tz=get_timezone())
    periodos_activos = [
        periodo
        for grupo in grupos
        for controlador, periodos in grupo.controladores.items()
        for periodo in periodos
        if periodo.hora_inicio_tz <= now <= periodo.hora_fin_tz
    ]

    if user:
        for periodo in periodos_activos:
            if periodo.controlador == user:
                grupo = next(
                    (grupo for grupo in grupos if user in grupo.controladores),
                    None,
                )
                if grupo:
                    grupo.anchor = periodo
                    return

    # Si no hay grupo con el usuario, se marca el grupo con más controladores
    if periodos_activos:
        grupo_con_mas_controladores = max(grupos, key=lambda g: len(g.controladores))
        for periodo in periodos_activos:
            if periodo.controlador in grupo_con_mas_controladores.controladores:
                grupo_con_mas_controladores.anchor = periodo
                return


def _genera_actividad(per: Periodo) -> str:
    """Genera la actividad de un periodo para presentar en una plantilla."""
    if per.actividad == "D":
        return ""
    if per.actividad == "CAS":
        return "CAS"
    return f"{per.actividad}-{per.sector.nombre}"


@dataclass
class ColorManager:
    """Clase para gestionar los colores de los sectores."""

    sector_colors: dict[str, tuple[str, str]] = field(default_factory=dict)
    used_colors: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        """Inicializa la tabla de colores disponibles."""
        self.available_colors = [
            "#FF5733",
            "#33FF57",
            "#3357FF",
            "#FF33A1",
            "#A133FF",
            "#33FFF2",
            "#FFC133",
            "#FF3333",
            "#33FF99",
            "#FF33FF",
            "#FF5733",
            "#33FF57",
            "#3357FF",
            "#FF33A1",
            "#A133FF",
            "#33FFF2",
            "#FFC133",
            "#FF3333",
            "#33FF99",
            "#FF33FF",
        ]

    def get_color(self, sector: str, *, is_executive: bool) -> str:
        """Devuelve un color para el sector, diferenciando entre ejecutivo y plani."""
        if sector not in self.sector_colors:
            color = self.available_colors.pop(0)
            self.sector_colors[sector] = (color, self._darken_color(color))
        executive_color, planner_color = self.sector_colors[sector]
        return executive_color if is_executive else planner_color

    def _darken_color(self, color: str) -> str:
        """Genera una versión más oscura del color."""
        red, green, blue = (float(int(color[i : i + 2], 16)) for i in (1, 3, 5))
        hue, lum, sat = colorsys.rgb_to_hls(red / 255.0, green / 255.0, blue / 255.0)
        lum = max(0, lum - 0.3)  # Reduce lightness by 30%
        red, green, blue = colorsys.hls_to_rgb(hue, lum, sat)
        return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"


# Actualización de funciones para usar ColorManager
def _genera_color(per: Periodo, color_manager: ColorManager) -> str:
    """Genera el color de un periodo para presentar en una plantilla."""
    if per.actividad == "D":
        return "white"
    return color_manager.get_color(per.sector.nombre, is_executive=per.actividad == "E")


def _genera_horas_de_inicio(
    dur_total: int,
    controladores: dict[ATC, list[Periodo]],
) -> list[PeriodoData]:
    """Busca todas las horas de inicio de todos los periodos.

    El objetivo es dar a la plantilla los datos necesarios para hacer
    una fila que muestre cuándo empiezan los periodos de cada controlador.
    """
    periodos_todos = []
    for periodos in controladores.values():
        periodos_todos.extend(periodos)

    periodos_todos.sort(key=lambda p: p.hora_inicio)
    periodos_deque: deque[Periodo] = deque(periodos_todos)

    horas_inicio = []

    while periodos_deque:
        current_period = periodos_deque.popleft()
        hora_inicio = current_period.hora_inicio
        while periodos_deque and periodos_deque[0].hora_inicio == hora_inicio:
            current_period = periodos_deque.popleft()

        if periodos_deque:
            duracion = (periodos_deque[0].hora_inicio - hora_inicio).seconds // 60
        else:
            duracion = (current_period.hora_fin - hora_inicio).seconds // 60

        horas_inicio.append(
            PeriodoData(
                hora_inicio=datetime.strftime(hora_inicio, "%H:%M"),
                hora_fin="",
                actividad="",
                color="",
                duracion=duracion,
                porcentaje=duracion / dur_total * 100,
            ),
        )

    return horas_inicio


def _es_activo(
    hora_inicio: datetime,
    hora_fin: datetime,
    grupo_hora_inicio: datetime,
    grupo_hora_fin: datetime,
) -> str:
    """Determina si un periodo está activo, pasado o futuro."""
    now = datetime.now(tz=get_timezone())
    if now < grupo_hora_inicio or now > grupo_hora_fin:
        return "FUT"
    if hora_fin < now:
        return "PAS"
    if hora_inicio > now:
        return "FUT"
    return "ACT"


def genera_datos_grupo(grupo: Grupo, color_manager: ColorManager, user: ATC | None = None) -> GrupoDatos:
    """Genera los datos de un grupo de controladores para presentar en una plantilla."""
    sectores = [sector.nombre for sector in grupo.sectores]
    sectores.sort()
    atcs = []
    for controlador, periodos in grupo.controladores.items():
        atc_data = EstadilloPersonalData(
            nombre=f"{controlador.nombre_apellidos}",
            periodos=[
                PeriodoData(
                    hora_inicio=datetime.strftime(p.hora_inicio, "%H:%M"),
                    hora_fin=datetime.strftime(p.hora_fin, "%H:%M"),
                    actividad=_genera_actividad(p),
                    color=_genera_color(p, color_manager),
                    duracion=(duracion := (p.hora_fin - p.hora_inicio).seconds // 60),
                    porcentaje=duracion / grupo.duracion * 100,
                    activo=_es_activo(
                        p.hora_inicio_tz,
                        p.hora_fin_tz,
                        grupo.estadillo.hora_inicio,
                        grupo.estadillo.hora_fin,
                    ),
                    scroll_anchor=p == grupo.anchor,
                )
                for p in periodos
            ],
            usuario_actual=controlador == user,
        )
        atcs.append(atc_data)

    horas_inicio = _genera_horas_de_inicio(grupo.duracion, grupo.controladores)

    return GrupoDatos(sectores=sectores, atcs=atcs, horas_inicio=horas_inicio)


def genera_datos_estadillo(
    estadillo: Estadillo,
    session: Session | scoped_session,
    user: ATC | None = None,
) -> list[GrupoDatos]:
    """Genera los datos de un estadillo para presentar en una plantilla."""
    grupos = identifica_grupos(estadillo, session)
    marca_anchor(grupos, user)
    color_manager = ColorManager()  # Crear una instancia de ColorManager
    datos_grupo = [genera_datos_grupo(grupo, color_manager, user) for grupo in grupos]
    # datos_grupo.sort(key=lambda g: len(g.atcs), reverse=True)
    return datos_grupo
