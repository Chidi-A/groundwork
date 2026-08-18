"""add_search_vector_to_insight_and_document

Revision ID: 73eb85054b83
Revises: 8929621d9ab7
Create Date: 2026-08-18 08:17:28.546779

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = '73eb85054b83'
down_revision = '8929621d9ab7'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        ALTER TABLE insight ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (
            to_tsvector('english',
                coalesce(text, '') || ' ' ||
                coalesce(source_quote, '') || ' ' ||
                coalesce(theme, '')
            )
        ) STORED
    """)
    op.create_index(
        "ix_insight_search_vector", "insight", ["search_vector"],
        postgresql_using="gin",
    )

    op.execute("""
        ALTER TABLE document ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('english', coalesce(filename, ''))) STORED
    """)
    op.create_index(
        "ix_document_search_vector", "document", ["search_vector"],
        postgresql_using="gin",
    )


def downgrade():
    op.drop_index("ix_document_search_vector", table_name="document")
    op.execute("ALTER TABLE document DROP COLUMN search_vector")
    op.drop_index("ix_insight_search_vector", table_name="insight")
    op.execute("ALTER TABLE insight DROP COLUMN search_vector")