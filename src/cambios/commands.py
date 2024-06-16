"""Exportar e importar ATCs de la base de datos."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import click
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import ATC  # Asegúrate de que models tiene estas importaciones

if TYPE_CHECKING:
    from sqlalchemy.orm.session import Session

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
logger.addHandler(log_handler)

# Definir constantes globales para los nombres de los atributos
ATTR_APELLIDOS_NOMBRE = "apellidos_nombre"
ATTR_NOMBRE = "nombre"
ATTR_APELLIDOS = "apellidos"
ATTR_EMAIL = "email"
ATTR_ES_ADMIN = "es_admin"
ATTR_POLITICA_ACEPTADA = "politica_aceptada"

verbose_option = click.option(
    "-v",
    "--verbose",
    count=True,
    default=0,
    help="-v for DEBUG",
)


@click.group()
def cli() -> None:
    """Exportar e importar ATCs."""


def get_session(db_uri: str) -> Session:
    """Obtener una sesión de SQLAlchemy."""
    engine = create_engine(db_uri)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def set_verbose_level(verbose: int) -> None:
    """Establecer el nivel de verbosidad del logger."""
    if verbose == 1:
        logger.setLevel(logging.DEBUG)
    elif verbose > 1:
        logger.setLevel(logging.DEBUG)
        sqllogger = logging.getLogger("sqlalchemy.engine")
        sqllogger.setLevel(logging.INFO)
        sqllogger.addHandler(log_handler)
    else:
        logger.setLevel(logging.INFO)


@click.command("export-atcs")
@click.argument("output_file", type=click.File("w"))
@click.argument("db_uri", type=str)
@verbose_option
def export_atcs(verbose: int, output_file: click.File, db_uri: str) -> None:
    """Exportar ATCs a un archivo JSON."""
    set_verbose_level(verbose)
    session = get_session(db_uri)

    atcs = session.query(ATC).filter(~ATC.email.like("%example%")).all()
    atc_list = [
        {
            ATTR_APELLIDOS_NOMBRE: atc.apellidos_nombre,
            ATTR_NOMBRE: atc.nombre,
            ATTR_APELLIDOS: atc.apellidos,
            ATTR_EMAIL: atc.email,
            ATTR_ES_ADMIN: atc.es_admin,
            ATTR_POLITICA_ACEPTADA: atc.politica_aceptada,
        }
        for atc in atcs
    ]

    json.dump(atc_list, output_file, ensure_ascii=False, indent=4)  # type: ignore[arg-type]
    click.echo(f"Exported {len(atc_list)} ATCs to {output_file.name}")


@click.command("import-atcs")
@click.argument("input_file", type=click.File("r"))
@click.argument("db_uri", type=str)
@verbose_option
def import_atcs(verbose: int, input_file: click.File, db_uri: str) -> None:
    """Importar ATCs desde un archivo JSON a la base de datos."""
    set_verbose_level(verbose)
    data = json.load(input_file)  # type: ignore[arg-type]

    session = get_session(db_uri)

    n_added, n_reviewed, n_edited = 0, 0, 0

    for item in data:
        atc = (
            session.query(ATC)
            .filter_by(
                apellidos_nombre=item[ATTR_APELLIDOS_NOMBRE],
            )
            .first()
        )
        if not atc:
            logger.info("Creando ATC %s", item[ATTR_APELLIDOS_NOMBRE])
            atc = ATC(
                apellidos_nombre=item[ATTR_APELLIDOS_NOMBRE],
                nombre=item[ATTR_NOMBRE],
                apellidos=item[ATTR_APELLIDOS],
                email=item[ATTR_EMAIL],
                es_admin=item[ATTR_ES_ADMIN],
                politica_aceptada=item[ATTR_POLITICA_ACEPTADA],
            )
            session.add(atc)
            logger.debug("ATC %s añadido", item[ATTR_APELLIDOS_NOMBRE])
            n_added += 1
            continue

        logger.debug("Revisando ATC %s", item[ATTR_APELLIDOS_NOMBRE])
        atc.nombre = item[ATTR_NOMBRE]
        atc.apellidos = item[ATTR_APELLIDOS]
        atc.email = item[ATTR_EMAIL]
        atc.es_admin = item[ATTR_ES_ADMIN]
        atc.politica_aceptada = item[ATTR_POLITICA_ACEPTADA]
        n_reviewed += 1
        if session.is_modified(atc):
            n_edited += 1
            logger.debug("ATC %s editado", item[ATTR_APELLIDOS_NOMBRE])
        else:
            logger.debug("ATC %s no modificado", item[ATTR_APELLIDOS_NOMBRE])

    session.commit()
    click.echo(f"Añadidos: {n_added}, Revisados: {n_reviewed}, Editados: {n_edited}")


cli.add_command(export_atcs)
cli.add_command(import_atcs)

if __name__ == "__main__":
    cli()
