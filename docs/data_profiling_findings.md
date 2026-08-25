# Data Profiling Findings

## 1. Purpose

本文件記錄 `moa-agri-pipeline` 在 Data Profiling 階段對農業部農產品交易行情資料所得到的觀察結果、推導過程與目前決策。

Profiling 的目的為：

- 理解來源資料的實際結構、型別與分布。
- 找出特殊紀錄與可能的資料例外。
- 在建立 Candidate Business Key 前，先理解識別欄位之間的關係。
- 為後續 Transform、Data Quality Rule、Load Schema 與資料模型設計提供依據。

本文件記錄的是 **observation（觀察結果）**、**decision（目前決策）** 與 **pending validation（待驗證事項）**。

除非特別註明，這些結果不代表所有歷史或未來資料永遠成立，也不代表所有觀察都已正式成為 Data Quality Rule。

---

## 2. Data Source and Profiling Scope

資料來源：

- 農業部農業資料開放平臺
- Dataset：EIR030 農產品交易行情

主要分析期間：

```text
2026-08-01 ~ 2026-08-07
```

本期間取得的原始資料：

```text
Total rows: 17,946
Fields:     11
```

官方 API 文件說明部分市場可能存在休市情形，但未定義 API 會如何表示休市紀錄。

本文件中的結論原則上只代表目前 2026-08-01 至 2026-08-07 所觀察到的資料特性。

---

## 3. Structure Profiling

### 3.1 Raw Data Profile

Raw Data：

```text
Rows:   17,946
Fields: 11
Record types: dict = 17,946
```

11 個欄位皆沒有 Missing Key。

Raw Data 中觀察到：

```text
作物名稱 Null: 86 (0.48%)
種類代碼 Null: 86 (0.48%)
```

其他欄位目前未觀察到 Null。

五個數值欄位：

```text
上價
中價
下價
平均價
交易量
```

在 Raw Data 中皆已為 `float`。

數值範圍：

| 欄位 | Min | Max |
|---|---:|---:|
| 上價 | 0.0 | 1050.0 |
| 中價 | 0.0 | 1000.0 |
| 下價 | 0.0 | 1000.0 |
| 平均價 | 0.0 | 1000.0 |
| 交易量 | 0.0 | 234587.0 |

### Observation

Structure Profiling 顯示五個數值欄位的最小值皆為 `0.0`。

這代表來源資料確實存在零值，但此時尚不能判斷：

- 這些 `0` 是否出現在同一批 records。
- `0` 是否代表休市。
- `0` 是否代表無交易。
- `0` 是否為合法的一般交易資料。
- 不同 Zero Pattern 是否具有不同資料意義。

因此需要進一步檢查多個數值欄位共同為 `0` 的 records。

另外，`作物名稱` 與 `種類代碼` 各有 86 筆 Null，但僅從欄位摘要無法確認兩者是否完全發生在同一批 records。

此部分需由後續 Relationship Profiling 再確認。

---

### 3.2 Transformed Data Profile

Transform 後：

```text
Rows:   17,946
Fields: 11
Record types: dict = 17,946
```

主要型別標準化結果：

```text
trade_date
str → datetime.date

upper_price
middle_price
lower_price
avg_price
volume
→ float
```

Transform 後 Null 狀況仍為：

```text
category_code Null: 86 (0.48%)
crop_name Null:     86 (0.48%)
```

表示目前 Transform 沒有自行填補或刪除來源中的 Null。

### Decision

Transform 階段目前維持：

- 欄位名稱標準化。
- 日期型別標準化。
- 數值型別標準化。
- 不自行填補來源 Null。
- 不因為數值為 `0` 就刪除資料。

---

## 4. Initial All-Zero Record Discovery

### 4.1 Why This Inspection Was Performed

Structure Profiling 已經確認：

```text
upper_price min  = 0.0
middle_price min = 0.0
lower_price min  = 0.0
avg_price min    = 0.0
volume min       = 0.0
```

官方文件又指出部分市場存在休市情形，但沒有說明 API 如何表示休市。

因此下一步不是直接搜尋 `"休市"` 或 `"rest"`，而是先從數值分布自然產生問題：

> 是否存在五個數值欄位同時為 `0.0` 的 records？這些 records 實際長什麼樣？

