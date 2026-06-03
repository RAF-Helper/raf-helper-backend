"""add_vector_routing

Revision ID: 50012ff4ae96
Revises: add_document_fields
Create Date: 2026-05-06 22:15:07.858289

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '50012ff4ae96'
down_revision: Union[str, Sequence[str], None] = 'add_document_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Create vector schema
    op.execute("CREATE SCHEMA IF NOT EXISTS vector")

    # Create routes table
    op.execute("""
        CREATE TABLE vector.routes (
            id SERIAL PRIMARY KEY,
            name VARCHAR(16) UNIQUE NOT NULL
        )
    """)

    # Create intents table
    op.execute("""
        CREATE TABLE vector.intents (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            text_embedding vector.vector(1024),
            route_id INT REFERENCES vector.routes(id) ON DELETE CASCADE
        )
    """)

    # Create HNSW index for cosine similarity search
    op.execute("""
        CREATE INDEX idx_intents_embedding ON vector.intents
        USING hnsw (text_embedding vector.vector_cosine_ops)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS vector.intents")
    op.execute("DROP TABLE IF EXISTS vector.routes")
    op.execute("DROP SCHEMA IF EXISTS vector")
    # Extension is usually left enabled unless specifically requested to be removed

