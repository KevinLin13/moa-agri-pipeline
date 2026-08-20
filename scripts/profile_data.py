from datetime import date

from moa_agri_pipeline.extract.moa_api import fetch_all_pages
from moa_agri_pipeline.profiling.records import (
    profile_composite_relationship,
    find_duplicate_record_groups,
    profile_duplicate_keys,
    profile_field_relationship,
    profile_records,
)
from moa_agri_pipeline.profiling.report import (
    print_duplicate_profile,
    print_profile,
    print_relationship_profile,
)
from moa_agri_pipeline.quality.raw import validate_raw_records
from moa_agri_pipeline.transform.agri_prices import (
    transform_agri_prices,
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

    raw_profile = profile_records(rows)

    print_profile(
        "Raw Data Profile",
        raw_profile,
    )

    transformed_rows = transform_agri_prices(rows)
    transformed_profile = profile_records(
        transformed_rows
    )
    print_profile(
        "Transformed Data Profile",
        transformed_profile,
    )

    category_crop_relationship = (
        profile_field_relationship(
            transformed_rows,
            "category_code",
            "crop_name",
        )
    )

    market_relationship = (
        profile_field_relationship(
            transformed_rows,
            "market_code",
            "market_name",
        )
    )

    crop_relationship = (
        profile_field_relationship(
            transformed_rows,
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

    duplicate_profile = profile_duplicate_keys(
        transformed_rows,
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
        transformed_rows,
        (
            "trade_date",
            "category_code",
            "crop_code",
            "market_code",
        ),
    )

    print("\n=== Duplicate Record Details ===")

    for key, records in list(
        duplicate_groups.items()
    )[:5]:
        print(f"\nKey: {key}")

        for record in records:
            print(record)

    market_category_relationship = (
        profile_composite_relationship(
            transformed_rows,
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
            transformed_rows,
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
            for record in transformed_rows
            if record["trade_date"] == trade_date
            and record["category_code"] == category_code
            and record["market_code"] == market_code
        ]

        for record in matching_records:
            print(
                {
                    "crop_code": record["crop_code"],
                    "crop_name": record["crop_name"],
                    "market_name": record["market_name"],
                }
            )

        rest_records = [
            record
            for record in transformed_rows
            if record["crop_code"] == "rest"
        ]

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


        non_rest_records = [
            record
            for record in transformed_rows
            if record["crop_code"] != "rest"
        ]

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


if __name__ == "__main__":
    main()