在尚未進行 Rest / Non-Rest 分流前，針對全部 17,946 筆 Transform 後 records 檢查：

```text
upper_price  = 0.0
middle_price = 0.0
lower_price  = 0.0
avg_price    = 0.0
volume       = 0.0
```

結果：

```text
All-zero rows: 101
```

---

### 4.2 Two Types of All-Zero Records

檢視 101 筆 All-Zero records 後，發現至少存在兩種不同型態。

#### Type A：特殊休市紀錄

其中 55 筆具有：

```text
crop_code = "rest"
crop_name = "休市"
```

而且五個數值欄位皆為：

```text
0.0
```

#### Type B：一般作物紀錄

另外 46 筆：

- 具有一般的 `crop_code`。
- 具有一般的 `crop_name`。
- 並非 `crop_code = "rest"`。
- 五個數值欄位仍全部為 `0.0`。

在目前 2026-08-01 至 2026-08-07 的資料中，這 46 筆皆為：

```text
category_code = N06
```

其中：

```text
market_code = 700 / 台南市場
38 rows
```

占 46 筆 Non-Rest All-Zero records 的約：

```text
82.6%
```

其餘目前觀察到：

```text
market_code = 514: 3 rows
market_code = 400: 3 rows
market_code = 105: 1 row
market_code = 800: 1 row
```

### Observation

因此：

```text
All numeric fields = 0
```

不能直接推論：

```text
Rest record
```

因為 Non-Rest records 同樣可能出現五個數值欄位皆為 `0.0`。

目前七天資料顯示，Non-Rest All-Zero records 全部出現在 `N06`，且高度集中於台南市場。

但分析期間只有七天，因此目前不能推論：

- 只有 N06 才會出現 All-Zero。
- 只有台南市場才會出現 All-Zero。
- 所有歷史與未來資料皆維持相同模式。

---

## 5. Rest Record Identification and Split

### 5.1 Rest Representation Observed in the Source

經過 Initial All-Zero Record Inspection 後，確認來源 API 中存在一類特殊紀錄：

```text
crop_code = "rest"
crop_name = "休市"
```

在目前期間共：

```text
55 rows
```

所有這 55 筆 Rest records 的：

```text
upper_price
middle_price
lower_price
avg_price
volume
```

皆為：

```text
0.0
```

Rest records 涵蓋的 `category_code`：

```text
N04
N05
N06
```

目前涵蓋 20 個市場名稱：

```text
三重區
南投市
台中市
台北一
台北二
台北市場
台南市場
台東市
宜蘭市
屏東市
東勢鎮
板橋區
桃農
永靖鄉
溪湖鎮
花蓮市
西螺鎮
豐原區
高雄市
鳳山區
```

---

### 5.2 Split Result

確認 Rest representation 後，將全部 records 分為：

```text
Total rows:     17,946
Rest rows:          55
Non-Rest rows:  17,891
```

目前 Rest 判定使用：

```text
crop_code = "rest"
```

`crop_name = "休市"` 可作為 Rest record 的一致性驗證資訊。

### Decision

不使用：

```text
all numeric fields = 0
```

作為 Rest 判定條件。

原因是目前已有 46 筆 Non-Rest records 同樣符合此 Zero Pattern。

後續以下 Profiling 原則上應將 Rest 與 Non-Rest 分開：

- Identifier Relationship。
- Candidate Business Key。
- Duplicate / Uniqueness。
- Numeric Distribution。
- Zero Pattern。
- 後續 Data Quality Rule 評估。

---

## 6. Identifier Relationship Profiling

### 6.1 Methodology Correction

先前曾直接使用全部 Transform 後 records 進行：

```text
market_code ↔ market_name
crop_code ↔ crop_name
```

Relationship Profiling。

後續確認 Rest records 與一般交易 records 應分開處理後，發現這個方法存在 scope 問題。

例如目前 All-Zero Inspection 已直接觀察到：

```text
Non-Rest:
market_code = 400
market_name = 台中市場

Rest:
market_code = 400
market_name = 台中市
```

以及：

```text
Non-Rest:
market_code = 514
market_name = 彰化市場

Rest:
market_code = 514
market_name = 溪湖鎮
```

因此，如果把 Rest 與 Non-Rest 混在一起分析：

```text
market_code → market_name
```

會產生看似一對多的 Relationship。

