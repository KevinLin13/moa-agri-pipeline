from datetime import date
import logging

from moa_agri_pipeline.extract.moa_api import fetch_all_pages


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

    print(f"查詢日期：{query_date}")
    print(f"總資料筆數：{len(rows)}")

    if rows:
        print("\n第一筆資料：")
        print(rows[0])

        print("\n最後一筆資料：")
        print(rows[-1])
    else:
        print("API 回傳空清單")


if __name__ == "__main__":
    main()