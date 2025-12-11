"""change_id_from_int_to_uuid

Revision ID: 2ffbb8090ed3
Revises: 20251210_single_ds
Create Date: 2025-12-10 16:30:00.516946

This migration converts all ID columns from INTEGER to UUID.
Since there's no existing data to preserve, we drop and recreate the tables.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2ffbb8090ed3'
down_revision: Union[str, Sequence[str], None] = '20251210_single_ds'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - drop all tables and recreate with UUID."""
    # Drop all tables in reverse dependency order
    op.drop_table('task_recommendations')
    op.drop_table('chat_messages')
    op.drop_table('analysis_sessions')
    op.drop_table('data_source_raw_mappings')
    op.drop_table('data_sources')
    op.drop_table('raw_data')
    op.drop_table('uploaded_files')
    op.drop_table('database_connections')
    op.drop_table('users')
    
    # Recreate users table with UUID
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('username', sa.String(50), nullable=False, comment='用户名'),
        sa.Column('email', sa.String(100), nullable=False, comment='邮箱'),
        sa.Column('nickname', sa.String(50), nullable=False, comment='昵称'),
        sa.Column('hashed_password', sa.String(255), nullable=False, comment='加密密码'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='是否激活'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, default=False, comment='是否超级管理员'),
        sa.Column('create_by', sa.String(50), nullable=True, comment='创建人'),
        sa.Column('update_by', sa.String(50), nullable=True, comment='更新人'),
        sa.Column('create_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='更新时间'),
        sa.Column('deleted', sa.Integer(), nullable=False, default=0, comment='逻辑删除(0:未删除 1:已删除)'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    
    # Recreate database_connections table with UUID
    op.create_table(
        'database_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='连接名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='连接描述'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='所属用户ID'),
        sa.Column('db_type', sa.String(20), nullable=False, comment='数据库类型: mysql/postgresql'),
        sa.Column('host', sa.String(255), nullable=False, comment='数据库主机'),
        sa.Column('port', sa.Integer(), nullable=False, comment='数据库端口'),
        sa.Column('database', sa.String(100), nullable=False, comment='数据库名'),
        sa.Column('username', sa.String(100), nullable=False, comment='用户名'),
        sa.Column('password', sa.String(255), nullable=False, comment='加密密码'),
        sa.Column('extra_params', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='额外连接参数(JSON)'),
        sa.Column('last_tested_at', sa.String(50), nullable=True, comment='最后测试时间'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True, comment='是否可用'),
        sa.Column('create_by', sa.String(50), nullable=True, comment='创建人'),
        sa.Column('update_by', sa.String(50), nullable=True, comment='更新人'),
        sa.Column('create_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='更新时间'),
        sa.Column('deleted', sa.Integer(), nullable=False, default=0, comment='逻辑删除(0:未删除 1:已删除)'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_index(op.f('ix_database_connections_user_id'), 'database_connections', ['user_id'], unique=False)
    
    # Recreate uploaded_files table with UUID
    op.create_table(
        'uploaded_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('original_name', sa.String(255), nullable=False, comment='原始文件名'),
        sa.Column('stored_name', sa.String(255), nullable=False, comment='存储文件名(UUID)'),
        sa.Column('object_key', sa.String(500), nullable=False, comment='MinIO对象存储Key'),
        sa.Column('bucket_name', sa.String(100), nullable=False, comment='MinIO桶名称'),
        sa.Column('file_type', sa.String(20), nullable=False, comment='文件类型: csv/excel/json/parquet'),
        sa.Column('file_size', sa.BigInteger(), nullable=False, comment='文件大小(字节)'),
        sa.Column('mime_type', sa.String(100), nullable=True, comment='MIME类型'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='上传用户ID'),
        sa.Column('row_count', sa.Integer(), nullable=True, comment='数据行数'),
        sa.Column('column_count', sa.Integer(), nullable=True, comment='数据列数'),
        sa.Column('columns_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='列信息(JSON)'),
        sa.Column('preview_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='预览数据(前几行)'),
        sa.Column('status', sa.String(20), nullable=False, default='pending', comment='处理状态: pending/processing/ready/error'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('create_by', sa.String(50), nullable=True, comment='创建人'),
        sa.Column('update_by', sa.String(50), nullable=True, comment='更新人'),
        sa.Column('create_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='更新时间'),
        sa.Column('deleted', sa.Integer(), nullable=False, default=0, comment='逻辑删除(0:未删除 1:已删除)'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.UniqueConstraint('stored_name')
    )
    op.create_index(op.f('ix_uploaded_files_user_id'), 'uploaded_files', ['user_id'], unique=False)
    
    # Recreate raw_data table with UUID
    op.create_table(
        'raw_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='数据对象名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='数据对象描述'),
        sa.Column('raw_type', sa.String(20), nullable=False, comment='数据对象类型: database_table/file'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='所属用户ID'),
        sa.Column('connection_id', postgresql.UUID(as_uuid=True), nullable=True, comment='数据库连接ID'),
        sa.Column('schema_name', sa.String(100), nullable=True, comment='Schema名称'),
        sa.Column('table_name', sa.String(100), nullable=True, comment='表名'),
        sa.Column('custom_sql', sa.Text(), nullable=True, comment='自定义SQL查询（可选）'),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=True, comment='关联的上传文件ID'),
        sa.Column('columns_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='列结构信息(JSON)'),
        sa.Column('sample_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='预览抽样数据(JSON)'),
        sa.Column('row_count_estimate', sa.Integer(), nullable=True, comment='估算行数'),
        sa.Column('synced_at', sa.String(50), nullable=True, comment='最后同步时间'),
        sa.Column('status', sa.String(20), nullable=False, default='pending', comment='状态: pending/syncing/ready/error'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='错误信息'),
        sa.Column('create_by', sa.String(50), nullable=True, comment='创建人'),
        sa.Column('update_by', sa.String(50), nullable=True, comment='更新人'),
        sa.Column('create_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='更新时间'),
        sa.Column('deleted', sa.Integer(), nullable=False, default=0, comment='逻辑删除(0:未删除 1:已删除)'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['connection_id'], ['database_connections.id'], ),
        sa.ForeignKeyConstraint(['file_id'], ['uploaded_files.id'], )
    )
    op.create_index(op.f('ix_raw_data_user_id'), 'raw_data', ['user_id'], unique=False)
    
    # Recreate data_sources table with UUID
    op.create_table(
        'data_sources',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='数据源名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='数据源描述'),
        sa.Column('category', sa.String(20), nullable=True, comment='数据源分类: fact/dimension/event/other'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='所属用户ID'),
        sa.Column('target_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='目标字段定义(JSON)'),
        sa.Column('schema_cache', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='表结构缓存(JSON)'),
        sa.Column('insights', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='数据源记忆(JSON)'),
        sa.Column('create_by', sa.String(50), nullable=True, comment='创建人'),
        sa.Column('update_by', sa.String(50), nullable=True, comment='更新人'),
        sa.Column('create_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='更新时间'),
        sa.Column('deleted', sa.Integer(), nullable=False, default=0, comment='逻辑删除(0:未删除 1:已删除)'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_index(op.f('ix_data_sources_user_id'), 'data_sources', ['user_id'], unique=False)
    
    # Recreate data_source_raw_mappings table with UUID
    op.create_table(
        'data_source_raw_mappings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=False, comment='数据源ID'),
        sa.Column('raw_data_id', postgresql.UUID(as_uuid=True), nullable=False, comment='数据对象ID'),
        sa.Column('field_mappings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment='字段映射(JSON)'),
        sa.Column('priority', sa.Integer(), nullable=False, default=0, comment='映射优先级'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, default=True, comment='是否启用该映射'),
        sa.Column('create_by', sa.String(50), nullable=True, comment='创建人'),
        sa.Column('update_by', sa.String(50), nullable=True, comment='更新人'),
        sa.Column('create_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='更新时间'),
        sa.Column('deleted', sa.Integer(), nullable=False, default=0, comment='逻辑删除(0:未删除 1:已删除)'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], ),
        sa.ForeignKeyConstraint(['raw_data_id'], ['raw_data.id'], )
    )
    op.create_index(op.f('ix_data_source_raw_mappings_data_source_id'), 'data_source_raw_mappings', ['data_source_id'], unique=False)
    op.create_index(op.f('ix_data_source_raw_mappings_raw_data_id'), 'data_source_raw_mappings', ['raw_data_id'], unique=False)
    
    # Recreate analysis_sessions table with UUID
    op.create_table(
        'analysis_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('name', sa.String(100), nullable=False, comment='会话名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='会话描述'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, comment='所属用户ID'),
        sa.Column('data_source_id', postgresql.UUID(as_uuid=True), nullable=True, comment='关联的数据源ID'),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='会话配置(JSON)'),
        sa.Column('status', sa.String(20), nullable=False, default='active', comment='会话状态: active/archived'),
        sa.Column('message_count', sa.Integer(), nullable=False, default=0, comment='消息数量'),
        sa.Column('create_by', sa.String(50), nullable=True, comment='创建人'),
        sa.Column('update_by', sa.String(50), nullable=True, comment='更新人'),
        sa.Column('create_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='更新时间'),
        sa.Column('deleted', sa.Integer(), nullable=False, default=0, comment='逻辑删除(0:未删除 1:已删除)'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['data_source_id'], ['data_sources.id'], )
    )
    op.create_index(op.f('ix_analysis_sessions_user_id'), 'analysis_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_data_source_id'), 'analysis_sessions', ['data_source_id'], unique=False)
    
    # Recreate chat_messages table with UUID
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False, comment='所属会话ID'),
        sa.Column('message_type', sa.String(20), nullable=False, comment='消息类型: human/ai/system/tool'),
        sa.Column('content', sa.Text(), nullable=False, comment='消息内容'),
        sa.Column('message_id', sa.String(100), nullable=True, comment='LangChain 消息ID'),
        sa.Column('name', sa.String(100), nullable=True, comment='消息名称(可选)'),
        sa.Column('tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='工具调用列表(JSON)'),
        sa.Column('invalid_tool_calls', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='无效工具调用列表(JSON)'),
        sa.Column('usage_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Token使用统计(JSON)'),
        sa.Column('tool_call_id', sa.String(100), nullable=True, comment='工具调用ID'),
        sa.Column('artifact', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='工具产出物(JSON)'),
        sa.Column('status', sa.String(20), nullable=True, comment='工具执行状态: success/error'),
        sa.Column('additional_kwargs', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='额外参数(JSON)'),
        sa.Column('response_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='响应元数据(JSON)'),
        sa.Column('create_by', sa.String(50), nullable=True, comment='创建人'),
        sa.Column('update_by', sa.String(50), nullable=True, comment='更新人'),
        sa.Column('create_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='更新时间'),
        sa.Column('deleted', sa.Integer(), nullable=False, default=0, comment='逻辑删除(0:未删除 1:已删除)'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['analysis_sessions.id'], ondelete='CASCADE')
    )
    op.create_index(op.f('ix_chat_messages_session_id'), 'chat_messages', ['session_id'], unique=False)
    
    # Recreate task_recommendations table with UUID
    op.create_table(
        'task_recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, comment='主键ID'),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), nullable=False, comment='所属会话ID'),
        sa.Column('title', sa.String(200), nullable=False, comment='推荐任务标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='任务描述'),
        sa.Column('category', sa.String(30), nullable=False, default='overview', comment='任务分类'),
        sa.Column('source_type', sa.String(20), nullable=False, default='initial', comment='推荐来源类型'),
        sa.Column('priority', sa.Integer(), nullable=False, default=0, comment='优先级（0最高）'),
        sa.Column('status', sa.String(20), nullable=False, default='pending', comment='状态'),
        sa.Column('trigger_message_id', postgresql.UUID(as_uuid=True), nullable=True, comment='触发推荐的消息ID'),
        sa.Column('create_by', sa.String(50), nullable=True, comment='创建人'),
        sa.Column('update_by', sa.String(50), nullable=True, comment='更新人'),
        sa.Column('create_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='创建时间'),
        sa.Column('update_time', sa.DateTime(), nullable=False, server_default=sa.func.now(), comment='更新时间'),
        sa.Column('deleted', sa.Integer(), nullable=False, default=0, comment='逻辑删除(0:未删除 1:已删除)'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['analysis_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['trigger_message_id'], ['chat_messages.id'], )
    )
    op.create_index(op.f('ix_task_recommendations_session_id'), 'task_recommendations', ['session_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - this migration cannot be reversed easily."""
    # Since we dropped and recreated tables, downgrade would need to recreate
    # with INTEGER types. For simplicity, just drop and let the previous
    # migration handle recreation.
    op.drop_table('task_recommendations')
    op.drop_table('chat_messages')
    op.drop_table('analysis_sessions')
    op.drop_table('data_source_raw_mappings')
    op.drop_table('data_sources')
    op.drop_table('raw_data')
    op.drop_table('uploaded_files')
    op.drop_table('database_connections')
    op.drop_table('users')

