from moa_agri_pipeline.extract.moa_api import fetch_sample_data


def main() -> None:
    rows = fetch_sample_data()

    print(f"回傳型別：{type(rows)}")
    print(f"資料筆數：{len(rows)}")

    if rows:
        print("第一筆資料：")
        print(rows[0])
    else:
        print("API 回傳空清單")


if __name__ == "__main__":
    main()