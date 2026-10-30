# Learning & Engineering Execution Framework

> **Status：Active｜制定日期：2026-10-30｜專案：`moa-agri-pipeline`**
>
> 核心目標：同時完成**可展示的資料工程作品**與培養**能獨立解決資料工程問題的能力**，不再陷入任務過度切碎、反覆執行測試與 Commit、只複製貼上程式碼的循環。

## 1. 專案目的與終點

建立一條可以在雲端執行的農業部 EIR030 農產品交易行情資料管線：

```text
GitHub Actions（觸發）
  ↓
MOA Open Data API（Extract）
  ↓
Raw JSON + Metadata（保存原始快照）
  ↓
Raw Validation → Transform → Data Quality
  ↓
Canonical Parquet
  ↓
Cloudflare R2（歷史 Snapshot 保存）
  ↓
Neon PostgreSQL（更新可查詢的交易行情）
```

以上是**目標架構**，不表示每一段都已整合。主要完成界線是：能在受控雲端環境成功執行端到端 Pipeline，核對 R2 Snapshot、Neon 資料與執行證據，並能清楚解釋失敗處置和已知限制。

優先完成可展示的 MVP。不為了「可以再加一個檢查」無限擴張架構、監控、重試策略或附加功能。

## 2. 目前基準與三階段主線

以下是 **2026-10-30 的歷史基準**，每個新 Session 都必須重新查詢 GitHub 最新 `main` 與近期測試證據，不能將它當成永遠不變的進度。

- 已有 Extract、Transform、Data Quality、Parquet、本機 PostgreSQL Load 與本機 Pipeline。
- Cloudflare R2：已完成合成資料的獨立上傳、下載與 SHA-256 PoC；尚未整合正式 ETL。
- Neon PostgreSQL：已有連線及基本交易／ROLLBACK 驗證；**不能推論完整 replacement load 已在 Neon 驗收**。
- R2 最新已知 GitHub checkpoint：`3e2866c`，完成上傳前檔案關聯／日期／Object Key 驗證；使用者本機回報 `5 passed`、完整 `71 passed, 4 skipped`。這些是**當時本機測試**，不是新 Session 的最新 CI。
- 正式的 R2 Upload、GitHub Actions 雲端端到端 ETL：尚未完成。

後續主要工作限制在以下三個交付階段：

| 階段 | 交付與驗收標準 |
| --- | --- |
| **A：R2 Snapshot Upload v1** | 可重用上傳元件；同 Key 已存在且內容相同則跳過、內容不同拒絕覆寫；上傳後完整性驗證；部分失敗可以安全重試；正式使用前處理 Snapshot ID 時區／碰撞風險；完成必要離線與受控 R2 測試。 |
| **B：整合既有 Pipeline** | R2 保存成功後再更新 PostgreSQL；R2 失敗時不可悄悄寫入資料庫；PostgreSQL 失敗時已保存的快照仍可回查；用整合測試確認。 |
| **C：GitHub Actions 端到端驗收** | 在受控環境成功執行正式資料流，確認 R2 物件、Neon 查詢結果、執行紀錄和失敗回報，整理作品集的架構與測試證據；正式啟用排程另行確認。 |

不直接推進 A／B／C 驗收的想法，先記成 backlog；除非能指出真實阻礙或高風險，不立即開新支線。

## 3. 每個新 Session 必做的同步

1. 讀取 GitHub 最新 `main` Commit、`AGENTS.md`、本文件、`docs/project_development_workflow.md`、當前階段的設計文件、相關程式碼和 tests；若無法查詢 GitHub，須明確告知，不得假裝完成同步。
2. 區分**遠端已提交內容**、**使用者本機未提交修改**及**當前／歷史測試輸出**；不可因本機測試通過就聲稱 GitHub 已更新。
3. 用簡短摘要指出：目前階段、已驗收成果、本次交付目標、尚未驗證的風險。
4. 不重做已驗收功能、不恢復使用者移除的文件內容；使用者當輪明確要求優先。

## 4. 任務粒度：一個可驗收功能，不是一個 `if`

每輪先定義一個**可觀察、可驗收的工程成果**：

- **Why**：解決哪個現實問題？不做會怎樣？
- **How**：有哪些設計選項與取捨？刻意不做什麼？
- **Validation / Done**：成功與失敗如何判定？何時算完成？

例如「R2 Snapshot 上傳前驗證」本來就應包括檔案存在、Snapshot ID、Metadata、日期與 Object Key 等同一組邏輯；**不應每新增一個條件，就再啟動一輪新任務、完整回歸測試、文件更新及 Commit**。

