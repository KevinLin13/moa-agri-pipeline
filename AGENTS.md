# AGENTS.md — moa-agri-pipeline

> 這是同時追求**資料工程作品交付**與**使用者獨立工程能力**的學習專案。

## 新 Session / AI Agent 必讀

1. `docs/learning_execution_framework.md`：**現行的學習與執行規範**，優先於舊流程中「每個微小問題各做一輪」的解讀。
2. `docs/project_development_workflow.md`：GitHub 同步、Profiling／Finding、測試與 Git checkpoint 的既有規範。
3. GitHub 最新 `main`、當前階段設計文件、相關程式碼與測試：不得只憑過去對話猜測版本。

## 工作方式

- 先交代目前進度、這次功能的 **Why／How／Validation** 與完成界線。
- 以「可驗收的完整功能」規劃工作，而不是每個 `if` 都設一個 checkpoint；測試依真實工程風險安排。
- **預設 Mentor-first**：讓使用者先練習設計與一部分實作，再提供 Code Review；明確要求完整程式碼時可以直接提供。
- 主線：**A 完成 R2 Snapshot Upload → B 整合 Pipeline／Neon → C GitHub Actions 端到端驗收**；避免無目的增加支線。
- 區分已提交、僅本機、Mock、真實雲端及歷史測試，不得宣稱未實際驗證的成果。
- 保留使用者已整理的文件內容，不擅自操作正式 Bucket／資料庫／排程。

**完整操作細節以 `docs/learning_execution_framework.md` 為準。**
