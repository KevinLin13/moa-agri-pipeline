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

後續 Relationship Profiling 已確認這 86 筆為 `category_code` 與 `crop_name` 同時為 Null；詳細結果記錄於第 6 節。

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

確認 Rest representation 後，才將全部 records 分為：

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

### 6.1 Rest Market Code / Market Name Relationship

分析範圍：

```text
55 Rest records
```

NULL Pattern：

```text
market_code NULL=False, market_name NULL=False: 55
```

Relationship 結果：

```text
market_code → market_name
multiple mapping: 0

market_name → market_code
multiple mapping: 0
```

### Observation

在目前 55 筆 Rest records 中：

- `market_code` 沒有 Null。
- `market_name` 沒有 Null。
- 一個 `market_code` 只對應一個 `market_name`。
- 一個 `market_name` 也只對應一個 `market_code`。

### Current Decision

在目前七天資料中，Rest records 的 Market Relationship 可視為穩定的一對一。

但此結果仍只代表目前 Profiling 期間，不直接宣告所有歷史與未來 Rest records 永遠維持相同關係。

---

### 6.2 Non-Rest Category / Crop Name NULL Relationship

分析範圍：

```text
17,891 Non-Rest records
```

Relationship 結果：

```text
category_code NULL=False, crop_name NULL=False: 17,805
category_code NULL=True,  crop_name NULL=True:      86
```

沒有觀察到：

```text
category_code 有值、crop_name 為 NULL
```

或：

```text
category_code 為 NULL、crop_name 有值
```

的組合。

### Observation

目前 86 筆 Null records 中：

```text
category_code = NULL
crop_name     = NULL
```

是共同發生的。

進一步列出這 86 筆 records 後，確認：

- `crop_code` 仍有值。
- `market_code` 仍有值。
- `market_name` 仍有值。
- 相同的 Null pattern 會跨多個日期、crop_code 與市場重複出現。
- 例如 `FE800`、`FH010`、`FH011` 等 crop code 在不同日期與市場反覆出現相同的 Null pattern。

因此這不是單一 record 的偶發缺值，而是目前來源資料中可重複觀察到的資料表示方式。

官方 API 文件定義了 `種類代碼` 與 `作物名稱` 欄位，但沒有說明這兩個欄位一定 non-null，也沒有說明這類 Null record 的產生原因。

### Current Decision

目前不自行推導或填補：

```text
category_code
crop_name
```

因此 Transform 仍保留來源 `None`。

目前 Schema / Data Quality 設計應允許：

```text
category_code: str | None
crop_name:     str | None
```

但：

```text
crop_code
market_code
market_name
```

在目前資料中仍應視為必要識別資訊。

另外，目前「`category_code` 與 `crop_name` 同時 Null」只能視為目前觀察到的 pattern，不先建立 hard failure rule，避免把七天資料的現象誤當成永久資料契約。

---

### 6.3 Non-Rest Crop Code / Crop Name Relationship

NULL Pattern：

```text
crop_code NULL=False, crop_name NULL=False: 17,805
crop_code NULL=False, crop_name NULL=True:      86
```

Relationship 結果：

```text
crop_code → crop_name
multiple mapping: 0
```

表示在目前有 `crop_name` 的 records 中，沒有觀察到同一個 `crop_code` 對應多個不同 `crop_name`。

反方向：

```text
crop_name → crop_code
multiple mapping: 6
```

目前觀察到：

```text
其他
→ 91
→ OX1

小白菜-土白菜
→ LB1
→ LB12

蘿蔔-矸仔
→ SA3
→ SA32

繡球花-粉
→ FH464
→ IH464

繡球花-白
→ FH466
→ IH466

繡球花-藍
→ FH467
→ IH467
```

### Observation

`crop_name` 並不是唯一 identifier。

官方代碼表本身即存在不同 code 使用相同或高度相似顯示名稱的情況，例如：

- 不同類別可能使用「其他」作為名稱。
- `LB1`、`LB11`、`LB12` 在官方代碼表中具有更細的洗／未洗分類，但 API 實際顯示名稱未必保留完整細分類資訊。
- 本土與進口花卉可能具有不同 code，但顯示為相同花名，例如 `FH464` 與 `IH464`。

因此：

```text
crop_name
```

較適合作為 descriptive label，而不是唯一識別欄位。

### Current Decision

目前資料支持：

