"""add insight embedding

Revision ID: aadf2316e829
Revises: 73eb85054b83
Create Date: 2026-09-26 13:21:07.566204

"""
from alembic import op

revision = "aadf2316e829"
down_revision = "73eb85054b83"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE insight ADD COLUMN IF NOT EXISTS embedding vector(1536)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_insight_embedding "
        "ON insight USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_insight_embedding")
    op.execute("ALTER TABLE insight DROP COLUMN IF EXISTS embedding")