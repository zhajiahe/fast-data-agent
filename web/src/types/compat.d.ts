// 类型兼容层：为后端新增/调整字段提供可选扩展，降低前端改动成本。
declare module '@/api/fastDataAgent' {
  interface DataSourceResponse {
    source_type?: string | null;
    file_id?: number | null;
    group_name?: string | null;
    db_type?: string | null;
  }

  interface DataSourceCreate {
    source_type?: string | null;
    file_id?: number | null;
    group_name?: string | null;
    db_config?: any;
    target_fields?: any;
    raw_mappings?: any;
  }

  interface AnalysisSessionCreate {
    data_source_ids?: number[];
  }

  interface AnalysisSessionDetail {
    data_sources?: any[];
  }
}
