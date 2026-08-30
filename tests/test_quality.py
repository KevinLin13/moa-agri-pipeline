from datetime import date

import pytest

from moa_agri_pipeline.quality.checks import (
    validate_transformed_records,
)


VALID_TRANSFORMED_RECORD = {
    "trade_date": date(2026, 8, 5),
    "category_code": "N05",
    "crop_code": "11",
    "crop_name": "椰子",
    "market_code": "104",
    "market_name": "台北二",
    "upper_price": 28.9,
    "middle_price": 18.8,
    "lower_price": 12.7,
    "avg_price": 19.6,
    "volume": 2502.0,
}


def test_validate_transformed_records_accepts_valid_record():
    validate_transformed_records([VALID_TRANSFORMED_RECORD])

def test_validate_transformed_records_allows_empty_list():
    validate_transformed_records([])

def test_validate_transformed_records_accepts_trade_date_in_range():
    validate_transformed_records(
        [VALID_TRANSFORMED_RECORD],
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 10),
    )

def test_validate_transformed_records_rejects_trade_date_before_start_date():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["trade_date"] = date(2026, 7, 31)

    with pytest.raises(
        ValueError,
        match="第 1 筆 trade_date 早於查詢 start_date",
    ):
        validate_transformed_records(
            [record],
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 10),
        )


def test_validate_transformed_records_rejects_trade_date_after_end_date():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["trade_date"] = date(2026, 8, 11)

    with pytest.raises(
        ValueError,
        match="第 1 筆 trade_date 晚於查詢 end_date",
    ):
        validate_transformed_records(
            [record],
            start_date=date(2026, 8, 1),
            end_date=date(2026, 8, 10),
        )

def test_validate_transformed_records_rejects_non_list():
    with pytest.raises(
        TypeError,
        match="Transform 後資料必須是 list",
    ):
        validate_transformed_records({})


def test_validate_transformed_records_rejects_non_dict_record():
    with pytest.raises(
        TypeError,
        match="第 1 筆 Transform 資料必須是 dict",
    ):
        validate_transformed_records(["invalid record"])


def test_validate_transformed_records_rejects_missing_required_field():
    record = VALID_TRANSFORMED_RECORD.copy()
    del record["volume"]

    with pytest.raises(ValueError) as exc_info:
        validate_transformed_records([record])

    error_message = str(exc_info.value)

    assert "第 1 筆 Transform 資料缺少欄位" in error_message
    assert "volume" in error_message


def test_validate_transformed_records_rejects_invalid_trade_date_type():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["trade_date"] = "2026-08-05"

    with pytest.raises(
        TypeError,
        match="第 1 筆 trade_date 必須是 date",
    ):
        validate_transformed_records([record])


def test_validate_transformed_records_rejects_invalid_numeric_type():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["avg_price"] = "19.6"

    with pytest.raises(
        TypeError,
        match="第 1 筆 avg_price 必須是 float",
    ):
        validate_transformed_records([record])

def test_validate_transformed_records_rejects_negative_price():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["avg_price"] = -19.6

    with pytest.raises(
        ValueError,
        match="第 1 筆 avg_price 不得小於 0",
    ):
        validate_transformed_records([record])


def test_validate_transformed_records_rejects_negative_volume():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["volume"] = -2502.0

    with pytest.raises(
        ValueError,
        match="第 1 筆 volume 不得小於 0",
    ):
        validate_transformed_records([record])

def test_validate_transformed_records_rejects_nan():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["avg_price"] = float("nan")

    with pytest.raises(
        ValueError,
        match="第 1 筆 avg_price 必須是有限數值",
    ):
        validate_transformed_records([record])


def test_validate_transformed_records_rejects_positive_infinity():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["avg_price"] = float("inf")

    with pytest.raises(
        ValueError,
        match="第 1 筆 avg_price 必須是有限數值",
    ):
        validate_transformed_records([record])


def test_validate_transformed_records_rejects_negative_infinity():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["avg_price"] = float("-inf")

    with pytest.raises(
        ValueError,
        match="第 1 筆 avg_price 必須是有限數值",
    ):
        validate_transformed_records([record])

def test_validate_transformed_records_rejects_empty_crop_code():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["crop_code"] = ""

    with pytest.raises(
        ValueError,
        match="第 1 筆 crop_code 不得為空",
    ):
        validate_transformed_records([record])

def test_validate_transformed_records_rejects_blank_market_code():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["market_code"] = "   "

    with pytest.raises(
        ValueError,
        match="第 1 筆 market_code 不得為空",
    ):
        validate_transformed_records([record])

def test_validate_transformed_records_allows_nullable_fields():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["category_code"] = None
    record["crop_name"] = None

    validate_transformed_records([record])

def test_validate_transformed_records_rejects_null_crop_code():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["crop_code"] = None

    with pytest.raises(
        TypeError,
        match="第 1 筆 crop_code 必須是 str",
    ):
        validate_transformed_records([record])