```text
crop_code
```

比：

```text
crop_name
```

更適合作為 Candidate Business Key 的作物識別組成欄位。

這不代表 `crop_code` 單獨就是 Business Key；Business Key uniqueness 仍需由完整欄位組合另外驗證。

---

### 6.4 Non-Rest Market Code / Market Name Relationship

NULL Pattern：

```text
market_code NULL=False, market_name NULL=False: 17,891
```

因此目前沒有 Market Code / Market Name 的 Null 問題。

Relationship 結果：

```text
market_code → market_name
multiple mapping: 3
```

目前觀察到：

```text
400
→ 台中市
→ 台中市場

514
→ 彰化市場
→ 溪湖鎮

800
→ 高雄市
→ 高雄市場
```

反方向：

```text
market_name → market_code
multiple mapping: 0
```

### Observation

排除 Rest records 後：

```text
market_code → market_name
```

仍然不是全域一對一。

官方市場代碼表將市場依蔬菜、水果、花卉分開列示，而且相同 `market_code` 可能在不同 category context 中重複出現。

例如：

```text
514
蔬菜 → 溪湖
花卉 → 彰化
```

另外，這次 86 筆 `category_code = NULL` records 中也觀察到：

```text
400 → 台中市
514 → 溪湖鎮
800 → 高雄市
```

這些 Null-category records 可能參與目前的 Market Name conflict，因此需要把 `category_code` context 納入分析，而不是直接把 `market_code` 當成全域市場 identifier。

### Current Decision

目前：

- 不使用 `market_name` 作為 Business Key。
- 不假設 `market_code` 在所有 category 中具有全域唯一的市場語意。
- 不自行統一 `台中市 / 台中市場`、`高雄市 / 高雄市場` 等來源名稱。
- 保留 API 原始提供的 `market_name`。
- 進一步驗證：

```text
(category_code, market_code) → market_name
```

由於目前有 86 筆 `category_code = NULL`，這批 records 必須維持獨立觀察，不能因 composite relationship 無法建立完整 key 就直接刪除或補值。

---

### 6.5 Non-Rest Category + Market Code / Market Name Relationship

為確認 `market_code → market_name` 的 3 組一對多是否來自不同 `category_code` context，進一步分析：

```text
category_code + market_code → market_name
```

Relationship 結果：

```text
NULL 組合：
category_code NULL=False, market_code NULL=False, market_name NULL=False: 17,805
category_code NULL=True, market_code NULL=False, market_name NULL=False:      86

同一 category_code + market_code 對應多個 market_name：0 組
```

### Observation

在 `category_code` 有值的 Non-Rest records 中：

```text
category_code + market_code → market_name
```

沒有觀察到一對多 conflict。

因此目前七天資料支持：

> `market_code` 單獨使用時不是跨 category 的全域唯一市場識別欄位；但加入 `category_code` 後，目前可以穩定對應唯一的 `market_name`。

這也說明先前觀察到的：

```text
400 → 台中市 / 台中市場
514 → 彰化市場 / 溪湖鎮
800 → 高雄市 / 高雄市場
```

不能直接視為 Market Mapping 錯誤，而應先考慮不同 `category_code` 下的市場語意。

另外仍有 86 筆：

```text
category_code = NULL
market_code != NULL
market_name != NULL
```

這些 records 無法形成完整的 `category_code + market_code` composite identifier，因此目前仍保留來源值，不自行補上 `category_code`。

### Current Decision

目前市場欄位的識別關係應理解為：

```text
category_code + market_code
→ market_name
```

而不是：

```text
market_code
→ market_name
```

因此：

- 不使用 `market_name` 作為 Business Key。
- 不把 `market_code` 視為跨 category 的全域唯一市場 identifier。
- 不自行修改或統一 API 提供的 `market_name`。
- 86 筆 `category_code = NULL` records 繼續保留，不自行推導 category。

---

### 6.6 Non-Rest Crop Code / Category Code Relationship

為判斷 `category_code` 是否需要納入 Non-Rest Candidate Business Key，進一步檢查：

```text
crop_code → category_code
```

NULL Pattern：

```text
crop_code NULL=False, category_code NULL=False: 17,805
crop_code NULL=False, category_code NULL=True:      86
```

在 `category_code` 有值的 records 中：

```text
同一 crop_code 對應多個 category_code：0 組
```

### Observation

