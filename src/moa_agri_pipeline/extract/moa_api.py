from typing import Any

import requests

API_URL = (
    "https://data.moa.gov.tw/"
    "Service/OpenData/FromM/FarmTransData.aspx"
)

def fetch_sample_data() -> list[dict[str, Any]]:
    """從農業部 API 取得少量農產品交易行情資料。"""

    params = {
        "$top": 10,
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