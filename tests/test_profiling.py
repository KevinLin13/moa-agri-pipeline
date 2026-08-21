from datetime import date

import pytest

from moa_agri_pipeline.profiling.records import (
    find_duplicate_record_groups,
    profile_composite_relationship,
    profile_duplicate_keys,
    profile_field_relationship,
    profile_numeric_fields,
)


def test_profile_field_relationship_detects_null_pattern_and_conflict():
    records = [
        {
            "market_code": "400",
            "market_name": "台中市場",
        },
        {
            "market_code": "400",
            "market_name": "台中市",
        },
        {
            "market_code": "800",
            "market_name": None,
        },
    ]

    result = profile_field_relationship(
        records,
        "market_code",
        "market_name",
    )

    assert result["null_patterns"][(False, False)] == 2
    assert result["null_patterns"][(False, True)] == 1

    assert result["left_with_multiple_right"] == {
        "400": ["台中市", "台中市場"],
    }


def test_profile_composite_relationship_detects_conflict():
    records = [
        {
            "category_code": "N06",
            "market_code": "400",
            "market_name": "台中市場",
        },
        {
            "category_code": "N06",
            "market_code": "400",
            "market_name": "台中市",
        },
        {
            "category_code": "N05",
            "market_code": "400",
            "market_name": "台中市",
        },
    ]

    result = profile_composite_relationship(
        records,
        (
            "category_code",
            "market_code",
        ),
        "market_name",
    )

    assert result["left_key_count"] == 2
    assert result["conflict_count"] == 1
    assert result["conflicts"] == {
        ("N06", "400"): [
            "台中市",
            "台中市場",
        ],
    }


def test_profile_duplicate_keys_detects_duplicate_group():
    records = [
        {
            "trade_date": date(2026, 8, 1),
            "crop_code": "11",
            "market_code": "104",
        },
        {
            "trade_date": date(2026, 8, 1),
            "crop_code": "11",
            "market_code": "104",
        },
        {
            "trade_date": date(2026, 8, 1),
            "crop_code": "12",
            "market_code": "104",
        },
    ]

    result = profile_duplicate_keys(
        records,
        (
            "trade_date",
            "crop_code",
            "market_code",
        ),
    )

    assert result["row_count"] == 3
    assert result["unique_key_count"] == 2
    assert result["duplicate_group_count"] == 1
    assert result["duplicate_row_count"] == 2
    assert result["excess_duplicate_row_count"] == 1


def test_find_duplicate_record_groups_returns_duplicate_records():
    records = [
        {
            "trade_date": date(2026, 8, 1),
            "crop_code": "11",
            "market_code": "104",
            "avg_price": 20.0,
        },
        {
            "trade_date": date(2026, 8, 1),
            "crop_code": "11",
            "market_code": "104",
            "avg_price": 21.0,
        },
        {
            "trade_date": date(2026, 8, 1),
            "crop_code": "12",
            "market_code": "104",
            "avg_price": 30.0,
        },
    ]

    result = find_duplicate_record_groups(
        records,
        (
            "trade_date",
            "crop_code",
            "market_code",
        ),
    )

    key = (
        date(2026, 8, 1),
        "11",
        "104",
    )

    assert len(result) == 1
    assert len(result[key]) == 2
    assert result[key][0]["avg_price"] == 20.0
    assert result[key][1]["avg_price"] == 21.0


def test_profile_numeric_fields_calculates_distribution():
    records = [
        {"avg_price": 0.0},
        {"avg_price": 10.0},
        {"avg_price": 20.0},
        {"avg_price": 30.0},
    ]

    result = profile_numeric_fields(
        records,
        ("avg_price",),
    )

    profile = result["fields"]["avg_price"]

    assert result["row_count"] == 4

    assert profile["finite_count"] == 4
    assert profile["non_numeric_count"] == 0
    assert profile["non_finite_count"] == 0

    assert profile["zero_count"] == 1
    assert profile["zero_rate"] == pytest.approx(0.25)

    assert profile["mean"] == pytest.approx(15.0)
    assert profile["min"] == 0.0
    assert profile["q1"] == pytest.approx(7.5)
    assert profile["median"] == 15.0
    assert profile["q3"] == pytest.approx(22.5)
    assert profile["max"] == 30.0


def test_profile_numeric_fields_separates_invalid_numeric_values():
    records = [
        {"avg_price": 10.0},
        {"avg_price": float("inf")},
        {"avg_price": "20.0"},
    ]

    result = profile_numeric_fields(
        records,
        ("avg_price",),
    )

    profile = result["fields"]["avg_price"]

    assert profile["finite_count"] == 1
    assert profile["non_numeric_count"] == 1
    assert profile["non_finite_count"] == 1