目前資料顯示，只要 `category_code` 有值，沒有觀察到同一個 `crop_code` 跨不同 category 出現。

但這不能直接宣告所有 Non-Rest records 都存在完整的：

```text
crop_code → category_code
```

functional dependency，因為仍有 86 筆 `category_code = NULL` records。

針對這 86 筆 records 進一步檢查後：

```text
Distinct crop_codes with category_code NULL: 14
Crop codes also observed with non-NULL category: 0
Crop codes never observed with non-NULL category: 14
```

這 14 個 crop code 為：

```text
DF3
FE800
FE820
FE880
FH010
FH011
FH013
FU645
IC804
ID452
ID453
ID504
ID752
IH008
```

也就是說，在目前七天資料中，這 14 個 crop code 只出現在 `category_code = NULL` 的 records，沒有可由同期間其他 records 直接確認其 category 的觀察值。

### Current Decision

目前可以確認：

- 對 `category_code` 非 NULL 的 Non-Rest records，`crop_code → category_code` 沒有觀察到 conflict。
- 但不能將這個結果擴張為「所有 Non-Rest crop_code 都能由目前資料推得 category_code」。
- 不因 crop code 的外觀或其他推測自行補上這 86 筆 records 的 `category_code`。
- Transform 繼續保留來源提供的 `None`。
- Candidate Business Key 是否需要 `category_code`，仍應以完整 key 的實際 uniqueness 驗證，而不是只依賴這個 relationship 推論。

---

### 6.7 Current Identifier Relationship Conclusion

目前可以確認：

```text
Rest:
market_code ↔ market_name
→ 目前為一對一

Non-Rest:
category_code / crop_name
→ 86 筆共同 NULL

Non-Rest:
crop_code → crop_name
→ 目前無一對多

Non-Rest:
crop_name → crop_code
→ 6 組一對多

Non-Rest:
market_code → market_name
→ 3 組一對多

Non-Rest:
category_code + market_code → market_name
→ 0 組一對多（限完整 composite key records）

Non-Rest:
crop_code → category_code
→ 非 NULL category records 中 0 組一對多
→ 但 14 個 crop_code 在目前期間只出現 NULL category
```

因此：

- `crop_code` 目前比 `crop_name` 更適合作為作物 identifier。
- `crop_name` 不適合作為唯一識別欄位。
- `market_name` 不適合作為市場 Business Key。
- `market_code` 的市場語意需要搭配 category context 解讀。
- 在 `category_code` 有值時，`category_code + market_code` 可穩定對應 `market_name`。
- `category_code` 的 nullable 特性必須在 Business Key / Schema 設計中明確處理。
- 不能因目前 `crop_code → category_code` 無 conflict，就自行推導或補填缺失的 `category_code`。

目前 Identifier Relationship Profiling 已完成本階段需要回答的問題；Candidate Business Key 的實際 uniqueness 結果記錄於第 7 節。

---

## 7. Candidate Business Key / Duplicate Profiling

Identifier Relationship Profiling 完成後，分別對 Non-Rest 與 Rest records 驗證候選 Business Key 的 uniqueness。

目前 Business Key 的目的，是在 Pipeline 中提供可重複執行的 record identity 與 duplicate detection 依據。

這裡的結果仍只代表目前 Profiling 範圍，不等同於官方 API 已保證這些欄位組合永久唯一。

### 7.1 Non-Rest Candidate Business Key

候選欄位：

```text
trade_date
+ crop_code
+ market_code
```

實際結果：

```text
Rows:                  17,891
Unique keys:           17,891
Duplicate key groups:       0
Rows in duplicate groups:   0
Excess duplicate rows:      0
```

### Observation

在目前 2026-08-01 至 2026-08-07 的 17,891 筆 Non-Rest records 中：

```text
(trade_date, crop_code, market_code)
```

可以唯一識別每一筆 record，沒有觀察到 duplicate key group。

`category_code` 沒有加入這組 key，原因包括：

- `category_code` 在目前 Non-Rest records 中有 86 筆為 `NULL`。
- 這 86 筆 records 的 `crop_code`、`market_code` 仍有值。
- 實際 uniqueness 驗證顯示，不加入 `category_code` 時，17,891 筆 records 仍全部具有唯一 key。
- `market_name` 與 `crop_name` 為 descriptive label，不適合加入 Business Key。

### Current Decision

