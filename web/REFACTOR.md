## Fast Data Agent 前端重构计划

### 目标
- 简化“选数据源 → 选表/列 → 建会话 → 对话分析”主路径。
- 文件与数据库统一成可视化向导，减少记忆成本。
- 在对话页强化上下文可视化（数据源、表/列、工具调用、产物）。

### 关键能力（后端现状）
- 文件：`POST /files/upload` 返回 `columns_info`、`row_count`，默认自动创建 RawData；`GET /files`；预览 `POST /files/{id}/preview`。
- 数据库：`POST /database-connections` 默认自动为前 20 张表创建 RawData；`GET /database-connections`; 表列表 `GET /database-connections/{id}/tables`; **表结构** `GET /database-connections/{id}/schema?schema_name=&table_name=`。
- RawData：可预览 `POST /raw-data/{id}/preview`。
- 数据源：`POST /data-sources`（target_fields + raw_mappings，后端有自动映射兜底）。
- 会话：`POST /sessions`，聊天 SSE `POST /sessions/{id}/chat`。

### IA / 导航
- 顶部/侧边导航：Dashboard / 数据源 / 会话 / 设置。
- 全局 CTA：“新建数据源”“新建会话”。
- 数据源详情与会话页互链（右栏可跳转数据源详情）。

### 核心流程
1) 数据源向导（三步，文件/数据库统一入口）
   - 选择来源：文件列表（上传）、数据库连接列表（可新建）。
   - 选择数据对象：文件=勾选文件即对应 RawData；数据库=选连接后加载表列表。
   - 选择列/映射：文件用 `columns_info`；数据库用 `/schema` 接口；支持“同名一键映射”，生成 target_fields/raw_mappings。
   - 提交：调用 `POST /data-sources`。
2) 会话创建
   - 从数据源详情或全局 CTA 调用 `POST /sessions`，支持多数据源选择。
   - 系统消息展示可用 VIEW（含统一视图）。
3) 会话页
   - 左栏：会话列表、数据源标签。
   - 主区：SSE 消息流，展示 text / tool 输入输出 / artifact（表格、Plotly）。
   - 右栏：任务推荐、数据源面板（VIEW+列+来源标记 file/db）、会话文件列表。
   - 工具可视化：`execute_sql`（SQL/错误+可用视图）、`quick_analysis`（摘要/列统计）、`generate_chart`（Plotly）。

### 组件拆分建议
- 向导：SourcePicker（文件/数据库）、FileListWithColumns、DbConnectionList、DbTableSelector、ColumnSelector（通用）、MappingPreview。
- 会话页：ChatStreamViewer（SSE）、ToolCallCard、DataSourcePanel、RecommendationPanel、FilesPanel。

### 状态与数据
- React Query：API 缓存；表/列按 (connectionId, schema, table) 作为 key。
- Zustand：向导 UI 状态、选中项、侧栏折叠。
- SSE：按事件类型分发（start/text/tool-input/tool-output/error/stream-status）。

### 交互细节
- 懒加载：表列表、表结构按需加载；列选择支持搜索/全选。
- 空状态：无文件/无连接/无数据源时给出明确 CTA。
- 安全：不显示密码；错误以红块+“让 AI 修复”。
- 性能：表过多时分页或截断；列表骨架屏。

### 前端迭代任务建议
1. 搭建“数据源向导”路由与框架（步骤条 + 文件/数据库 Tab）。
2. 接文件列表/上传，显示列并支持勾选。
3. 接数据库连接列表、表列表接口。
4. 接 `/database-connections/{id}/schema` 获取列，列勾选与同名映射生成 target_fields/raw_mappings。
5. 组装并提交 DataSource 创建表单；结果页展示 DataSource 概览。
6. 会话页右栏展示数据源来源/VIEW/列；对话流工具可视化与错误提示优化。
7. 回归测试（含新 schema 接口）。

