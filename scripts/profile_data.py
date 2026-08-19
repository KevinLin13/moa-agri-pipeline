from datetime import date

from moa_agri_pipeline.extract.moa_api import fetch_all_pages
from moa_agri_pipeline.profiling.records import profile_records
from moa_agri_pipeline.profiling.report import print_profile
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

    print_profile(
        "Transformed Data Profile",
        transformed_profile,
    )


if __name__ == "__main__":
    main()