這不能直接用來判斷 Non-Rest 的 `market_code` 是否適合作為市場 identifier。

### Decision

先前基於全部 Transform records 得到的 Market Relationship conflict：

```text
400 → 台中市 / 台中市場
514 → 溪湖鎮 / 彰化市場
800 → 高雄市 / 高雄市場
```

暫不作為 Non-Rest Identifier Relationship 的最終 finding。

Relationship Profiling 應重新使用分流後資料執行。

---

### 6.2 Planned Non-Rest Relationship Profiling

下一步針對：

```text
17,891 Non-Rest records
```

重新確認：

#### Category / Crop Name Null Pattern

```text
category_code ↔ crop_name
```

目的：

- 確認 `category_code` 與 `crop_name` 的 Null 是否共同發生。
- 釐清 Structure Profiling 中兩欄各 86 筆 Null 的實際關係。

#### Crop Identifier Relationship

```text
crop_code ↔ crop_name
```

目的：

- 檢查一個 `crop_code` 是否對應多個 `crop_name`。
- 檢查一個 `crop_name` 是否可能對應多個 `crop_code`。
- 評估 `crop_code` 是否比 `crop_name` 更適合作為 identifier。

#### Market Identifier Relationship

```text
market_code ↔ market_name
```

目的：

- 確認排除 Rest 後，一個 `market_code` 是否仍對應多個 `market_name`。
- 評估 `market_code` 是否適合作為 Non-Rest Candidate Business Key 的市場識別欄位。

---

### 6.3 Planned Rest Relationship Profiling

Rest records 另外分析：

```text
market_code ↔ market_name
```

不與 Non-Rest records 混合。

目前 Rest 的：

```text
crop_code = "rest"
crop_name = "休市"
```

已具有固定特殊語意，因此目前沒有必要把 Rest 的 `crop_code ↔ crop_name` 當作一般作物 identifier relationship 重新評估。

### Current Status

Identifier Relationship 尚待依新的 Rest / Non-Rest scope 重新執行。

因此目前不先宣告：

```text
Non-Rest market_code → market_name
```

一定為一對一。

該結論必須由重新執行後的資料結果決定。

---

## 7. Candidate Business Keys

目前已曾針對分流後的 Rest / Non-Rest records 執行 Duplicate / Uniqueness Profiling。

這些 uniqueness 結果仍可保留，但在 Identifier Relationship 重新確認完成前，目前將 Candidate Business Key 視為 **provisional（暫定）**。

---

### 7.1 Non-Rest Records

目前候選組合：

```text
trade_date + crop_code + market_code
```

Profiling 結果：

```text
Rows:                  17,891
Unique keys:           17,891
Duplicate key groups:       0
Rows in duplicate groups:   0
Excess duplicate rows:      0
```

### Observation

在 2026-08-01 至 2026-08-07：

```text
trade_date + crop_code + market_code
```

具有完整 uniqueness，可唯一識別目前全部 17,891 筆 Non-Rest records。

### Current Decision

目前保留為：

```text
Provisional Candidate Business Key
```

但在最終確認前，仍需完成前一節：

```text
crop_code ↔ crop_name
market_code ↔ market_name
```

的 Non-Rest Relationship Profiling。

另外，未來仍需要使用更長日期區間持續驗證 uniqueness。

---

### 7.2 Rest Records

目前候選組合：

```text
trade_date + category_code + market_code
```

Profiling 結果：

```text
Rows:                     55
Unique keys:              55
Duplicate key groups:      0
Rows in duplicate groups:  0
Excess duplicate rows:     0
```

### Observation

在目前七天資料中，此組欄位可唯一識別全部 55 筆 Rest records。

### Current Decision

Rest records 與 Non-Rest records 具有不同資料語意，因此不使用相同 Candidate Business Key。

目前保留：

```text
trade_date + category_code + market_code
```

作為：

```text
Provisional Rest Record Key
```

---

## 8. Numeric Distribution — Non-Rest Records

確認 Rest representation 並完成分流後，數值分布只針對：

```text
17,891 Non-Rest records
```

不包含 55 筆 Rest records。

### 8.1 Data Type / Finite Value Check

五個數值欄位：

```text
upper_price
middle_price
lower_price
avg_price
volume
```

全部 17,891 筆皆為 finite numeric values。

