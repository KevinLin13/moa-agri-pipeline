from typing import Any


def get_business_key(
    record: dict[str, Any],
) -> tuple[Any, ...]:
    """取得 canonical record 的 Business Key。"""

    if record["crop_code"] == "rest":
        return (
            "rest",
            record["trade_date"],
            record["category_code"],
            record["market_code"],
        )

    return (
        "non_rest",
        record["trade_date"],
        record["crop_code"],
        record["market_code"],
    )


def build_snapshot_index(
    records: list[dict[str, Any]],
) -> dict[tuple[Any, ...], dict[str, Any]]:
    """依 Business Key 建立 snapshot index。"""

    index = {}

    for record in records:
        business_key = get_business_key(record)

        if business_key in index:
            raise ValueError(
                f"Snapshot 內 Business Key 重複：{business_key}"
            )

        index[business_key] = record

    return index


def get_changed_fields(
    earlier_record: dict[str, Any],
    later_record: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """找出同一 Business Key 前後發生變化的欄位。"""

    changed_fields = {}

    for field in earlier_record:
        earlier_value = earlier_record[field]
        later_value = later_record[field]

        if earlier_value != later_value:
            changed_fields[field] = {
                "earlier": earlier_value,
                "later": later_value,
            }

    return changed_fields


def diff_snapshots(
    earlier_records: list[dict[str, Any]],
    later_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """比較兩個 canonical snapshots 的資料變化。"""

    earlier_index = build_snapshot_index(
        earlier_records
    )
    later_index = build_snapshot_index(
        later_records
    )

    earlier_keys = set(earlier_index)
    later_keys = set(later_index)

    inserted_keys = later_keys - earlier_keys
    disappeared_keys = earlier_keys - later_keys
    common_keys = earlier_keys & later_keys

    inserted = [
        later_index[key]
        for key in inserted_keys
    ]

    disappeared = [
        earlier_index[key]
        for key in disappeared_keys
    ]

    changed = []
    unchanged_count = 0

    for key in common_keys:
        earlier_record = earlier_index[key]
        later_record = later_index[key]

        changed_fields = get_changed_fields(
            earlier_record,
            later_record,
        )

        if changed_fields:
            changed.append(
                {
                    "business_key": key,
                    "changed_fields": changed_fields,
                }
            )
        else:
            unchanged_count += 1

    return {
        "earlier_row_count": len(earlier_records),
        "later_row_count": len(later_records),
        "inserted_count": len(inserted),
        "changed_count": len(changed),
        "disappeared_count": len(disappeared),
        "unchanged_count": unchanged_count,
        "inserted": inserted,
        "changed": changed,
        "disappeared": disappeared,
    }