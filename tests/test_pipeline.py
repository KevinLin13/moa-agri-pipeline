from datetime import date

import moa_agri_pipeline.pipeline as pipeline_module
from moa_agri_pipeline.pipeline import run_pipeline


def test_run_pipeline_orchestrates_all_stages(
    monkeypatch,
    tmp_path,
):
    query_date = date(2026, 9, 21)

    raw_rows = [{"raw": "record"}]

    transformed_rows = [
        {
            "trade_date": query_date,
        }
    ]

    raw_path = (
        tmp_path
        / "raw"
        / "agri_prices_20260921T120000.json"
    )

    metadata_path = (
        tmp_path
        / "raw"
        / "agri_prices_20260921T120000_metadata.json"
    )

    canonical_path = (
        tmp_path
        / "processed"
        / "agri_prices_20260921T120000.parquet"
    )

    calls = []

    def fake_fetch_all_pages(
        *,
        start_date,
        end_date,
        page_size,
    ):
        calls.append("extract")
        assert start_date == query_date
        assert end_date == query_date
        assert page_size == 1000
        return raw_rows

    def fake_save_raw_json(*, records, output_dir):
        calls.append("save_raw")
        assert records == raw_rows
        return raw_path

    def fake_save_extract_metadata(**kwargs):
        calls.append("save_metadata")
        return metadata_path

    def fake_validate_raw_records(records):
        calls.append("raw_validation")
        assert records == raw_rows

    def fake_transform_agri_prices(records):
        calls.append("transform")
        assert records == raw_rows
        return transformed_rows

    def fake_validate_transformed_records(
        records,
        *,
        start_date,
        end_date,
    ):
        calls.append("data_quality")
        assert records == transformed_rows
        assert start_date == query_date
        assert end_date == query_date

    def fake_save_canonical_parquet(
        records,
        output_dir,
        *,
        snapshot_id,
    ):
        calls.append("parquet")
        assert records == transformed_rows
        assert snapshot_id == "20260921T120000"
        return canonical_path

    def fake_replace_trade_date_records(
        connection,
        trade_date,
        records,
    ):
        calls.append("postgres")
        assert trade_date == query_date
        assert records == transformed_rows
        return len(records)

    monkeypatch.setattr(
        pipeline_module,
        "fetch_all_pages",
        fake_fetch_all_pages,
    )
    monkeypatch.setattr(
        pipeline_module,
        "save_raw_json",
        fake_save_raw_json,
    )
    monkeypatch.setattr(
        pipeline_module,
        "save_extract_metadata",
        fake_save_extract_metadata,
    )
    monkeypatch.setattr(
        pipeline_module,
        "validate_raw_records",
        fake_validate_raw_records,
    )
    monkeypatch.setattr(
        pipeline_module,
        "transform_agri_prices",
        fake_transform_agri_prices,
    )
    monkeypatch.setattr(
        pipeline_module,
        "validate_transformed_records",
        fake_validate_transformed_records,
    )
    monkeypatch.setattr(
        pipeline_module,
        "save_canonical_parquet",
        fake_save_canonical_parquet,
    )
    monkeypatch.setattr(
        pipeline_module,
        "replace_trade_date_records",
        fake_replace_trade_date_records,
    )

    result = run_pipeline(
        query_date=query_date,
        connection=object(),
        raw_output_dir=tmp_path / "raw",
        processed_output_dir=tmp_path / "processed",
    )

    assert calls == [
        "extract",
        "save_raw",
        "save_metadata",
        "raw_validation",
        "transform",
        "data_quality",
        "parquet",
        "postgres",
    ]

    assert result.query_date == query_date
    assert result.raw_row_count == 1
    assert result.transformed_row_count == 1
    assert result.postgres_row_count == 1
    assert result.raw_path == raw_path
    assert result.metadata_path == metadata_path
    assert result.canonical_path == canonical_path