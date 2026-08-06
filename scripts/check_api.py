from moa_agri_pipeline.extract.moa_api import fetch_all_pages


def main() -> None:
    rows = fetch_all_pages(page_size=1000)

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