目前沒有觀察到：

```text
Non-numeric value
NaN
Infinity
-Infinity
```

---

### 8.2 Upper Price

```text
Zero:      48 (0.27%)
Mean:      96.70
Std:       90.60
Min:        0.00
Q1:        35.00
Median:    69.80
Q3:       130.00
Max:     1050.00
```

---

### 8.3 Middle Price

```text
Zero:      48 (0.27%)
Mean:      79.23
Std:       78.01
Min:        0.00
Q1:        26.00
Median:    52.00
Q3:       108.00
Max:     1000.00
```

---

### 8.4 Lower Price

```text
Zero:      54 (0.30%)
Mean:      64.16
Std:       72.15
Min:        0.00
Q1:        18.00
Median:    38.00
Q3:        87.00
Max:     1000.00
```

---

### 8.5 Average Price

```text
Zero:      48 (0.27%)
Mean:      79.55
Std:       77.87
Min:        0.00
Q1:        26.40
Median:    52.80
Q3:       108.50
Max:     1000.00
```

---

### 8.6 Volume

```text
Zero:          46 (0.26%)
Mean:        1905.28
Std:         6846.21
Min:            0.00
Q1:            54.00
Median:       267.50
Q3:          1332.00
Max:       234587.00
```

---

## 9. Zero Pattern — Non-Rest Records

針對 17,891 筆 Non-Rest records，分析：

```text
upper_price
middle_price
lower_price
avg_price
volume
```

五個欄位的 Zero Pattern。

結果：

| Zero Pattern | Rows | Rate |
|---|---:|---:|
| 無任何 0 值 | 17,837 | 99.70% |
| 五個數值欄位皆為 0 | 46 | 0.26% |
| 僅 `lower_price = 0` | 6 | 0.03% |
| 四種價格皆為 0，但 `volume > 0` | 2 | 0.01% |

總計：

```text
17,837 + 46 + 6 + 2 = 17,891
```

---

### 9.1 All Numeric Fields Zero

```text
Rows: 46
```

目前七天資料中：

```text
category_code = N06
46 / 46
```

市場分布目前觀察到：

```text
market_code = 700: 38
market_code = 514:  3
market_code = 400:  3
market_code = 105:  1
market_code = 800:  1
```

### Observation

Non-Rest All-Zero pattern 並非隨機平均分布。

目前：

- 全部出現在 N06。
- 約 82.6% 出現在 market_code=700 / 台南市場。

但因目前只分析七天資料，因此不將此模式寫成 Data Quality hard rule。

---

### 9.2 Lower Price Only Zero

```text
Rows: 6
```

目前觀察到：

```text
category_code = N04
market_code = 900
market_name = 屏東市
```

作物並不完全相同。

### Observation

`lower_price = 0` 並不必然代表整筆行情沒有交易或資料失效。

因此目前不建立：

```text
lower_price > 0
```

的 hard rule。

---

### 9.3 All Prices Zero With Positive Volume

```text
Rows: 2
```

目前兩筆皆為：

```text
category_code = N04
market_code = 900
market_name = 屏東市
crop_code = FL2
```

且：

```text
upper_price  = 0
middle_price = 0
lower_price  = 0
avg_price    = 0
volume       > 0
```

### Observation

來源資料確實可能出現：

```text
prices = 0
volume > 0
```

因此價格為 `0` 不能直接判定為 invalid data。

---

### 9.4 Current Zero-Value Decision

目前 Data Profiling 支持：

```text
numeric value >= 0
```

而不支持：

```text
numeric value > 0
```

因此目前：

- `0` 保留為合法來源值。
- 不因 `0` 自動刪除 record。
- 不把 All-Zero 自動視為 Rest。
- 不把 Non-Rest All-Zero 自動視為 invalid data。
- 若未來需要，可將特殊 Zero Pattern 作為 warning / monitoring 指標，而非立即 hard fail。

---

## 10. Price and Volume Distribution Findings

### 10.1 Price Distribution

四個價格欄位均呈右尾分布特徵。

以 `avg_price` 為例：

```text
Mean:     79.55
Median:   52.80
Q3:      108.50
Max:    1000.00
```

平均數高於中位數，且最大值遠高於第三四分位數。

### Current Decision

目前不將高價格直接視為資料錯誤。

