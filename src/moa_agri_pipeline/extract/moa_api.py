from typing import Any
from datetime import date

import requests


API_URL = (
    "https://data.moa.gov.tw/"
    "Service/OpenData/FromM/FarmTransData.aspx"
)

def format_minguo_date(value: date) -> str:
    """將 Python 西元日期轉成農業部 API 使用的民國日期格式。"""

    minguo_year = value.year - 1911

    if minguo_year <= 0:
        raise ValueError("日期必須晚於民國元年")

    return f"{minguo_year:03d}.{value.month:02d}.{value.day:02d}"


def fetch_page(
    top: int = 10,
    skip: int = 0,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict[str, Any]]:
    """從農業部 API 取得一頁農產品交易行情資料。"""

    if not 1 <= top <= 1000:
        raise ValueError("top 必須介於 1 到 1000 之間")

    if skip < 0:
        raise ValueError("skip 不得小於 0")

    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date 不得晚於 end_date")
    
    params: dict[str, int | str] = {
        "$top": top,
        "$skip": skip,
    }

    if start_date is not None:
        params["StartDate"] = format_minguo_date(start_date)

    if end_date is not None:
        params["EndDate"] = format_minguo_date(end_date)

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
    start_date: date | None = None,
    end_date: date | None = None,
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
            start_date=start_date,
            end_date=end_date,
        )

        all_rows.extend(page)

        if len(page) < page_size:
            break

        skip += page_size

    return all_rows