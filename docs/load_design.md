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
✅ COMPLETE

Transaction / Rollback Validation
✅ COMPLETE

Idempotency Validation
✅ COMPLETE

PostgreSQL Pipeline Integration
✅ COMPLETE

Pipeline Orchestration
✅ COMPLETE

Runtime Configuration / Runtime Entry Point
→ NEXT
```

### PostgreSQL Schema Validation Result

已建立 PostgreSQL canonical table：

```text
agri_prices
```

目前 schema 對應既有 11 欄 canonical contract：

```texttrade_date      DATE              NOT NULL
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

### PostgreSQL Trade-Date Replacement Load Validation Result

已新增 PostgreSQL canonical load boundary：

```text
src/moa_agri_pipeline/load/postgres.py
```

核心行為為：

```text
replace_trade_date_records(
    connection,
    trade_date,
    records,
)
```

執行流程：

```text
Validate all record trade_date
↓
BEGIN TRANSACTION
↓
DELETE target trade_date
↓
INSERT latest canonical records
↓
COMMIT
```

若傳入 record 的 `trade_date` 與 target `trade_date` 不一致：

```text
raise ValueError
```

而且 validation 發生在 database transaction 開始前，因此不會先刪除既有資料。

若 validated canonical snapshot 為空：

```text
records = []
```

仍允許執行：

```text
DELETE target trade_date
→ INSERT 0 rows
→ COMMIT
```

使 database state 能反映最新完整 snapshot 為空的情況。

Unit tests：

```text
pytest tests/test_postgres_load.py -v
```

結果：

```text
3 passed
```

測試涵蓋：

```text
Mixed trade_date
→ rejected before transaction

Non-empty snapshot
→ DELETE + INSERT

Empty snapshot
→ DELETE + INSERT 0 rows
```

另外新增真實 PostgreSQL integration tests：

```text
tests/integration/test_postgres_load_integration.py
```

使用：

```text
localhost:5432
database = moa_agri
table = public.agri_prices
```

驗證正常 replacement：

```text
Old record
↓
DELETE
↓
INSERT latest record
↓
COMMIT
↓
Latest record remains
```

以及 transaction rollback：

```text
Old record exists
↓
DELETE old record
↓
INSERT first new record
↓
INSERT duplicate Business Key
↓
UniqueViolation
↓
ROLLBACK
↓
Old record remains unchanged
```

Integration tests：

```text
pytest tests/integration/test_postgres_load_integration.py -v
```

結果：

```text
2 passed
```

完整 Python test suite：

```text
pytest -v
```

結果：

```text
56 passed
```

代表新增 PostgreSQL unit / integration tests 後，既有：

```text
Raw Validation
Transform
Profiling
Data Quality
Parquet Load
Snapshot Diff
PostgreSQL Schema
```

相關功能沒有 regression。

Integration test 使用測試日期：

```text
trade_date = 2099-01-02
```

測試完成後再次確認：

```text
COUNT(*) = 0
```

因此 PostgreSQL integration tests 未留下測試資料。

### Current Decision

PostgreSQL Trade-Date Replacement Load v1 已完成，並以真實 PostgreSQL 驗證：

```text
成功 replacement
→ COMMIT

Load 中途發生 database constraint error
→ ROLLBACK
→ 原本資料維持不變
```

因此：

```text
PostgreSQL Trade-Date Replacement Load
Transaction / Rollback Validation
```

目前皆視為完成。

### Idempotency Validation Result

已在真實 PostgreSQL integration test 中，對同一個：

```text
trade_date
```

與同一份：

```text
validated canonical snapshot
```

連續執行兩次：

```text
replace_trade_date_records()
```

驗證流程：

```text
第一次 replacement
↓
取得 database state A
↓
第二次 replacement
↓
取得 database state B
↓
A == B
```

結果確認：

```text
同一份 snapshot 重複 Load
→ row count 不增加
→ 不產生 duplicate
→ record 內容不改變
→ 最終 database state 完全一致
```

PostgreSQL integration tests：

```text
pytest tests/integration/test_postgres_load_integration.py -v
```

結果：

```text
3 passed
```

完整 Python test suite：

```text
pytest -v
```

結果：

```text
57 passed
```

因此目前可以確認：

```text
Trade-Date Replacement Load
→ 具備 state-level idempotency
```

`Idempotency Validation` 視為完成。

### PostgreSQL Pipeline Integration Validation Result

已將 PostgreSQL Trade-Date Replacement Load 正式接入目前的執行流程：

```text
scripts/check_api.py
```

目前流程已可完成：

```text
Extract
↓
Save Raw JSON / Metadata
↓
Raw Validation
↓
Transform
↓
Data Quality
↓
Canonical Parquet
↓
PostgreSQL Trade-Date Replacement
```

使用真實農業部 API 執行：

```text
trade_date = 2026-09-21
```

結果：

```text
API rows:        451
Raw Validation:  PASS
Data Quality:    PASS
PostgreSQL Load: 451 rows
```

本次執行產生：

```text
data/raw/agri_prices_20260921T155941.json
data/raw/agri_prices_20260921T155941_metadata.json
data/processed/agri_prices_20260921T155941.parquet
```

並直接查詢 PostgreSQL：

```text
localhost:5432
database = moa_agri
table = public.agri_prices
```

執行：

```sql
SELECT COUNT(*)
FROM agri_prices
WHERE trade_date = '2026-09-21';
```

結果：

```text
451
```

另外查詢：

```sql
SELECT *
FROM agri_prices
WHERE trade_date = '2026-09-21'
LIMIT 10;
```

已確認實際 canonical records 正確存在於 PostgreSQL，包括 Rest 與 Non-Rest records。

完整 Python test suite：

```text
pytest -v
```

結果：

```text
57 passed
```

因此目前可以確認：

```text
農業部 API
→ Raw Validation
→ Transform
→ Data Quality
→ Canonical Parquet
→ PostgreSQL Trade-Date Replacement
```

完整 end-to-end 路徑已以真實資料驗證成功。

`PostgreSQL Pipeline Integration` 視為完成。

### Pipeline Orchestration Validation Result

已新增正式 Pipeline orchestration layer：

```text
src/moa_agri_pipeline/pipeline.py
```

並提供：

```text
run_pipeline()
PipelineRunResult
```

`run_pipeline()` 目前負責協調：

```text
Extract
↓
Save Raw JSON
↓
Save Metadata
↓
Raw Validation
↓
Transform
↓
Data Quality
↓
Canonical Parquet
↓
PostgreSQL Trade-Date Replacement
```

新增 orchestration test：

```text
tests/test_pipeline.py
```

執行：

```text
pytest tests/test_pipeline.py -v
```

結果：

```text
1 passed
```

完整 Python test suite：

```text
pytest -v
```

