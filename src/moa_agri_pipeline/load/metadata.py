import json
from datetime import date, datetime
from pathlib import Path


def save_extract_metadata(
    raw_data_path: Path,
    start_date: date | None,
    end_date: date | None,
    page_size: int,
    row_count: int,
) -> Path:
    """保存本次 API 擷取作業的 Metadata。"""

    # 1. 整理資訊
    metadata = {
        "dataset": "EIR030",
        "source": "MOA Open Data",
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
        "page_size": page_size,
        "row_count": row_count,
        "raw_file": raw_data_path.name,
        "metadata_created_at": datetime.now().isoformat(timespec="seconds"),
    }

    # 2. 決定檔案位置
    metadata_path = raw_data_path.with_name(
        f"{raw_data_path.stem}_metadata.json"
    )
    # 3. 寫入 JSON

    with metadata_path.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            metadata,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # 4. 告訴外部檔案存在哪
    return metadata_path