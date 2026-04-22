"""Add document_id, name, format to file_metadata

Revision ID: add_document_fields
Revises: 6ed5f9512fc2
Create Date: 2026-06-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'add_document_fields'
down_revision: Union[str, Sequence[str], None] = '6ed5f9512fc2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add document_id (UUID with default generation)
    op.add_column(
        'file_metadata',
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()'))
    )
    op.create_index('ix_file_metadata_document_id', 'file_metadata', ['document_id'], unique=True)

    # Add name (extracted document title)
    op.add_column(
        'file_metadata',
        sa.Column('name', sa.String(length=1024), nullable=True)
    )

    # Add format (pdf, docx, pptx, txt)
    op.add_column(
        'file_metadata',
        sa.Column('format', sa.String(length=32), nullable=False, server_default='txt')
    )


def downgrade() -> None:
    op.drop_index('ix_file_metadata_document_id', table_name='file_metadata')
    op.drop_column('file_metadata', 'document_id')
    op.drop_column('file_metadata', 'name')
    op.drop_column('file_metadata', 'format')