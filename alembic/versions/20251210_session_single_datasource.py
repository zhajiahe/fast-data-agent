"""session_single_datasource

将 analysis_sessions 表的 data_source_ids (ARRAY) 改为 data_source_id (Integer 外键)

Revision ID: 20251210_single_ds
Revises: 08c3e78c6b1f
Create Date: 2025-12-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251210_single_ds'
down_revision: Union[str, Sequence[str], None] = '08c3e78c6b1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade: data_source_ids -> data_source_id"""
    # 1. 添加新列 data_source_id
    op.add_column(
        'analysis_sessions',
        sa.Column('data_source_id', sa.Integer(), nullable=True, comment='关联的数据源ID')
    )

    # 2. 迁移数据：从 data_source_ids 数组取第一个元素
    op.execute("""
        UPDATE analysis_sessions
        SET data_source_id = data_source_ids[1]
        WHERE data_source_ids IS NOT NULL AND array_length(data_source_ids, 1) > 0
    """)

    # 3. 删除旧列 data_source_ids
    op.drop_column('analysis_sessions', 'data_source_ids')

    # 4. 添加外键约束
    op.create_foreign_key(
        'fk_analysis_sessions_data_source_id',
        'analysis_sessions',
        'data_sources',
        ['data_source_id'],
        ['id']
    )

    # 5. 添加索引
    op.create_index(
        op.f('ix_analysis_sessions_data_source_id'),
        'analysis_sessions',
        ['data_source_id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade: data_source_id -> data_source_ids"""
    # 1. 删除索引
    op.drop_index(op.f('ix_analysis_sessions_data_source_id'), table_name='analysis_sessions')

    # 2. 删除外键约束
    op.drop_constraint('fk_analysis_sessions_data_source_id', 'analysis_sessions', type_='foreignkey')

    # 3. 添加旧列 data_source_ids
    op.add_column(
        'analysis_sessions',
        sa.Column('data_source_ids', postgresql.ARRAY(sa.Integer()), nullable=True, comment='关联的数据源ID列表')
    )

    # 4. 迁移数据：将 data_source_id 转为数组
    op.execute("""
        UPDATE analysis_sessions
        SET data_source_ids = ARRAY[data_source_id]
        WHERE data_source_id IS NOT NULL
    """)

    # 5. 删除新列 data_source_id
    op.drop_column('analysis_sessions', 'data_source_id')