不同種類農產品的價格尺度可能具有實質差異，因此目前不設定固定價格上限。

是否進一步分析高價格紀錄，需以該分析是否會影響：

- Schema。
- Data Quality。
- Storage。
- Monitoring。

作為判斷依據。

---

### 10.2 Volume Distribution

`volume` 呈高度右偏：

```text
Mean:       1905.28
Median:      267.50
Q3:         1332.00
Max:      234587.00
```

少量大型交易量明顯拉高平均數與標準差。

### Current Decision

目前不將：

```text
234587
```

或其他大型交易量直接判定為異常。

在沒有明確 domain rule 或來源文件依據前，不設定任意交易量上限。

---

## 11. Current Data Engineering Implications

目前已確認、可供後續 Pipeline 設計參考的事項：

### Schema / Nullable

- `category_code` 在來源中可能為 `None`。
- `crop_name` 在來源中可能為 `None`。
- Transform 應保留來源 Null，不自行推導或填值。

### Rest Handling

- Rest 是來源中的特殊 record type。
- 目前可由 `crop_code = "rest"` 識別。
- `crop_name = "休市"` 可作為一致性驗證。
- Rest 的全部數值為 `0.0`。
- 但 All-Zero 不能用來判斷 Rest。

### Numeric Quality

目前支持：

```text
numeric value >= 0
```

目前不支持：

```text
numeric value > 0
```

### Candidate Keys

目前暫定：

```text
Non-Rest:
trade_date + crop_code + market_code

Rest:
trade_date + category_code + market_code
```

但 Non-Rest identifier relationship 尚需在正確 scope 下重新驗證。

---

## 12. Resolved Questions

目前已回答：

1. 五個數值欄位是否存在 `0`？
   - 有。

2. 是否存在五個數值欄位全部為 `0` 的 records？
   - 有，共 101 筆（未分流前）。

3. All-Zero 是否等同 Rest？
   - 否。

4. 目前如何辨識 Rest？
   - `crop_code = "rest"`。

5. Rest records 有幾筆？
   - 55 筆。

6. Non-Rest records 是否也會 All-Zero？
   - 會，共 46 筆。

7. 目前 Non-Rest All-Zero 是否只出現在 N06？
   - 在目前七天資料中是，但不能推論所有歷史或未來資料皆如此。

8. `numeric value > 0` 是否適合作為目前 Data Quality Rule？
   - 不適合。

9. Rest / Non-Rest 後續是否應分開 Profiling？
   - 是。

---

## 13. Pending Validation and Deferred Questions

### 13.1 Next Required Profiling

目前下一個必要步驟是重新執行分流後的 Identifier Relationship Profiling：

```text
Non-Rest:
category_code ↔ crop_name
crop_code ↔ crop_name
market_code ↔ market_name

Rest:
market_code ↔ market_name
```

完成後應立即更新本文件，再重新確認 Candidate Business Key 的設計依據。

---

### 13.2 Deferred Questions

目前暫不繼續深入處理：

1. 高價格紀錄集中在哪些 category / crop / market？
2. `volume` 極端值的實際商業背景為何？
3. 為什麼 N06 All-Zero records 高度集中於台南市場？
4. 為什麼部分 N04 records 會出現價格為 0 但 `volume > 0`？

這些問題目前不影響已知的基本 Schema、Rest split 與零值合法性判斷，因此先保留為 Deferred Questions。

另外：

5. Candidate Business Key 在更長日期區間是否仍保持唯一？

此問題未來在進入正式 Load / Upsert 設計前仍需持續驗證。

---

## 14. Next Step

目前 Data Profiling 尚未完全結束。

下一步：

```text
Structure Profiling
        ↓
Initial All-Zero Inspection
        ↓
Rest Representation Confirmed
        ↓
Rest / Non-Rest Split
        ↓
▶ Identifier Relationship Profiling
        ↓
Update data_profiling_findings.md
        ↓
Reconfirm Candidate Business Keys
        ↓
Finalize Data Quality Rules
```

在 Identifier Relationship 重新驗證完成前：

- 不使用舊的 mixed Rest / Non-Rest Relationship 結果作為最終結論。
- 不新增新的 Candidate Key 欄位。
- 不修改來源名稱。
- 不因 `0` 刪除資料。
- 不宣告 Profiling 階段完成。
