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
Monitoring
Audit / Reconciliation
```

---
## 5. Validation Result

Canonical Parquet Load 與 Snapshot Diff 完成後執行：

```text
pytest tests/test_parquet_load.py -v
```

結果：

```text
3 passed
```

測試包含：

```text
Canonical records
→ write Parquet
→ read Parquet
→ round trip comparison
```

```text
Empty records
→ write Parquet
→ preserve canonical schema
```

以及：

```text
Canonical Parquet
→ load_canonical_parquet()
→ restore canonical records
```

Snapshot Diff 測試：

```text
pytest tests/test_snapshot_diff.py -v
```

結果：

```text
3 passed
```

測試包含：

```text
Inserted
Changed
Disappeared
Unchanged
```

四種 snapshot change type。

並驗證：

```text
Non-Rest Business Key
(trade_date, crop_code, market_code)

Rest Business Key
(trade_date, category_code, market_code)
```

以及 duplicate Business Key protection。

完整 test suite：

```text
pytest -v
```

結果：

```text
51 passed
```

代表新增：

```text
Canonical Parquet Read
Snapshot Diff
Snapshot Comparison
```

沒有破壞既有：

```text
Raw Validation
Transform
Profiling
Data Quality
Parquet Load
```

相關功能。

---

## 6. Real Data Validation

### 6.1 Canonical Parquet Persistence

使用真實農業部 API 查詢：

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

Raw、Metadata 與 Canonical Parquet 使用相同：

```text
snapshot_id = 20260831T075626
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

---

### 6.2 Snapshot Diff Integration Check

使用同一份真實 Canonical Parquet：

```text
agri_prices_20260831T075626.parquet
vs
agri_prices_20260831T075626.parquet
```

執行 Snapshot Diff。

結果：

```text
Earlier rows:    3480
Later rows:      3480

Inserted:        0
Changed:         0
Disappeared:     0
Unchanged:       3480
```

### Finding

目前已驗證完整路徑：

```text
Canonical Parquet
→ load_canonical_parquet()
→ Business Key indexing
→ diff_snapshots()
→ human-readable report
```

可以正確處理真實 canonical snapshot。

同一份 snapshot 與自己比較時：

```text
Inserted = 0
Changed = 0
Disappeared = 0
Unchanged = row_count
```

符合預期。

---

### 6.3 Current-Date Snapshot Capture

將 Pipeline 查詢日期改為執行當日後，於：

```text
2026-08-31 10:12
```

成功取得：

```text
trade_date = 2026-08-31
Rows = 26
```

並完成：

```text
Raw Validation: PASS
Data Quality:   PASS
Canonical Parquet: SAVED
```

實際產生：

```text
data/raw/agri_prices_20260831T101205.json
data/raw/agri_prices_20260831T101205_metadata.json
data/processed/agri_prices_20260831T101205.parquet
```

### Observation

這次執行證明：

```text
正在更新中的 current trade_date
```

也可以完成完整的：

```text
Extract
→ Validation
→ Transform
→ Data Quality
→ Canonical Parquet Snapshot
```

流程。

但單一 current-date snapshot 不能證明 API 的 intra-day update behavior。

因此目前不將：

```text
Inserted / Changed / Disappeared
```

任一來源更新模式視為已確認的永久規則。

---
## 7. Same-Day Snapshot Diff Design

Snapshot Diff 的目的為比較：

```text
Earlier Snapshot
vs
Later Snapshot
```

並將 record 分類為：

```text
Inserted
Changed
Disappeared
Unchanged
```

Candidate Business Key 沿用 Data Quality v1：

```text
Non-Rest
(trade_date, crop_code, market_code)

Rest
(trade_date, category_code, market_code)
```

實作時另外加入：

```text
rest / non_rest
```

類型標記，避免兩套 Business Key 在同一 index 中發生意義上的碰撞。

若相同 Business Key 的 non-key 欄位發生變化：

```text
Changed
```

並記錄 field-level differences。

例如：

```text
avg_price
20.0 → 25.0

volume
200.0 → 250.0
```

若 snapshot 內出現 duplicate Business Key：

```text
raise ValueError
```

而不是在建立 index 時靜默覆寫 record。

### Finding

Snapshot Diff 的功能完整性不需要等待真實 API 在某一天剛好出現所有 change type 才能驗證。

目前 unit tests 已人工覆蓋：

```text
Inserted
Changed
Disappeared
Unchanged
```

因此：

```text
API 某次實際只出現其中一部分狀況
```

不會限制程式對其他狀況的支援。

### Current Decision

Snapshot Diff 的角色定位為：

```text
Source Behavior Observation
Reconciliation
Monitoring
Audit / Investigation
```

工具。

Snapshot Diff **不是**正式 PostgreSQL Load 的必要前置步驟。

因此：

```text
Source intra-day behavior profiling
```

可以持續累積多個 snapshots 後再分析，而不阻塞主要 Load 開發。

單一日期或單一 snapshot pair 所觀察到的結果，不應被外推為 API 永久更新規則。

---

## 8. PostgreSQL Load Strategy

正式 PostgreSQL canonical table 的目標狀態定義為：

> 對每一個 `trade_date`，資料庫應反映最近一次完整取得、通過 Raw Validation、Transform 與 Data Quality 的 canonical snapshot。

因此目前不採用：

```text
逐列 Snapshot Diff
→ Inserted → INSERT
→ Changed → UPDATE
→ Disappeared → DELETE
```

作為主要 Load 機制。

目前採用的 v1 方向為：

```text
Latest Valid Canonical Snapshot
        ↓
Database Transaction
        ↓
Replace target trade_date
        ↓
Commit
```

