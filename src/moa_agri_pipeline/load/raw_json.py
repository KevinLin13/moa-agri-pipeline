import json
from datetime import datetime
from pathlib import Path
from typing import Any


def save_raw_json(
    records: list[dict[str, Any]],
    output_dir: Path,
) -> Path:
    """將 API 原始資料保存為 UTF-8 JSON 檔案。"""

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    extracted_at = datetime.now().strftime("%Y%m%dT%H%M%S")

    output_path = (
        output_dir
        / f"agri_prices_{extracted_at}.json"
    )

    with output_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )

    return output_path