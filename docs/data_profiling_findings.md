# Data Profiling Findings

## 1. Purpose

本文件記錄 `moa-agri-pipeline` 在 Data Profiling 階段對農業部農產品交易行情資料所得到的觀察結果。

Profiling 的目的為：

* 理解來源資料的實際結構與分布。
* 找出特殊紀錄與可能的資料例外。
* 驗證候選 Business Key。
* 為後續 Transform、Data Quality Rule 與資料模型設計提供依據。

本文件記錄的是 **observation（觀察結果）**，不代表所有觀察都已經正式成為 Data Quality Rule。

---

## 2. Profiling Scope

資料來源：

* 農業部農業資料開放平臺
* Dataset：EIR030 農產品交易行情

主要分析期間：

```text
2026-08-01 ~ 2026-08-07
```

本期間取得：

```text
Total rows:     17,946
Non-Rest rows: 17,891
Rest rows:         55
```

因此，本文件中的結論原則上只代表目前分析期間所觀察到的資料特性，不直接推論為所有歷史或未來資料永遠成立。

---

## 3. Special Rest Records

### Observation

資料中存在特殊的休市紀錄：

```text
crop_code = "rest"
crop_name = "休市"
```

2026-08-01 至 2026-08-07 共發現：

```text
55 rows
```

休市紀錄涵蓋的 `category_code`：

```text
N04
N05
N06
```

涵蓋 20 個市場名稱：

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

所有休市紀錄的以下數值欄位皆為 `0.0`：

```text
upper_price
middle_price
lower_price
avg_price
volume
```

### Decision

休市紀錄與一般有交易的行情紀錄具有不同的資料意義。

因此後續進行：

* 一般交易價格分布
* 交易量分布
* Business Key 分析
* Zero Value 分析

時，應將 Rest 與 Non-Rest records 分開處理。

---

## 4. Candidate Business Keys

### 4.1 Non-Rest Records

候選 Business Key：

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

在目前分析期間：

```text
trade_date + crop_code + market_code
```

可以唯一識別全部 17,891 筆 Non-Rest records。

### Decision

目前將此組欄位視為：

```text
Candidate Business Key
```

尚不直接宣告為永久 Primary Key 或適用於所有歷史資料。

未來應使用更長日期區間持續驗證其唯一性。

---

### 4.2 Rest Records

候選 Rest Record Key：

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

在目前分析期間，此組欄位可以唯一識別全部 55 筆休市紀錄。

### Decision

Rest records 不使用 Non-Rest 的 Business Key 規則，而另外使用：

```text
trade_date + category_code + market_code
```

作為目前的候選識別鍵。

---

## 5. Market Code / Market Name Relationship

Profiling 發現部分市場代號不是單純的一對一名稱關係。

目前觀察到的例子包含：

```text
(category_code=N06, market_code=400)
→ 台中市
→ 台中市場

(category_code=N06, market_code=514)
→ 彰化市場
→ 溪湖鎮

(category_code=N06, market_code=800)
→ 高雄市
→ 高雄市場
```

### Observation

因此：

```text
market_code → market_name
```

不能直接假設在所有情況下都是一對一。

即使加入 `category_code`，目前資料中仍觀察到名稱衝突。

### Decision

目前不將 `market_name` 納入 Business Key，也不自行修正或統一這些名稱。

在確認來源命名規則以前，保留 API 原始提供的名稱。

---

## 6. Numeric Distribution — Non-Rest Records

以下統計只針對：

```text
17,891 Non-Rest records
```

不包含 55 筆休市紀錄。

### 6.1 Data Type / Finite Value Check

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

### 6.2 Upper Price

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

### 6.3 Middle Price

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

### 6.4 Lower Price

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

### 6.5 Average Price

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

### 6.6 Volume

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

## 7. Numeric Distribution Findings

### Observation: Zero Values

即使已經排除 Rest records，Non-Rest records 中仍存在少量 `0`：

```text
upper_price:  48
middle_price: 48
lower_price:  54
avg_price:    48
volume:       46
```

各欄位 Zero Count 不完全相同，因此目前不能假設所有零值都來自完全相同的一批 records。

### Current Decision

目前仍允許：

```text
numeric value >= 0
```

尚無足夠證據將規則修改為：

```text
numeric value > 0
```

下一階段需進一步分析 Non-Rest records 的 Zero Pattern。

---

### Observation: Price Distribution

四個價格欄位皆呈現明顯右尾特徵。

例如 `avg_price`：

```text
Mean:     79.55
Median:   52.80
Q3:      108.50
Max:    1000.00
```

平均數高於中位數，且最大值遠高於第三四分位數。

### Current Decision

目前不將高價格直接視為資料錯誤。

不同種類農產品的價格尺度可能有實質差異，因此在沒有進一步依 `category_code`、`crop_code` 等欄位分析以前，不設定固定價格上限。

---

### Observation: Volume Distribution

`volume` 的分布高度右偏：

```text
Mean:       1905.28
Median:      267.50
Q3:         1332.00
Max:      234587.00
```

少量大型交易量明顯拉高平均數與標準差。

### Current Decision

目前不將 `234587` 或其他大型交易量直接判定為異常。

後續需要查看 Extreme Value 所對應的：

```text
trade_date
category_code
crop_code
crop_name
market_code
market_name
```

再判斷是否屬於合理交易紀錄。

---

## 8. Open Questions

目前尚待進一步 Profiling 的問題：

1. Non-Rest records 中的零值是哪些欄位組合？
2. 是否存在「只有 lower_price = 0」但其他價格正常的紀錄？
3. 是否存在 `volume = 0` 但價格大於 0 的紀錄？
4. Non-Rest 中是否仍存在「所有五個數值欄位皆為 0」的特殊紀錄？
5. 高價格紀錄集中在哪些 category / crop / market？
6. `volume` 的極端值是否為合理的大型交易？
7. Candidate Business Key 在更長日期區間是否仍保持唯一？

---

## 9. Planned Profiling Work

接續 Profiling 順序：

```text
Non-Rest Zero Pattern Profiling
        ↓
Zero Record Details
        ↓
Numeric Extreme Value Profiling
        ↓
依 category / crop / market 理解極端值
        ↓
重新評估 Data Quality Rules
```

在上述 Profiling 完成以前，不因目前觀察到的 `0` 或極端值而新增任意 Data Quality 上限或 `> 0` 規則。
