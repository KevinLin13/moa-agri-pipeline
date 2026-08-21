from collections import Counter, defaultdict
from math import isfinite
from statistics import fmean, median, pstdev, quantiles
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

def profile_composite_relationship(
    records: list[dict[str, Any]],
    left_fields: tuple[str, ...],
    right_field: str,
) -> dict[str, Any]:
    """分析多個欄位組成的 key 與單一欄位之間的對應關係。"""

    left_to_right = defaultdict(set)

    for record in records:
        left_key = tuple(
            record.get(field)
            for field in left_fields
        )

        right_value = record.get(right_field)

        if (
            all(value is not None for value in left_key)
            and right_value is not None
        ):
            left_to_right[left_key].add(
                right_value
            )

    conflicts = {
        key: sorted(values)
        for key, values in left_to_right.items()
        if len(values) > 1
    }

    return {
        "left_fields": left_fields,
        "right_field": right_field,
        "left_key_count": len(left_to_right),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
    }

def profile_numeric_fields(
    records: list[dict[str, Any]],
    fields: tuple[str, ...],
) -> dict[str, Any]:
    """分析指定數值欄位的分布。"""

    field_profiles = {}

    for field in fields:
        values = [
            record.get(field)
            for record in records
        ]

        numeric_values = [
            value
            for value in values
            if isinstance(value, (int, float))
            and not isinstance(value, bool)
        ]

        finite_values = [
            float(value)
            for value in numeric_values
            if isfinite(value)
        ]

        non_numeric_count = (
            len(values) - len(numeric_values)
        )

        non_finite_count = (
            len(numeric_values) - len(finite_values)
        )

        zero_count = sum(
            value == 0
            for value in finite_values
        )

        if not finite_values:
            field_profiles[field] = {
                "row_count": len(values),
                "finite_count": 0,
                "non_numeric_count": non_numeric_count,
                "non_finite_count": non_finite_count,
                "zero_count": 0,
                "zero_rate": None,
                "mean": None,
                "std": None,
                "min": None,
                "q1": None,
                "median": None,
                "q3": None,
                "max": None,
            }
            continue

        if len(finite_values) == 1:
            q1 = finite_values[0]
            q3 = finite_values[0]
        else:
            q1, _, q3 = quantiles(
                finite_values,
                n=4,
                method="inclusive",
            )

        field_profiles[field] = {
            "row_count": len(values),
            "finite_count": len(finite_values),
            "non_numeric_count": non_numeric_count,
            "non_finite_count": non_finite_count,
            "zero_count": zero_count,
            "zero_rate": zero_count / len(finite_values),
            "mean": fmean(finite_values),
            "std": pstdev(finite_values),
            "min": min(finite_values),
            "q1": q1,
            "median": median(finite_values),
            "q3": q3,
            "max": max(finite_values),
        }

    return {
        "row_count": len(records),
        "fields": field_profiles,
    }

def profile_zero_patterns(
    records: list[dict[str, Any]],
    fields: tuple[str, ...],
) -> dict[str, Any]:
    """分析多個數值欄位的 0 值共同出現模式。"""

    pattern_counts = Counter(
        tuple(
            record.get(field) == 0
            for field in fields
        )
        for record in records
    )

    patterns = []

    for pattern, count in pattern_counts.most_common():
        zero_fields = [
            field
            for field, is_zero in zip(fields, pattern)
            if is_zero
        ]

        patterns.append(
            {
                "pattern": pattern,
                "zero_fields": tuple(zero_fields),
                "count": count,
                "rate": (
                    count / len(records)
                    if records
                    else None
                ),
            }
        )

    all_zero_pattern = tuple(
        True
        for _ in fields
    )

    no_zero_pattern = tuple(
        False
        for _ in fields
    )

    return {
        "row_count": len(records),
        "fields": fields,
        "pattern_count": len(pattern_counts),
        "all_zero_count": pattern_counts.get(
            all_zero_pattern,
            0,
        ),
        "no_zero_count": pattern_counts.get(
            no_zero_pattern,
            0,
        ),
        "patterns": patterns,
    }