目前採用以下欄位組合作為 **Non-Rest v1 Candidate Business Key**：

```text
(trade_date, crop_code, market_code)
```

這是目前 Pipeline 設計的 candidate key，而不是宣告來源系統已提供永久不變的官方 primary key。

後續 Data Quality 階段應持續檢查這組 key 的 duplicate；若未來資料出現 violation，再重新調查來源資料語意與 key 設計。

---

### 7.2 Rest Candidate Business Key

Rest records 的：

```text
crop_code = "rest"
```

因此 `crop_code` 本身無法提供一般作物紀錄中的作物識別差異。

目前驗證的候選欄位為：

```text
trade_date
+ category_code
+ market_code
```

實際結果：

```text
Rows:                     55
Unique keys:              55
Duplicate key groups:      0
Rows in duplicate groups:  0
Excess duplicate rows:     0
```

### Observation

在目前 55 筆 Rest records 中：

```text
(trade_date, category_code, market_code)
```

可以唯一識別每一筆 Rest record，沒有觀察到 duplicate key group。

### Current Decision

目前採用以下欄位組合作為 **Rest v1 Candidate Business Key**：

```text
(trade_date, category_code, market_code)
```

Rest 與 Non-Rest 不強迫共用同一組 Business Key，因為兩類 records 的來源表示方式不同：

```text
Non-Rest
→ crop_code 表示實際作物

Rest
→ crop_code 固定為 "rest"
```

因此分開定義 Candidate Business Key，較符合目前實際資料語意。

---

### 7.3 Current Business Key Conclusion

目前 Profiling 範圍內：

```text
Non-Rest v1 Candidate Business Key
(trade_date, crop_code, market_code)

Rows:        17,891
Unique keys: 17,891
Duplicates:       0
```

```text
Rest v1 Candidate Business Key
(trade_date, category_code, market_code)

Rows:        55
Unique keys: 55
Duplicates:   0
```

### Current Decision

目前 Business Key / Duplicate Profiling 已完成本階段需要回答的問題。

後續 Profiling 已完成：

```text
Numeric Distribution Profiling
→ 第 8 節

Zero Pattern Profiling
→ 第 9 節
```

Numeric Distribution 與 Zero Pattern 的目前 findings 均已整理完成；下一階段進入 Data Quality Rule 的收斂與實作。

---

## 8. Non-Rest Numeric Distribution Profiling

### 8.1 Scope and Method

Numeric Distribution Profiling 只分析：

```text
17,891 Non-Rest records
```

Rest records 已知五個數值欄位皆為 `0.0`，因此不納入一般交易數值分布，以避免休市資料影響 Non-Rest distribution 的解讀。

分析欄位：

```text
upper_price
middle_price
lower_price
avg_price
volume
```

本階段使用的描述統計包括：

- finite / non-numeric / non-finite count
- zero count / zero rate
- mean / standard deviation
- coefficient of variation（CV）
- skewness
- min / Q1 / median / Q3 / max

其中：

```text
CV = standard deviation / mean
```

用來描述相對離散程度；`skewness` 用來描述分布的不對稱程度。兩者用途不同，不使用 CV 作為偏態判定指標。

Skewness 目前採用 population moment skewness，與目前使用 population standard deviation 的 descriptive profiling 定義保持一致。

---

### 8.2 Numeric Distribution Result

| Field | Finite | Non-numeric | Non-finite | Zero | Zero Rate | Mean | Std | CV | Skewness | Min | Q1 | Median | Q3 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `upper_price` | 17,891 | 0 | 0 | 48 | 0.27% | 96.70 | 90.60 | 0.94 | 2.57 | 0.00 | 35.00 | 69.80 | 130.00 | 1050.00 |
| `middle_price` | 17,891 | 0 | 0 | 48 | 0.27% | 79.23 | 78.01 | 0.98 | 2.73 | 0.00 | 26.00 | 52.00 | 108.00 | 1000.00 |
| `lower_price` | 17,891 | 0 | 0 | 54 | 0.30% | 64.16 | 72.15 | 1.12 | 3.13 | 0.00 | 18.00 | 38.00 | 87.00 | 1000.00 |
| `avg_price` | 17,891 | 0 | 0 | 48 | 0.27% | 79.55 | 77.87 | 0.98 | 2.72 | 0.00 | 26.40 | 52.80 | 108.50 | 1000.00 |
| `volume` | 17,891 | 0 | 0 | 46 | 0.26% | 1905.28 | 6846.21 | 3.59 | 16.56 | 0.00 | 54.00 | 267.50 | 1332.00 | 234587.00 |

