from dataclasses import dataclass
from datetime import date
import logging
from typing import Any, Literal

from psycopg import Connection


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PostgreSQLLoadResult:
    status: Literal["LOADED", "NO_DATA", "SKIPPED_EMPTY"]
    written_rows: int
    existing_rows: int | None = None


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
) -> PostgreSQLLoadResult:
    """以最新快照替換指定日期；空快照不清除已存在的資料。"""

    for index, record in enumerate(records):
        if record["trade_date"] != trade_date:
            raise ValueError(
                f"第 {index + 1} 筆 trade_date "
                f"不符合 target trade_date"
            )

    if not records:
        # 空快照是來源允許的格式；僅在 Load 邊界檢查既有資料。
        # 避免「原本 N 筆 → 新快照 0 筆」誤觸 DELETE。
        existing_rows = connection.execute(
            "SELECT COUNT(*) FROM agri_prices WHERE trade_date = %s",
            (trade_date,),
        ).fetchone()[0]

        if existing_rows > 0:
            logger.warning(
                "EMPTY_SNAPSHOT: trade_date=%s existing_rows=%d "
                "incoming_rows=0 action=SKIP_LOAD",
                trade_date,
                existing_rows,
            )
            return PostgreSQLLoadResult(
                status="SKIPPED_EMPTY",
                written_rows=0,
                existing_rows=existing_rows,
            )

        logger.info(
            "NO_DATA: trade_date=%s existing_rows=0 incoming_rows=0",
            trade_date,
        )
        return PostgreSQLLoadResult(
            status="NO_DATA",
            written_rows=0,
            existing_rows=0,
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
            cursor.executemany(INSERT_SQL, rows)

    return PostgreSQLLoadResult(
        status="LOADED",
        written_rows=len(records),
    )
