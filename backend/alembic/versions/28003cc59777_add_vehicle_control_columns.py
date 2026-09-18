"""add vehicle control columns

Revision ID: 28003cc59777
Revises: ca9df87f2abf
Create Date: 2026-09-18 08:33:19.566751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28003cc59777'
down_revision: Union[str, None] = 'ca9df87f2abf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
