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