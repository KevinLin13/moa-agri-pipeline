from datetime import date

import pyarrow as pa
import pyarrow.parquet as pq

from moa_agri_pipeline.load.parquet import (
    CANONICAL_SCHEMA,
    save_canonical_parquet,
)


CANONICAL_RECORDS = [
    {
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
    },
    {
        "trade_date": date(2026, 8, 5),
        "category_code": None,
        "crop_code": "FE800",
        "crop_name": None,
        "market_code": "105",
        "market_name": "台北市場",
        "upper_price": 100.0,
        "middle_price": 80.0,
        "lower_price": 60.0,
        "avg_price": 80.0,
        "volume": 20.0,
    },
]


def test_save_canonical_parquet_round_trip(
    tmp_path,
):
    output_path = save_canonical_parquet(
        CANONICAL_RECORDS,
        tmp_path,
        snapshot_id="20260805T120000",
    )

    assert output_path == (
        tmp_path
        / "agri_prices_20260805T120000.parquet"
    )

    assert output_path.exists()

    table = pq.read_table(output_path)

    assert table.num_rows == 2
    assert table.column_names == (
        CANONICAL_SCHEMA.names
    )

    assert (
        table.schema.field("trade_date").type
        == pa.date32()
    )

    assert (
        table.schema.field("upper_price").type
        == pa.float64()
    )

    loaded_records = table.to_pylist()

    assert loaded_records == CANONICAL_RECORDS


def test_save_canonical_parquet_allows_empty_records(
    tmp_path,
):
    output_path = save_canonical_parquet(
        [],
        tmp_path,
        snapshot_id="20260805T120000",
    )

    table = pq.read_table(output_path)

    assert table.num_rows == 0
    assert table.column_names == (
        CANONICAL_SCHEMA.names
    )