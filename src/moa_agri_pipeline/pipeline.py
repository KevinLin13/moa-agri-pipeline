from dataclasses import dataclass
from datetime import date
from pathlib import Path

from psycopg import Connection

from moa_agri_pipeline.extract.moa_api import fetch_all_pages
from moa_agri_pipeline.load.metadata import save_extract_metadata
from moa_agri_pipeline.load.parquet import save_canonical_parquet
from moa_agri_pipeline.load.postgres import replace_trade_date_records
from moa_agri_pipeline.load.raw_json import save_raw_json
from moa_agri_pipeline.quality.checks import validate_transformed_records
from moa_agri_pipeline.quality.raw import validate_raw_records
from moa_agri_pipeline.transform.agri_prices import transform_agri_prices


@dataclass(frozen=True)
class PipelineRunResult:
    query_date: date
    raw_row_count: int
    transformed_row_count: int
    postgres_row_count: int
    raw_path: Path
    metadata_path: Path
    canonical_path: Path


def run_pipeline(
    *,
    query_date: date,
    connection: Connection,
    page_size: int = 1000,
    raw_output_dir: Path = Path("data/raw"),
    processed_output_dir: Path = Path("data/processed"),
) -> PipelineRunResult:
    """執行指定交易日期的完整農產品行情 Pipeline。"""

    # Extract
    rows = fetch_all_pages(
        start_date=query_date,
        end_date=query_date,
        page_size=page_size,
    )

    # Save Raw Data
    raw_path = save_raw_json(
        records=rows,
        output_dir=raw_output_dir,
    )

    metadata_path = save_extract_metadata(
        raw_data_path=raw_path,
        start_date=query_date,
        end_date=query_date,
        page_size=page_size,
        row_count=len(rows),
    )

    # Raw Validation
    validate_raw_records(rows)

    # Transform
    transformed_rows = transform_agri_prices(rows)

    # Data Quality
    validate_transformed_records(
        transformed_rows,
        start_date=query_date,
        end_date=query_date,
    )

    # Canonical Parquet
    snapshot_id = raw_path.stem.removeprefix(
        "agri_prices_"
    )

    canonical_path = save_canonical_parquet(
        transformed_rows,
        processed_output_dir,
        snapshot_id=snapshot_id,
    )

    # PostgreSQL
    postgres_row_count = replace_trade_date_records(
        connection,
        query_date,
        transformed_rows,
    )

    return PipelineRunResult(
        query_date=query_date,
        raw_row_count=len(rows),
        transformed_row_count=len(transformed_rows),
        postgres_row_count=postgres_row_count,
        raw_path=raw_path,
        metadata_path=metadata_path,
        canonical_path=canonical_path,
    )