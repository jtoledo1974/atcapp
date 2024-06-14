"""Comandos CLI."""

import json

import click
from flask.cli import with_appcontext

from .database import db, init_db
from .models import ATC

# Definir constantes globales para los nombres de los atributos
ATTR_APELLIDOS_NOMBRE = "apellidos_nombre"
ATTR_NOMBRE = "nombre"
ATTR_APELLIDOS = "apellidos"
ATTR_EMAIL = "email"
ATTR_ES_ADMIN = "es_admin"
ATTR_POLITICA_ACEPTADA = "politica_aceptada"


@click.command("export-atcs")
@click.argument("output_file", type=click.File("w"))
@with_appcontext
def export_atcs(output_file: click.File) -> None:
    """Exportar ATCs a un archivo JSON."""
    atcs = ATC.query.filter(~ATC.email.like("%example%")).all()
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
@with_appcontext
def import_atcs(input_file: click.File, db_uri: str) -> None:
    """Importar ATCs desde un archivo JSON a otra base de datos."""
    data = json.load(input_file)  # type: ignore[arg-type]

    # Configura la URI de la base de datos
    db.engine.dispose()  # Dispone la conexión existente
    db.get_engine(bind=db_uri)

    with db.get_app().app_context():
        init_db()

        for item in data:
            atc = ATC.query.filter_by(
                apellidos_nombre=item[ATTR_APELLIDOS_NOMBRE],
            ).first()
            if atc:
                atc.nombre = item[ATTR_NOMBRE]
                atc.apellidos = item[ATTR_APELLIDOS]
                atc.es_admin = item[ATTR_ES_ADMIN]
                atc.politica_aceptada = item[ATTR_POLITICA_ACEPTADA]
                db.session.add(atc)

        db.session.commit()
        click.echo(f"Imported {len(data)} ATCs to the database at {db_uri}")
