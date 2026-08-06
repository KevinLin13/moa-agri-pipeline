from typing import Any

import requests


API_URL = (
    "https://data.moa.gov.tw/"
    "Service/OpenData/FromM/FarmTransData.aspx"
)


def fetch_page(
    top: int = 10,
    skip: int = 0,
) -> list[dict[str, Any]]:
    """從農業部 API 取得一頁農產品交易行情資料。"""

    if not 1 <= top <= 1000:
        raise ValueError("top 必須介於 1 到 1000 之間")

    if skip < 0:
        raise ValueError("skip 不得小於 0")

    params = {
        "$top": top,
        "$skip": skip,
    }

    response = requests.get(
        API_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    if not isinstance(data, list):
        raise TypeError("API 回傳的 JSON 最外層不是 list")

    return data

def fetch_all_pages(
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    """分頁取得農業部 API 目前預設日期範圍內的全部資料。"""

    if not 1 <= page_size <= 1000:
        raise ValueError("page_size 必須介於 1 到 1000 之間")

    all_rows: list[dict[str, Any]] = []
    skip = 0

    while True:
        page = fetch_page(
            top=page_size,
            skip=skip,
        )

        all_rows.extend(page)

        if len(page) < page_size:
            break

        skip += page_size

    return all_rows