結果：

```text
58 passed
```

因此目前可以確認：

```text
Pipeline stage order
→ verified

query_date / records / snapshot_id / output paths
→ correctly passed between stages

existing Extract / Transform / Quality / Load behavior
→ no regression
```

`Pipeline Orchestration` 視為完成。

`scripts/check_api.py` 暫時保留作為開發、學習與人工 end-to-end 驗證腳本，用來清楚觀察完整 Pipeline 各階段的執行流程；正式 Runtime Entry Point 尚未實作。

下一個主要工程問題改為：

> 如何將執行日期、輸出位置與其他 runtime 參數從 Pipeline orchestration 中分離，建立正式且可配置的 Runtime Entry Point？

也就是進入：

```text
Runtime Configuration / Runtime Entry Point
```

Source intra-day behavior 可繼續透過不同時間點保存的 Parquet snapshots 觀察，但仍為 non-blocking，不影響後續 Runtime Configuration / Runtime Entry Point 的進行。

---

## 11. Runtime Entry Point v1 Validation Result

本節記錄 `Pipeline Orchestration` 完成後，正式 Runtime Entry Point v1 的實作與驗證結果。

本節為目前最新進度；前述 `Runtime Configuration / Runtime Entry Point → NEXT` 為當時的階段狀態，現已由本節更新。

### Runtime Entry Point v1

已新增正式執行入口：

```text
scripts/run_daily.py
```

其責任限定為：

```text
Parse runtime arguments
↓
建立 PostgreSQL connection
↓
呼叫既有 run_pipeline()
↓
輸出 PipelineRunResult 摘要
```

目前執行方式：

```powershell
python scripts/run_daily.py --date 2026-09-21
```

其中：

```text
--date
→ required
→ 解析為 datetime.date
```

正式 Runtime Entry Point 不重新實作：

```text
Extract
Raw Validation
Transform
Data Quality
Canonical Parquet
PostgreSQL Load
```

上述 Pipeline stages 仍統一由：

```text
src/moa_agri_pipeline/pipeline.py
→ run_pipeline()
```

負責 orchestration。

因此正式 runtime path 為：

```text
PowerShell / CLI
↓
scripts/run_daily.py
↓
psycopg.connect()
↓
run_pipeline()
↓
Extract
↓
Save Raw JSON / Metadata
↓
Raw Validation
↓
Transform
↓
Data Quality
↓
Canonical Parquet
↓
PostgreSQL Trade-Date Replacement
```

### Runtime Configuration v1 Decision

Runtime Entry Point v1 不另外建立自訂 `config.py` 重新解析 PostgreSQL 連線參數。

目前使用：

```python
psycopg.connect(
    autocommit=True,
)
```

並將 PostgreSQL connection configuration 交由：

```text
psycopg
↓
libpq
↓
PostgreSQL standard runtime configuration
```

處理。

因此：

```text
PGHOST
PGPORT
PGDATABASE
PGUSER
password source
```

不硬寫於 Python source code。

目前 v1 不新增額外 dotenv / configuration dependency，也不將 PostgreSQL 密碼寫入：

```text
Python
Git
CLI argument
```

`run_pipeline()` 本身仍只接收已建立完成的：

```text
connection
```

而不直接處理 PostgreSQL credential。

### Runtime Entry Point Unit Tests

已新增：

```text
tests/test_run_daily.py
```

執行：

```text
pytest tests/test_run_daily.py -v
```

結果：

```text
4 passed
```

測試涵蓋：

```text
parse_date()
→ valid ISO date accepted

parse_date()
→ invalid date format rejected

parse_args()
→ --date correctly converted to datetime.date

main()
→ psycopg.connect() called
→ run_pipeline() called
→ query_date / connection correctly passed
→ PipelineRunResult summary printed
```

`main()` 測試使用 mock，因此：

```text
不呼叫真實農業部 API
不修改真實 PostgreSQL
```

### Full Regression Test

完成 Runtime Entry Point v1 後執行：

```text
pytest -v
```

結果：

```text
62 collected
59 passed
3 skipped
```

其中 3 個 skipped tests 為既有：

```text
tests/integration/test_postgres_load_integration.py
```

因未設定：

```text
RUN_POSTGRES_INTEGRATION=1
```

而依既有設計跳過。

本次新增的 4 個 Runtime Entry Point tests 全數通過，且既有：

```text
Raw Validation
Transform
Profiling
Data Quality
Parquet Load
Snapshot Diff
PostgreSQL Load
Pipeline Orchestration
```

相關測試均無 regression。

### Real Runtime End-to-End Validation

使用正式 Runtime Entry Point 與真實 PostgreSQL 執行：

```powershell
python scripts/run_daily.py --date 2026-09-21
```

結果：

```text
查詢日期：2026-09-21
Raw rows：1527
Transformed rows：1527
PostgreSQL rows：1527
Raw：data\raw\agri_prices_20261005T094044.json
Metadata：data\raw\agri_prices_20261005T094044_metadata.json
Canonical：data\processed\agri_prices_20261005T094044.parquet
```

因此已透過正式 Runtime Entry Point 驗證：

```text
CLI argument
↓
PostgreSQL connection
↓
run_pipeline()
↓
Agriculture API
↓
Raw / Metadata persistence
↓
Raw Validation
↓
Transform
↓
Data Quality
↓
Canonical Parquet
↓
PostgreSQL Trade-Date Replacement
```

完整 end-to-end path 成功。

本次執行三層 row count 一致：

```text
Raw rows          = 1527
Transformed rows  = 1527
PostgreSQL rows   = 1527
```

並直接查詢 PostgreSQL：

```sql
SELECT COUNT(*)
FROM agri_prices
WHERE trade_date = '2026-09-21';
```

已確認實際 database row count 與本次 Runtime Entry Point 輸出一致。

### Same-Date Runtime Re-run Validation

在第一次 Runtime Entry Point 寫入完成後，再次以相同：

```text
trade_date = 2026-09-21
```

執行：

```powershell
python scripts/run_daily.py --date 2026-09-21
```

第二次執行成功。

重新查詢 PostgreSQL 後，確認：

```text
同一 trade_date 重跑
→ 不累積 duplicate rows
→ database state 仍反映最新完整 snapshot
```

因此既有：

```text
Trade-Date Replacement
→ state-level idempotency
```

在正式 Runtime Entry Point 路徑下亦已完成真實驗證。

### Current Decision

目前可確認：

```text
Pipeline Orchestration
✅ COMPLETE

Runtime Configuration v1
✅ VALIDATED

Runtime Entry Point v1
✅ COMPLETE
```

`scripts/check_api.py` 繼續保留作為：

```text
Development
Learning
Manual stage-by-stage verification
```

用途。

正式日常 runtime execution 則改由：

