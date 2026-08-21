from typing import Any


def _format_type_counts(
    type_counts: dict[str, int],
) -> str:
    """將型別統計轉成適合閱讀的文字。"""

    return ", ".join(
        f"{type_name}={count}"
        for type_name, count in type_counts.items()
    )


def _print_numeric_summary(
    profile: dict[str, Any],
) -> None:
    """顯示可辨識為數值的欄位摘要。"""

    numeric_fields = [
        (field, stats["numeric_summary"])
        for field, stats in profile["fields"].items()
        if stats["numeric_summary"] is not None
    ]

    if not numeric_fields:
        return

    print("\n數值摘要")

    print(
        "| 欄位 | Count | Min | Max |"
    )
    print(
        "|---|---:|---:|---:|"
    )

    for field, summary in numeric_fields:
        print(
            f"| {field} "
            f"| {summary['count']} "
            f"| {summary['min']} "
            f"| {summary['max']} |"
        )


def _print_low_cardinality_values(
    profile: dict[str, Any],
) -> None:
    """顯示種類較少的欄位常見值。"""

    low_cardinality_fields = [
        (field, stats)
        for field, stats in profile["fields"].items()
        if 0 < stats["unique_count"] <= 20
    ]

    if not low_cardinality_fields:
        return

    print("\n低基數欄位常見值")

    for field, stats in low_cardinality_fields:
        print(f"\n{field}:")

        for value, count in stats["top_values"]:
            print(
                f"  {value}: {count}"
            )

def print_profile(
    title: str,
    profile: dict[str, Any],
) -> None:
    """將 Data Profile 以易讀格式輸出到終端機。"""

    print(f"\n=== {title} ===")
    print(f"Rows: {profile['row_count']}")
    print(f"Fields: {profile['field_count']}")

    record_types = _format_type_counts(
        profile["record_type_counts"]
    )
    print(f"Record types: {record_types}")

    print("\n欄位摘要")

    print(
        "| 欄位 | Missing Key | Null | Null % "
        "| Blank | Unique | Types |"
    )
    print(
        "|---|---:|---:|---:|---:|---:|---|"
    )

    for field, stats in profile["fields"].items():
        type_text = _format_type_counts(
            stats["type_counts"]
        )

        print(
            f"| {field} "
            f"| {stats['missing_key_count']} "
            f"| {stats['null_count']} "
            f"| {stats['null_ratio']:.2%} "
            f"| {stats['blank_count']} "
            f"| {stats['unique_count']} "
            f"| {type_text} |"
        )

    _print_numeric_summary(profile)
    _print_low_cardinality_values(profile)


def print_relationship_profile(
    title: str,
    profile: dict[str, Any],
    *,
    show_left_conflicts: bool = True,
    show_right_conflicts: bool = False,
) -> None:
    """以易讀格式顯示兩個欄位的關係剖析結果。"""

    print(f"\n=== {title} ===")

    left_field = profile["left_field"]
    right_field = profile["right_field"]

    print(f"{left_field} → {right_field}")

    print("\nNULL 組合：")

    for pattern, count in profile["null_patterns"].items():
        left_null, right_null = pattern

        print(
            f"  {left_field} NULL={left_null}, "
            f"{right_field} NULL={right_null}: "
            f"{count}"
        )

    if show_left_conflicts:
        conflicts = profile["left_with_multiple_right"]

        print(
            f"\n同一 {left_field} 對應多個 "
            f"{right_field}：{len(conflicts)} 組"
        )

        for value, mapped_values in conflicts.items():
            print(
                f"  {value!r} → "
                f"{', '.join(map(str, mapped_values))}"
            )

    if show_right_conflicts:
        conflicts = profile["right_with_multiple_left"]

        print(
            f"\n同一 {right_field} 對應多個 "
            f"{left_field}：{len(conflicts)} 組"
        )

        for value, mapped_values in conflicts.items():
            print(
                f"  {value!r} → "
                f"{', '.join(map(str, mapped_values))}"
            )

def print_duplicate_profile(
    title: str,
    profile: dict[str, Any],
) -> None:
    """顯示 Business Key 重複分析結果。"""

    print(f"\n=== {title} ===")

    key_text = " + ".join(
        profile["key_fields"]
    )

    print(f"Candidate key: {key_text}")
    print(f"Rows: {profile['row_count']}")
    print(
        "Unique keys: "
        f"{profile['unique_key_count']}"
    )
    print(
        "Duplicate key groups: "
        f"{profile['duplicate_group_count']}"
    )
    print(
        "Rows in duplicate groups: "
        f"{profile['duplicate_row_count']}"
    )
    print(
        "Excess duplicate rows: "
        f"{profile['excess_duplicate_row_count']}"
    )

    duplicate_keys = profile[
        "duplicate_keys"
    ]

    if not duplicate_keys:
        return

    print("\n重複 Key 範例：")

    for key, count in list(
        duplicate_keys.items()
    )[:10]:
        print(
            f"  {key}: {count} 筆"
        )

def print_numeric_distribution_profile(
    title: str,
    profile: dict[str, Any],
) -> None:
    """顯示數值欄位分布剖析結果。"""

    print(f"\n=== {title} ===")
    print(f"Rows: {profile['row_count']}")

    for field, field_profile in profile["fields"].items():
        print(f"\n{field}")

        print(
            "  Finite values: "
            f"{field_profile['finite_count']}"
        )
        print(
            "  Non-numeric: "
            f"{field_profile['non_numeric_count']}"
        )
        print(
            "  Non-finite: "
            f"{field_profile['non_finite_count']}"
        )

        zero_rate = field_profile["zero_rate"]

        if zero_rate is None:
            zero_rate_text = "-"
        else:
            zero_rate_text = f"{zero_rate:.2%}"

        print(
            "  Zero: "
            f"{field_profile['zero_count']} "
            f"({zero_rate_text})"
        )

        for statistic in (
            "mean",
            "std",
            "min",
            "q1",
            "median",
            "q3",
            "max",
        ):
            value = field_profile[statistic]

            if value is None:
                value_text = "-"
            else:
                value_text = f"{value:.2f}"

            print(
                f"  {statistic}: {value_text}"
            )

def print_zero_pattern_profile(
    title: str,
    profile: dict[str, Any],
) -> None:
    """顯示數值欄位的 0 值共同出現模式。"""

    print(f"\n=== {title} ===")
    print(f"Rows: {profile['row_count']}")
    print(
        "Distinct zero patterns: "
        f"{profile['pattern_count']}"
    )
    print(
        "Rows with no zero: "
        f"{profile['no_zero_count']}"
    )
    print(
        "Rows with all fields zero: "
        f"{profile['all_zero_count']}"
    )

    print("\nZero patterns:")

    for item in profile["patterns"]:
        zero_fields = item["zero_fields"]

        if not zero_fields:
            zero_text = "(no zero fields)"
        else:
            zero_text = " + ".join(zero_fields)

        rate = item["rate"]

        if rate is None:
            rate_text = "-"
        else:
            rate_text = f"{rate:.2%}"

        print(
            f"  {zero_text}: "
            f"{item['count']} "
            f"({rate_text})"
        )