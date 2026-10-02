"""add sequence_number to camera_media

Revision ID: 787d2c8b5326
Revises: 15b8fd0263a8
Create Date: 2026-10-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '787d2c8b5326'
down_revision: Union[str, None] = '15b8fd0263a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable first so existing rows (if any) don't break the add, then
    # backfilled per vehicle+type in creation order, then locked to NOT NULL.
    op.add_column('camera_media', sa.Column('sequence_number', sa.Integer(), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, vehicle_id, media_type FROM camera_media ORDER BY vehicle_id, media_type, created_at"
    )).fetchall()

    counters = {}
    for row in rows:
        key = (row.vehicle_id, row.media_type)
        counters[key] = counters.get(key, 0) + 1
        conn.execute(
            sa.text("UPDATE camera_media SET sequence_number = :seq WHERE id = :id"),
            {"seq": counters[key], "id": row.id},
        )

    op.alter_column('camera_media', 'sequence_number', nullable=False)


def downgrade() -> None:
    op.drop_column('camera_media', 'sequence_number')