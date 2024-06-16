"""App entry point.

Pensado para que gunicorn tenga la aplicación
"""

from cambios.app import create_app

app = create_app()
