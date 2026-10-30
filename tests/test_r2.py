
import json
from datetime import date

import pytest

from moa_agri_pipeline.load.raw_json import save_raw_json
from moa_agri_pipeline.load.metadata import save_extract_metadata
from moa_agri_pipeline.load.parquet import save_canonical_parquet
from moa_agri_pipeline.load.r2 import build_snapshot_object_keys


@pytest.fixture
def snapshot_files(tmp_path):
    query_date = date(2026, 10, 30)

    raw_path = save_raw_json([], tmp_path / "raw")
    snapshot_id = raw_path.stem.removeprefix("agri_prices_")

    metadata_path = save_extract_metadata(
        raw_data_path=raw_path,
        start_date=query_date,
        end_date=query_date,
        page_size=1000,
        row_count=0,
    )

    canonical_path = save_canonical_parquet(
        [],
        tmp_path / "processed",
        snapshot_id=snapshot_id,
    )

    return query_date, raw_path, metadata_path, canonical_path


def test_build_keys_success(snapshot_files):
    query_date, raw, metadata, canonical = snapshot_files

    keys = build_snapshot_object_keys(
        raw_path=raw,
        metadata_path=metadata,
        canonical_path=canonical,
        trade_date=query_date,
    )

    assert set(keys) == {"raw", "metadata", "canonical"}
    assert "trade_date=2026-10-30" in keys["raw"]
    assert keys["raw"].endswith(raw.name)
    assert keys["metadata"].endswith(metadata.name)
    assert keys["canonical"].endswith(canonical.name)


def test_reject_missing_file(snapshot_files):
    query_date, raw, metadata, canonical = snapshot_files
    canonical.unlink()

    with pytest.raises(FileNotFoundError):
        build_snapshot_object_keys(
            raw_path=raw,
            metadata_path=metadata,
            canonical_path=canonical,
            trade_date=query_date,
        )


def test_reject_mismatched_snapshot_id(snapshot_files):
    query_date, raw, metadata, canonical = snapshot_files

    wrong_canonical = canonical.with_name("agri_prices_other.parquet")
    wrong_canonical.write_bytes(canonical.read_bytes())

    with pytest.raises(ValueError, match="Snapshot ID 不一致"):
        build_snapshot_object_keys(
            raw_path=raw,
            metadata_path=metadata,
            canonical_path=wrong_canonical,
            trade_date=query_date,
        )


def test_reject_wrong_metadata_reference(snapshot_files):
    query_date, raw, metadata, canonical = snapshot_files

    content = json.loads(metadata.read_text(encoding="utf-8"))
    content["raw_file"] = "wrong.json"
    metadata.write_text(
        json.dumps(content, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="raw_file"):
        build_snapshot_object_keys(
            raw_path=raw,
            metadata_path=metadata,
            canonical_path=canonical,
            trade_date=query_date,
        )

def test_reject_mismatched_trade_date(snapshot_files):
    _, raw, metadata, canonical = snapshot_files

    with pytest.raises(ValueError, match="交易日期"):
        build_snapshot_object_keys(
            raw_path=raw,
            metadata_path=metadata,
            canonical_path=canonical,
            trade_date=date(2026, 10, 29),
        )