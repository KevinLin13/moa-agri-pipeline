"""R2 Snapshot PoC: manual, synthetic files only; never runs the ETL."""

import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from moa_agri_pipeline.load.parquet import (
    load_canonical_parquet,
    save_canonical_parquet,
)
from moa_agri_pipeline.load.raw_json import save_raw_json


EXPECTED_BUCKET = "moa-agri-pipeline-snapshots"
TEST_DATE = date(2099, 1, 3)


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing GitHub Actions setting: {name}")
    return value


def create_test_snapshot(root: Path):
    """Use existing Raw/Parquet writers; mark metadata as synthetic."""
    raw_record = {
        "交易日期": "188.01.03",  # 2099-01-03, deliberately synthetic
        "種類代碼": "N05",
        "作物代號": "POC-ONLY",
        "作物名稱": "Synthetic Test Crop",
        "市場代號": "POC-ONLY",
        "市場名稱": "Synthetic Test Market",
        "上價": 12.0,
        "中價": 10.0,
        "下價": 8.0,
        "平均價": 10.0,
        "交易量": 5.0,
    }
    canonical_record = {
        "trade_date": TEST_DATE,
        "category_code": "N05",
        "crop_code": "POC-ONLY",
        "crop_name": "Synthetic Test Crop",
        "market_code": "POC-ONLY",
        "market_name": "Synthetic Test Market",
        "upper_price": 12.0,
        "middle_price": 10.0,
        "lower_price": 8.0,
        "avg_price": 10.0,
        "volume": 5.0,
    }

    raw_path = save_raw_json([raw_record], root / "raw")
    snapshot_id = raw_path.stem.removeprefix("agri_prices_")

    # Intentionally NOT calling save_extract_metadata: it labels the data
    # as real "MOA Open Data", which would misrepresent this test fixture.
    metadata_path = raw_path.with_name(f"{raw_path.stem}_metadata.json")
    metadata = {
        "test_only": True,
        "source": "SYNTHETIC_R2_POC_NO_MOA_API_CALL",
        "dataset": "EIR030_POC",
        "snapshot_id": snapshot_id,
        "raw_file": raw_path.name,
        "start_date": TEST_DATE.isoformat(),
        "end_date": TEST_DATE.isoformat(),
        "row_count": 1,
    }
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    canonical_path = save_canonical_parquet(
        [canonical_record], root / "processed", snapshot_id=snapshot_id
    )

    assert canonical_path.stem == raw_path.stem
    return snapshot_id, metadata, canonical_record, [
        (raw_path, f"raw/{raw_path.name}"),
        (metadata_path, f"raw/{metadata_path.name}"),
        (canonical_path, f"processed/{canonical_path.name}"),
    ]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("This PoC may only run inside GitHub Actions")

    account_id = required_env("R2_ACCOUNT_ID")
    bucket = required_env("R2_BUCKET_NAME")
    access_key = required_env("R2_ACCESS_KEY_ID")
    secret_key = required_env("R2_SECRET_ACCESS_KEY")
    run_id = required_env("GITHUB_RUN_ID")
    attempt = required_env("GITHUB_RUN_ATTEMPT")

    if bucket != EXPECTED_BUCKET:
        raise RuntimeError("Bucket does not match the isolated PoC bucket")
    if not re.fullmatch(r"[0-9a-fA-F]{32}", account_id):
        raise RuntimeError("R2_ACCOUNT_ID is not a valid 32-character account ID")
    if not run_id.isdecimal() or not attempt.isdecimal():
        raise RuntimeError("GitHub Actions run identifier is invalid")

    client = boto3.client(
        "s3",
        endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
        region_name="auto",
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            signature_version="s3v4",
            retries={"mode": "standard", "max_attempts": 3},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )
    prefix = f"poc/r2-snapshot-roundtrip/{run_id}/attempt-{attempt}"

    with TemporaryDirectory(prefix="r2_snapshot_poc_") as directory:
        root = Path(directory)
        snapshot_id, metadata, canonical_record, files = create_test_snapshot(root)
        downloaded_root = root / "downloaded"
        uploaded_keys = []

        for source_path, relative_key in files:
            object_key = f"{prefix}/{relative_key}"
            print(f"Upload/download: {relative_key}")
            # Small PoC objects: avoid multipart and any DELETE operations.
            original_bytes = source_path.read_bytes()
            client.put_object(Bucket=bucket, Key=object_key, Body=original_bytes)
            response = client.get_object(Bucket=bucket, Key=object_key)
            downloaded_bytes = response["Body"].read()
            if sha256_bytes(downloaded_bytes) != sha256_bytes(original_bytes):
                raise RuntimeError(f"SHA-256 mismatch: {relative_key}")

            destination = downloaded_root / relative_key
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(downloaded_bytes)
            uploaded_keys.append(object_key)
            print(f"PASS: exact bytes recovered: {relative_key}")

        downloaded_metadata = json.loads(
            (downloaded_root / "raw" / f"agri_prices_{snapshot_id}_metadata.json").read_text(
                encoding="utf-8"
            )
        )
        if downloaded_metadata != metadata or not downloaded_metadata["test_only"]:
            raise RuntimeError("Synthetic metadata content mismatch")
        if downloaded_metadata["raw_file"] != f"agri_prices_{snapshot_id}.json":
            raise RuntimeError("Metadata/Raw snapshot relationship mismatch")
        downloaded_parquet = downloaded_root / "processed" / f"agri_prices_{snapshot_id}.parquet"
        if load_canonical_parquet(downloaded_parquet) != [canonical_record]:
            raise RuntimeError("Downloaded Parquet schema/content mismatch")

        print(f"PASS: {len(uploaded_keys)} synthetic snapshot objects round-tripped")
        print(f"PASS: same snapshot ID and metadata lineage: {snapshot_id}")
        print(f"R2 test-only prefix: {prefix}/")
        print("NOTE: test objects intentionally remain in R2 for independent inspection")


if __name__ == "__main__":
    try:
        main()
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "Unknown")
        sys.exit(f"FAIL: R2 S3 API error ({code}); credentials are not displayed")
    except Exception as exc:
        sys.exit(f"FAIL: R2 snapshot PoC ({type(exc).__name__}); no credentials displayed")
