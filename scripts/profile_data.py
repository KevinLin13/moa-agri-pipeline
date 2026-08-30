from datetime import date

from moa_agri_pipeline.extract.moa_api import fetch_all_pages
from moa_agri_pipeline.profiling.records import (
    find_duplicate_record_groups,
    find_zero_pattern_records,
    profile_composite_relationship,
    profile_duplicate_keys,
    profile_field_relationship,
    profile_numeric_fields,
    profile_records,
    profile_zero_patterns,
)
from moa_agri_pipeline.profiling.report import (
    print_composite_relationship_profile,
    print_duplicate_profile,
    print_numeric_distribution_profile,
    print_profile,
    print_record_table,
    print_rest_split_summary,
    print_relationship_profile,
    print_zero_pattern_profile,
)
from moa_agri_pipeline.quality.raw import validate_raw_records
from moa_agri_pipeline.transform.agri_prices import (
    transform_agri_prices,
)

def run_initial_all_zero_inspection(
    transformed_records: list[dict],
) -> None:
    """查看所有數值欄位皆為 0 的紀錄。"""

    numeric_fields = (
        "upper_price",
        "middle_price",
        "lower_price",
        "avg_price",
        "volume",
    )

    all_zero_records = find_zero_pattern_records(
        transformed_records,
        zero_fields=numeric_fields,
    )

    print_record_table(
        "Initial All-Zero Record Inspection",
        all_zero_records,
        fields=(
            "trade_date",
            "category_code",
            "crop_code",
            "crop_name",
            "market_code",
            "market_name",
        ),
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

def run_non_rest_relationship_profiling(
    non_rest_records: list[dict],
) -> None:
    """分析一般交易紀錄中的欄位關係。"""

    category_crop_relationship = (
        profile_field_relationship(
            non_rest_records,
            "category_code",
            "crop_name",
        )
    )
    print_relationship_profile(
        "Non-Rest Category / Crop Name Relationship",
        category_crop_relationship,
        show_left_conflicts=False,
        show_right_conflicts=False,
    )

    crop_category_relationship = (
        profile_field_relationship(
            non_rest_records,
            "crop_code",
            "category_code",
        )
    )
    print_relationship_profile(
        "Non-Rest Crop Code / Category Relationship",
        crop_category_relationship,
        show_left_conflicts=True,
        show_right_conflicts=False,
    )

    crop_relationship = (
        profile_field_relationship(
            non_rest_records,
            "crop_code",
            "crop_name",
        )
    )
    print_relationship_profile(
        "Non-Rest Crop Code / Name Relationship",
        crop_relationship,
        show_left_conflicts=True,
        show_right_conflicts=True,
    )

    market_relationship = (
        profile_field_relationship(
            non_rest_records,
            "market_code",
            "market_name",
        )
    )
    print_relationship_profile(
        "Non-Rest Market Code / Name Relationship",
        market_relationship,
        show_left_conflicts=True,
        show_right_conflicts=True,
    )

def run_rest_relationship_profiling(
    rest_records: list[dict],
) -> None:
    """分析休市紀錄中的市場欄位關係。"""

    market_relationship = (
        profile_field_relationship(
            rest_records,
            "market_code",
            "market_name",
        )
    )
    print_relationship_profile(
        "Rest Market Code / Name Relationship",
        market_relationship,
        show_left_conflicts=True,
        show_right_conflicts=True,
    )

def run_non_rest_null_category_crop_code_inspection(
    non_rest_records: list[dict],
) -> None:
    """檢查 category_code 為 NULL 的 crop_code 是否曾出現已知 category。"""

    null_category_crop_codes = {
        record["crop_code"]
        for record in non_rest_records
        if record["category_code"] is None
    }

    print(
        "\n=== Non-Rest NULL Category Crop Code Inspection ==="
    )

    print(
        "Distinct crop_codes with category_code NULL: "
        f"{len(null_category_crop_codes)}"
    )

    crop_codes_with_known_category = {}
    crop_codes_without_known_category = []

    for crop_code in sorted(null_category_crop_codes):
        known_categories = sorted(
            {
                record["category_code"]
                for record in non_rest_records
                if record["crop_code"] == crop_code
                and record["category_code"] is not None
            }
        )

        if known_categories:
            crop_codes_with_known_category[
                crop_code
            ] = known_categories
        else:
            crop_codes_without_known_category.append(
                crop_code
            )

    print(
        "Crop codes also observed with non-NULL category: "
        f"{len(crop_codes_with_known_category)}"
    )

    for crop_code, categories in (
        crop_codes_with_known_category.items()
    ):
        print(
            f"  {crop_code} → "
            f"{', '.join(categories)}"
        )

    print(
        "Crop codes never observed with non-NULL category: "
        f"{len(crop_codes_without_known_category)}"
    )

    for crop_code in crop_codes_without_known_category:
        print(f"  {crop_code}")

def run_non_rest_null_record_inspection(
    non_rest_records: list[dict],
) -> None:
    """查看 category_code / crop_name 出現 NULL 的一般交易紀錄。"""

    null_records = [
        record
        for record in non_rest_records
        if record["category_code"] is None
        or record["crop_name"] is None
    ]

    print_record_table(
        "Non-Rest NULL Record Inspection",
        null_records,
        fields=(
            "trade_date",
            "category_code",
            "crop_code",
            "crop_name",
            "market_code",
            "market_name",
        ),
    )

def run_non_rest_market_composite_relationship_profiling(
    non_rest_records: list[dict],
) -> None:
    """分析 category + market code 與 market name 的關係。"""

    market_relationship = (
        profile_composite_relationship(
            non_rest_records,
            (
                "category_code",
                "market_code",
            ),
            "market_name",
        )
    )

    print_composite_relationship_profile(
        (
            "Non-Rest Category + Market Code "
            "/ Market Name Relationship"
        ),
        market_relationship,
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


def run_numeric_distribution_profiling(
    non_rest_records: list[dict],
) -> None:
    """分析一般交易紀錄的數值分布。"""

    numeric_fields = (
        "upper_price",
        "middle_price",
        "lower_price",
        "avg_price",
        "volume",
    )

    numeric_profile = profile_numeric_fields(
        non_rest_records,
        numeric_fields,
    )

    print_numeric_distribution_profile(
        "Non-Rest Numeric Distribution Profile",
        numeric_profile,
    )

def run_zero_pattern_profiling(
    non_rest_records: list[dict],
) -> None:
    """分析一般交易紀錄的數值 0 值共同出現模式。"""

    numeric_fields = (
        "upper_price",
        "middle_price",
        "lower_price",
        "avg_price",
        "volume",
    )

    zero_pattern_profile = profile_zero_patterns(
        non_rest_records,
        numeric_fields,
    )

    print_zero_pattern_profile(
        "Non-Rest Zero Pattern Profile",
        zero_pattern_profile,
    )

def run_zero_pattern_targeted_inspection(
    non_rest_records: list[dict],
) -> None:
    """檢視需要進一步解讀的 Non-Rest Zero Patterns。"""

    price_fields = (
        "upper_price",
        "middle_price",
        "lower_price",
        "avg_price",
    )

    numeric_fields = (
        *price_fields,
        "volume",
    )

    all_numeric_zero_records = find_zero_pattern_records(
        non_rest_records,
        zero_fields=numeric_fields,
    )

    lower_price_only_zero_records = find_zero_pattern_records(
        non_rest_records,
        zero_fields=("lower_price",),
        nonzero_fields=(
            "upper_price",
            "middle_price",
            "avg_price",
            "volume",
        ),
    )

    zero_prices_with_volume_records = find_zero_pattern_records(
        non_rest_records,
        zero_fields=price_fields,
        nonzero_fields=("volume",),
    )

    identifier_fields = (
        "trade_date",
        "category_code",
        "crop_code",
        "crop_name",
        "market_code",
        "market_name",
    )

    detail_fields = (
        *identifier_fields,
        "upper_price",
        "middle_price",
        "lower_price",
        "avg_price",
        "volume",
    )

    print_record_table(
        "Non-Rest All Numeric Fields Zero Inspection",
        all_numeric_zero_records,
        fields=identifier_fields,
    )

    print_record_table(
        "Lower Price Only Zero Inspection",
        lower_price_only_zero_records,
        fields=detail_fields,
    )

    print_record_table(
        "All Prices Zero With Volume Inspection",
        zero_prices_with_volume_records,
        fields=detail_fields,
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

    run_initial_all_zero_inspection(
        transformed_rows,
    )

    rest_records, non_rest_records = (
        split_rest_records(
            transformed_rows
        )
    )
    print_rest_split_summary(
        total_count=len(transformed_rows),
        rest_count=len(rest_records),
        non_rest_count=len(non_rest_records),
    )

    run_non_rest_relationship_profiling(
        non_rest_records,
    )
    run_rest_relationship_profiling(
        rest_records,
    )

    run_non_rest_null_record_inspection(
        non_rest_records,
    )

    run_non_rest_null_category_crop_code_inspection(
        non_rest_records,
    )

    run_non_rest_market_composite_relationship_profiling(
        non_rest_records,
    )

    non_rest_business_key_profile = profile_duplicate_keys(
        non_rest_records,
        (
            "trade_date",
            "crop_code",
            "market_code",
        ),
    )
    print_duplicate_profile(
        "Non-Rest Candidate Business Key Profile",
        non_rest_business_key_profile,
    )

    rest_business_key_profile = profile_duplicate_keys(
        rest_records,
        (
            "trade_date",
            "category_code",
            "market_code",
        ),
    )
    print_duplicate_profile(
        "Rest Candidate Business Key Profile",
        rest_business_key_profile,
    )

    run_numeric_distribution_profiling(
        non_rest_records,
    )

    run_zero_pattern_profiling(
        non_rest_records,
    )

    run_zero_pattern_targeted_inspection(
        non_rest_records,
    )

    # run_rest_record_profiling(
    #     rest_records,
    # )


if __name__ == "__main__":
    main()