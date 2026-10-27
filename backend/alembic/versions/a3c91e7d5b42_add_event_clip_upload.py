"""add device key, event-clip fields on camera_media, and clip_uploads table

Revision ID: a3c91e7d5b42
Revises: 787d2c8b5326
Create Date: 2026-10-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a3c91e7d5b42'
down_revision: Union[str, None] = '787d2c8b5326'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# create_type=False: we create/drop the Postgres enum types ourselves below,
# so add_column / create_table don't try to create them a second time.
source_enum = postgresql.ENUM('manual', 'event', name='cameramediasource', create_type=False)
status_enum = postgresql.ENUM('uploading', 'complete', 'failed', 'aborted',
                              name='clipuploadstatus', create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    source_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)

    # ── vehicles: the secret the camera uses to upload ─────────────────────
    op.add_column('vehicles', sa.Column('device_key_hash', sa.String(64), nullable=True))
    op.add_column('vehicles', sa.Column('device_key_created_at', sa.DateTime(timezone=True), nullable=True))

    # ── camera_media: who made the item, and why ───────────────────────────
    # server_default makes every existing row "manual" in the same statement.
    op.add_column('camera_media', sa.Column(
        'source', source_enum, nullable=False, server_default='manual',
    ))
    op.add_column('camera_media', sa.Column('trigger_reason', sa.String(100), nullable=True))
    op.add_column('camera_media', sa.Column('client_clip_id', sa.String(64), nullable=True))
    op.create_unique_constraint(
        'uq_camera_media_vehicle_clip', 'camera_media', ['vehicle_id', 'client_clip_id'],
    )

    # ── clip_uploads: in-progress event clips ──────────────────────────────
    op.create_table(
        'clip_uploads',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('vehicle_id', sa.Integer(), sa.ForeignKey('vehicles.id'), nullable=False),
        sa.Column('client_clip_id', sa.String(64), nullable=False),
        sa.Column('status', status_enum, nullable=False, server_default='uploading'),
        sa.Column('trigger_reason', sa.String(100), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('total_segments', sa.Integer(), nullable=True),
        sa.Column('bytes_received', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('media_id', sa.Integer(), sa.ForeignKey('camera_media.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint('vehicle_id', 'client_clip_id', name='uq_clip_upload_vehicle_clip'),
    )
    op.create_index('ix_clip_uploads_id', 'clip_uploads', ['id'])
    op.create_index('ix_clip_uploads_vehicle_id', 'clip_uploads', ['vehicle_id'])
    op.create_index('ix_clip_uploads_status', 'clip_uploads', ['status'])
    op.create_index('ix_clip_uploads_updated_at', 'clip_uploads', ['updated_at'])


def downgrade() -> None:
    op.drop_index('ix_clip_uploads_updated_at', table_name='clip_uploads')
    op.drop_index('ix_clip_uploads_status', table_name='clip_uploads')
    op.drop_index('ix_clip_uploads_vehicle_id', table_name='clip_uploads')
    op.drop_index('ix_clip_uploads_id', table_name='clip_uploads')
    op.drop_table('clip_uploads')

    op.drop_constraint('uq_camera_media_vehicle_clip', 'camera_media', type_='unique')
    op.drop_column('camera_media', 'client_clip_id')
    op.drop_column('camera_media', 'trigger_reason')
    op.drop_column('camera_media', 'source')

    op.drop_column('vehicles', 'device_key_created_at')
    op.drop_column('vehicles', 'device_key_hash')

    bind = op.get_bind()
    status_enum.drop(bind, checkfirst=True)
    source_enum.drop(bind, checkfirst=True)