```text
scripts/run_daily.py
```

作為入口。

目前 Runtime Entry Point v1 已具備：

```text
Explicit trade date
PostgreSQL runtime connection
Existing pipeline orchestration reuse
Runtime summary output
Unit test coverage
Full regression coverage
Real API + PostgreSQL end-to-end validation
Same-date re-run validation
```

下一步應先建立本階段 checkpoint，再討論後續 runtime operationalization，例如排程、自動化執行、logging / observability 或其他 production runtime concerns；不在本階段直接擴張功能範圍。

---

## 12. Runtime Failure Handling v1 Validation Result

本節記錄 Runtime Entry Point v1 完成後，針對正式 CLI 執行成功、CLI 使用錯誤與 Runtime exception 的實際行為驗證。

本階段以「先驗證 Python / argparse 既有行為，再決定是否需要新增 exception handling」為原則；驗證結果顯示目前既有行為已足以形成 Runtime Failure Handling v1，因此本階段不修改 `scripts/run_daily.py`。

### Runtime Exit Contract v1

目前已實際確認以下 process exit behavior：

```text
Successful execution
→ exit code 0

Unhandled runtime exception
→ exit code 1

CLI usage error
→ exit code 2
```

### Successful Execution Validation

使用正式 Runtime Entry Point 執行：

```powershell
python scripts/run_daily.py --date 2026-10-05
```

結果：

```text
查詢日期：2026-10-05
Raw rows：497
Transformed rows：497
PostgreSQL rows：497
Raw：data\raw\agri_prices_20261005T111025.json
Metadata：data\raw\agri_prices_20261005T111025_metadata.json
Canonical：data\processed\agri_prices_20261005T111025.parquet
```

並確認：

```text
Exit code: 0
```

因此正式 Runtime Entry Point 在完整 Pipeline 成功時會正常以 exit code `0` 結束。

### Runtime Exception Validation

為避免修改正式 credential 或 `pgpass.conf`，僅在目前 PowerShell session 暫時將：

```text
PGDATABASE
```

改為不存在的 database：

```text
__invalid_moa_agri__
```

再執行正式 Runtime Entry Point。

PostgreSQL connection 失敗後產生：

```text
psycopg.OperationalError
```

並保留完整 Python traceback。

實際確認：

```text
Exit code: 1
```

且錯誤輸出包含：

```text
host
port
database name
exception type
failure reason
```

本次輸出未顯示 PostgreSQL password。

測試後 `PGDATABASE` 已恢復為：

```text
moa_agri
```

因此目前 Runtime exception 採用 fail-fast behavior：

```text
Runtime exception
→ 不由 run_daily.py 廣泛捕捉
→ exception / traceback 保留
→ process 以 non-zero exit code 結束
```

目前不新增：

```python
except Exception:
```

或自訂錯誤包裝層，以避免在沒有明確需求時隱藏原始 traceback。

### CLI Usage Error Validation

執行：

```powershell
python scripts/run_daily.py --abc
```

因 `--date` 為 required argument，`argparse` 在進入 Pipeline 前直接拒絕此次 CLI invocation。

實際輸出：

```text
usage: run_daily.py [-h] --date DATE
run_daily.py: error: the following arguments are required: --date
```

並確認：

```text
Exit code: 2
```

因此 CLI usage error 可與 Runtime exception 使用不同 exit code 區分。

### Runtime Failure Handling Tests

在既有：

```text
tests/test_run_daily.py
```

新增兩個 regression tests：

```text
test_parse_args_exits_with_code_2_when_date_is_missing
test_main_propagates_connection_error
```

第一個測試確認：

```text
missing required --date
→ argparse
→ SystemExit
→ code == 2
```

第二個測試透過 `monkeypatch` 模擬 PostgreSQL connection failure，確認：

```text
psycopg.connect()
→ RuntimeError
→ main() 不吞掉 exception
→ exception 向外 propagate
```

該 failure-path test 不會：

```text
呼叫真實農業部 API
連線真實 PostgreSQL
寫入 Parquet
修改資料庫
```

執行：

```text
pytest tests/test_run_daily.py -v
```

結果：

```text
6 collected
6 passed
```

### Full Regression Test

完成 Runtime Failure Handling tests 後執行：

```text
pytest -v
```

結果：

```text
64 collected
61 passed
3 skipped
```

其中 3 個 skipped tests 仍為既有：

```text
tests/integration/test_postgres_load_integration.py
```

因未設定：

```text
RUN_POSTGRES_INTEGRATION=1
```

而依既有設計跳過。

新增 Runtime Failure Handling tests 全數通過，且既有：

```text
Raw Validation
Transform
Profiling
Data Quality
Parquet Load
Snapshot Diff
PostgreSQL Load
Pipeline Orchestration
Runtime Entry Point
```

相關測試均無 regression。

### Current Decision

Runtime Failure Handling v1 目前定義為：

```text
Success
→ exit code 0
→ stdout 顯示 PipelineRunResult 摘要

CLI usage error
→ argparse 負責錯誤訊息
→ exit code 2
→ 不進入 Pipeline

Unhandled runtime failure
→ exception / traceback 保留
→ stderr 顯示錯誤
→ exit code 1
```

目前沒有證據顯示需要在 `scripts/run_daily.py` 新增 broad exception handling。

因此：

```text
Runtime Configuration v1
✅ VALIDATED

Runtime Entry Point v1
✅ COMPLETE

Runtime Failure Handling v1
✅ COMPLETE
```

本階段實際程式修改僅限：

```text
tests/test_run_daily.py
```

正式 Runtime Entry Point implementation 維持不變。

下一步應先建立本階段 checkpoint，再進入 Runtime Operationalization 的下一個工程問題，例如正式排程 / 自動化執行；logging / observability 則應在有明確需求時再擴充。


---

## 13. Runtime Operationalization v1 — Scheduler-like Execution Test

本節記錄在尚未建立 Windows Task Scheduler 工作之前，以非專案工作目錄、未啟用 `.venv` 的 PowerShell，呼叫正式 Runtime Entry Point 的驗證結果。

### Engineering Question

當執行環境不在專案根目錄，且未啟用虛擬環境時，`scripts/run_daily.py` 是否能可靠啟動、完成 Pipeline，並將 Raw JSON、Metadata、Canonical Parquet 儲存在預期位置？

本階段不建立 Windows Task Scheduler 工作、不新增 logging framework、也不調整 PostgreSQL Load Strategy。

### Initial Observation — Working Directory Dependency

以 `.venv\Scripts\python.exe` 及 `scripts\run_daily.py` 的絕對路徑，自下列非專案工作目錄執行：

```text
C:\Users\dearl\AppData\Local\Temp\moa-agri-scheduler-test
```

測試交易日期：

