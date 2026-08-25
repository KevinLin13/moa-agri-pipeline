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

這些 Null-category records 可能參與目前的 Market Name conflict，因此下一步必須把 `category_code` context 納入分析，而不是直接把 `market_code` 當成全域市場 identifier。

### Current Decision

目前：

- 不使用 `market_name` 作為 Business Key。
- 不假設 `market_code` 在所有 category 中具有全域唯一的市場語意。
- 不自行統一 `台中市 / 台中市場`、`高雄市 / 高雄市場` 等來源名稱。
- 保留 API 原始提供的 `market_name`。
- 下一步驗證：

```text
(category_code, market_code) → market_name
```

以確認在 `category_code` 有值的 Non-Rest records 中，加入 category context 後 Market Relationship 是否恢復為一對一。

由於目前有 86 筆 `category_code = NULL`，這批 records 必須維持獨立觀察，不能因 composite relationship 無法建立完整 key 就直接刪除或補值。

---

### 6.5 Current Identifier Relationship Conclusion

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
```

因此：

- `crop_code` 目前比 `crop_name` 更適合作為作物 identifier。
- `market_name` 不應作為市場 Business Key 欄位。
- `market_code` 的語意需要搭配 category context 再確認。
- `category_code` 的 nullable 特性會影響後續 Market Relationship 與資料模型設計。

Identifier Relationship 尚未完全結束；下一個必要驗證是：

```text
(category_code, market_code) → market_name
```