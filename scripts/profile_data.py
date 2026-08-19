from datetime import date

from moa_agri_pipeline.extract.moa_api import fetch_all_pages
from moa_agri_pipeline.profiling.records import (
    profile_records,
    profile_field_relationship,
)
from moa_agri_pipeline.profiling.report import (
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

    raw_profile = profile_records(rows)

    print_profile(
        "Raw Data Profile",
        raw_profile,
    )

    validate_raw_records(rows)

    transformed_rows = transform_agri_prices(rows)

    transformed_profile = profile_records(
        transformed_rows
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

    print_profile(
        "Transformed Data Profile",
        transformed_profile,
    )


if __name__ == "__main__":
    main()