---

### 8.3 Numeric Validity

五個 Non-Rest 數值欄位皆有：

```text
Finite values: 17,891
Non-numeric:         0
Non-finite:          0
```

### Observation

目前 2026-08-01 至 2026-08-07 的 Non-Rest records 中，未觀察到：

- 非數值型資料混入上述五個數值欄位。
- `NaN`。
- `+Infinity`。
- `-Infinity`。

這表示在目前 Profiling 範圍內，五個數值欄位的 numeric type / finite-value 狀態一致。

---

### 8.4 Zero Values

五個數值欄位皆存在少量 `0.0`：

```text
upper_price   48 rows  (0.27%)
middle_price  48 rows  (0.27%)
lower_price   54 rows  (0.30%)
avg_price     48 rows  (0.27%)
volume        46 rows  (0.26%)
```

### Observation

各欄位的 zero rate 目前皆約落在：

```text
0.26% ~ 0.30%
```

但這些數字只是各欄位的 marginal zero count。

因此不能僅由：

```text
upper_price = 48
middle_price = 48
avg_price = 48
```

直接推論這三個欄位的 `0` 一定發生在完全相同的 48 筆 records。

同樣地，也不能僅由：

```text
lower_price = 54
其他價格欄位 = 48
```

直接宣告額外 6 筆一定是「只有 lower_price = 0」。

不同數值欄位的 zero 是否共同出現在相同 records，已由第 9 節 Zero Pattern Profiling 直接驗證。

### Current Decision

目前不因單一數值欄位為 `0.0` 就判定 record invalid，也不把目前的 zero count 差異直接轉換成 Data Quality Rule。

---

### 8.5 Price Distribution Shape

四個價格欄位的 skewness：

```text
upper_price   2.57
middle_price  2.73
lower_price   3.13
avg_price     2.72
```

四個數值皆明顯大於 `0`，且 mean 亦高於 median：

```text
upper_price   mean 96.70  > median 69.80
middle_price  mean 79.23  > median 52.00
lower_price   mean 64.16  > median 38.00
avg_price     mean 79.55  > median 52.80
```

### Observation

目前資料顯示四個價格欄位皆具有明顯的正偏（右偏）與長右尾。

其中 `lower_price` 在四個價格欄位中具有目前最高的：

```text
CV       = 1.12
Skewness = 3.13
```

表示在目前資料範圍內，其相對離散程度與分布不對稱程度均高於其他三個價格欄位。

但目前不將任何固定 skewness 數值視為正式統計檢定的臨界值；skewness 在此僅作為 descriptive distribution measure。

另外，雖然最大價格：

```text
upper_price max  = 1050
middle_price max = 1000
lower_price max  = 1000
avg_price max    = 1000
```

明顯高於各欄位的 Q3，但目前資料同時混合不同作物、category 與市場，因此尚無證據將這些高值直接判定為錯誤資料。

---

### 8.6 Volume Distribution Shape

`volume` 的分布：

```text
Mean:       1905.28
Median:      267.50
Std:        6846.21
CV:            3.59
Skewness:     16.56
Q3:         1332.00
Max:      234587.00
```

### Observation

`volume` 呈現比價格欄位更強烈的正偏與長右尾。

其中：

```text
CV = 3.59
```

表示標準差約為平均數的 3.59 倍，反映目前資料具有很高的相對離散程度。

而：

```text
Skewness = 16.56
```

則直接顯示目前 `volume` 分布具有非常強烈的正偏與長右尾。

這兩個指標的意義應分開解讀：

```text
CV
→ relative variability

Skewness
→ distribution asymmetry
```

因此不能以：

```text
Std > Mean × 3
```

作為「嚴重右偏」的正式判定標準。

同時：

```text
Max = 234587
```

雖然遠高於 median 與 Q3，但這只能表示存在非常高的交易量 observations；目前沒有足夠依據判定這些 observations 為資料錯誤。

---

### 8.7 Current Numeric Distribution Decision

目前 Numeric Distribution Profiling 可以確認：

