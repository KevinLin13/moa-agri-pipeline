# Load Design

## 1. Purpose

本文件記錄 `moa-agri-pipeline` 在 Load 階段的設計決策、實作驗證結果與尚待確認的工程問題。

本文件的範圍包括：

- Canonical data 的持久化格式。
- Snapshot 命名與 lineage。
- Load schema。
- Load validation。
- Same-Day Snapshot Diff。
- 後續 PostgreSQL Load Strategy。
- Idempotency / Upsert / Reconciliation 等 Load 層設計。

本文件不取代：

```text
docs/data_profiling_findings.md
```

`data_profiling_findings.md` 仍負責記錄：

```text
Profiling Observation
→ Investigation
→ Finding
→ Schema / Business Key / Data Quality Decision
```

而本文件從 Data Quality v1 完成後開始，專注記錄：

```text
Validated Canonical Data
→ Persistence
→ Snapshot
→ Database Load
→ Idempotency
```

---

## 2. Current Load Context

目前 Pipeline 已完成：

```text
Extract
→ Save Raw JSON
→ Raw Validation
→ Transform
→ Data Quality v1
```

Data Quality v1 通過後，Pipeline 需要將 transformed canonical records 持久化，作為後續分析與資料庫 Load 的穩定資料層。

目前 canonical record 共 11 個欄位：

```text
trade_date
category_code
crop_code
crop_name
market_code
market_name
upper_price
middle_price
lower_price
avg_price
volume
```

目前欄位契約為：

```text
trade_date
→ datetime.date

category_code
→ str | None

crop_code
→ str

crop_name
→ str | None

market_code
→ str

market_name
→ str

upper_price
middle_price
lower_price
avg_price
volume
→ float
```

其中：

```text
category_code
crop_name
```

允許 `None`。

其餘必要識別欄位與數值欄位已由 Data Quality v1 驗證。

---

## 3. Canonical Parquet Snapshot Load

### 3.1 Why Parquet

Canonical persistence v1 採用：

```text
Parquet
```

而不是 CSV 或 JSON。

主要原因：

- 能保留日期、字串、NULL 與數值型別。
- 適合作為 analytical / canonical data format。
- 相較 CSV，不需要在讀回時重新猜測資料型別。
- 相較 JSON，更適合作為結構化分析資料的持久化格式。
- 可以在進入 PostgreSQL 前，先獨立驗證 canonical serialization / deserialization 是否正確。

目前 Pipeline 仍以：

```text
list[dict]
```

作為主要資料表示方式，因此 Parquet Load 直接使用：

```text
list[dict]
→ PyArrow Table
→ Parquet
```

暫不為了 Parquet persistence 額外引入 pandas DataFrame 作為 Pipeline 中介格式。

---

### 3.2 Explicit Canonical Schema

Parquet Load 不完全依賴 PyArrow 自動推論 schema，而是明確定義 canonical schema。

目前 schema：

```text
trade_date      date32        NOT NULL
category_code   string        NULLABLE
crop_code       string        NOT NULL
crop_name       string        NULLABLE
market_code     string        NOT NULL
market_name     string        NOT NULL
upper_price     float64       NOT NULL
middle_price    float64       NOT NULL
lower_price     float64       NOT NULL
avg_price       float64       NOT NULL
volume          float64       NOT NULL
```

### Current Decision

Canonical Parquet schema 應與 Data Quality v1 的資料契約一致。

因此：

- `trade_date` 以日期 logical type 保存，不轉回一般字串。
- `category_code` / `crop_name` 保留來源 `NULL`。
- 五個數值欄位以 `float64` 保存。
- 不因 Load 階段自行改寫、補值或刪除資料。

---

## 4. Snapshot Design and Lineage

### 4.1 Snapshot ID

Raw JSON 目前在 Extract 時使用 timestamp 產生 snapshot ID，例如：

```text
20260831T075626
```

Canonical Parquet 不另外產生新的 timestamp，而是沿用同一次 Raw Extract 的 snapshot ID。

因此同一次 Pipeline run 可以形成：

```text
data/raw/
agri_prices_20260831T075626.json

data/raw/
agri_prices_20260831T075626_metadata.json

data/processed/
agri_prices_20260831T075626.parquet
```

### Finding

Raw、Metadata 與 Canonical Parquet 可以透過相同：

```text
snapshot_id = 20260831T075626
```

建立直接 lineage。

這比 Raw 與 Parquet 分別各自取得系統時間更適合，因為：

```text
同一次 Extract
→ 應對應同一個 Snapshot Identity
```

而不是：

```text
Raw timestamp
!=
Canonical timestamp
```

即使兩者只相差數秒，也會降低 lineage 的清楚程度。

---

### 4.2 Same Trade Date Can Have Multiple Snapshots

目前已知農業部 API 同一天會有多次更新，因此：

```text
trade_date
```

不能直接等同於：

```text
snapshot identity
```

同一個交易日期可能在不同時段被多次擷取，例如：

```text
trade_date = 2026-08-31

09:00 snapshot
12:00 snapshot
22:00 snapshot
```

因此 Canonical Parquet v1 採用：

```text
每次 Extract
→ 保存獨立 snapshot
```

而不是：

```text
同一 trade_date
→ 永遠覆寫同一個 Parquet 檔案
```

