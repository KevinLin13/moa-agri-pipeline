from datetime import date
from pathlib import Path

import logging

from moa_agri_pipeline.extract.moa_api import fetch_all_pages
from moa_agri_pipeline.load.raw_json import save_raw_json
from moa_agri_pipeline.load.metadata import save_extract_metadata
from moa_agri_pipeline.transform.agri_prices import (
    convert_numeric_fields,
    convert_trade_dates,
    rename_fields,
)

def main() -> None:
    logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    query_date = date(2026, 8, 5)

    rows = fetch_all_pages(
        start_date=query_date,
        end_date=query_date,
        page_size=1000,
    )

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

    transformed_rows = rename_fields(rows)
    transformed_rows = convert_trade_dates(transformed_rows)
    transformed_rows = convert_numeric_fields(transformed_rows)

    print(f"查詢日期：{query_date}")
    print(f"總資料筆數：{len(rows)}")
    print(f"原始資料已保存：{output_path}")
    print(f"Metadata 已保存：{metadata_path}")

    if rows:
        print("\n第一筆資料：")
        print(rows[0])

        print("\n最後一筆資料：")
        print(rows[-1])
    else:
        print("API 回傳空清單")

    if transformed_rows:
        first_row = transformed_rows[0]

        print("\n轉換後第一筆資料：")
        print(first_row)

        print("\n數值欄位型別：")
        print("upper_price:", type(first_row["upper_price"]))
        print("middle_price:", type(first_row["middle_price"]))
        print("lower_price:", type(first_row["lower_price"]))
        print("avg_price:", type(first_row["avg_price"]))
        print("volume:", type(first_row["volume"]))

if __name__ == "__main__":
    main()