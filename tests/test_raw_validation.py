import pytest

from moa_agri_pipeline.quality.raw import validate_raw_records


VALID_RAW_RECORD = {
    "交易日期": "115.08.05",
    "種類代碼": "N05",
    "作物代號": "11",
    "作物名稱": "椰子",
    "市場代號": "104",
    "市場名稱": "台北二",
    "上價": 28.9,
    "中價": 18.8,
    "下價": 12.7,
    "平均價": 19.6,
    "交易量": 2502.0,
}


def test_validate_raw_records_allows_empty_list():
    validate_raw_records([])


def test_validate_raw_records_rejects_non_list():
    with pytest.raises(
        TypeError,
        match="API 原始資料必須是 list",
    ):
        validate_raw_records({})


def test_validate_raw_records_rejects_non_dict_record():
    with pytest.raises(
        TypeError,
        match="第 1 筆資料必須是 dict",
    ):
        validate_raw_records(["invalid record"])


def test_validate_raw_records_rejects_missing_required_field():
    record = VALID_RAW_RECORD.copy()
    del record["交易量"]

    with pytest.raises(ValueError) as exc_info:
        validate_raw_records([record])

    error_message = str(exc_info.value)

    assert "第 1 筆資料缺少欄位" in error_message
    assert "交易量" in error_message