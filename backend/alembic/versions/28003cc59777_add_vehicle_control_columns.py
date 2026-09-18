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
    op.add_column('vehicles', sa.Column('is_armed', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('vehicles', sa.Column('doors_locked', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('vehicles', sa.Column('mirror_fl', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('vehicles', sa.Column('mirror_fr', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('vehicles', sa.Column('mirror_rl', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('vehicles', sa.Column('mirror_rr', sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column('vehicles', sa.Column('engine_started', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('vehicles', sa.Column('ac_on', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    op.drop_column('vehicles', 'ac_on')
    op.drop_column('vehicles', 'engine_started')
    op.drop_column('vehicles', 'mirror_rr')
    op.drop_column('vehicles', 'mirror_rl')
    op.drop_column('vehicles', 'mirror_fr')
    op.drop_column('vehicles', 'mirror_fl')
    op.drop_column('vehicles', 'doors_locked')
    op.drop_column('vehicles', 'is_armed')
