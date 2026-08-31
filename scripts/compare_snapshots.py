import argparse
from pathlib import Path
from typing import Any

from moa_agri_pipeline.load.parquet import (
    load_canonical_parquet,
)
from moa_agri_pipeline.load.snapshot_diff import (
    diff_snapshots,
    get_business_key,
)


def validate_same_day_snapshots(
    earlier_records: list[dict[str, Any]],
    later_records: list[dict[str, Any]],
) -> None:
    """確認兩份 snapshot 屬於相同的單一 trade_date。"""

    earlier_dates = {
        record["trade_date"]
        for record in earlier_records
    }

    later_dates = {
        record["trade_date"]
        for record in later_records
    }

    if len(earlier_dates) > 1:
        raise ValueError(
            "Earlier Snapshot 包含多個 trade_date"
        )

    if len(later_dates) > 1:
        raise ValueError(
            "Later Snapshot 包含多個 trade_date"
        )

    if (
        earlier_dates
        and later_dates
        and earlier_dates != later_dates
    ):
        raise ValueError(
            "Earlier / Later Snapshot 的 trade_date 不一致"
        )


def print_snapshot_diff(
    result: dict[str, Any],
    *,
    example_limit: int = 10,
) -> None:
    """顯示 Snapshot Diff 摘要。"""

    print("\n=== Same-Day Snapshot Diff ===")

    print(
        f"Earlier rows:    "
        f"{result['earlier_row_count']}"
    )
    print(
        f"Later rows:      "
        f"{result['later_row_count']}"
    )

    print()

    print(
        f"Inserted:        "
        f"{result['inserted_count']}"
    )
    print(
        f"Changed:         "
        f"{result['changed_count']}"
    )
    print(
        f"Disappeared:     "
        f"{result['disappeared_count']}"
    )
    print(
        f"Unchanged:       "
        f"{result['unchanged_count']}"
    )

    if result["changed"]:
        print("\nChanged examples:")

        for item in result["changed"][
            :example_limit
        ]:
            print(
                "\n  Business Key: "
                f"{item['business_key']}"
            )

            for (
                field,
                values,
            ) in item[
                "changed_fields"
            ].items():
                print(
                    f"    {field}: "
                    f"{values['earlier']!r}"
                    " -> "
                    f"{values['later']!r}"
                )

    if result["inserted"]:
        print("\nInserted Key examples:")

        for record in result["inserted"][
            :example_limit
        ]:
            print(
                "  "
                f"{get_business_key(record)}"
            )

    if result["disappeared"]:
        print("\nDisappeared Key examples:")

        for record in result[
            "disappeared"
        ][:example_limit]:
            print(
                "  "
                f"{get_business_key(record)}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "比較兩份同日 canonical "
            "Parquet snapshots"
        )
    )

    parser.add_argument(
        "earlier_snapshot",
        type=Path,
    )

    parser.add_argument(
        "later_snapshot",
        type=Path,
    )

    parser.add_argument(
        "--examples",
        type=int,
        default=10,
        help="各類變化最多顯示幾個範例",
    )

    args = parser.parse_args()

    earlier_records = load_canonical_parquet(
        args.earlier_snapshot
    )

    later_records = load_canonical_parquet(
        args.later_snapshot
    )

    validate_same_day_snapshots(
        earlier_records,
        later_records,
    )

    result = diff_snapshots(
        earlier_records,
        later_records,
    )

    print_snapshot_diff(
        result,
        example_limit=args.examples,
    )


if __name__ == "__main__":
    main()