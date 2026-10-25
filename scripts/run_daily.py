import argparse
from datetime import date
from pathlib import Path

import psycopg

from moa_agri_pipeline.pipeline import run_pipeline


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            "日期格式必須為 YYYY-MM-DD"
        ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="執行農產品交易行情每日 Pipeline"
    )

    parser.add_argument(
        "--date",
        required=True,
        type=parse_date,
        help="交易日期，格式：YYYY-MM-DD",
    )

    parser.add_argument(
        "--expected-database",
        help="執行 Pipeline 前核對實際連線的 PostgreSQL 資料庫；不符則拒絕執行",
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    project_root = Path(__file__).resolve().parents[1]

    with psycopg.connect(
        autocommit=True,
    ) as connection:
        # 排程測試的第二道防線：核對連線到的真實資料庫身分。
        # 必須在 run_pipeline() 呼叫 API 或寫入資料之前完成。
        if args.expected_database is not None:
            actual_database = connection.execute(
                "SELECT current_database()"
            ).fetchone()[0]

            if actual_database != args.expected_database:
                raise RuntimeError(
                    "資料庫安全檢查失敗："
                    f"預期 {args.expected_database!r}，"
                    f"實際 {actual_database!r}；Pipeline 未啟動"
                )

            print(f"Database verified: {actual_database}")

        result = run_pipeline(
            query_date=args.date,
            connection=connection,
            raw_output_dir=project_root / "data" / "raw",
            processed_output_dir=project_root / "data" / "processed",
        )

    print(f"查詢日期：{result.query_date}")
    print(f"Raw rows：{result.raw_row_count}")
    print(
        f"Transformed rows："
        f"{result.transformed_row_count}"
    )
    print(
        f"PostgreSQL rows："
        f"{result.postgres_row_count}"
    )
    print(f"Raw：{result.raw_path}")
    print(f"Metadata：{result.metadata_path}")
    print(f"Canonical：{result.canonical_path}")


if __name__ == "__main__":
    main()