def test_validate_transformed_records_rejects_blank_market_code():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["market_code"] = "   "

    with pytest.raises(
        ValueError,
        match="第 1 筆 market_code 不得為空",
    ):
        validate_transformed_records([record])

def test_validate_transformed_records_rejects_invalid_optional_text_type():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["category_code"] = 123

    with pytest.raises(
        TypeError,
        match="第 1 筆 category_code 必須是 str 或 None",
    ):
        validate_transformed_records([record])

def test_validate_transformed_records_rejects_nan():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["avg_price"] = float("nan")

    with pytest.raises(
        ValueError,
        match="第 1 筆 avg_price 必須是有限數值",
    ):
        validate_transformed_records([record])


def test_validate_transformed_records_rejects_infinity():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["avg_price"] = float("inf")

    with pytest.raises(
        ValueError,
        match="第 1 筆 avg_price 必須是有限數值",
    ):
        validate_transformed_records([record])

def test_validate_transformed_records_rejects_negative_price():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["avg_price"] = -19.6

    with pytest.raises(
        ValueError,
        match="第 1 筆 avg_price 不得小於 0",
    ):
        validate_transformed_records([record])


def test_validate_transformed_records_rejects_negative_volume():
    record = VALID_TRANSFORMED_RECORD.copy()
    record["volume"] = -2502.0

    with pytest.raises(
        ValueError,
        match="第 1 筆 volume 不得小於 0",
    ):
        validate_transformed_records([record])

def test_validate_transformed_records_rejects_duplicate_non_rest_business_key():
    record_1 = VALID_TRANSFORMED_RECORD.copy()
    record_2 = VALID_TRANSFORMED_RECORD.copy()

    record_2["avg_price"] = 25.0
    record_2["volume"] = 3000.0

    with pytest.raises(
        ValueError,
        match="第 2 筆 Non-Rest Business Key 重複",
    ):
        validate_transformed_records(
            [record_1, record_2],
            start_date=date(2026, 8, 5),
            end_date=date(2026, 8, 5),
        )

def test_validate_transformed_records_allows_different_non_rest_market():
    record_1 = VALID_TRANSFORMED_RECORD.copy()
    record_2 = VALID_TRANSFORMED_RECORD.copy()

    record_2["market_code"] = "109"
    record_2["market_name"] = "台北一"

    validate_transformed_records(
        [record_1, record_2],
        start_date=date(2026, 8, 5),
        end_date=date(2026, 8, 5),
    )

def test_validate_transformed_records_rejects_duplicate_rest_business_key():
    record_1 = VALID_TRANSFORMED_RECORD.copy()
    record_2 = VALID_TRANSFORMED_RECORD.copy()

    for record in (record_1, record_2):
        record["category_code"] = "N04"
        record["crop_code"] = "rest"
        record["crop_name"] = "休市"
        record["market_code"] = "104"
        record["market_name"] = "台北二"
        record["upper_price"] = 0.0
        record["middle_price"] = 0.0
        record["lower_price"] = 0.0
        record["avg_price"] = 0.0
        record["volume"] = 0.0

    with pytest.raises(
        ValueError,
        match="第 2 筆 Rest Business Key 重複",
    ):
        validate_transformed_records(
            [record_1, record_2],
            start_date=date(2026, 8, 5),
            end_date=date(2026, 8, 5),
        )

def test_validate_transformed_records_allows_different_rest_category():
    record_1 = VALID_TRANSFORMED_RECORD.copy()
    record_2 = VALID_TRANSFORMED_RECORD.copy()

    for record in (record_1, record_2):
        record["crop_code"] = "rest"
        record["crop_name"] = "休市"
        record["market_code"] = "104"
        record["market_name"] = "台北二"
        record["upper_price"] = 0.0
        record["middle_price"] = 0.0
        record["lower_price"] = 0.0
        record["avg_price"] = 0.0
        record["volume"] = 0.0

    record_1["category_code"] = "N04"
    record_2["category_code"] = "N06"

    validate_transformed_records(
        [record_1, record_2],
        start_date=date(2026, 8, 5),
        end_date=date(2026, 8, 5),
    )

def test_validate_transformed_records_rejects_null_rest_category_code():
    record = VALID_TRANSFORMED_RECORD.copy()

    record["category_code"] = None
    record["crop_code"] = "rest"
    record["crop_name"] = "休市"
    record["upper_price"] = 0.0
    record["middle_price"] = 0.0
    record["lower_price"] = 0.0
    record["avg_price"] = 0.0
    record["volume"] = 0.0

    with pytest.raises(
        ValueError,
        match="第 1 筆 Rest record 的 category_code 不得為 None",
    ):
        validate_transformed_records(
            [record],
            start_date=date(2026, 8, 5),
            end_date=date(2026, 8, 5),
        )