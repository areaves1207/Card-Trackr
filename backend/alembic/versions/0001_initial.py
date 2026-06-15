"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-15
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_username", "users", ["username"])

    op.create_table(
        "pokemon_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_id", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("set_name", sa.String(100), nullable=False),
        sa.Column("set_id", sa.String(50), nullable=False),
        sa.Column("collector_number", sa.String(20), nullable=False),
        sa.Column("rarity", sa.String(50), nullable=True),
        sa.Column("image_small", sa.String(500), nullable=True),
        sa.Column("image_large", sa.String(500), nullable=True),
        sa.Column("cached_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pokemon_cards_api_id", "pokemon_cards", ["api_id"])
    op.create_index("ix_pokemon_cards_name", "pokemon_cards", ["name"])

    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_collections_user_id", "collections", ["user_id"])

    op.create_table(
        "collection_cards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collection_id", sa.Integer(), sa.ForeignKey("collections.id"), nullable=False),
        sa.Column("pokemon_card_id", sa.Integer(), sa.ForeignKey("pokemon_cards.id"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("condition", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_collection_cards_collection_id", "collection_cards", ["collection_id"])
    op.create_index("ix_collection_cards_pokemon_card_id", "collection_cards", ["pokemon_card_id"])

    op.create_table(
        "scan_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("source_type", sa.String(10), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_scan_sessions_user_id", "scan_sessions", ["user_id"])

    op.create_table(
        "scan_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("scan_sessions.id"), nullable=False),
        sa.Column("pokemon_card_id", sa.Integer(), sa.ForeignKey("pokemon_cards.id"), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("frame_timestamp", sa.Float(), nullable=True),
        sa.Column("auto_added", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("raw_ocr_name", sa.String(100), nullable=True),
        sa.Column("raw_ocr_number", sa.String(20), nullable=True),
    )
    op.create_index("ix_scan_results_session_id", "scan_results", ["session_id"])


def downgrade() -> None:
    op.drop_table("scan_results")
    op.drop_table("scan_sessions")
    op.drop_table("collection_cards")
    op.drop_table("collections")
    op.drop_table("pokemon_cards")
    op.drop_table("users")
