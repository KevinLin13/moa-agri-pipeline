from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


CANONICAL_SCHEMA = pa.schema(
    [
        pa.field(
            "trade_date",
            pa.date32(),
            nullable=False,
        ),
        pa.field(
            "category_code",
            pa.string(),
            nullable=True,
        ),
        pa.field(
            "crop_code",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "crop_name",
            pa.string(),
            nullable=True,
        ),
        pa.field(
            "market_code",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "market_name",
            pa.string(),
            nullable=False,
        ),
        pa.field(
            "upper_price",
            pa.float64(),
            nullable=False,
        ),
        pa.field(
            "middle_price",
            pa.float64(),
            nullable=False,
        ),
        pa.field(
            "lower_price",
            pa.float64(),
            nullable=False,
        ),
        pa.field(
            "avg_price",
            pa.float64(),
            nullable=False,
        ),
        pa.field(
            "volume",
            pa.float64(),
            nullable=False,
        ),
    ]
)

def save_canonical_parquet(
    records: list[dict[str, Any]],
    output_dir: Path,
    *,
    snapshot_id: str,
) -> Path:
    """將通過 Data Quality 的 canonical records 保存為 Parquet snapshot。"""

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / f"agri_prices_{snapshot_id}.parquet"
    )

    table = pa.Table.from_pylist(
        records,
        schema=CANONICAL_SCHEMA,
    )

    pq.write_table(
        table,
        output_path,
        compression="snappy",
    )

    return output_path

def load_canonical_parquet(
    input_path: Path,
) -> list[dict[str, Any]]:
    """讀取 canonical Parquet snapshot。"""

    table = pq.read_table(input_path)

    if not table.schema.equals(
        CANONICAL_SCHEMA
    ):
        raise ValueError(
            "Parquet schema 不符合 canonical schema"
        )

    return table.to_pylist()