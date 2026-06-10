"""Add export_path column to chat_messages

Revision ID: add_export_path
Revises: 50012ff4ae96
Create Date: 2026-06-10 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'add_export_path'
down_revision: Union[str, Sequence[str], None] = '50012ff4ae96'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'chat_messages',
        sa.Column('export_path', sa.String(length=4096), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('chat_messages', 'export_path')