```text
2026-10-05
```

首次真實執行結果：

```text
Raw rows：1546
Transformed rows：1546
PostgreSQL rows：1546
Exit Code：0
```

Raw JSON、Metadata 與 Parquet 當時實際儲存在測試工作目錄底下的 `data/raw`、`data/processed`，而非專案根目錄的 `data/`。可見 CLI 成功與 Exit Code `0` 並不能單獨證明檔案輸出位置正確。

根因是 `run_pipeline()` 原有預設參數採用：

```python
raw_output_dir = Path("data/raw")
processed_output_dir = Path("data/processed")
```

而 `run_daily.py` 原本沒有傳入明確的輸出目錄。相對路徑因此由執行程序的 Current Working Directory（CWD）解析。

### Minimal Fix — Runtime Entry Point Output Paths

保留 `run_pipeline()` 的既有預設參數與 Extract / Transform / Data Quality / PostgreSQL 核心邏輯，只修改 `scripts/run_daily.py`：

```python
from pathlib import Path

project_root = Path(__file__).resolve().parents[1]

result = run_pipeline(
    query_date=args.date,
    connection=connection,
    raw_output_dir=project_root / "data" / "raw",
    processed_output_dir=project_root / "data" / "processed",
)
```

以上為 `main()` 相關修改片段，非完整函式。程式依據自身檔案位置推導專案根目錄，不硬編 Windows 使用者名稱或磁碟位置。`scripts/run_daily.py` 成為正式 Runtime 執行時的固定輸出路徑邊界。

### Automated Tests

更新 `tests/test_run_daily.py` 中既有 `test_main_connects_and_runs_pipeline`：透過 `monkeypatch.chdir(tmp_path)` 模擬非專案工作目錄，並確認傳給 `run_pipeline()` 的兩個輸出目錄符合預期且皆為絕對路徑。

Runtime tests：

```text
pytest tests/test_run_daily.py -v
6 passed
```

完整 regression tests：

```text
pytest -v
64 collected
61 passed
3 skipped
```

3 個 skipped 仍為未啟用的 PostgreSQL integration tests，並非失敗。以上結果來自本輪使用者實際執行的測試輸出。

### Real Scheduler-like Execution Validation After Fix

再次從以下非專案工作目錄啟動正式入口，沒有執行虛擬環境的 `activate`：

```text
C:\Users\dearl\AppData\Local\Temp\moa-agri-scheduler-test
```

本次使用絕對路徑呼叫虛擬環境 Python 與 `scripts/run_daily.py`，交易日期仍為 `2026-10-05`。

正式 Pipeline 回報：

```text
查詢日期：2026-10-05
Raw rows：1546
Transformed rows：1546
PostgreSQL rows：1546
Exit Code：0
```

本次 Snapshot 實際輸出：

```text
C:\Users\dearl\Kevin-agent\projects\moa-agri-pipeline\data\raw\agri_prices_20261014T134215.json
C:\Users\dearl\Kevin-agent\projects\moa-agri-pipeline\data\raw\agri_prices_20261014T134215_metadata.json
C:\Users\dearl\Kevin-agent\projects\moa-agri-pipeline\data\processed\agri_prices_20261014T134215.parquet
```

上述三個實際檔案皆已透過 `Test-Path -LiteralPath` 確認存在（`True`）。此外，以唯讀 SQL 再次查詢 PostgreSQL：

```sql
SELECT COUNT(*)
FROM agri_prices
WHERE trade_date = DATE '2026-10-05';
```

實際得到：

```text
PostgreSQL actual rows: 1546
Exit Code: 0
```

故本輪已獨立確認 PostgreSQL 實際筆數與 Runtime 回報一致；並確認檔案沒有因為外部工作目錄而寫到測試目錄。

### Git Scope Verification

本輪 `git status --short` 顯示僅修改：

```text
 M scripts/run_daily.py
 M tests/test_run_daily.py
```

`git diff --check` 未回報格式問題。後續將本節加入 `docs/load_design.md`，再一併檢查最終 diff 與 staged files。

### Current Decision and Boundary

```text
Runtime Entry Point — Non-project CWD invocation
✅ VERIFIED

Raw / Metadata / Canonical output paths
✅ VERIFIED IN PROJECT DATA DIRECTORY

Runtime Exit Code
✅ 0

PostgreSQL actual row count
✅ 1546 (trade_date = 2026-10-05)

Automated regression
✅ 61 passed, 3 skipped

Windows Task Scheduler creation
→ NOT STARTED
```

**Finding：** 使用絕對路徑啟動 Python 與 Script，並不會自動變更 Current Working Directory；正式 Runtime 必須對輸出路徑明確指定基準。本輪已在 `run_daily.py` 修正輸出目錄，並以真實 Pipeline 驗證，具備繼續評估 Windows Task Scheduler 的基本前提。

**尚未驗證：** Windows Task Scheduler 的實際非互動式工作、排程服務帳戶權限、排程環境的 PostgreSQL credential / environment、失敗通知與排程歷史。這些不得由本輪 Scheduler-like Execution Test 的成功直接推論為已通過。

下一步為更新文件、檢查最終 Git diff，並建立一致範圍的 checkpoint；本輪不進入 Task Scheduler 建置。

---

## 14. Runtime Operationalization v1 — Windows Task Scheduler Dry-Run PoC

本節為第 13 節 Scheduler-like Execution Test 之後的新增驗證紀錄；第 13 節「Windows Task Scheduler creation → NOT STARTED」及其他舊階段狀態為當時的歷史紀錄，應以本節的最新結果判讀目前進度。

### Engineering Question and Scope

在不呼叫真實農業部 API、不產生 Raw / Metadata / Canonical 資料檔，也不變更 PostgreSQL 的前提下，Windows Task Scheduler 能否依設定時間，自動啟動本專案的 PowerShell wrapper，並以可辨識的 process exit code 結束？

本階段定位為本機概念驗證（Proof of Concept, PoC），暫以 Windows 筆電執行。使用者無法保證個人電腦每天開機及連網，因此本機排程不視為長期正式營運方案；未來仍以雲端排程為方向。本節不實作雲端排程、重構 ETL、增加 logging framework 或修改 credentials。

### Minimal Wrapper — `scripts/run_scheduled.ps1`

本輪新增一個 PowerShell 包裝腳本，保留既有正式入口 `scripts/run_daily.py` 與其必要參數 `--date YYYY-MM-DD`，不修改 `src/moa_agri_pipeline/pipeline.py`。

腳本的責任：

