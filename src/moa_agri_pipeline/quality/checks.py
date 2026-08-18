from datetime import date
from typing import Any


TRANSFORMED_REQUIRED_FIELDS = (
    "trade_date",
    "category_code",
    "crop_code",
    "crop_name",
    "market_code",
    "market_name",
    "upper_price",
    "middle_price",
    "lower_price",
    "avg_price",
    "volume",
)


NUMERIC_FIELDS = (
    "upper_price",
    "middle_price",
    "lower_price",
    "avg_price",
    "volume",
)


def validate_transformed_records(records: Any) -> None:
    """檢查 Transform 後資料的基本品質。"""

    if not isinstance(records, list):
        raise TypeError("Transform 後資料必須是 list")

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(
                f"第 {index + 1} 筆 Transform 資料必須是 dict"
            )

        missing_fields = [
            field
            for field in TRANSFORMED_REQUIRED_FIELDS
            if field not in record
        ]

        if missing_fields:
            raise ValueError(
                f"第 {index + 1} 筆 Transform 資料缺少欄位："
                f"{missing_fields}"
            )

        if not isinstance(record["trade_date"], date):
            raise TypeError(
                f"第 {index + 1} 筆 trade_date 必須是 date"
            )

        for field in NUMERIC_FIELDS:
            if not isinstance(record[field], float):
                raise TypeError(
                    f"第 {index + 1} 筆 {field} 必須是 float"
                )