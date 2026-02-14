"""enable unaccent extension for search

Revision ID: f6e7a8b9c0d1
Revises: e5f6a7b8c9d0
Create Date: enable unaccent for accent-insensitive search

"""
from alembic import op


revision = "f6e7a8b9c0d1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Required for accent-insensitive search in list endpoints (orders, clients, products, users).
    # Requires superuser or CREATEEXTENSION on the database.
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")


def downgrade() -> None:
    # Dropping the extension is optional; leave it in place if other objects might use it.
    op.execute("DROP EXTENSION IF EXISTS unaccent;")