- 透過 `$PSScriptRoot` 定位 `scripts/`，推導 project root；不硬編 Windows 使用者目錄。
- 使用 project root 下的 `.venv\Scripts\python.exe` 和 `scripts\run_daily.py` 絕對路徑。
- 使用 `Taipei Standard Time` 將 UTC 現在時間換算為台灣日期，指定**執行當天**的交易日期，而非前一天。
- 執行前檢查 Python 與 `run_daily.py` 檔案是否存在。
- `-DryRun` 時只顯示 project root、台灣日期、路徑檢查及預計執行指令，直接以 exit code `0` 結束，不呼叫 Python。
- 不帶 `-DryRun` 時，先將 working directory 設為 project root，再以 `--date` 呼叫 Python；將 `$LASTEXITCODE` 傳回外層程序。
- wrapper 自身發生未處理的 PowerShell 錯誤時，以 exit code `1` 結束。

**執行安全邊界：** `-DryRun` 不會呼叫 API 或存取 PostgreSQL；但不帶 `-DryRun` 的正式模式會執行既有 Pipeline，可能依 trade-date replacement 策略取代指定交易日期的 PostgreSQL 資料。

### Manual Validation — Date and Wrapper

在筆電的互動式 PowerShell 中已完成：

1. 時區邊界驗證：`2026-10-14T16:30:00+00:00` 換算為台灣日期 `2026-10-15`；通過。
2. 實際台灣日期與 `YYYY-MM-DD` 格式驗證：2026-10-15；通過。
3. `.venv` Python 與 `scripts/run_daily.py` 的 `Test-Path` 結果皆為 `True`；通過。
4. 從 `C:\Windows\System32` 執行 wrapper `-DryRun`，正確顯示 project root、交易日期與完整 Python 指令；外層 exit code 為 `0`；通過。
5. 失敗路徑測試：僅在目前 PowerShell 工作階段暫時將 `PGDATABASE` 改為不存在的名稱，直接執行不帶 `-DryRun` 的 wrapper；Python 在 `psycopg.connect()` 階段失敗，`Python exit code: 1` 與 `Wrapper exit code: 1` 一致。`try/finally` 測試指令包含環境變數復原步驟。

上述失敗測試實際出現的是 `psycopg.OperationalError: ... fe_sendauth: no password supplied`，**不是**預期的 `database does not exist`。因此只能確認例外發生於資料庫連線階段且退出碼成功向外傳遞，不能將本次結果記為「已驗證不存在的資料庫錯誤訊息」。可能原因是 `pgpass.conf` 密碼條目與暫時指定的 database 名稱不匹配；此原因未另行驗證。本次沒有進入 `run_pipeline()`，所以沒有呼叫真實農業部 API 或執行 PostgreSQL replacement。

### Windows Task Scheduler Configuration

使用 Windows 工作排程器圖形介面建立一次性測試工作：

```text
Task name:       moa-agri-pipeline-dry-run-once
Execution host:  Windows 筆電
Account:         當時登入的本機 Windows 使用者（dearl）
Logon option:    僅在使用者登入時執行
Elevation:       不勾選「以最高權限執行」
Trigger:         Once — 2026-10-15 20:40（筆電台灣本地時間）
Action program:  powershell.exe
Action args:     -NoProfile -ExecutionPolicy Bypass -File "C:\Users\dearl\Kevin-agent\projects\moa-agri-pipeline\scripts\run_scheduled.ps1" -DryRun
Start in:        C:\Users\dearl\Kevin-agent\projects\moa-agri-pipeline
```

這個 Action 明確使用 `-DryRun`，本階段沒有設定每天重複執行，也沒有建立可寫入正式資料庫的週期性工作。Task Scheduler 工作設定保存在該 Windows 電腦；本輪未匯出或提交排程工作的 XML 定義。

### Actual Scheduled Run Validation — 2026-10-15

使用者提供 Windows 工作排程器截圖，顯示一次性工作於 `2026-10-15 20:40:00` 觸發，約在 `20:40:01` 完成。事件歷程包含：

```text
Event 107  Task triggered on scheduler
Event 129  Created Task Process
Event 100  Task Started
Event 200  Action started
Event 201  Action completed
Event 102  Task completed
```

重新整理後，該工作「上次執行結果」顯示：

```text
操作順利完成 (0x0)
```

**Finding：** Windows Task Scheduler 確實依指定時間觸發所設定的 PowerShell Action，且該次工作程序以成功退出碼 `0x0` 結束。這與先前互動式 `-DryRun` 成功的結果一致，足以支持 **「一次性 Task Scheduler Dry-Run 啟動 PoC」已通過**。

**證據邊界：** 本次沒有另外保存排程程序的 stdout / stderr，故不能單憑 `0x0` 獨立證明排程當下輸出的交易日期與路徑文字；也沒有在 Task Scheduler 下實際執行 Python ETL、農業部 API、Parquet 寫入或 PostgreSQL Load，更未驗證未登入執行、睡眠喚醒、錯過排程補跑、持續運作及雲端部署。

### Tests, Checkpoint Scope and Next Stage

本輪 wrapper 以 PowerShell 人工驗證、受控失敗案例與 Task Scheduler 事件紀錄驗收。**沒有新增 PowerShell 自動化測試，也尚未在本輪重新取得完整 pytest regression 結果**。先前第 13 節記錄的 `61 passed, 3 skipped` 屬於既有 Python 程式版本的歷史驗收結果，不應標為本輪重新執行。

本輪準備提交的檔案限定為：

```text
scripts/run_scheduled.ps1
docs/load_design.md
```

本機已確認：

```text
git status --short
?? scripts/run_scheduled.ps1

git rev-parse --short HEAD
d8ef225
```

文件更新以前的 GitHub `main` 版本仍停在第 13 節；本節僅追加新階段驗證結果，保留第 1～13 節既有文字與歷史紀錄。

目前最新階段：

```text
PowerShell wrapper — timezone / paths / manual Dry Run
✅ VERIFIED

PowerShell wrapper — non-zero exit propagation
✅ VERIFIED FOR ONE CONNECTION FAILURE CASE

Windows Task Scheduler — one-time Dry-Run invocation
✅ VERIFIED (2026-10-15 20:40, 0x0)

Scheduled real API + PostgreSQL end-to-end execution
→ NOT STARTED

Cloud scheduler
→ FUTURE STAGE
```

下一個 checkpoint 應先審查本輪 Git diff、必要測試與文件，再由使用者自行決定 commit / push。後續若要進行真正的排程端對端測試，必須先告知真實 API 呼叫與指定交易日期 PostgreSQL replacement 的副作用，並再次取得使用者明確同意。


---

## 15. Runtime Operationalization v2 — Windows Task Scheduler Real ETL Acceptance

本節接續第 14 節的一次性 Windows Task Scheduler Dry-Run PoC，記錄 2026-10-25 實際由 Windows Task Scheduler 啟動農業部 EIR030 ETL、產生快照並寫入**隔離 PostgreSQL 測試資料庫**的驗收結果。第 14 節「Scheduled real API + PostgreSQL end-to-end execution → NOT STARTED」為當時的歷史狀態，應以本節結果解讀最新進度；不回寫或改動第 1～14 節既有內容。

