# Project Development Workflow

## Purpose

本文件定義 `moa-agri-pipeline` 專案後續開發與 ChatGPT 協作的固定流程。

目標是讓：

```text
GitHub 程式碼
測試結果
Data Profiling Findings
目前開發進度
```

保持同步，避免對話中的程式版本、GitHub 版本與文件紀錄互相脫節。

---

## Standard Workflow

### Step 1 — Push Current Checkpoint

每完成一個可獨立驗收的階段，先：

```text
test
↓
commit
↓
push GitHub
```

GitHub `main` 作為下一階段開始時的基準版本。

---

### Step 2 — Sync From GitHub

開始下一階段前，由 ChatGPT：

1. 讀取 GitHub 最新程式碼。
2. 讀取相關 tests。
3. 讀取最新 `docs/data_profiling_findings.md`。
4. 確認目前程式、測試與 findings 的進度一致。
5. 再決定下一個最小充分任務。

不應僅依賴先前對話中的舊程式碼推測目前狀態。

---

### Step 3 — Work on One Profiling / Engineering Question

每一輪優先只回答一個明確問題，例如：

```text
All-Zero 是否等於 Rest？
```

```text
crop_code → crop_name 是否穩定？
```

```text
category_code + market_code → market_name 是否仍有 conflict？
```

```text
Candidate Business Key 是否唯一？
```

流程：

```text
定義問題
↓
檢查現有函式是否已足夠
↓
必要時新增最小程式碼
↓
必要時新增 / 修改 report
↓
新增或修改對應 test
↓
執行真實資料
↓
閱讀輸出
↓
討論 finding
```

避免因為「可以再寫一個函式」就繼續增加無法改變後續決策的功能。

---

### Step 4 — Validate Before Documenting

本輪程式完成後：

```text
pytest tests/<relevant_test>.py -v
↓
pytest -v
↓
執行 profiling / pipeline script
```

只有在：

- test 通過；
- 真實資料輸出已確認；
- finding 已經可以清楚表述；

之後，才更新 findings。

---

### Step 5 — Update Findings From Latest GitHub Version

在更新 `docs/data_profiling_findings.md` 前，由 ChatGPT：

1. 重新讀取 GitHub 上目前版本的 MD。
2. 以 GitHub 版本作為 base。
3. 只加入本輪實際得到的新 finding、methodology correction 或 decision。
4. 保留使用者已經自行刪減與整理過的結構。
5. 不把尚未驗證的 hypothesis 寫成 finding。
6. 不自行恢復使用者已刪除的舊內容。

更新完成後，ChatGPT 直接提供：

```text
完整的 data_profiling_findings.md
```

供使用者直接取代專案內的文件，而不是只提供零碎 Markdown 片段。

---

### Step 6 — Create Git Checkpoint

Finding 文件同步後，由 ChatGPT 提供：

```text
建議 stage 的檔案
commit title
必要時 commit body
```

使用者確認後：

```text
git add
git commit
git push
```

此 push 完成後，本輪結束。

下一個階段再次回到 Step 2，重新從 GitHub 同步。

---

## Working Principles

### GitHub Is the Source of Truth

每個新階段開始時：

```text
GitHub latest main
```

是程式與文件的基準。

對話中先前貼過的程式碼只作為歷史脈絡，不應凌駕 GitHub 最新版本。

---

### Finding Before Rule

Data Profiling 的順序：

```text
Observation
↓
Investigation
↓
Finding
↓
Decision
↓
Data Quality / Schema Rule
```

不能先猜一個 Data Quality Rule，再要求資料符合該規則。

---

### Hypothesis Is Not a Finding

例如：

```text
可能是 Rest 導致 market_code conflict
```

只能記為 hypothesis。

重新分流後實際跑資料才能決定：

```text
Rest 是否真的是 conflict 的原因
```

文件必須區分：

- Observation
- Hypothesis
- Finding
- Current Decision

---

### Keep Profiling Decision-Oriented

新增 Profiling 前先問：

```text
這個分析要回答什麼問題？
現有輸出是否已能回答？
答案是否會影響 Schema / Transform / Quality / Key / Load / Monitoring？
```

如果只是產生更多資訊，卻不改變任何工程決策，原則上不繼續擴充。

---

### Keep Reports Human-Readable

`report.py` 的目的不是單純把 Python object 移到另一個檔案 `print()`。

Report 應該：

- 使用一致的術語。
- 優先以表格或簡潔摘要呈現。
- Relationship Profiling 使用一致的 one-to-many / NULL pattern 表達方式。
- 避免加入與當前分析問題無關的統計數字。
- 讓前後階段的結果可以直接比較。

---

### One Checkpoint, One Coherent Change

理想 commit 應包含同一個階段的：

```text
implementation
+ report
+ tests
+ findings
```

若有獨立的專案流程文件或大型重構，可視情況拆成單獨 docs / refactor commit。

---

## Cycle Summary

整個專案後續固定循環：

```text
Push checkpoint
      ↓
ChatGPT sync GitHub
      ↓
Define next question
      ↓
Implement minimal change
      ↓
Run tests
      ↓
Run real data
      ↓
Interpret finding
      ↓
ChatGPT re-read GitHub findings
      ↓
Generate complete updated MD
      ↓
Commit + Push
      ↓
Repeat
```
