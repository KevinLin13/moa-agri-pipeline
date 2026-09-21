from datetime import date
from unittest.mock import MagicMock

import pytest

from moa_agri_pipeline.load.postgres import (
    replace_trade_date_records,
)


TARGET_DATE = date(2026, 8, 5)


VALID_RECORD = {
    "trade_date": TARGET_DATE,
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


def make_mock_connection():
    connection = MagicMock()
    cursor = MagicMock()

    connection.cursor.return_value.__enter__.return_value = cursor

    return connection, cursor


def test_replace_trade_date_records_rejects_mixed_trade_date():
    connection, _ = make_mock_connection()

    record = VALID_RECORD.copy()
    record["trade_date"] = date(2026, 8, 6)

    with pytest.raises(
        ValueError,
        match="第 1 筆 trade_date 不符合 target trade_date",
    ):
        replace_trade_date_records(
            connection,
            TARGET_DATE,
            [record],
        )

    connection.transaction.assert_not_called()


def test_replace_trade_date_records_deletes_and_inserts_records():
    connection, cursor = make_mock_connection()

    result = replace_trade_date_records(
        connection,
        TARGET_DATE,
        [VALID_RECORD],
    )

    assert result == 1

    connection.transaction.assert_called_once_with()

    cursor.execute.assert_called_once()

    delete_sql, delete_params = (
        cursor.execute.call_args.args
    )

    assert "DELETE FROM agri_prices" in delete_sql
    assert delete_params == (TARGET_DATE,)

    cursor.executemany.assert_called_once()

    insert_sql, rows = (
        cursor.executemany.call_args.args
    )

    assert "INSERT INTO agri_prices" in insert_sql

    assert rows == [
        (
            TARGET_DATE,
            "N05",
            "11",
            "椰子",
            "104",
            "台北二",
            28.9,
            18.8,
            12.7,
            19.6,
            2502.0,
        )
    ]


def test_replace_trade_date_records_allows_empty_snapshot():
    connection, cursor = make_mock_connection()

    result = replace_trade_date_records(
        connection,
        TARGET_DATE,
        [],
    )

    assert result == 0

    cursor.execute.assert_called_once()

    delete_sql, delete_params = (
        cursor.execute.call_args.args
    )

    assert "DELETE FROM agri_prices" in delete_sql
    assert delete_params == (TARGET_DATE,)

    cursor.executemany.assert_not_called()