### Engineering Question and Acceptance Criteria

**問題：** Windows Task Scheduler 能否按預定時間，自動啟動完整 ETL，成功從農業部 API 擷取指定日期資料、轉換與品質檢查、保存 Raw/Metadata/Canonical 快照，並將交易行情寫入 PostgreSQL？

**驗收標準：**

1. 一次性排程確實被觸發，`LastTaskResult = 0`，並留下可檢視的執行日誌。
2. 日誌中可確認正確交易日期、實際連線資料庫、Raw/Transform/PostgreSQL 筆數、快照路徑及 Python/Task exit code。
3. 以**獨立 SQL 查詢**確認 PostgreSQL 測試資料庫中指定交易日期筆數與 ETL 回報一致。
4. 以**獨立 Parquet 讀取**確認 Canonical 快照筆數及交易日期與測試資料庫一致。
5. 測試全程不指定原有 `moa_agri` 為目標資料庫；禁止將測試結果推論為已驗證正式環境的常態排程。

### Test Scope and Safety Controls

```text
Run date (Windows/Taipei): 2026-10-25
Requested trade date:      2026-10-05
Test PostgreSQL database:  moa_agri_sched_test
Target table:              agri_prices
Original database:         moa_agri (not a target of this test)
Schedule:                  One-time, not recurring
```

先於 PostgreSQL 建立獨立的 `moa_agri_sched_test` 資料庫，使用既有 `sql/schema.sql` 建立 `agri_prices` 及兩個 unique indexes，並確認初始筆數為 `0`。使用 `pgpass.conf` 提供非互動式認證（密碼不寫入版本控制、文件或執行日誌）；`psql -w` 與 Python `psycopg.connect(autocommit=True)` 均驗證可連線到測試庫，Python 初始查詢為 `Rows: 0` 且 exit code `0`。

本輪調整兩個執行入口：

- `scripts/run_scheduled.ps1`：新增可選的 `-RequestedTradeDate`；未指定時仍使用台灣當天日期。新增 `-TargetDatabase`，此 PoC 的允許值限定為 `moa_agri_sched_test`。真實執行模式未指定測試資料庫時拒絕啟動；帶入參數時，設定子程序的 `PGHOST=localhost`、`PGPORT=5432`、`PGUSER=postgres`、`PGDATABASE=moa_agri_sched_test`，並傳遞 `--expected-database`。
- `scripts/run_daily.py`：新增可選的 `--expected-database`；當有指定時，在 `run_pipeline()`（包含 API 呼叫與 Load）之前查詢 `SELECT current_database()`。若實際名稱與預期不符，拋出錯誤並拒絕啟動 Pipeline；未指定參數時，保留原有 CLI 執行路徑。

另外新增 `tests/test_run_daily_db_guard.py`，驗證資料庫名稱符合時可繼續執行，以及不符合時會在呼叫 Pipeline 前停止。這個資料庫 guard 是針對本次排程 PoC 的防護；**不可推論所有直接使用 `run_daily.py` 而未提供 `--expected-database` 的執行也會被強制檢查。**

在 PowerShell `-DryRun` 下，明確指定歷史日期、測試資料庫時 exit code `0`；指定不允許的 `moa_agri` 時由 `ValidateSet` 拒絕，exit code `1`。未指定日期的 Dry Run 仍能正確取台灣當天 `2026-10-25`。透過 PowerShell 輸出重新導向，人工 Dry Run 的 stdout/stderr 已成功保存成 `.log`，但這項人工驗證與下述真實排程證據分開記錄。

### Automated and Real-Connection Safety Validation

使用者於本機執行：

```text
pytest tests/test_run_daily.py tests/test_run_daily_db_guard.py -v
8 passed

pytest -v
63 passed, 3 skipped
```

其中 `3 skipped` 為既有 PostgreSQL integration tests 未啟用，不能記為通過。新增資料庫 guard 的兩項測試已通過。

額外使用**真實 PostgreSQL 連線**驗證 guard：實際連線 `moa_agri_sched_test`，並以臨時函式 `block_pipeline()` 攔截 `run_pipeline()`，確保測試不呼叫農業部 API、也不進行資料寫入。最終輸出：

```text
Database verified: moa_agri_sched_test
PASS: expected=moa_agri_sched_test
PASS: expected=moa_agri
Exit code: 0
```

第二個 `PASS` 是指「當預期名稱故意設成 `moa_agri` 時，程式成功拒絕錯誤資料庫名稱」，**不是成功連接或寫入 `moa_agri`**。第一次測試因錯誤文字斷言不符而 exit code `1`，修正測試斷言後重新執行通過；並未修改實際 Pipeline 功能以迴避該測試。

### One-Time Task Scheduler Execution — 2026-10-25

使用者於 `%LOCALAPPDATA%\moa-agri-pipeline\run_real_once.ps1` 建立本機排程啟動器，負責：

- 以固定日期 `2026-10-05`、`-TargetDatabase moa_agri_sched_test` 執行專案內 `scripts/run_scheduled.ps1`，**不帶 `-DryRun`**。
- 將 stdout/stderr 寫入 `%LOCALAPPDATA%\moa-agri-pipeline\logs\scheduled_real_YYYYMMDD_HHMMSS.log`。
- 將內層 Python 的 exit code 經 wrapper 傳至排程啟動器及 Task Scheduler。

該啟動器與日誌存放在 Windows 使用者的 Local AppData，**不是本次 Git checkpoint 的檔案**。Task Scheduler 設定為目前 Windows 使用者登入狀態下的一次性工作；本輪沒有建立每日週期排程。

實際排程設定與結果：

```text
Task name:       moa-agri-pipeline-real-once
Scheduled at:    2026-10-25 07:38:22 (Windows local / Taipei)
LastRunTime:     2026-10-25 07:38:22
LastTaskResult:  0
State afterward: Ready
```

`Ready` 是工作已就緒的狀態，不代表正在執行。此處以 `LastRunTime` 與 `LastTaskResult = 0`，搭配下方獨立日誌與資料庫查詢，判定此次一次性排程**確實執行且成功結束**。

真實執行日誌：

```text
C:\Users\dearl\AppData\Local\moa-agri-pipeline\logs\scheduled_real_20261025_073823.log
```

日誌關鍵輸出：

```text
Trade date (explicit): 2026-10-05
Target database (explicit): moa_agri_sched_test
Python exists: True
Script exists: True
Database verified: moa_agri_sched_test
查詢日期：2026-10-05
Raw rows：1546
Transformed rows：1546
PostgreSQL rows：1546
Python exit code: 0
Task exit code: 0
```