概念流程：

```text
完整取得 API
↓
Raw Validation PASS
↓
Transform
↓
Data Quality PASS
↓
Canonical snapshot ready
↓
BEGIN TRANSACTION
↓
DELETE target trade_date
↓
INSERT latest canonical snapshot
↓
COMMIT
```

若 Database Load 中途失敗：

```text
ROLLBACK
```

原本資料應維持不變。

### Why Trade-Date Replacement

此方式自然處理：

```text
Inserted
Changed
Disappeared
Unchanged
```

而不需要逐列 reconciliation。

例如：

```text
Earlier:
A
B
C

Latest:
A
B'
D
```

replacement 後資料自然為：

```text
A
B'
D
```

因此：

```text
B → changed
C → disappeared
D → inserted
```

皆能反映最新 canonical snapshot。

### Finding

PostgreSQL Load 的正確性不需要依賴：

```text
先執行 Snapshot Diff
→ 再依 change type 決定逐列 SQL
```

只要新的 canonical snapshot 已經完整取得且通過所有 validation，正式 Load 可以直接以最新 snapshot 取代目標 `trade_date` 的既有資料。

這將：

```text
Source change observation
```

與：

```text
Database state synchronization
```

分離。

---

## 9. Idempotency Direction

目前 idempotency 定義為：

> 同一份 validated canonical snapshot 重跑，不應造成額外 duplicate 或不正確副作用；來源真的發生更新時，資料庫則必須反映新的來源狀態。

因此：

```text
idempotency
!=
第一次寫入後永遠不可修改
```

對同一：

```text
trade_date
```

重跑完全相同 snapshot：

```text
replace old trade_date data
→ insert same canonical state
```

最終資料庫狀態不變。

因此 trade-date replacement 可以提供：

```text
state-level idempotency
```

正式實作仍需透過 PostgreSQL transaction 測試：

```text
成功 → COMMIT
失敗 → ROLLBACK
```

### Current Decision

Load 階段優先確保：

```text
Latest Valid Source State
=
Current Database State for that trade_date
```

而不是優先追求逐列最小修改。

在目前每日資料量僅數千筆的情境下，trade-date replacement 的設計較簡單、容易驗證，也能自然處理來源 record 的新增、修改與消失。

---

## 10. Current Stage

目前 Load 階段進度：

```text
Canonical Parquet Snapshot Load
✅ COMPLETE

Canonical Parquet Read
✅ COMPLETE

Snapshot Diff Core
✅ COMPLETE

Snapshot Diff Integration Check
✅ COMPLETE

Source Intra-Day Behavior Observation
→ ONGOING / NON-BLOCKING

PostgreSQL Schema
✅ COMPLETE

PostgreSQL Trade-Date Replacement Load
→ NEXT

Transaction / Rollback Validation
→ PENDING

Idempotency Validation
→ PENDING
```

### PostgreSQL Schema Validation Result

已建立 PostgreSQL canonical table：

```text
agri_prices
```

目前 schema 對應既有 11 欄 canonical contract：

```text
trade_date      DATE              NOT NULL
category_code   TEXT              NULLABLE
crop_code       TEXT              NOT NULL
crop_name       TEXT              NULLABLE
market_code     TEXT              NOT NULL
market_name     TEXT              NOT NULL
upper_price     DOUBLE PRECISION  NOT NULL
middle_price    DOUBLE PRECISION  NOT NULL
lower_price     DOUBLE PRECISION  NOT NULL
avg_price       DOUBLE PRECISION  NOT NULL
volume          DOUBLE PRECISION  NOT NULL
```

Business Key constraint 以 PostgreSQL partial unique index 實作：

```text
Non-Rest
(trade_date, crop_code, market_code)
WHERE crop_code <> 'rest'
```

```text
Rest
(trade_date, category_code, market_code)
WHERE crop_code = 'rest'
```

另外加入：

```text
Rest category_code
→ category_code IS NOT NULL
```

以及五個數值欄位：

```text
value >= 0
```

的 database-level CHECK constraint。

實際 PostgreSQL constraint test 已驗證：

```text
Non-Rest duplicate
→ rejected

Rest duplicate
→ rejected

Rest category_code = NULL
→ rejected

Negative numeric value
→ rejected
```

測試使用 transaction 執行，最後：

```text
ROLLBACK
```

並再次確認測試日期：

```text
trade_date = 2099-01-01
```

在 `agri_prices` 中：

```text
COUNT(*) = 0
```

因此本次 schema constraint 測試未留下測試資料。

本階段開始前亦重新執行完整 Python test suite：

```text
python -m pytest -v
```

結果：

```text
51 passed
```

### Current Decision

PostgreSQL Schema v1 已能保存目前 11 欄 canonical records，並在 database layer 維持目前 Data Quality v1 / Business Key 的核心 constraint。

下一個主要工程問題改為：

> PostgreSQL Trade-Date Replacement Load 應如何實作，才能在單一 transaction 中刪除目標 `trade_date` 的既有資料、寫入最新 validated canonical snapshot，並為後續 rollback / idempotency validation 提供可測試的 load boundary？

Source intra-day behavior 可透過不同時間點保存的 Parquet snapshots 持續觀察，但不再作為 PostgreSQL Load 開發的 blocking prerequisite。

進入 PostgreSQL Trade-Date Replacement Load 前：

- 不改變既有 Data Quality v1 規則。
- 不刪除不同時點保存的 Raw / Canonical snapshots。
- 不把單一 snapshot pair 的結果外推為永久 API 更新規則。
- Snapshot Diff 繼續保留為 observation / monitoring / audit 工具。