1. 五個 Non-Rest 數值欄位均為 finite numeric values，未觀察到 non-numeric、`NaN` 或 `±Infinity`。
2. 五個欄位皆存在少量 `0.0`，zero rate 約為 `0.26% ~ 0.30%`，但各欄位零值的 joint pattern 尚未由本階段確認。
3. 四個價格欄位均呈明顯正偏與長右尾，skewness 約為 `2.57 ~ 3.13`。
4. `volume` 的 `CV = 3.59`、`skewness = 16.56`，顯示相對離散程度很高，且具有非常強烈的正偏與長右尾。
5. 目前沒有足夠依據將高價格、高交易量或單一欄位的 `0.0` 直接判定為 invalid data。

### Current Decision

目前不根據整體：

```text
mean
standard deviation
CV
skewness
max
```

直接建立價格或交易量的固定上限 Hard Fail Rule。

這些統計量目前用於理解來源 distribution，而不是作為自動判定資料錯誤的 threshold。

Numeric Distribution Profiling 到此完成。

五個數值欄位在 record 層級的 joint zero patterns 已由第 9 節 Zero Pattern Profiling 進一步驗證。

Numeric Distribution Profiling 到此維持完成狀態。

---

## 9. Non-Rest Zero Pattern Profiling

### 9.1 Scope and Method

Zero Pattern Profiling 延續 Numeric Distribution 的範圍，只分析：

```text
17,891 Non-Rest records
```

分析欄位：

```text
upper_price
middle_price
lower_price
avg_price
volume
```

本階段的問題不是再次查看單一欄位的 zero count，而是直接回答：

> 五個數值欄位的 `0.0` 在 record 層級實際形成哪些共同 Zero Patterns？

因此針對每一筆 Non-Rest record，記錄上述五個欄位是否為 `0.0`，並統計各 joint pattern 的 count 與 rate。

在取得 pattern summary 後，再針對會影響後續 Data Quality 設計的特殊 pattern 進行 targeted inspection。

---

### 9.2 Joint Zero Pattern Result

實際結果：

```text
Rows:                   17,891
Distinct zero patterns:      4
Rows with no zero:       17,837
Rows with all fields zero:   46
```

| Zero Pattern | Rows | Rate |
|---|---:|---:|
| No zero fields | 17,837 | 99.70% |
| `upper_price + middle_price + lower_price + avg_price + volume = 0` | 46 | 0.26% |
| `lower_price = 0` only | 6 | 0.03% |
| `upper_price + middle_price + lower_price + avg_price = 0`, `volume != 0` | 2 | 0.01% |

### Observation

目前七天的 17,891 筆 Non-Rest records 中，只觀察到上述 4 種 Zero Pattern，沒有其他 joint zero combinations。

因此共有：

```text
46 + 6 + 2 = 54 rows
```

至少一個數值欄位為 `0.0`；其餘 17,837 筆五個數值欄位皆非零。

這 4 種 pattern 的總筆數為：

```text
17,837 + 46 + 6 + 2 = 17,891
```

與 Non-Rest row count 完全一致。

---

### 9.3 Relationship to Numeric Distribution Zero Counts

第 8 節 Numeric Distribution 中的 marginal zero counts 為：

```text
upper_price   48
middle_price  48
lower_price   54
avg_price     48
volume        46
```

Zero Pattern Profiling 現在可直接解釋這些 counts：

```text
upper_price
= 46 all-numeric-zero
+ 2 all-prices-zero-with-volume
= 48
```

```text
middle_price
= 46 + 2
= 48
```

```text
avg_price
= 46 + 2
= 48
```

```text
lower_price
= 46 all-numeric-zero
+ 6 lower-price-only-zero
+ 2 all-prices-zero-with-volume
= 54
```

```text
volume
= 46 all-numeric-zero
```

### Finding

因此，第 8 節只能由 marginal counts 提出的以下 hypotheses，現已由 record-level joint pattern 直接驗證：

- `upper_price`、`middle_price`、`avg_price` 的 48 筆 zero 確實發生在相同 48 筆 records。
- `lower_price` 額外的 6 筆 zero 確實都是 `lower_price` alone zero，而其他四個數值欄位皆非零。
- 48 筆四個價格欄位皆為 zero 的 records 中，46 筆 `volume = 0`，另有 2 筆 `volume > 0`。

在目前七天資料中，只要任一數值欄位為 `0.0`，`lower_price` 也一定為 `0.0`；但這只是目前 dataset 的 observed pattern，不視為永久資料契約。

---