該次執行回報產生以下快照：

```text
data/raw/agri_prices_20261025T073835.json
data/raw/agri_prices_20261025T073835_metadata.json
data/processed/agri_prices_20261025T073835.parquet
```

以上快照路徑來自真實執行日誌；本節另外對 Parquet 內容做了唯讀查核，並非宣稱已逐一比對 Raw 與 Metadata 全部欄位。

### Independent PostgreSQL and Parquet Verification

使用者在排程完成後，以 `psql -w -d moa_agri_sched_test` 執行唯讀查詢，結果如下：

```text
database_name       = moa_agri_sched_test
total_rows          = 1546
target_date_rows    = 1546  (trade_date = 2026-10-05)
other_date_rows     = 0
```

接著使用 `pyarrow.parquet` 讀取該次 Canonical Parquet 快照，獨立確認：

```text
Parquet rows: 1546
Target date rows: 1546
Other date rows: 0
PASS: Parquet row count and trade dates verified
Exit code: 0
```

**Finding：** Windows Task Scheduler 已成功啟動本機一次性真實 ETL，API Extract、Transform、資料品質檢查、Canonical Parquet 產生與 PostgreSQL Load 均由 Pipeline 正常返回；資料庫身分保護、程序退出碼、排程結果及外部 SQL/Parquet 查詢互相支持。本次可判定 **Windows Task Scheduler Real ETL Acceptance — PASSED**。

**驗證邊界：**

- SQL 與 Parquet 已驗證總筆數、指定交易日期筆數及其他日期筆數一致；**尚未逐筆比較所有欄位值或完整 business key 集合**。
- 本輪未獨立查詢原有 `moa_agri` 在排程前後的資料差異；「未以原資料庫為目標」由啟動參數、實際資料庫身分日誌與測試庫查詢支持，不應誤寫成已完成原資料庫的前後差異比對。
- 本次測試在登入且電腦可執行排程的狀態下進行；未驗證未登入執行、睡眠喚醒、斷網重試、異常通知、排程補跑、每天長期運作或雲端排程。
- 既有 `replace_trade_date_records()` 對指定日期採 DELETE + INSERT replacement；本次只在新建的隔離測試庫執行。API 回傳空資料的情況可能導致指定日期資料被清空，不能因本次成功而排除該風險。

### Current Checkpoint Scope and Next Direction

本輪應納入同一個 Git checkpoint 的專案檔案：

```text
scripts/run_daily.py                  # optional --expected-database guard
scripts/run_scheduled.ps1             # test date / target DB / fail-closed
tests/test_run_daily_db_guard.py      # new guard tests
docs/load_design.md                   # append this acceptance record
```

依使用者當時 `git status --short`，提交前既有變更為 `scripts/run_daily.py`、`scripts/run_scheduled.ps1` 及新增的 `tests/test_run_daily_db_guard.py`；本節文件亦應同步更新，再檢查 `git diff`、`git diff --check`、stage 範圍後 Commit / Push。勿提交 `pgpass.conf`、本機排程啟動器、日誌、Raw JSON 或 Parquet 輸出。

本階段最新狀態：

```text
Windows Task Scheduler one-time Dry Run
✅ VERIFIED (2026-10-15)

Windows Task Scheduler one-time real ETL
✅ VERIFIED (2026-10-25)

Real PostgreSQL target DB identity guard
✅ VERIFIED

PostgreSQL trade-date rows (independent query)
✅ 1546 in moa_agri_sched_test

Canonical Parquet rows and trade date
✅ 1546 / 2026-10-05

Full field-by-field PostgreSQL ↔ Parquet comparison
→ NOT PERFORMED

Recurring unattended production scheduling / cloud scheduler
→ NOT VERIFIED / FUTURE STAGE
```

**Current decision：** 本次本機一次性真實排程驗收達成；結束本階段後，應先將程式碼、測試與本節文件整理為同一個 Git checkpoint。後續是否移轉至雲端排程、強化空快照保護及異常告警，應另開獨立工程問題處理，而非視為本輪已完成。


## 16. Pipeline Reliability v1 — Empty Snapshot Load Safety

### Engineering Question

當指定交易日期的農業部 API 快照由既有 N 筆變為最新 0 筆時，如何保留原始快照以供追查，同時避免 PostgreSQL 既有資料被直接清空？

### Decision / Scope

本輪採用 **Warn + Preserve Existing Rows**：空陣列 `[]` 仍是合法的 Raw／Canonical 輸入，不改動既有 Raw Validation、Transform、Data Quality 判準，也不將「新資料筆數下降」一律視為異常；僅在 PostgreSQL Load 邊界對**新快照為 0 筆**的情況查詢指定 `trade_date` 之原有筆數。

| 指定交易日期的原有筆數 | 本次新快照筆數 | Load status | PostgreSQL 行為 |
| ---: | ---: | --- | --- |
| 任意（包含 0） | 大於 0 | `LOADED` | 沿用原本 transaction 內 DELETE + INSERT replacement |
| 0 | 0 | `NO_DATA` | 不執行 DELETE／INSERT，記錄無資料 |
| 大於 0 | 0 | `SKIPPED_EMPTY` | `WARNING: EMPTY_SNAPSHOT`，跳過 DELETE／INSERT，保留既有資料 |

此處的 `SKIPPED_EMPTY` 是**載入安全防護**，不代表 API 回傳資料格式不合法，也不代表已證實來源異常。當最新合法快照為空、DB 原有資料非空時，PostgreSQL 會暫時保留舊版；Raw JSON、Extract Metadata 與 Canonical Parquet 仍保存本次空快照，兩者可能暫時不一致，須以 `Load status` 區分。

### Implementation

- `src/moa_agri_pipeline/load/postgres.py`：`replace_trade_date_records()` 對空快照先以參數化 SQL 查詢該交易日期現有筆數；依結果回傳 `PostgreSQLLoadResult(status, written_rows, existing_rows)`。原有資料大於 0 時記錄包含交易日期、原有筆數、新資料 0 筆與 `action=SKIP_LOAD` 的 `WARNING`，且不進入 DELETE／INSERT transaction。非空資料維持原有日期驗證與 transaction replacement。
- `src/moa_agri_pipeline/pipeline.py`：`PipelineRunResult` 新增 `postgres_load_status` 與 `postgres_existing_rows`，繼續傳遞本次寫入筆數及 Raw／Metadata／Canonical 路徑。
- `scripts/run_daily.py`、`scripts/check_api.py`：適配 Load Result，讓 CLI 可顯示成功更新、無資料或跳過更新的結果，不將 `SKIPPED_EMPTY` 錯誤描述為已成功寫入 0 筆且完成替換。
- 既有 PostgreSQL 連線身分防護及 Windows 排程流程不因本次變更而取消；本輪不加入通知服務、雲端排程或新的監控資料表。