執行可小步前進，但 Git checkpoint 以**一個有意義、可回溯的完整變更（coherent change）**為單位。先檢查既有功能是否足夠，避免不必要的新模組、過度設計與重複實作。

## 5. 學習協作：Mentor-first

預設不是「ChatGPT 提供完整程式碼 → 使用者貼上 → 跑 pytest」，而是：

1. 先以繁體中文（必要時 `/ELI5`）說明資料流、需求與關鍵觀念。
2. 用一個實際情境，請使用者先提出設計判斷、流程或少量核心程式碼。
3. 由 ChatGPT 做 Code Review、指出反例與取捨，涵蓋正確性、冪等性、可恢復性、效能、成本和維護性。
4. 以短而真實的 micro-practical 練習核心技能；由使用者嘗試部分實作，必要時才提供提示或示範。
5. **除非使用者明確要求完整程式碼、直接完成工作，或已卡住需要範例，否則不要預先交付整份可複製貼上的解答**。尊重使用者希望加快進度的要求。
6. 功能完成後，簡短確認使用者能否說明：「這段做什麼？失敗怎麼處理？為什麼這樣設計？」不要重複考同一題。

可視情況使用 A/B/C/D 選擇題，但不強制；優先提升獨立設計、Python／SQL 實作與除錯能力。

## 6. 風險導向測試，不追求測試數量

- **Unit tests**：覆蓋主要成功路徑與有實際價值的失敗／邊界情境；上傳介面優先用 Mock／注入 Client 做離線測試。
- **Integration tests**：在隔離環境確認與 R2／Neon 的真實交互；必須先確認目標、測試資料、權限與回復方式。禁止未經同意碰正式資料。
- **E2E tests**：在主要階段驗收資料從來源到目的地是否真的正常流動，不能用「單元測試全過」取代實際雲端驗證。
- 開發中只跑相關 targeted tests；**在完整功能／checkpoint 驗收時**再跑整套 regression suite。除非確有必要，不因每行修改都重跑全部測試。
- 如實區分 `passed`、`failed`、`skipped`，以及 Mock、真實服務、使用者提供的日誌與尚未驗證的假設。
- 每個測試都應能回答一項工程風險；不要為增加通過數或覆蓋所有想像情境而無限補測試。

## 7. 文件與 Git 規範

- GitHub `main` 是**已提交程式碼與文件的基準**，不是使用者本機尚未提交修改的替代品。
- 原 `docs/project_development_workflow.md` 的 GitHub 同步、Finding Before Rule、Observation／Hypothesis／Finding 區分、版本保護及 Git checkpoint 原則繼續適用。
- **如有衝突，本文件優先規範學習互動、任務粒度、測試節奏與 MVP 範圍**；舊流程中「一個最小問題」不可解讀成每個 `if` 都要 Commit。
- 新增已確認的 Data Profiling finding，仍要及時更新 `docs/data_profiling_findings.md`；與 Profiling 無關的 R2 開發不必硬塞進 findings 文件。
- R2／Neon／Pipeline 實際驗收後，應以 GitHub 最新版本為基礎追加 `docs/load_design.md`，保留原章節及使用者已整理的文字，不把未經驗證的內容寫成 `PASSED`。
- 完成同一功能的實作、測試與必要文件後，才決定 Commit／Push；**不以每個小檢查為 Commit 週期**。
- 不擅自修改正式資料庫／Bucket、啟用排程、破壞既有 Pipeline；外部寫入與部署需依使用者當下授權執行。

## 8. 每輪結束的簡短回顧

1. **做成什麼**：新增哪項資料工程能力。
2. **學會什麼**：至少一個設計決策或技術取捨。
3. **證據與限制**：測試、真實輸出、Commit，以及尚未驗證的部分。
4. **下一個主要交付物**：必須能推進 A／B／C。

**最重要的成功標準**不只是 `pytest passed` 或 GitHub 有 Commit，而是使用者能逐步獨立說明架構、設計失敗行為、修改程式碼，最後在面試中講清楚這個作品。

---

**給後續 Session 的入口**：`README.md` → `AGENTS.md` → 本文件 → `docs/project_development_workflow.md` → 當前程式碼／設計文件。注意：**GitHub 文件不會保證被 ChatGPT 新 Session 自動讀取**，應另外在 ChatGPT Project Instructions 固定要求開場閱讀與同步。