### 9.4 Non-Rest All Numeric Fields Zero

Pattern：

```text
upper_price  = 0
middle_price = 0
lower_price  = 0
avg_price    = 0
volume       = 0
```

目前共：

```text
46 rows
0.26% of Non-Rest records
```

Targeted inspection 確認這 46 筆：

```text
category_code = N06
```

全部皆成立。

市場分布：

```text
market_code = 700 / 台南市場: 38 rows
market_code = 514 / 彰化市場:  3 rows
market_code = 400 / 台中市場:  3 rows
market_code = 105 / 台北市場:  1 row
market_code = 800 / 高雄市場:  1 row
```

其中台南市場占：

```text
38 / 46 ≈ 82.6%
```

這些 records 並非只出現在單一日期或單一作物。

目前觀察日期涵蓋：

```text
2026-08-03
2026-08-04
2026-08-05
2026-08-06
2026-08-07
```

且包含多個不同 `crop_code` / `crop_name`，例如玫瑰、洋桔梗、菊花、蘭花與進口花卉等。

### Observation

這 46 筆 records 具有明顯的 category / market concentration，且跨多個日期與作物重複出現，因此不能只依「數值全為 0」就判定為單筆偶發 corruption。

同時，這些 records 的：

```text
crop_code != "rest"
```

因此仍不能把：

```text
all numeric fields = 0
```

當作 Rest 判定條件。

目前來源資料本身不足以確認這類 Non-Rest All-Zero records 的實際 business meaning，例如是否代表沒有成交、沒有報價或其他市場狀態，因此不自行賦予未經證實的語意。

### Current Decision

目前：

- 保留這 46 筆 records 與來源提供的 `0.0`。
- 不因 Non-Rest All-Zero 就刪除、改寫或轉成 `NULL`。
- 不將此 pattern 設為 Hard Fail。
- 將 Non-Rest All-Zero 的 count / rate 視為後續 Warning / Monitoring 的候選品質訊號。

這仍是 Data Quality Rule Freeze 前的候選定位，不代表 warning threshold 已正式定義。

---

### 9.5 Lower Price Only Zero

Pattern：

```text
lower_price = 0

upper_price  != 0
middle_price != 0
avg_price    != 0
volume       != 0
```

目前共：

```text
6 rows
0.03% of Non-Rest records
```

Targeted inspection 結果：

```text
category_code = N04: 6 / 6
market_code   = 900: 6 / 6
market_name   = 屏東市: 6 / 6
```

6 筆資料分布於不同日期與不同作物：

| Trade Date | Crop Code | Crop Name | Upper | Middle | Lower | Avg | Volume |
|---|---|---|---:|---:|---:|---:|---:|
| 2026-08-05 | FM2 | 菜豆-青色 | 51.1 | 30.5 | 0.0 | 28.5 | 290.0 |
| 2026-08-04 | LA92 | 甘藍-進口 改良種 | 0.7 | 0.1 | 0.0 | 0.1 | 720.0 |
| 2026-08-02 | LI92 | 萵苣菜-進口 結球萵 | 13.2 | 6.1 | 0.0 | 6.1 | 658.0 |
| 2026-08-02 | SA3 | 蘿蔔-矸仔 | 2.5 | 1.2 | 0.0 | 1.2 | 1335.0 |
| 2026-08-02 | SD9 | 洋蔥-進口 | 6.7 | 5.0 | 0.0 | 4.4 | 240.0 |
| 2026-08-01 | SG6 | 大蒜-蒜仁 | 20.0 | 12.4 | 0.0 | 11.4 | 84.0 |

### Observation

這 6 筆全部集中於同一個 category / market context，但跨不同日期與不同作物重複出現。

同時，其他價格欄位與 `volume` 仍為正值，因此目前資料明確顯示：

```text
lower_price = 0
```

並不必然代表整筆交易紀錄無效。

### Current Decision

目前將 `lower_price = 0` only 視為 **Allowed observed pattern**：

- 保留來源值。
- 不改為 `NULL`。
- 不刪除 record。
- 不建立 `lower_price > 0` 的 Hard Fail Rule。

是否需要額外 monitoring，可在 Data Quality Rule Freeze 階段再評估；目前沒有證據支持將每一筆 lower-price-only-zero 都視為 warning。

---

### 9.6 All Prices Zero With Positive Volume

Pattern：

