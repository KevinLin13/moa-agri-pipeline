from typing import Any


RAW_REQUIRED_FIELDS = (
    "交易日期",
    "種類代碼",
    "作物代號",
    "作物名稱",
    "市場代號",
    "市場名稱",
    "上價",
    "中價",
    "下價",
    "平均價",
    "交易量",
)


def validate_raw_records(records: Any) -> None:
    """檢查農業部 API 原始資料的基本結構。"""

    if not isinstance(records, list):
        raise TypeError("API 原始資料必須是 list")

    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise TypeError(
                f"第 {index + 1} 筆資料必須是 dict"
            )

        missing_fields = [
            field
            for field in RAW_REQUIRED_FIELDS
            if field not in record
        ]

        if missing_fields:
            raise ValueError(
                f"第 {index + 1} 筆資料缺少欄位：{missing_fields}"
            )