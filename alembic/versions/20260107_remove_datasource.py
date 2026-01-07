"""Remove DataSource and add SessionRawData

Revision ID: 20260107_remove_ds
Revises: 20251218_time_fields
Create Date: 2026-01-07

This migration:
1. Creates session_raw_data table
2. Removes data_source_id column from analysis_sessions
3. Drops data_source_raw_mappings and data_sources tables (if exist)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260107_remove_ds"
down_revision = "20251218_time_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: Create session_raw_data table
    op.create_table(
        "session_raw_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_data_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alias", sa.String(100), nullable=True, comment="表别名（可选）"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, default=True, comment="是否启用"),
        sa.Column("create_by", sa.String(50), nullable=True, comment="创建人"),
        sa.Column("update_by", sa.String(50), nullable=True, comment="更新人"),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Integer(), nullable=False, default=0, comment="是否删除 0-否 1-是"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_data_id"], ["raw_data.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_session_raw_data_session_id", "session_raw_data", ["session_id"])
    op.create_index("ix_session_raw_data_raw_data_id", "session_raw_data", ["raw_data_id"])

    # Step 2: Remove data_source_id column from analysis_sessions
    # Use raw SQL to drop constraint and index safely
    op.execute("ALTER TABLE analysis_sessions DROP CONSTRAINT IF EXISTS analysis_sessions_data_source_id_fkey")
    op.execute("DROP INDEX IF EXISTS ix_analysis_sessions_data_source_id")
    op.drop_column("analysis_sessions", "data_source_id")

    # Step 3: Drop old DataSource tables (if exist)
    op.execute("DROP TABLE IF EXISTS data_source_raw_mappings CASCADE")
    op.execute("DROP TABLE IF EXISTS data_sources CASCADE")


def downgrade() -> None:
    # Recreate data_sources table
    op.create_table(
        "data_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=True),
        sa.Column("target_fields", postgresql.JSONB(), nullable=True),
        sa.Column("config", postgresql.JSONB(), nullable=True),
        sa.Column("create_by", sa.String(50), nullable=True),
        sa.Column("update_by", sa.String(50), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_data_sources_user_id", "data_sources", ["user_id"])
    op.create_index("ix_data_sources_name", "data_sources", ["name"])

    # Recreate data_source_raw_mappings table
    op.create_table(
        "data_source_raw_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("data_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_data_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("field_mappings", postgresql.JSONB(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, default=0),
        sa.Column("create_by", sa.String(50), nullable=True),
        sa.Column("update_by", sa.String(50), nullable=True),
        sa.Column("create_time", sa.DateTime(), nullable=True),
        sa.Column("update_time", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Integer(), nullable=False, default=0),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["data_source_id"], ["data_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_data_id"], ["raw_data.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_data_source_raw_mappings_data_source_id", "data_source_raw_mappings", ["data_source_id"])
    op.create_index("ix_data_source_raw_mappings_raw_data_id", "data_source_raw_mappings", ["raw_data_id"])

    # Add data_source_id column back to analysis_sessions
    op.add_column("analysis_sessions", sa.Column("data_source_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_analysis_sessions_data_source_id", "analysis_sessions", ["data_source_id"])
    op.create_foreign_key(
        "analysis_sessions_data_source_id_fkey",
        "analysis_sessions",
        "data_sources",
        ["data_source_id"],
        ["id"],
    )

    # Drop session_raw_data table
    op.drop_index("ix_session_raw_data_raw_data_id", "session_raw_data")
    op.drop_index("ix_session_raw_data_session_id", "session_raw_data")
    op.drop_table("session_raw_data")
