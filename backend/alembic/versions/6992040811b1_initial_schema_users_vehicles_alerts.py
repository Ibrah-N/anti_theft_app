"""initial schema - users, vehicles, alerts

Revision ID: 6992040811b1
Revises: 
Create Date: 2026-06-30 14:39:37.613309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6992040811b1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    op.create_index('ix_users_phone', 'users', ['phone'], unique=True)

    op.create_table('vehicles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('reg_number', sa.String(length=50), nullable=False),
        sa.Column('device_id', sa.String(length=100), nullable=False),
        sa.Column('engine_on', sa.Boolean(), nullable=False),
        sa.Column('fuel_flowing', sa.Boolean(), nullable=False),
        sa.Column('speed_kmh', sa.Float(), nullable=False),
        sa.Column('battery_level', sa.Float(), nullable=False),
        sa.Column('signal_bars', sa.Integer(), nullable=False),
        sa.Column('zone_fl', sa.Boolean(), nullable=False),
        sa.Column('zone_fr', sa.Boolean(), nullable=False),
        sa.Column('zone_rl', sa.Boolean(), nullable=False),
        sa.Column('zone_rr', sa.Boolean(), nullable=False),
        sa.Column('zone_bonnet', sa.Boolean(), nullable=False),
        sa.Column('zone_trunk', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('device_id'),
        sa.UniqueConstraint('reg_number')
    )
    op.create_index('ix_vehicles_id', 'vehicles', ['id'], unique=False)

    op.create_table('alerts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('category', sa.Enum('engine', 'gps', 'door', 'system', name='alertcategory'), nullable=False),
        sa.Column('severity', sa.Enum('critical', 'warning', 'info', name='alertseverity'), nullable=False),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_alerts_id', 'alerts', ['id'], unique=False)
    op.create_index('ix_alerts_created_at', 'alerts', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('alerts')
    op.drop_table('vehicles')
    op.drop_table('users')
