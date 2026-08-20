from datetime import date

from moa_agri_pipeline.extract.moa_api import fetch_all_pages
from moa_agri_pipeline.profiling.records import (
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
    query_date = date(2026, 8, 5)

    rows = fetch_all_pages(
        start_date=query_date,
        end_date=query_date,
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
            "crop_code",
            "market_code",
        ),
    )

    print_duplicate_profile(
        "Candidate Business Key Duplicate Profile",
        duplicate_profile,
    )

if __name__ == "__main__":
    main()