from datetime import date
from pathlib import Path

import logging

from moa_agri_pipeline.extract.moa_api import fetch_all_pages
from moa_agri_pipeline.load.metadata import save_extract_metadata
from moa_agri_pipeline.load.raw_json import save_raw_json
from moa_agri_pipeline.load.parquet import (
    save_canonical_parquet,
)
from moa_agri_pipeline.quality.checks import validate_transformed_records
from moa_agri_pipeline.quality.raw import validate_raw_records
from moa_agri_pipeline.transform.agri_prices import transform_agri_prices


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    query_date = date(2026, 8, 5)

    # Extract
    rows = fetch_all_pages(
        start_date=query_date,
        end_date=query_date,
        page_size=1000,
    )

    # Save Raw Data
    output_path = save_raw_json(
        records=rows,
        output_dir=Path("data/raw"),
    )

    metadata_path = save_extract_metadata(
        raw_data_path=output_path,
        start_date=query_date,
        end_date=query_date,
        page_size=1000,
        row_count=len(rows),
    )

    # Raw Validation
    validate_raw_records(rows)

    print("\nRaw Validation：")
    print(f"檢查通過，共 {len(rows)} 筆")

    # Transform
    transformed_rows = transform_agri_prices(rows)

    # Data Quality
    validate_transformed_records(
        transformed_rows,
        start_date=query_date,
        end_date=query_date,
    )

    print("\nData Quality：")
    print(f"檢查通過，共 {len(transformed_rows)} 筆")

    # Load Canonical Parquet
    snapshot_id = output_path.stem.removeprefix(
        "agri_prices_"
    )

    canonical_path = save_canonical_parquet(
        transformed_rows,
        Path("data/processed"),
        snapshot_id=snapshot_id,
    )

    # Execution Summary
    print(f"\n查詢日期：{query_date}")
    print(f"總資料筆數：{len(rows)}")
    print(f"原始資料已保存：{output_path}")
    print(f"Metadata 已保存：{metadata_path}")
    print(f"Canonical Parquet 已保存：{canonical_path}")

    if rows:
        print("\n第一筆 Raw Data：")
        print(rows[0])

        print("\n最後一筆 Raw Data：")
        print(rows[-1])
    else:
        print("\nAPI 回傳空清單")

    if transformed_rows:
        print("\n轉換後第一筆資料：")
        print(transformed_rows[0])


if __name__ == "__main__":
    main()