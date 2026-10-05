from datetime import date
from types import SimpleNamespace

import argparse
import pytest

import importlib.util
from pathlib import Path

RUN_DAILY_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_daily.py"
)

spec = importlib.util.spec_from_file_location(
    "run_daily",
    RUN_DAILY_PATH,
)

assert spec is not None
assert spec.loader is not None

run_daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_daily)

def test_parse_date_accepts_iso_date():
    result = run_daily.parse_date("2026-10-04")

    assert result == date(2026, 10, 4)


def test_parse_date_rejects_invalid_date():
    with pytest.raises(
        argparse.ArgumentTypeError,
        match="日期格式必須為 YYYY-MM-DD",
    ):
        run_daily.parse_date("2026/10/04")


def test_parse_args_parses_required_date(monkeypatch):
    # monkeypatch = pytest準備好的MonkeyPatch物件
    # 模擬使用者於命令中輸入「python run_daily.py --date 2026-10-04」
    monkeypatch.setattr( # setattr：set attribute 設定屬性
        "sys.argv",
        [
            "run_daily.py",
            "--date",
            "2026-10-04",
        ],
    )

    args = run_daily.parse_args()

    assert args.date == date(2026, 10, 4)


def test_main_connects_and_runs_pipeline(monkeypatch, capsys):
    # capsys：pytest 用來捕捉程式輸出到終端機內容的 fixture
    query_date = date(2026, 10, 4)
    connection = object()
    # 建立假的資料庫 connection
    # 後續可驗證 main() 傳給 run_pipeline() 的 connection
    # 是否為前面 connect 所產生的同一個物件。

    class FakeConnectionContext: # 建立假的 context manager
        def __enter__(self):
            return connection

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return False

    def fake_connect(*, autocommit):
        assert autocommit is True
        return FakeConnectionContext()

    def fake_run_pipeline(*, query_date, connection):
        assert query_date == date(2026, 10, 4)
        assert connection is globals_connection

        return SimpleNamespace(
            query_date=query_date,
            raw_row_count=10,
            transformed_row_count=10,
            postgres_row_count=10,
            raw_path="data/raw/raw.json",
            metadata_path="data/raw/metadata.json",
            canonical_path="data/processed/data.parquet",
        )

    globals_connection = connection

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_daily.py",
            "--date",
            "2026-10-04",
        ],
    )
    monkeypatch.setattr(
        run_daily.psycopg,
        "connect",
        fake_connect,
    )
    monkeypatch.setattr(
        run_daily,
        "run_pipeline",
        fake_run_pipeline,
    )

    run_daily.main()

    output = capsys.readouterr().out

    assert "查詢日期：2026-10-04" in output
    assert "Raw rows：10" in output
    assert "Transformed rows：10" in output
    assert "PostgreSQL rows：10" in output

def test_parse_args_exits_with_code_2_when_date_is_missing(
    monkeypatch,
):
    monkeypatch.setattr(
        "sys.argv",
        ["run_daily.py"],
    )

    with pytest.raises(SystemExit) as exc_info:
        run_daily.parse_args()

    assert exc_info.value.code == 2


def test_main_propagates_connection_error(monkeypatch):
    def fake_connect(*, autocommit):
        assert autocommit is True
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        "sys.argv",
        [
            "run_daily.py",
            "--date",
            "2026-10-05",
        ],
    )

    monkeypatch.setattr(
        run_daily.psycopg,
        "connect",
        fake_connect,
    )

    with pytest.raises(
        RuntimeError,
        match="database unavailable",
    ):
        run_daily.main()