from collections import Counter, defaultdict
from math import isfinite
from typing import Any


_MISSING = object()


def profile_records(
    records: list[Any],
) -> dict[str, Any]:
    """分析 records 的欄位結構、型別、缺失值與常見值。"""

    row_count = len(records)

    record_type_counts = Counter(
        type(record).__name__
        for record in records
    )

    dict_records = [
        record
        for record in records
        if isinstance(record, dict)
    ]

    fields = sorted(
        {
            field
            for record in dict_records
            for field in record.keys()
        }
    )

    field_profiles = {}

    for field in fields:
        values = [
            record.get(field, _MISSING)
            for record in dict_records
        ]

        missing_key_count = sum(
            value is _MISSING
            for value in values
        )

        null_count = sum(
            value is None
            for value in values
        )

        blank_count = sum(
            isinstance(value, str)
            and not value.strip()
            for value in values
        )

        type_counts = Counter(
            type(value).__name__
            for value in values
            if value is not _MISSING
        )

        usable_values = [
            value
            for value in values
            if value is not _MISSING
            and value is not None
        ]

        value_counts = Counter(
            repr(value)
            for value in usable_values
        )

        numeric_values = [
            value
            for value in usable_values
            if isinstance(value, (int, float))
            and not isinstance(value, bool)
            and isfinite(value)
        ]

        numeric_summary = None

        if numeric_values:
            numeric_summary = {
                "count": len(numeric_values),
                "min": min(numeric_values),
                "max": max(numeric_values),
            }

        field_profiles[field] = {
            "missing_key_count": missing_key_count,
            "null_count": null_count,
            "null_ratio": (
                null_count / row_count
                if row_count
                else 0.0
            ),
            "blank_count": blank_count,
            "type_counts": dict(type_counts),
            "unique_count": len(value_counts),
            "top_values": value_counts.most_common(10),
            "numeric_summary": numeric_summary,
        }

    return {
        "row_count": row_count,
        "record_type_counts": dict(record_type_counts),
        "field_count": len(fields),
        "fields": field_profiles,
    }

def profile_field_relationship(
    records: list[dict[str, Any]],
    left_field: str,
    right_field: str,
) -> dict[str, Any]:
    """分析兩個欄位之間的值對應關係。"""

    left_to_right = defaultdict(set)
    right_to_left = defaultdict(set)

    null_patterns = Counter()

    for record in records:
        left_value = record.get(left_field)
        right_value = record.get(right_field)

        null_patterns[
            (
                left_value is None,
                right_value is None,
            )
        ] += 1

        if (
            left_value is not None
            and right_value is not None
        ):
            left_to_right[left_value].add(
                right_value
            )
            right_to_left[right_value].add(
                left_value
            )

    left_with_multiple_right = {
        left: sorted(values)
        for left, values in left_to_right.items()
        if len(values) > 1
    }

    right_with_multiple_left = {
        right: sorted(values)
        for right, values in right_to_left.items()
        if len(values) > 1
    }

    return {
        "left_field": left_field,
        "right_field": right_field,
        "null_patterns": dict(null_patterns),
        "left_with_multiple_right": (
            left_with_multiple_right
        ),
        "right_with_multiple_left": (
            right_with_multiple_left
        ),
    }

def profile_duplicate_keys(
    records: list[dict[str, Any]],
    key_fields: tuple[str, ...],
) -> dict[str, Any]:
    """分析指定欄位組合是否存在重複 key。"""

    key_counts = Counter(
        tuple(
            record.get(field)
            for field in key_fields
        )
        for record in records
    )

    duplicate_keys = {
        key: count
        for key, count in key_counts.items()
        if count > 1
    }

    duplicate_group_count = len(
        duplicate_keys
    )

    duplicate_row_count = sum(
        duplicate_keys.values()
    )

    excess_duplicate_row_count = sum(
        count - 1
        for count in duplicate_keys.values()
    )

    return {
        "key_fields": key_fields,
        "row_count": len(records),
        "unique_key_count": len(key_counts),
        "duplicate_group_count": duplicate_group_count,
        "duplicate_row_count": duplicate_row_count,
        "excess_duplicate_row_count": (
            excess_duplicate_row_count
        ),
        "duplicate_keys": duplicate_keys,
    }

def find_duplicate_record_groups(
    records: list[dict[str, Any]],
    key_fields: tuple[str, ...],
) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
    """找出指定 key 下的完整重複資料群組。"""

    groups = defaultdict(list)

    for record in records:
        key = tuple(
            record.get(field)
            for field in key_fields
        )

        groups[key].append(record)

    return {
        key: grouped_records
        for key, grouped_records in groups.items()
        if len(grouped_records) > 1
    }