```text
upper_price  = 0
middle_price = 0
lower_price  = 0
avg_price    = 0
volume       > 0
```

目前共：

```text
2 rows
0.01% of Non-Rest records
```

兩筆 targeted inspection 結果：

| Trade Date | Category | Crop Code | Crop Name | Market Code | Market Name | Volume |
|---|---|---|---|---|---|---:|
| 2026-08-04 | N04 | FL2 | 豌豆-紅花 | 900 | 屏東市 | 8.0 |
| 2026-08-02 | N04 | FL2 | 豌豆-紅花 | 900 | 屏東市 | 84.0 |

兩筆 records 具有相同的：

```text
category_code = N04
crop_code     = FL2
crop_name     = 豌豆-紅花
market_code   = 900
market_name   = 屏東市
```

但發生於不同日期，且 `volume` 分別為 `8.0` 與 `84.0`。

### Observation

這個 pattern 在資料語意上值得注意，因為 record 同時表示：

```text
volume > 0
```

但四個價格欄位全部為 `0.0`。

然而，同一 crop / market context 在不同日期重複出現相同 pattern，因此目前不能只根據直覺就宣告為 corrupted data。

目前來源文件與 dataset 本身也不足以確認其實際 business meaning。

### Current Decision

目前：

- 保留兩筆來源 records 與所有原始數值。
- 不自行把價格改成 `NULL` 或其他推定值。
- 不刪除 records。
- 不將此 pattern 設為 Hard Fail。
- 將 `all prices = 0` 且 `volume > 0` 視為後續 Warning candidate。

實際 warning rule 與呈現方式留待 Data Quality Rule Freeze 階段正式定義。

---

### 9.7 Data Quality Boundary for Observed Zero Patterns

本輪 Zero Pattern Profiling 進一步確認一個工程邊界：

```text
Data Quality detection
!=
source data modification
```

對來源中看起來特殊或可疑的數值狀態，Data Engineering pipeline 可以同時做到：

```text
保留 API 原始值
+
產生品質訊號 / warning / monitoring metric
```

因此，觀察到特殊 Zero Pattern 不代表必須：

```text
刪除 record
把 0 改成 NULL
自行補值
重新計算來源價格
```

在沒有官方定義或已確認 business rule 的情況下，這些處理反而可能改變來源資料語意與 lineage。

### Current Decision

目前 pipeline 的原則維持：

- Raw layer 忠實保存 API response。
- Transform 只做已定義的欄位與型別標準化，不因 zero pattern 自行改寫業務值。
- Data Quality 可以偵測、統計、標記或告警特殊 pattern，但偵測本身不等於刪除或修正資料。
- Hard Fail 應保留給有明確資料契約或工程必要性的 violation，而不是只因數值看起來異常。

---

### 9.8 Current Zero Pattern Decision

目前 2026-08-01 至 2026-08-07 的 Non-Rest Zero Pattern Profiling 可以確認：

1. 17,891 筆 Non-Rest records 中只觀察到 4 種 joint zero patterns。
2. 17,837 筆（99.70%）五個數值欄位皆非零。
3. 46 筆（0.26%）五個數值欄位全部為 zero；全部為 `N06`，其中 38 筆集中於台南市場。
4. 6 筆（0.03%）只有 `lower_price = 0`；全部集中於 `N04 / market_code 900 / 屏東市`，且其他價格與交易量仍為正值。
5. 2 筆（0.01%）四個價格皆為 zero 但 `volume > 0`；兩筆皆為 `N04 / FL2 / 豌豆-紅花 / market_code 900 / 屏東市`，並發生於不同日期。
6. 目前沒有任何一種 Non-Rest Zero Pattern 有足夠證據應直接刪除、改值或設定為 Hard Fail。

目前候選工程定位：

| Pattern | Candidate Quality Treatment | Data Treatment |
|---|---|---|
| Non-Rest All Numeric Zero | Warning / Monitoring candidate | Preserve |
| Lower Price Only Zero | Allowed observed pattern | Preserve |
| All Prices Zero + Positive Volume | Warning candidate | Preserve |

上述 quality treatment 尚屬 Data Quality Rule Freeze 前的候選分類；正式 rule、severity、輸出格式與 monitoring threshold 仍需在下一階段定義。

Zero Pattern Profiling 到此完成。

下一階段：

```text
Data Quality Rule Freeze
→ Data Quality implementation
```

