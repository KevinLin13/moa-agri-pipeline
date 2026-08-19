from collections import Counter
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