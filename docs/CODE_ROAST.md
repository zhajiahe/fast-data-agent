🔍 潜在改进方向（非紧急）


文档: 部分复杂方法缺少详细注释

错误日志: 某些异常只 log.warning，可考虑更详细的上下文

连接池管理: 沙盒 HTTP 客户端已有池化，但沙盒内的 DuckDB 连接可考虑复用

缓存: schema_cache 未被主动填充，可考虑在 init_session 时填充


❓ 需要讨论的功能点


target_fields 字段映射: 目前 DataSource 有 target_fields 但实际使用的是 RawData 原始字段

多 RawData 合并查询: 当前只支持单个 VIEW 查询