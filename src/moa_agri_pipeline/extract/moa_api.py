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