### Current Decision

Parquet snapshot 應保留不同 Extract 時點的狀態，以支援後續：

```text
Snapshot Diff
Source Update Investigation
Load Reconciliation
```

---

## 5. Validation Result

Canonical Parquet Load 完成後執行：

```text
pytest tests/test_parquet_load.py -v
```

結果：

```text
2 passed
```

測試包含：

```text
Canonical records
→ write Parquet
→ read Parquet
→ round trip comparison
```

以及：

```text
Empty records
→ write Parquet
→ preserve canonical schema
```

完整 test suite：

```text
pytest -v
```

結果：

```text
47 passed
```

代表新增 Parquet Load 沒有破壞既有：

```text
Raw Validation
Transform
Profiling
Data Quality
```

相關測試。

---

## 6. Real API Validation

使用真實農業部 API 執行：

```text
python scripts/check_api.py
```

本次查詢：

```text
trade_date = 2026-08-05
```

結果：

```text
Raw Validation: PASS
Data Quality:   PASS
Rows:           3,480
```

實際產生：

```text
data/raw/agri_prices_20260831T075626.json
data/raw/agri_prices_20260831T075626_metadata.json
data/processed/agri_prices_20260831T075626.parquet
```

三個 output 使用相同 snapshot ID：

```text
20260831T075626
```

### Finding

目前已驗證：

1. 通過 Data Quality v1 的 transformed canonical records 可以成功保存為 Parquet。
2. Parquet 可以重新讀回並維持 canonical schema 與資料內容。
3. `trade_date` 可以維持日期型別。
4. nullable 欄位可以維持 `NULL / None`。
5. 數值欄位可以維持 `float64`。
6. 空資料仍可建立具有 canonical schema 的 Parquet。
7. Raw、Metadata 與 Canonical Parquet 可以共用同一 snapshot ID。
8. 真實 API 3,480 筆資料已成功完成 Canonical Parquet Load。

### Current Decision

```text
Canonical Parquet Load v1
→ COMPLETE
```

---

## 7. Current Limitation

本次真實 Pipeline 的執行時間為：

```text
2026-08-31
```

但實際查詢的交易日期為：

```text
2026-08-05
```

因此本次驗證只能證明：

```text
Canonical Parquet Persistence
+
Snapshot Lineage
```

正常。

目前尚不能由這次結果判斷同一交易日期在 API 不同更新時段之間是否會發生：

```text
新增 Business Key
修改既有 Business Key 的欄位
移除先前存在的 Business Key
```

因此目前不能宣告：

```text
API intra-day update behavior
→ 已確認
```

---

## 8. Pending Validation — Same-Day Snapshot Diff

下一個 Load 工程問題為：

> 同一個仍在更新中的 `trade_date`，在不同 API 更新時段之間，資料實際會如何變化？

預計比較：

```text
Earlier Snapshot
vs
Later Snapshot
```

並針對 Candidate Business Key 判斷：

```text
Inserted Keys
→ 後一版新增的 Business Key

Changed Keys
→ 相同 Business Key，但其他欄位內容改變

Disappeared Keys
→ 前一版存在，但後一版不存在
```

目前 Candidate Business Key：

```text
Non-Rest
(trade_date, crop_code, market_code)

Rest
(trade_date, category_code, market_code)
```

### Why This Matters

這項 finding 會直接影響 PostgreSQL Load Strategy。

可能情況：

```text
只新增
→ INSERT / UPSERT 即可
```

```text
新增 + 修改
→ UPSERT
```

```text
新增 + 修改 + 消失
→ 單純 UPSERT 可能不足
→ 需要 reconciliation / partition replacement / other strategy
```

因此在 Same-Day Snapshot Diff 完成以前，不先凍結 PostgreSQL Load Strategy。

---

## 9. Idempotency Direction

目前對 idempotency 的定義為：

> 同一份來源狀態重跑多次，不應因重跑產生額外錯誤副作用；但當來源資料真的更新時，目標資料必須能正確反映新的來源狀態。

因此：

```text
idempotency
!=
同一天第一次寫入後永遠不能修改
```

較合理的未來行為可能是：

```text
New Business Key
→ INSERT

Existing Business Key + changed values
→ UPDATE

Existing Business Key + same values
→ no duplicate / no unintended side effect
```

但這仍需等 Same-Day Snapshot Diff 確認來源更新模式後，再正式決定 PostgreSQL 實作方式。

---

## 10. Next Stage

目前 Load 階段進度：

```text
Canonical Parquet Snapshot Load
✅ COMPLETE

Same-Day Snapshot Diff
→ NEXT

PostgreSQL Schema
→ PENDING

PostgreSQL Load
→ PENDING

Upsert / Reconciliation
→ PENDING

Idempotency Validation
→ PENDING
```

下一個最小充分任務：

> 使用同一個正在更新中的 `trade_date`，保存至少兩個不同時間點的 snapshot，並比較 Inserted / Changed / Disappeared Business Keys。

在完成上述驗證前：

- 不先決定 PostgreSQL 是純 INSERT、UPSERT 或 partition replacement。
- 不把來源更新行為寫成已確認 finding。
- 不改變既有 Data Quality v1 規則。
- 不刪除或覆寫不同時點的 Raw / Canonical snapshots。
