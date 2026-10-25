"""排程資料庫身分檢查的單元測試；不連線 PostgreSQL、也不呼叫 API。"""
import importlib.util
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

RUN_DAILY_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_daily.py"
spec = importlib.util.spec_from_file_location("run_daily_db_guard", RUN_DAILY_PATH)
assert spec is not None and spec.loader is not None
run_daily = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_daily)


class FakeConnection:
    def __init__(self, actual_database: str):
        self.actual_database = actual_database
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql):
        self.queries.append(sql)
        assert sql == "SELECT current_database()"
        return SimpleNamespace(fetchone=lambda: (self.actual_database,))


def set_up_runtime(monkeypatch, actual_database):
    connection = FakeConnection(actual_database)
    monkeypatch.setattr(
        "sys.argv",
        ["run_daily.py", "--date", "2026-10-05",
         "--expected-database", "moa_agri_sched_test"],
    )

    def fake_connect(*, autocommit):
        assert autocommit is True
        return connection

    monkeypatch.setattr(run_daily.psycopg, "connect", fake_connect)
    return connection


def test_rejects_wrong_database_before_pipeline(monkeypatch):
    connection = set_up_runtime(monkeypatch, "moa_agri")

    def forbidden_pipeline(**kwargs):
        pytest.fail("Safety check failed: run_pipeline must not be called")

    monkeypatch.setattr(run_daily, "run_pipeline", forbidden_pipeline)

    with pytest.raises(RuntimeError, match="資料庫安全檢查失敗"):
        run_daily.main()

    assert connection.queries == ["SELECT current_database()"]


def test_allows_expected_database(monkeypatch, capsys):
    connection = set_up_runtime(monkeypatch, "moa_agri_sched_test")
    calls = []

    def fake_run_pipeline(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            query_date=date(2026, 10, 5),
            raw_row_count=10,
            transformed_row_count=10,
            postgres_row_count=10,
            raw_path="raw.json",
            metadata_path="metadata.json",
            canonical_path="canonical.parquet",
        )

    monkeypatch.setattr(run_daily, "run_pipeline", fake_run_pipeline)
    run_daily.main()

    assert connection.queries == ["SELECT current_database()"]
    assert len(calls) == 1
    assert calls[0]["connection"] is connection
    assert calls[0]["query_date"] == date(2026, 10, 5)
    assert "Database verified: moa_agri_sched_test" in capsys.readouterr().out
