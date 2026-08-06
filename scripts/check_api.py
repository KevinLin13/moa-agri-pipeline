from moa_agri_pipeline.extract.moa_api import fetch_page


def main() -> None:
    first_page = fetch_page(
        top=10,
        skip=0,
    )

    second_page = fetch_page(
        top=10,
        skip=10,
    )

    print(f"第一頁筆數：{len(first_page)}")
    print(f"第二頁筆數：{len(second_page)}")

    if first_page:
        print("\n第一頁第一筆：")
        print(first_page[0])

    if second_page:
        print("\n第二頁第一筆：")
        print(second_page[0])


if __name__ == "__main__":
    main()