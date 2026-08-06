from datetime import date
from pathlib import Path

import logging

from moa_agri_pipeline.extract.moa_api import fetch_all_pages
from moa_agri_pipeline.load.raw_json import save_raw_json


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

    print(f"查詢日期：{query_date}")
    print(f"總資料筆數：{len(rows)}")
    print(f"原始資料已保存：{output_path}")
    
    if rows:
        print("\n第一筆資料：")
        print(rows[0])

        print("\n最後一筆資料：")
        print(rows[-1])
    else:
        print("API 回傳空清單")


if __name__ == "__main__":
    main()