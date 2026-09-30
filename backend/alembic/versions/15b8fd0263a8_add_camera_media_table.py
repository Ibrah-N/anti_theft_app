"""add camera_media table

Revision ID: 15b8fd0263a8
Revises: 28003cc59777
Create Date: 2026-09-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15b8fd0263a8'
down_revision: Union[str, None] = '28003cc59777'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'camera_media',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('vehicle_id', sa.Integer(), sa.ForeignKey('vehicles.id'), nullable=False, index=True),
        sa.Column('media_type', sa.Enum('snapshot', 'recording', name='cameramediatype'), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('camera_media')
    sa.Enum(name='cameramediatype').drop(op.get_bind(), checkfirst=True)