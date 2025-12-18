"""
智能字段映射建议服务

基于字段名相似度和数据类型兼容性，为用户推荐最佳的字段映射关系。
"""

import uuid
from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class FieldMappingSuggestion:
    """字段映射建议"""

    target_field: str  # 目标字段名
    source_field: str  # 推荐的源字段名
    raw_data_id: uuid.UUID  # 来源 RawData ID
    raw_data_name: str  # 来源 RawData 名称
    confidence: float  # 匹配置信度 (0-1)
    reason: str  # 推荐理由


class FieldMappingService:
    """字段映射建议服务"""

    # 数据类型兼容映射
    TYPE_COMPATIBILITY = {
        # 数值类型
        "integer": {"integer", "bigint", "smallint", "int", "int64", "int32", "float", "double", "decimal", "numeric"},
        "float": {"float", "double", "decimal", "numeric", "real", "integer", "int"},
        "decimal": {"decimal", "numeric", "float", "double", "integer"},
        # 字符串类型
        "string": {"string", "varchar", "text", "char", "object", "str"},
        "text": {"text", "string", "varchar", "object"},
        # 日期时间类型
        "datetime": {"datetime", "timestamp", "date", "time", "datetime64"},
        "date": {"date", "datetime", "timestamp"},
        "time": {"time", "datetime", "timestamp"},
        # 布尔类型
        "boolean": {"boolean", "bool", "bit"},
        # JSON 类型
        "json": {"json", "jsonb", "object", "dict"},
    }

    # 常见字段名同义词
    FIELD_SYNONYMS = {
        # ID 相关
        "id": ["id", "pk", "key", "identifier", "_id"],
        "user_id": ["user_id", "userid", "uid", "user_pk", "member_id"],
        "order_id": ["order_id", "orderid", "order_no", "order_number"],
        # 名称相关
        "name": ["name", "title", "label", "display_name"],
        "username": ["username", "user_name", "login", "account"],
        "email": ["email", "mail", "email_address"],
        "phone": ["phone", "mobile", "tel", "telephone", "phone_number"],
        # 金额相关
        "amount": ["amount", "total", "sum", "price", "cost", "value"],
        "price": ["price", "unit_price", "amount", "cost"],
        # 数量相关
        "quantity": ["quantity", "qty", "count", "num", "number"],
        "count": ["count", "qty", "quantity", "total_count"],
        # 时间相关
        "created_at": ["created_at", "create_time", "created_time", "create_date", "created"],
        "updated_at": ["updated_at", "update_time", "updated_time", "update_date", "modified_at"],
        "deleted_at": ["deleted_at", "delete_time", "deleted_time"],
        # 状态相关
        "status": ["status", "state", "status_code"],
        "type": ["type", "category", "kind", "class"],
        # 描述相关
        "description": ["description", "desc", "remark", "note", "comment"],
        "address": ["address", "addr", "location"],
    }

    def suggest_mappings(
        self,
        target_fields: list[dict],
        raw_data_sources: list[dict],
    ) -> list[FieldMappingSuggestion]:
        """
        为目标字段推荐源字段映射

        Args:
            target_fields: 目标字段列表 [{name, data_type, description}]
            raw_data_sources: 数据对象源列表 [{id, name, columns_schema}]

        Returns:
            字段映射建议列表
        """
        suggestions: list[FieldMappingSuggestion] = []

        for target in target_fields:
            target_name = target.get("name", "")
            target_type = target.get("data_type", "")

            best_match: FieldMappingSuggestion | None = None
            best_score = 0.0

            for raw_source in raw_data_sources:
                raw_id = raw_source.get("id", 0)
                raw_name = raw_source.get("name", "")
                columns = raw_source.get("columns_schema") or []

                for col in columns:
                    col_name = col.get("name", "")
                    col_type = col.get("data_type", "")

                    # 计算匹配分数
                    score, reason = self._calculate_match_score(target_name, target_type, col_name, col_type)

                    if score > best_score:
                        best_score = score
                        best_match = FieldMappingSuggestion(
                            target_field=target_name,
                            source_field=col_name,
                            raw_data_id=raw_id,
                            raw_data_name=raw_name,
                            confidence=score,
                            reason=reason,
                        )

            if best_match and best_match.confidence >= 0.3:
                suggestions.append(best_match)

        return suggestions

    def _calculate_match_score(
        self,
        target_name: str,
        target_type: str,
        source_name: str,
        source_type: str,
    ) -> tuple[float, str]:
        """
        计算字段匹配分数

        Returns:
            (分数, 理由)
        """
        # 标准化名称（小写，去除下划线和特殊字符）
        target_normalized = self._normalize_name(target_name)
        source_normalized = self._normalize_name(source_name)

        # 1. 完全匹配
        if target_normalized == source_normalized:
            type_compatible = self._check_type_compatibility(target_type, source_type)
            if type_compatible:
                return 1.0, "字段名完全匹配且类型兼容"
            return 0.8, "字段名完全匹配但类型可能不兼容"

        # 2. 同义词匹配
        synonym_match = self._check_synonym_match(target_normalized, source_normalized)
        if synonym_match:
            type_compatible = self._check_type_compatibility(target_type, source_type)
            if type_compatible:
                return 0.9, f"字段名属于同义词组 ({synonym_match})"
            return 0.7, f"字段名属于同义词组 ({synonym_match})，但类型可能不兼容"

        # 3. 字符串相似度
        similarity = self._string_similarity(target_normalized, source_normalized)
        if similarity >= 0.8:
            type_compatible = self._check_type_compatibility(target_type, source_type)
            score = similarity * (0.9 if type_compatible else 0.7)
            return score, f"字段名相似度 {similarity:.0%}"

        # 4. 包含关系
        if target_normalized in source_normalized or source_normalized in target_normalized:
            type_compatible = self._check_type_compatibility(target_type, source_type)
            score = 0.5 * (1.2 if type_compatible else 1.0)
            return min(score, 0.8), "字段名存在包含关系"

        # 5. 仅类型匹配
        if self._check_type_compatibility(target_type, source_type):
            return 0.2, "仅类型兼容"

        return 0.0, ""

    def _normalize_name(self, name: str) -> str:
        """标准化字段名"""
        # 转小写，移除常见分隔符
        normalized = name.lower()
        for char in ["_", "-", ".", " "]:
            normalized = normalized.replace(char, "")
        return normalized

    def _string_similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度"""
        return SequenceMatcher(None, s1, s2).ratio()

    def _check_type_compatibility(self, target_type: str, source_type: str) -> bool:
        """检查类型兼容性"""
        target_lower = target_type.lower()
        source_lower = source_type.lower()

        # 完全相同
        if target_lower == source_lower:
            return True

        # 检查兼容映射
        compatible_types = self.TYPE_COMPATIBILITY.get(target_lower, set())
        return source_lower in compatible_types

    def _check_synonym_match(self, name1: str, name2: str) -> str | None:
        """检查是否属于同一同义词组"""
        for group_name, synonyms in self.FIELD_SYNONYMS.items():
            normalized_synonyms = [self._normalize_name(s) for s in synonyms]
            if name1 in normalized_synonyms and name2 in normalized_synonyms:
                return group_name
        return None

    def suggest_target_fields_from_raw(
        self,
        raw_data_sources: list[dict],
    ) -> list[dict]:
        """
        从数据对象源推断目标字段定义

        合并多个 RawData 的列，选择最常见的类型

        Args:
            raw_data_sources: 数据对象源列表 [{id, name, columns_schema}]

        Returns:
            推荐的目标字段列表 [{name, data_type, description, source_count}]
        """
        # 统计所有字段
        field_stats: dict[str, dict] = {}  # normalized_name -> {types, sources, original_names}

        for raw_source in raw_data_sources:
            raw_name = raw_source.get("name", "")
            columns = raw_source.get("columns_schema") or []

            for col in columns:
                col_name = col.get("name", "")
                col_type = col.get("data_type", "unknown")
                normalized = self._normalize_name(col_name)

                if normalized not in field_stats:
                    field_stats[normalized] = {
                        "types": {},
                        "sources": [],
                        "original_names": set(),
                    }

                field_stats[normalized]["types"][col_type] = field_stats[normalized]["types"].get(col_type, 0) + 1
                field_stats[normalized]["sources"].append(raw_name)
                field_stats[normalized]["original_names"].add(col_name)

        # 生成目标字段
        target_fields = []
        for _normalized, stats in field_stats.items():
            # 选择最常见的类型
            most_common_type = max(stats["types"].items(), key=lambda x: x[1])[0]
            # 选择最短的原始名称
            original_name = min(stats["original_names"], key=len)

            target_fields.append(
                {
                    "name": original_name,
                    "data_type": self._normalize_type(most_common_type),
                    "description": f"来自 {len(stats['sources'])} 个数据源",
                    "source_count": len(stats["sources"]),
                }
            )

        # 按出现次数排序
        target_fields.sort(key=lambda x: x["source_count"], reverse=True)
        return target_fields

    def _normalize_type(self, data_type: str) -> str:
        """标准化数据类型名称"""
        type_lower = data_type.lower()

        # 整数类型
        if type_lower in {"int", "int32", "int64", "bigint", "smallint", "integer"}:
            return "integer"
        # 浮点类型
        if type_lower in {"float", "float32", "float64", "double", "real"}:
            return "float"
        # 字符串类型
        if type_lower in {"str", "string", "varchar", "text", "char", "object"}:
            return "string"
        # 布尔类型
        if type_lower in {"bool", "boolean", "bit"}:
            return "boolean"
        # 日期时间类型
        if type_lower in {"datetime", "timestamp", "datetime64"}:
            return "datetime"
        if type_lower == "date":
            return "date"
        if type_lower == "time":
            return "time"

        return data_type
