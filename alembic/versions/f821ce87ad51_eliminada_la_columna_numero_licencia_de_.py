"""Eliminada la columna numero_licencia de atcs.

Revision ID: f821ce87ad51
Revises:
Create Date: 2024-06-30 19:10:14.304377

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import mysql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f821ce87ad51"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Elimina la columna numero_de_licencia de la tabla atcs."""
    op.drop_column("atcs", "numero_de_licencia")


def downgrade() -> None:
    """Añade la columna numero_de_licencia a la tabla atcs."""
    op.add_column(
        "atcs",
        sa.Column("numero_de_licencia", mysql.VARCHAR(length=6), nullable=True),
    )
