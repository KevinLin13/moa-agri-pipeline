from datetime import date
from typing import Any

from psycopg import Connection


INSERT_SQL = """
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
"""


def replace_trade_date_records(
    connection: Connection,
    trade_date: date,
    records: list[dict[str, Any]],
) -> int:
    """以最新 canonical snapshot 取代指定交易日期的資料。"""

    for index, record in enumerate(records):
        if record["trade_date"] != trade_date:
            raise ValueError(
                f"第 {index + 1} 筆 trade_date "
                f"不符合 target trade_date"
            )

    rows = [
        (
            record["trade_date"],
            record["category_code"],
            record["crop_code"],
            record["crop_name"],
            record["market_code"],
            record["market_name"],
            record["upper_price"],
            record["middle_price"],
            record["lower_price"],
            record["avg_price"],
            record["volume"],
        )
        for record in records
    ]

    with connection.transaction():
        with connection.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM agri_prices
                WHERE trade_date = %s
                """,
                (trade_date,),
            )

            if rows:
                cursor.executemany(
                    INSERT_SQL,
                    rows,
                )

    return len(records)