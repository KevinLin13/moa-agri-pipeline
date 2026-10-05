import argparse
from datetime import date

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

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    with psycopg.connect(
        autocommit=True,
    ) as connection:
        result = run_pipeline(
            query_date=args.date,
            connection=connection,
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