### Validation Evidence (2026-10-25)

使用者於 Windows 3.12.10 虛擬環境實際執行並回報：

```text
pytest tests/test_postgres_load.py tests/test_pipeline.py tests/test_run_daily.py tests/test_run_daily_db_guard.py -v
15 passed

pytest -v
66 passed, 4 skipped
```

完整迴歸測試的 4 個 skipped，為需要明確啟用的 PostgreSQL integration tests，**非失敗**。使用者隨後確認連線的 PostgreSQL 資料庫為 `moa_agri_sched_test`，並查到隔離測試交易日期 `2099-01-02` 的既有筆數為 0；再以 `RUN_POSTGRES_INTEGRATION=1` 啟用真實資料庫整合測試：

```text
pytest tests/integration/test_postgres_load_integration.py -v
4 passed in 0.43s
```

四項真實 PostgreSQL 測試涵蓋：正常 transaction replacement、插入失敗 rollback、相同資料重跑的冪等性、空快照時保留既有資料。最後一項整合測試使用 **1 筆測試資料 → 空快照**，比對操作前後資料列一致；**500 筆 → 0 筆**的筆數及 WARNING 內容則由 mock 單元測試驗證，不能誤稱真實資料庫已測試 500 筆。`0 → 0` 之 `NO_DATA` 行為同樣已有單元測試，未另列為真實 PostgreSQL integration case。

**Finding：** 本輪已通過相關單元測試、完整回歸測試與隔離 PostgreSQL 整合測試，可確認指定日期的空快照不再觸發既有資料的替換刪除；非空 snapshot 的 replacement、rollback、idempotency 仍通過相應測試。

### Verification Boundary / Next Direction

- 未使用真實 API 0 筆回傳進行端到端排程驗收；本輪以 deterministic tests 與隔離 PostgreSQL 進行驗證。
- 尚未測試重試、告警通知、長期排程、雲端執行或跨執行程序競爭條件。
- `SKIPPED_EMPTY` 為防護性跳過，不會自行補抓或覆蓋原有資料；是否需要後續人工覆核與重新載入策略，保留後續階段設計。
- 使用者完成本輪測試後，可將程式碼、測試及本節文件納入同一個 Git checkpoint；再規劃不依賴個人 Windows 電腦的持續執行方式。

## 17. Cloud PostgreSQL Connectivity PoC — Neon Free Sandbox

### Engineering Question

在不依賴本機 PostgreSQL、也不執行既有 ETL Load 的情況下，Windows 本機 Python 是否能透過網際網路安全地連接獨立 Neon PostgreSQL 測試資料庫，並以唯讀 SQL 確認實際資料庫與 Role 身分？

### Environment / Isolation

本階段新增一個**獨立的雲端 Sandbox**，不遷移、不清理、不改寫原有 Windows PostgreSQL 資料庫。

| Item | Value |
| --- | --- |
| Cloud provider / plan | Neon Free |
| Organization | `kevin-data-lab` |
| Neon Project | `moa-agri-pipeline-sandbox` |
| Neon Branch | `production`（Neon 建立的預設分支名稱；**不是**已上線的正式營運資料庫） |
| Region | AWS Asia Pacific 1（Singapore） |
| PostgreSQL database | `moa_agri_cloud_test` |
| Connected role | `moa_agri_cloud_test_owner` |
| Connection type | Direct Connection（Connection pooling 關閉；不使用 `-pooler` 端點） |
| Connection security parameters | `sslmode=require`、`channel_binding=require` |
| Client | Windows、Python 3.12.10、`psycopg` |
| Original local databases | `moa_agri`、`moa_agri_sched_test`（非本輪測試目標） |

本輪透過 Neon Console 建立 Project 與指定測試資料庫。連線密碼在本機 Python 使用 `getpass()` 互動輸入，不寫入程式碼、文件或 Git。此處不保存含帳號密碼的完整 Connection String。

### Read-Only Connection Validation — 2026-10-26

使用者在既有專案的 Python 虛擬環境啟動 Python REPL，直接呼叫 `psycopg.connect()`，指定上述 Neon 測試資料庫、Role、Direct Connection Host 與加密連線參數，並設定 `connect_timeout=20`。

連線物件建立成功後，僅執行以下唯讀 SQL：

```sql
SELECT current_database(), current_user;
```

使用者提供的實際 Python 執行輸出：

```text
>>> print(conn.execute(
...     "SELECT current_database(), current_user"
... ).fetchone())
('moa_agri_cloud_test', 'moa_agri_cloud_test_owner')
>>> conn.close()
```

**Finding / Result：Cloud PostgreSQL Connectivity PoC — PASSED（本機 Python → Neon）。**

- `psycopg.connect()` 在指定 `sslmode=require`、`channel_binding=require` 的設定下成功建立連線。
- `SELECT current_database()` 確認目標為 `moa_agri_cloud_test`。
- `SELECT current_user` 確認實際 Role 為 `moa_agri_cloud_test_owner`。
- `conn.close()` 正常返回。
- 本次只執行 `SELECT`；**未執行** `INSERT`、`UPDATE`、`DELETE`、`CREATE TABLE` 或完整 ETL。
- 未修改專案原始程式碼、PostgreSQL Load 行為或既有測試。
- 本階段未重新執行 `pytest`；先前 `66 passed, 4 skipped` 與 PostgreSQL integration `4 passed` 是**前一階段驗證紀錄**，不可列為本次 Neon 的測試結果。

### Verification Boundary / Current Decision

本次驗證僅證明**本機 Windows Python 可成功連接獨立 Neon PostgreSQL，且 SQL 查詢取得預期資料庫與 Role 身分**。不代表已經完成：

- GitHub Actions Runner → Neon 的連線或 GitHub Secrets 設定。
- Neon 上的 `sql/schema.sql` 部署、`agri_prices` 表與 unique constraints 驗證。
- Neon 上的寫入、Transaction / Rollback / Idempotency、Empty Snapshot Safety Guard 整合測試。
- 正式資料遷移、排程、重試與失敗監控。
- Raw JSON、Metadata、Parquet 的雲端持久化保存。

`sslmode=require` 與 `channel_binding=require` 已由此次成功連線使用；本輪沒有另外進行獨立的 TLS 憑證驗證稽核。

**Current decision：** 本機 → Neon 的唯讀連線驗收完成。此 checkpoint 僅需更新本文件，不新增 Pipeline 程式或測試。下一個獨立工程問題是**在 Neon Sandbox 建立並驗證既有 PostgreSQL Schema**；應先討論與定義驗收邊界，再執行可能改變 Neon Sandbox 的 SQL 操作。
