from datetime import date

import pytest

from moa_agri_pipeline.load.snapshot_diff import (
    build_snapshot_index,
    diff_snapshots,
)

def make_record(
    crop_code: str,
    *,
    avg_price: float,
    volume: float,
) -> dict:
    return {
        "trade_date": date(2026, 8, 31),
        "category_code": "N05",
        "crop_code": crop_code,
        "crop_name": crop_code,
        "market_code": "104",
        "market_name": "台北二",
        "upper_price": avg_price,
        "middle_price": avg_price,
        "lower_price": avg_price,
        "avg_price": avg_price,
        "volume": volume,
    }


def test_diff_snapshots_detects_all_change_types():
    earlier_records = [
        # A：完全不變
        make_record(
            "A",
            avg_price=10.0,
            volume=100.0,
        ),
        # B：Later 會修改
        make_record(
            "B",
            avg_price=20.0,
            volume=200.0,
        ),
        # C：Later 會消失
        make_record(
            "C",
            avg_price=30.0,
            volume=300.0,
        ),
    ]

    later_records = [
        # A：Unchanged
        make_record(
            "A",
            avg_price=10.0,
            volume=100.0,
        ),
        # B：Changed
        make_record(
            "B",
            avg_price=25.0,
            volume=250.0,
        ),
        # D：Inserted
        make_record(
            "D",
            avg_price=40.0,
            volume=400.0,
        ),
    ]

    result = diff_snapshots(
        earlier_records,
        later_records,
    )

    assert result["earlier_row_count"] == 3
    assert result["later_row_count"] == 3

    assert result["inserted_count"] == 1
    assert result["changed_count"] == 1
    assert result["disappeared_count"] == 1
    assert result["unchanged_count"] == 1

    changed = result["changed"][0]

    assert changed["changed_fields"] == {
        "upper_price": {
            "earlier": 20.0,
            "later": 25.0,
        },
        "middle_price": {
            "earlier": 20.0,
            "later": 25.0,
        },
        "lower_price": {
            "earlier": 20.0,
            "later": 25.0,
        },
        "avg_price": {
            "earlier": 20.0,
            "later": 25.0,
        },
        "volume": {
            "earlier": 200.0,
            "later": 250.0,
        },
    }


def test_build_snapshot_index_rejects_duplicate_business_key():
    records = [
        make_record(
            "A",
            avg_price=10.0,
            volume=100.0,
        ),
        make_record(
            "A",
            avg_price=20.0,
            volume=200.0,
        ),
    ]

    with pytest.raises(
        ValueError,
        match="Snapshot 內 Business Key 重複",
    ):
        build_snapshot_index(records)

def make_rest_record(
    category_code: str,
) -> dict:
    return {
        "trade_date": date(2026, 8, 31),
        "category_code": category_code,
        "crop_code": "rest",
        "crop_name": "休市",
        "market_code": "104",
        "market_name": "台北二",
        "upper_price": 0.0,
        "middle_price": 0.0,
        "lower_price": 0.0,
        "avg_price": 0.0,
        "volume": 0.0,
    }


def test_build_snapshot_index_uses_rest_business_key():
    records = [
        make_rest_record("N04"),
        make_rest_record("N05"),
    ]

    result = build_snapshot_index(records)

    assert len(result) == 2

    assert (
        "rest",
        date(2026, 8, 31),
        "N04",
        "104",
    ) in result

    assert (
        "rest",
        date(2026, 8, 31),
        "N05",
        "104",
    ) in result