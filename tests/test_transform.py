from datetime import date

from moa_agri_pipeline.transform.agri_prices import (
    convert_numeric_fields,
    convert_trade_dates,
    parse_minguo_date,
    rename_fields,
    transform_agri_prices,
)


RAW_RECORD = {
    "交易日期": "115.08.05",
    "種類代碼": "N05",
    "作物代號": "11",
    "作物名稱": "椰子",
    "市場代號": "104",
    "市場名稱": "台北二",
    "上價": "28.9",
    "中價": "18.8",
    "下價": "12.7",
    "平均價": "19.6",
    "交易量": "2502.0",
}


def test_rename_fields():
    result = rename_fields([RAW_RECORD])

    record = result[0]

    assert record["trade_date"] == "115.08.05"
    assert record["crop_name"] == "椰子"
    assert record["market_name"] == "台北二"
    assert record["avg_price"] == "19.6"
    assert record["volume"] == "2502.0"


def test_parse_minguo_date():
    result = parse_minguo_date("115.08.05")

    assert result == date(2026, 8, 5)


def test_convert_trade_dates():
    records = [
        {
            "trade_date": "115.08.05",
            "crop_name": "椰子",
        }
    ]

    result = convert_trade_dates(records)

    assert result[0]["trade_date"] == date(2026, 8, 5)
    assert result[0]["crop_name"] == "椰子"


def test_convert_numeric_fields():
    records = [
        {
            "upper_price": "28.9",
            "middle_price": "18.8",
            "lower_price": "12.7",
            "avg_price": "19.6",
            "volume": "2502.0",
        }
    ]

    result = convert_numeric_fields(records)

    assert result[0]["upper_price"] == 28.9
    assert result[0]["middle_price"] == 18.8
    assert result[0]["lower_price"] == 12.7
    assert result[0]["avg_price"] == 19.6
    assert result[0]["volume"] == 2502.0

    assert isinstance(result[0]["upper_price"], float)
    assert isinstance(result[0]["volume"], float)


def test_transform_agri_prices():
    result = transform_agri_prices([RAW_RECORD])

    record = result[0]

    assert record == {
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


def test_transform_agri_prices_allows_empty_list():
    result = transform_agri_prices([])

    assert result == []