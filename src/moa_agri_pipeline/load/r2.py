import json
import re
from datetime import date
from pathlib import Path


def build_snapshot_object_keys(
    *,
    raw_path: Path,
    metadata_path: Path,
    canonical_path: Path,
    trade_date: date,
) -> dict[str, str]:
    """驗證 Snapshot 檔案，產生三個 R2 Object Keys。"""

    # 1. 確認三份檔案存在
    for path in (raw_path, metadata_path, canonical_path):
        if not path.is_file():
            raise FileNotFoundError(f"Snapshot 檔案不存在：{path}")

    # 2. 從 Raw JSON 檔名取得 Snapshot ID
    if not (
        raw_path.name.startswith("agri_prices_")
        and raw_path.suffix == ".json"
    ):
        raise ValueError("Raw JSON 檔名格式不正確")

    snapshot_id = raw_path.stem.removeprefix("agri_prices_")

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", snapshot_id):
        raise ValueError("Snapshot ID 格式不正確")

    # 3. 確認三份檔案的命名關係
    expected_metadata = f"agri_prices_{snapshot_id}_metadata.json"
    expected_canonical = f"agri_prices_{snapshot_id}.parquet"

    if metadata_path.name != expected_metadata:
        raise ValueError("Metadata 與 Raw Snapshot ID 不一致")

    if canonical_path.name != expected_canonical:
        raise ValueError("Parquet 與 Raw Snapshot ID 不一致")

    # 4. 確認 Metadata 指向正確的 Raw JSON
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    if not isinstance(metadata, dict):
        raise ValueError("Metadata JSON 必須是物件")

    if metadata.get("raw_file") != raw_path.name:
        raise ValueError("Metadata 的 raw_file 與 Raw JSON 不一致")

    if (
        "snapshot_id" in metadata
        and metadata["snapshot_id"] != snapshot_id
    ):
        raise ValueError("Metadata 的 snapshot_id 不一致")

    # 確認 Metadata 日期與 R2 交易日期一致
    expected_date = trade_date.isoformat()

    if (
        metadata.get("start_date") != expected_date
        or metadata.get("end_date") != expected_date
    ):
        raise ValueError(
            "Metadata 交易日期與 trade_date 不一致"
        )

    # 5. 產生 R2 Object Keys
    prefix = (
        f"snapshots/EIR030/"
        f"trade_date={trade_date.isoformat()}/"
        f"snapshot_id={snapshot_id}"
    )

    return {
        "raw": f"{prefix}/raw/{raw_path.name}",
        "metadata": f"{prefix}/raw/{metadata_path.name}",
        "canonical": f"{prefix}/processed/{canonical_path.name}",
    }
