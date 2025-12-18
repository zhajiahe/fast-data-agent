"""Convert time fields from String to DateTime

Revision ID: 20251218_time_fields
Revises: 20251210_session_single_datasource
Create Date: 2025-12-18

将以下字段从 VARCHAR 转换为 TIMESTAMP：
- database_connections.last_tested_at
- raw_data.synced_at

使用 PostgreSQL 的 ISO 8601 格式解析字符串。
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251218_time_fields"
down_revision = "1d6fce1b3322"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    将时间字段从 VARCHAR 转换为 TIMESTAMP
    
    PostgreSQL 支持使用 USING 子句进行类型转换。
    ISO 8601 格式的字符串（如 "2025-01-15T10:30:00"）可以直接转换为 TIMESTAMP。
    """
    # 1. database_connections.last_tested_at: VARCHAR(50) -> TIMESTAMP
    op.execute("""
        ALTER TABLE database_connections 
        ALTER COLUMN last_tested_at TYPE TIMESTAMP 
        USING CASE 
            WHEN last_tested_at IS NOT NULL AND last_tested_at != '' 
            THEN last_tested_at::TIMESTAMP 
            ELSE NULL 
        END
    """)
    
    # 2. raw_data.synced_at: VARCHAR(50) -> TIMESTAMP
    op.execute("""
        ALTER TABLE raw_data 
        ALTER COLUMN synced_at TYPE TIMESTAMP 
        USING CASE 
            WHEN synced_at IS NOT NULL AND synced_at != '' 
            THEN synced_at::TIMESTAMP 
            ELSE NULL 
        END
    """)


def downgrade() -> None:
    """
    将时间字段从 TIMESTAMP 转回 VARCHAR
    """
    # 1. database_connections.last_tested_at: TIMESTAMP -> VARCHAR(50)
    op.execute("""
        ALTER TABLE database_connections 
        ALTER COLUMN last_tested_at TYPE VARCHAR(50) 
        USING CASE 
            WHEN last_tested_at IS NOT NULL 
            THEN to_char(last_tested_at, 'YYYY-MM-DD"T"HH24:MI:SS') 
            ELSE NULL 
        END
    """)
    
    # 2. raw_data.synced_at: TIMESTAMP -> VARCHAR(50)
    op.execute("""
        ALTER TABLE raw_data 
        ALTER COLUMN synced_at TYPE VARCHAR(50) 
        USING CASE 
            WHEN synced_at IS NOT NULL 
            THEN to_char(synced_at, 'YYYY-MM-DD"T"HH24:MI:SS') 
            ELSE NULL 
        END
    """)

