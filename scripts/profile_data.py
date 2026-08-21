from datetime import date

from moa_agri_pipeline.extract.moa_api import fetch_all_pages
from moa_agri_pipeline.profiling.records import (
    profile_composite_relationship,
    find_duplicate_record_groups,
    profile_duplicate_keys,
    profile_field_relationship,
    profile_numeric_fields,
    profile_records,
)
from moa_agri_pipeline.profiling.report import (
    print_duplicate_profile,
    print_numeric_distribution_profile,
    print_profile,
    print_relationship_profile,
)
from moa_agri_pipeline.quality.raw import validate_raw_records
from moa_agri_pipeline.transform.agri_prices import (
    transform_agri_prices,
)


def split_rest_records(
    records: list[dict],
) -> tuple[list[dict], list[dict]]:
    """將 Transform 後資料分成休市與一般交易紀錄。"""

    rest_records = [
        record
        for record in records
        if record["crop_code"] == "rest"
    ]

    non_rest_records = [
        record
        for record in records
        if record["crop_code"] != "rest"
    ]

    return rest_records, non_rest_records


def run_structure_profiling(
    raw_records: list[dict],
    transformed_records: list[dict],
) -> None:
    """執行 Raw 與 Transform 後的基本結構剖析。"""

    raw_profile = profile_records(raw_records)

    print_profile(
        "Raw Data Profile",
        raw_profile,
    )

    transformed_profile = profile_records(
        transformed_records
    )

    print_profile(
        "Transformed Data Profile",
        transformed_profile,
    )


def run_relationship_profiling(
    records: list[dict],
) -> None:
    """執行欄位與複合欄位關係剖析。"""

    category_crop_relationship = (
        profile_field_relationship(
            records,
            "category_code",
            "crop_name",
        )
    )

    market_relationship = (
        profile_field_relationship(
            records,
            "market_code",
            "market_name",
        )
    )

    crop_relationship = (
        profile_field_relationship(
            records,
            "crop_code",
            "crop_name",
        )
    )

    print_relationship_profile(
        "Category / Crop Name Relationship",
        category_crop_relationship,
        show_left_conflicts=False,
        show_right_conflicts=False,
    )

    print_relationship_profile(
        "Market Code / Name Relationship",
        market_relationship,
        show_left_conflicts=True,
        show_right_conflicts=False,
    )

    print_relationship_profile(
        "Crop Code / Name Relationship",
        crop_relationship,
        show_left_conflicts=True,
        show_right_conflicts=True,
    )

    market_category_relationship = (
        profile_composite_relationship(
            records,
            (
                "category_code",
                "market_code",
            ),
            "market_name",
        )
    )

    print(
        "\n=== Category + Market Code / Market Name ==="
    )
    print(market_category_relationship)

    daily_market_relationship = (
        profile_composite_relationship(
            records,
            (
                "trade_date",
                "category_code",
                "market_code",
            ),
            "market_name",
        )
    )

    print(
        "\n=== Date + Category + Market Code / Market Name ==="
    )
    print(daily_market_relationship)

    print("\n=== Market Name Conflict Details ===")

    for conflict_key in daily_market_relationship["conflicts"]:
        trade_date, category_code, market_code = conflict_key

        print(f"\nKey: {conflict_key}")

        matching_records = [
            record
            for record in records
            if record["trade_date"] == trade_date
            and record["category_code"] == category_code
            and record["market_code"] == market_code
        ]

        print(f"Matching rows: {len(matching_records)}")

        for record in matching_records[:5]:
            print(
                {
                    "crop_code": record["crop_code"],
                    "crop_name": record["crop_name"],
                    "market_name": record["market_name"],
                }
            )

def run_rest_record_profiling(
    rest_records: list[dict],
) -> None:
    """分析休市紀錄的基本特性。"""

    print("\n=== Rest Record Profile ===")
    print(f"Rows: {len(rest_records)}")

    print(
        "Category codes:",
        sorted(
            {
                record["category_code"]
                for record in rest_records
            },
            key=lambda value: str(value),
        ),
    )

    print(
        "Crop names:",
        {
            record["crop_name"]
            for record in rest_records
        },
    )

    print(
        "Market names:",
        sorted(
            {
                record["market_name"]
                for record in rest_records
            }
        ),
    )

    all_zero = all(
        record["upper_price"] == 0.0
        and record["middle_price"] == 0.0
        and record["lower_price"] == 0.0
        and record["avg_price"] == 0.0
        and record["volume"] == 0.0
        for record in rest_records
    )

    print(f"All numeric fields zero: {all_zero}")


def run_duplicate_profiling(
    records: list[dict],
    non_rest_records: list[dict],
    rest_records: list[dict],
) -> None:
    """執行候選 Business Key 與重複資料剖析。"""

    duplicate_profile = profile_duplicate_keys(
        records,
        (
            "trade_date",
            "category_code",
            "crop_code",
            "market_code",
        ),
    )

    print_duplicate_profile(
        "Candidate Business Key Duplicate Profile",
        duplicate_profile,
    )

    duplicate_groups = find_duplicate_record_groups(
        records,
        (
            "trade_date",
            "category_code",
            "crop_code",
            "market_code",
        ),
    )

    print("\n=== Duplicate Record Details ===")

    for key, duplicate_records in list(
        duplicate_groups.items()
    )[:5]:
        print(f"\nKey: {key}")

        for record in duplicate_records:
            print(record)

    non_rest_duplicate_profile = profile_duplicate_keys(
        non_rest_records,
        (
            "trade_date",
            "crop_code",
            "market_code",
        ),
    )

    print_duplicate_profile(
        "Non-Rest Business Key Duplicate Profile",
        non_rest_duplicate_profile,
    )

    rest_duplicate_profile = profile_duplicate_keys(
        rest_records,
        (
            "trade_date",
            "category_code",
            "market_code",
        ),
    )

    print_duplicate_profile(
        "Rest Record Key Duplicate Profile",
        rest_duplicate_profile,
    )


def run_numeric_profiling(
    non_rest_records: list[dict],
) -> None:
    """分析一般交易紀錄的數值分布。"""

    numeric_profile = profile_numeric_fields(
        non_rest_records,
        (
            "upper_price",
            "middle_price",
            "lower_price",
            "avg_price",
            "volume",
        ),
    )

    print_numeric_distribution_profile(
        "Non-Rest Numeric Distribution Profile",
        numeric_profile,
    )

def main() -> None:
    start_date = date(2026, 8, 1)
    end_date = date(2026, 8, 7)

    rows = fetch_all_pages(
        start_date=start_date,
        end_date=end_date,
        page_size=1000,
    )

    validate_raw_records(rows)

    transformed_rows = transform_agri_prices(rows)

    rest_records, non_rest_records = (
        split_rest_records(transformed_rows)
    )

    run_structure_profiling(
        rows,
        transformed_rows,
    )

    run_relationship_profiling(
        transformed_rows,
    )

    run_duplicate_profiling(
        transformed_rows,
        non_rest_records,
        rest_records,
    )

    run_rest_record_profiling(
        rest_records,
    )

    run_numeric_profiling(
        non_rest_records,
    )


if __name__ == "__main__":
    main()