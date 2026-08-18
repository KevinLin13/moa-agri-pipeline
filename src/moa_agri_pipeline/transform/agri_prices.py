from typing import Any
from datetime import date

COLUMN_MAPPING = {
    "交易日期": "trade_date",
    "種類代碼": "category_code",
    "作物代號": "crop_code",
    "作物名稱": "crop_name",
    "市場代號": "market_code",
    "市場名稱": "market_name",
    "上價": "upper_price",
    "中價": "middle_price",
    "下價": "lower_price",
    "平均價": "avg_price",
    "交易量": "volume",
}

def rename_fields(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """將農業部 API 中文欄位名稱轉為內部標準英文名稱。"""

    return [
        {
            COLUMN_MAPPING.get(key, key): value
            for key, value in record.items()
        }
        for record in records
    ]

def parse_minguo_date(value: str) -> date:
    """將民國日期字串轉換成 Python date。"""

    year_text, month_text, day_text = value.split(".")

    year = int(year_text) + 1911
    month = int(month_text)
    day = int(day_text)

    return date(year, month, day)

def convert_trade_dates(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """將資料中的交易日期轉換成 Python date。"""

    return [
        {
            **record,
            "trade_date": parse_minguo_date(record["trade_date"]),
        }
        for record in records
    ]