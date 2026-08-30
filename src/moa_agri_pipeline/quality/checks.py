from datetime import date
from math import isfinite
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


REQUIRED_TEXT_FIELDS = (
    "crop_code",
    "market_code",
    "market_name",
)


OPTIONAL_TEXT_FIELDS = (
    "category_code",
    "crop_name",
)


NUMERIC_FIELDS = (
    "upper_price",
    "middle_price",
    "lower_price",
    "avg_price",
    "volume",
)


def validate_transformed_records(
    records: Any,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
) -> None:
    """檢查 Transform 後資料的基本品質。"""

    if not isinstance(records, list):
        raise TypeError("Transform 後資料必須是 list")

    seen_non_rest_keys = set()
    seen_rest_keys = set()

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

        trade_date = record["trade_date"]
        if not isinstance(trade_date, date):
            raise TypeError(
                f"第 {index + 1} 筆 trade_date 必須是 date"
            )

        if (
            start_date is not None
            and trade_date < start_date
        ):
            raise ValueError(
                f"第 {index + 1} 筆 trade_date 早於查詢 start_date"
            )

        if (
            end_date is not None
            and trade_date > end_date
        ):
            raise ValueError(
                f"第 {index + 1} 筆 trade_date 晚於查詢 end_date"
            )

        for field in REQUIRED_TEXT_FIELDS:
            value = record[field]

            if not isinstance(value, str):
                raise TypeError(
                    f"第 {index + 1} 筆 {field} 必須是 str"
                )

            if not value.strip():
                raise ValueError(
                    f"第 {index + 1} 筆 {field} 不得為空"
                )

        for field in OPTIONAL_TEXT_FIELDS:
            value = record[field]

            if value is None:
                continue

            if not isinstance(value, str):
                raise TypeError(
                    f"第 {index + 1} 筆 {field} 必須是 str 或 None"
                )

            if not value.strip():
                raise ValueError(
                    f"第 {index + 1} 筆 {field} 不得為空字串"
                )

        for field in NUMERIC_FIELDS:
            value = record[field]

            if not isinstance(value, float):
                raise TypeError(
                    f"第 {index + 1} 筆 {field} 必須是 float"
                )

            if not isfinite(value):
                raise ValueError(
                    f"第 {index + 1} 筆 {field} 必須是有限數值"
                )

            if value < 0:
                raise ValueError(
                    f"第 {index + 1} 筆 {field} 不得小於 0"
                )

        if record["crop_code"] == "rest":
            category_code = record["category_code"]

            if category_code is None:
                raise ValueError(
                    f"第 {index + 1} 筆 Rest record "
                    "的 category_code 不得為 None"
                )

            business_key = (
                record["trade_date"],
                category_code,
                record["market_code"],
            )

            if business_key in seen_rest_keys:
                raise ValueError(
                    f"第 {index + 1} 筆 Rest Business Key 重複："
                    f"{business_key}"
                )

            seen_rest_keys.add(business_key)

        else:
            business_key = (
                record["trade_date"],
                record["crop_code"],
                record["market_code"],
            )

            if business_key in seen_non_rest_keys:
                raise ValueError(
                    f"第 {index + 1} 筆 Non-Rest Business Key 重複："
                    f"{business_key}"
                )

            seen_non_rest_keys.add(business_key)