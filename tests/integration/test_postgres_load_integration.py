import os
from datetime import date

import psycopg
import pytest

from moa_agri_pipeline.load.postgres import (
    replace_trade_date_records,
)


TEST_DATE = date(2099, 1, 2)


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_POSTGRES_INTEGRATION") != "1",
    reason=(
        "Set RUN_POSTGRES_INTEGRATION=1 "
        "to run PostgreSQL integration tests"
    ),
)


OLD_RECORD = {
    "trade_date": TEST_DATE,
    "category_code": "N05",
    "crop_code": "TEST001",
    "crop_name": "原始作物",
    "market_code": "M001",
    "market_name": "原始市場",
    "upper_price": 10.0,
    "middle_price": 9.0,
    "lower_price": 8.0,
    "avg_price": 9.0,
    "volume": 100.0,
}


NEW_RECORD = {
    "trade_date": TEST_DATE,
    "category_code": "N05",
    "crop_code": "TEST001",
    "crop_name": "更新後作物",
    "market_code": "M001",
    "market_name": "更新後市場",
    "upper_price": 20.0,
    "middle_price": 18.0,
    "lower_price": 16.0,
    "avg_price": 18.0,
    "volume": 200.0,
}


@pytest.fixture
def connection():
    connection = psycopg.connect(
        autocommit=True,
    )

    connection.execute(
        """
        DELETE FROM agri_prices
        WHERE trade_date = %s
        """,
        (TEST_DATE,),
    )

    connection.execute(
        """
        INSERT INTO agri_prices (
            trade_date,
            category_code,
            crop_code,
            crop_name,
            market_code,
            market_name,
            upper_price,
            middle_price,
            lower_price,
            avg_price,
            volume
        )
        VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        """,
        (
            OLD_RECORD["trade_date"],
            OLD_RECORD["category_code"],
            OLD_RECORD["crop_code"],
            OLD_RECORD["crop_name"],
            OLD_RECORD["market_code"],
            OLD_RECORD["market_name"],
            OLD_RECORD["upper_price"],
            OLD_RECORD["middle_price"],
            OLD_RECORD["lower_price"],
            OLD_RECORD["avg_price"],
            OLD_RECORD["volume"],
        ),
    )

    yield connection

    connection.execute(
        """
        DELETE FROM agri_prices
        WHERE trade_date = %s
        """,
        (TEST_DATE,),
    )

    connection.close()


def test_replace_trade_date_records_commits_replacement(
    connection,
):
    result = replace_trade_date_records(
        connection,
        TEST_DATE,
        [NEW_RECORD],
    )

    assert result == 1

    row = connection.execute(
        """
        SELECT
            crop_name,
            market_name,
            avg_price,
            volume
        FROM agri_prices
        WHERE trade_date = %s
        """,
        (TEST_DATE,),
    ).fetchone()

    assert row == (
        "更新後作物",
        "更新後市場",
        18.0,
        200.0,
    )


def test_replace_trade_date_records_rolls_back_on_failure(
    connection,
):
    duplicate_record = NEW_RECORD.copy()
    duplicate_record["crop_name"] = "重複作物"

    with pytest.raises(
        psycopg.errors.UniqueViolation
    ):
        replace_trade_date_records(
            connection,
            TEST_DATE,
            [
                NEW_RECORD,
                duplicate_record,
            ],
        )

    rows = connection.execute(
        """
        SELECT
            crop_name,
            market_name,
            avg_price,
            volume
        FROM agri_prices
        WHERE trade_date = %s
        """,
        (TEST_DATE,),
    ).fetchall()

    assert rows == [
        (
            "原始作物",
            "原始市場",
            9.0,
            100.0,
        )
    ]

def test_replace_trade_date_records_is_idempotent(
    connection,
):
    first_result = replace_trade_date_records(
        connection,
        TEST_DATE,
        [NEW_RECORD],
    )

    rows_after_first_load = connection.execute(
        """
        SELECT
            category_code,
            crop_code,
            crop_name,
            market_code,
            market_name,
            upper_price,
            middle_price,
            lower_price,
            avg_price,
            volume
        FROM agri_prices
        WHERE trade_date = %s
        """,
        (TEST_DATE,),
    ).fetchall()

    second_result = replace_trade_date_records(
        connection,
        TEST_DATE,
        [NEW_RECORD],
    )

    rows_after_second_load = connection.execute(
        """
        SELECT
            category_code,
            crop_code,
            crop_name,
            market_code,
            market_name,
            upper_price,
            middle_price,
            lower_price,
            avg_price,
            volume
        FROM agri_prices
        WHERE trade_date = %s
        """,
        (TEST_DATE,),
    ).fetchall()

    assert first_result == 1
    assert second_result == 1

    assert rows_after_second_load == rows_after_first_load

    assert rows_after_second_load == [
        (
            "N05",
            "TEST001",
            "更新後作物",
            "M001",
            "更新後市場",
            20.0,
            18.0,
            16.0,
            18.0,
            200.0,
        )
    ]