# Text Meal Canary 歷程主手冊

## Purpose

這份文件是 `text-meal-canary` 的完整歷史、避坑與接手手冊。

目標不是取代程式碼、測試或 `agent.md`，而是回答這些問題：

- 這個 canary 一開始要解什麼問題
- 中間試過哪些路
- 哪些路是錯的、為什麼錯
- 現在主路徑長什麼樣
- 哪些原則已經定下來
- 下一個 agent 接手時，哪些坑不能再踩
- 接下來最值得做的是什麼

適用對象：

- 新接手這個 repo 的 agent
- 新接手這個 repo 的工程師
- 需要快速理解設計歷史，而不是只看目前程式的人

文件分工：

- [agent.md](C:\Users\User\Documents\Playground\line-liff-calorie-helper-text-meal-canary-main\agent.md)
  - repo 級工程原則
  - 不記版本細節
- [HANDOFF.md](C:\Users\User\Documents\Playground\line-liff-calorie-helper-text-meal-canary-main\HANDOFF.md)
  - 短入口
  - 告訴接手者先看哪裡
- 本文件
  - 唯一完整歷史 / 避坑 / 現狀 / 下一步主手冊

這份文件以**實際發生過的問題與決策**為主。
若某段內容是設計歷史或對話決策，而不是 git 可追溯事實，會明確用「設計歷史 / 決策歷史」的角度書寫，不冒充為 git 歷史。

## Current Snapshot

### 當前版本

- 版本：`text-meal-canary.v10.4`
- schema signature：
  - `risk_gate+structured_main_path+local_retrieval_then_search_fallback+zero_kcal_guard+retry+uncertainty_drivers|request_id_trace`

### 當前主路徑一句話摘要

目前主路徑是：

1. 先做輕量 risk gate 與 meal template / local knowledge 準備
2. 主模型輸出 structured core answer
3. 若模型判定需要外部資料，先 local retrieval，再 search fallback
4. 用 structured evidence pass 修正 baseline
5. 經過 quality gate 與 retry
6. 最後由 renderer 產生自然語言給使用者

### 目前已經穩住的事情

- 不再依賴半結構化自然語言作主路徑
- 不再讓 `ASK_USER` 當主路由決策
- `0 kcal` 不再能輕易覆蓋已有非零答案
- external-data path 不再動不動掉成 `0 kcal`
- specific item 不再能被 broad meal template 輕易吞掉
- sibling variant evidence 已經開始收斂，不再像早期那樣常常被近似兄弟品項帶走
- follow-up 已經開始受到 `top_uncertainty_drivers` 約束，不再完全自由發揮

### 目前仍未解完的事情

- follow-up 的問題常常已經有方向，但還不夠精準
- `top_uncertainty_drivers` 的模板化目前有時過頭，會問得太 generic
- local knowledge coverage 還不夠大
- search evidence 雖然有幫助，但還不夠 product-aware
- item identity / variant consistency 還可以再收緊
- 目前最值得投資的主方向已經轉成：**更大的資料庫與更好的 retrieval / grounding**

## History by Phase

這裡不按單純版本號列 changelog，而按「問題 -> 嘗試 -> 結果」來寫。

### Phase 0: 最早期問題意識

一開始這個 canary 想解的是：

- 使用者輸入文字描述一餐
- 系統要估熱量
- 但不能只丟一個單值
- 需要先理解食物組成，再估 macros / kcal
- 若有不確定性，要自然表達

最早期的核心假設是：

- prompt 可以引導模型先理解組成
- 若模型缺資料，就補 search
- 若回答品質不夠，再讓 reviewer 修一輪

這個方向在當時看起來合理，因為：

- search 看起來可以補 brand / menu / nutrition 資訊
- reviewer 看起來可以修正 primary answer 的明顯問題
- 可以先用系統層 orchestration 撐起準確率

實際上，後面大部分歪路都從這三個假設開始長出來。

### Phase 1: weak search + reviewer 路徑

#### 當時做法

早期把 search 當成主幹補強：

- primary answer 先答
- search 去找外部資料
- after-search answer 再答一次
- reviewer 再做 second pass

#### 當時看起來合理的原因

- 如果 search 找到官方營養資訊，理論上能顯著變準
- reviewer 可以扮演「保底修正器」
- 多一層模型似乎就更穩

#### 實際發生的問題

1. search query 太泛
- 很多題只搜到 generic article
- 搜到的是「拉麵熱量一般文章」不是特定品項頁

2. after-search 反而把答案拉低
- 典型案例是拉麵
- 本來 primary 還抓得比較像 heavy ramen
- after-search 吃到 generic ramen article 後，收斂成普通豚骨拉麵

3. reviewer 明明修正了，但沒有被系統吃到
- reviewer 實際輸出可能存在 orchestrator trace 中
- 但程式讀的是空的 `raw_content`
- 結果 final 還是退回較差的答案

#### 這個階段得到的教訓

- weak web search 不能當主幹
- search 找到 generic article 不但沒幫助，還會帶偏答案
- reviewer 不是天然保險，因為 orchestration / parsing / selection 也可能失效
- 如果 evidence quality 不高，多一個 pass 只會把答案變得更不穩

### Phase 2: 收斂成 single-call 主導，弱化 reviewer

#### 當時調整

後來的方向開始轉成：

- 主模型應該是主體
- deterministic 只做小型 guardrails
- reviewer 不應該常駐
- `best-effort first` 比 `先問再說` 更像產品

這個階段開始定下幾個關鍵產品原則：

- 除非 truly private-only，否則先給答案
- `ASK_USER` 不應該是大眾產品的預設入口
- follow-up 是提高精度，不是進門門檻

#### 這個階段的收穫

- 產品體感明顯變好
- 使用者不會一進來就被擋住
- 系統也開始從「多 pass 控制」轉向「主模型 + 少量 gate」

### Phase 3: risk gate 與 local retrieval

#### 當時做法

系統開始建立兩種本地知識：

1. `risk gate packet`
- 高風險類型
- 必要補問
- 偏誤提醒

2. `exact item retrieval cards`
- 品牌商品 / 固定品項卡
- aliases
- kcal band
- 組成 / 份量 / 注意點

當時的想法是：

- risk gate 做高風險提醒
- local retrieval 提供更穩的 grounding
- 不再完全依賴 web search

#### 演進過程

risk gate 後來被收斂成三層：

- exact keywords
- archetype patterns
- shop / brand mapping

exact item card 也被收斂成：

- 強 title / alias 命中
- 或 brand + core tokens 命中

#### 收穫

- 這讓部分 brand / chain / convenience 題型開始有穩定進步
- 也讓「本地資料庫」開始成為比 generic web search 更可控的方向

#### 但也暴露了新的坑

- broad template 或 broad category 可能吞掉 specific item
- exact item card 若命中鬆散，會把完全不相干的 reference card 蓋上來
- `specific item` 和 `meal template` 的優先關係如果沒定清楚，後面會很容易炸

### Phase 4: `ASK_USER -> 0 kcal` 問題爆發

#### 問題樣貌

這是歷程中最重要的 failure mode 之一。

典型路徑是：

- 模型先回 `ASK_USER`
- 內容裡沒有完整的 component / kcal baseline
- parser 吃到的是：
  - `components = []`
  - `estimated_kcal = 0`
- retry 若也延續 ask-user 風格，就一路維持 `0 kcal`

#### 當時的關鍵判斷

這不是單純 prompt 小問題，而是架構問題：

- 模型不該主導「先問 user 還是先回答」
- external-data path 不該被 ask-user 短路
- 只要不是 truly private-only，就應該先給 baseline

#### 收穫

這個階段正式確立：

- `ASK_USER` 不能當主路由權
- `NEED_EXTERNAL_DATA` 應該只是補強訊號
- baseline answer 應該幾乎永遠存在

### Phase 5: 半結構化文本 + brittle parser 的失敗

#### 當時做法

系統長期使用：

- 控制行
- `Title`
- `可能組成`
- `營養估算`
- `熱量估算`
- `我需要你補充`

這種「看起來有結構」的文字格式

#### 為什麼當時會這樣做

- 比完全自然語言容易 parse
- 比完整 JSON 看起來更容易讓模型回答自然
- 可以同時給機器與給人讀

#### 為什麼後來證明是歪路

- 這不是真正的 structured output
- 模型只要換 heading、換句型、換順序，parser 就會吃不到
- with_search_evidence / retry 明明產生了可用數字，parser 仍然可能抓不到
- 最後又回到 `0 kcal`

#### 教訓

- 半結構化文本是最危險的中間地帶
- 它同時承擔：
  - routing
  - machine-readable shape
  - user-facing prose
- 這會讓 prompt / parser / retry 契約長期漂移

### Phase 6: `v10.4` structured main path

#### 為什麼要重做 structured output

之前不是因為「LLM 不適合 JSON」失敗，
而是因為：

- 以前做的是假結構化
- 不是嚴格 schema
- 模型仍然在輸出半自由文本

後來確認：

- Grok 透過 BuilderSpace 可以吃 schema
- 系統也可以把 user-facing prose 與 machine-readable answer 分離

#### `v10.4` 做了什麼

- 主流程改成 structured main path
- 主模型輸出 structured core object
- renderer 自己組自然語言
- local retrieval / search / retry 都使用同一份 structured schema
- non-zero candidate guard 保留
- parser 退到次要 fallback / debug 角色

#### 收穫

- external-data path 明顯穩定
- `0 kcal` 大幅減少
- 路徑控制與答案內容終於分離

### Phase 7: meal templates

#### 為什麼會加 meal templates

高度模糊題型，例如：

- 自助餐
- 滷味
- 火鍋
- 炸便當

其實不是單品問題，而是餐型與份量分配問題。

如果只靠通用模型常識，常常會：

- 看得出不確定性高
- 但沒有穩定的 baseline
- 最後低估或問偏

#### meal template 帶來的進步

- 自助餐 baseline 從偏低值拉到較合理區間
- 火鍋 / 滷味 / 便當這些餐型開始有穩定結構
- 系統能先給 coarse baseline 再追問

#### 這個階段的新問題

- broad template 可能吞掉 specific item
- 例如火鍋裡某個單品，被整體 hotpot template 覆蓋

這個坑後來引出 `P0 specific item protection`。

### Phase 8: `top_uncertainty_drivers`

#### 為什麼會加

當系統穩定後，最明顯的品質缺口不再是崩潰，而是：

- follow-up 問得不夠準
- 問到次要變數
- 沒問到真正會改變 kcal 最大的因素

#### 當時的策略

在 structured schema 裡新增：

- `top_uncertainty_drivers`

目標是：

- 先找 1-2 個最大熱量變因
- 再由 follow-up 去對應這些 driver

#### 收穫

- follow-up 的方向確實變得更穩
- 不再完全自由發揮

#### 目前新副作用

- follow-up 有時過度模板化
- driver 對了，但問題句子太 generic
- 或 driver 選錯時，問題會顯得很笨

這就是目前最值得優先繼續修的點之一：

- `driver applicability / confidence gate`

## Wrong Turns and Lessons

這一章專門記錄已知歪路。

### 1. 把 web search 當主幹

#### 當時怎麼做

- primary answer
- search
- with-search / after-search answer

#### 為什麼看起來合理

- 直覺上公開網頁很多，品牌資料可能容易找到

#### 實際怎麼壞

- 很多 query 只搜到 generic article
- evidence quality 低，但 still 進模型
- after-search 反而把較合理的 baseline 拉成 generic estimate

#### 現在定下的避免原則

- search 只能當 fallback，不是主幹
- local retrieval / exact card / better grounding 才是主方向
- search 的真正控制點是 evidence quality gate，不是「有搜就餵」

### 2. 讓 reviewer 常駐 second pass

#### 當時怎麼做

- primary -> search -> reviewer

#### 為什麼看起來合理

- 多一個模型像是保險

#### 實際怎麼壞

- reviewer 的輸出也會受 orchestration / parser / selection 影響
- reviewer 不是天然真理
- 還增加 latency 與複雜度

#### 現在定下的避免原則

- 主模型是主體
- reviewer 不作常駐設計
- 優先做 better baseline、better evidence、better candidate selection

### 3. 讓模型主導 `ASK_USER`

#### 當時怎麼做

- 模型直接輸出 `ASK_USER`
- 系統沿用它

#### 為什麼看起來合理

- 模型知道自己不確定

#### 實際怎麼壞

- `ASK_USER` 很容易把 baseline answer 一起放棄
- `ASK_USER -> 0 kcal`
- external-data path 被短路

#### 現在定下的避免原則

- 模型不主導 ask-user 路由
- 系統先要求 baseline
- truly private-only 才允許最後呈現 ask-user

### 4. 半結構化文本假裝 structured

#### 當時怎麼做

- heading + bullets + parser

#### 為什麼看起來合理

- 兼顧人讀與機器 parse

#### 實際怎麼壞

- parser 太脆
- prompt / retry / evidence 契約持續漂移
- `0 kcal` 問題反覆出現

#### 現在定下的避免原則

- 主路徑直接用 structured output
- renderer 與 machine-readable output 分離

### 5. 用 deterministic 做模糊判斷

#### 當時怎麼做

- 嘗試讓 deterministic 幫忙判食物類型、private-only、模糊語意

#### 為什麼看起來合理

- 覺得規則比較可控

#### 實際怎麼壞

- 容易長成大量特例表
- 規則會越補越多
- 對模糊語意判斷很脆弱

#### 現在定下的避免原則

- deterministic 只做高確定性事
- 模糊判斷交給模型

### 6. broad template 吞掉 specific item

#### 當時怎麼做

- 命中 meal template 後，template 可以蓋過具體 item

#### 為什麼看起來合理

- 覺得餐型模板比 item 更有結構

#### 實際怎麼壞

- 例如火鍋單品會被整體 hotpot template 吞掉

#### 現在定下的避免原則

- `specific item > broad meal template`
- template 只能輔助 baseline，不可改寫 item identity

### 7. sibling variant 混入 evidence

#### 當時怎麼做

- 只要同品牌、同類別夠像，就可能採用

#### 為什麼看起來合理

- 感覺近似品項至少有參考價值

#### 實際怎麼壞

- 明確商品可能被替成兄弟版本
- 熱量與 follow-up 都會被帶偏

#### 現在定下的避免原則

- 同品牌不等於同 variant
- sibling variant 只能當 weak evidence
- specific variant identity 必須被保護

### 8. follow-up 過度模板化

#### 當時怎麼做

- 一旦有 uncertainty driver，就強套 canonical question

#### 為什麼看起來合理

- 可以避免模型亂問

#### 實際怎麼壞

- 有些題問句會變得太 generic
- driver 如果選錯，問句就顯得更笨

#### 現在定下的避免原則

- follow-up 需要對應 driver
- 但模板化也需要 applicability / confidence gate
- 不應該硬套到讓問題失去貼題性

## Current Architecture

這裡只寫高階實際路徑，不重複規格文件。

### Model responsibilities

模型主要負責：

- `food_origin`
- `food_class`
- `needs_external_data`
- `private_info_risk`
- baseline `components`
- baseline `kcal_*`
- `uncertainty_factors`
- `followup_questions`
- `top_uncertainty_drivers`
- `external_data_query`

也就是：

- 食物理解
- baseline 估算
- 不確定性理解
- 外部資料需求判斷

### System responsibilities

系統主要負責：

- risk gate
- meal template / local knowledge 準備
- local retrieval
- search fallback
- evidence quality gate
- retry
- candidate selection
- non-zero candidate protection
- final renderer

也就是：

- 編排路徑
- 保護 item identity
- 保護 variant consistency
- 防止明顯系統級錯誤

### Deterministic boundary

目前已定下的邊界是：

deterministic 可以做：

- schema 驗證
- request / trace correlation
- strong match / mismatch
- candidate guard
- identity protection
- variant consistency
- driver 與 follow-up 的對齊檢查

deterministic 不應做：

- 模糊語意判斷
- private-only 主判定
- 食物本體理解
- 大量食物特例規則

### local retrieval / search / retry 的角色

#### local retrieval

- 主角色是高 precision grounding
- 偏 exact item / local knowledge
- 寧可漏，不可錯

#### search

- 只是 local retrieval 不足時的 fallback
- 不應該是主幹
- evidence quality 不夠時不該餵回模型

#### retry

- repair-only
- 不能重寫一切
- 更不能讓已有的非零答案退化成空答案

### structured output 與 renderer 分離

這是目前架構上最重要的穩定點之一：

- 模型輸出 structured core answer
- renderer 自己組自然語言

好處是：

- parser 不再扮演核心角色
- user-facing prose 與 machine-readable contract 分離
- retry 與 candidate selection 也更容易穩定

### uncertainty drivers 的角色

`top_uncertainty_drivers` 的定位是：

- 先找最大熱量變因
- 再讓 follow-up 去對應這些 driver

這不是為了加很多模板，而是為了讓 follow-up 的精準度有通用機制可依附。

## Non-negotiable Principles

以下原則已經定下來，不應輕易回退：

### 1. 通用能力優先於食物特例規則

- 優先強化 general judgment
- 優先強化 knowledge grounding
- 不要把系統做成一個越補越大的食物例外表

### 2. deterministic 只做高確定性事

- deterministic 不是第二個小模型
- 不做模糊食物判斷
- 只做保護欄與驗證

### 3. 強化資料庫與 retrieval 是主方向

- 長期主幹不是更多硬規則
- 而是更大的資料庫、更好的 retrieval、更好的 evidence quality

### 4. follow-up 要來自最大不確定因子

- follow-up 不是為了看起來有問問題
- 應只問最可能顯著改變 kcal 的 1-2 個因素

### 5. non-zero candidate 保護

- `0 kcal` 不是正常答案
- 已有非零候選時，0 不可覆蓋

### 6. specific item identity 必須被保護

- specific item > broad template
- same variant > sibling variant

### 7. ask-user 不是主路徑

- 非 truly private-only 題型，先給 baseline
- follow-up 是補強，不是阻塞

## Known Gaps

這裡只列目前仍未解決的缺口。

### A. 路徑性問題

- 大方向已穩，但 search evidence 還不夠 product-aware
- driver-based follow-up 還缺 applicability / confidence gate

### B. follow-up 品質問題

- `top_uncertainty_drivers` 已經改善方向
- 但 follow-up 仍常常太 generic
- 有些題 driver 對了，問題句子仍不夠貼題

### C. evidence / DB coverage 問題

- local knowledge coverage 還不夠大
- exact item / brand / variant coverage 還不夠穩
- 高頻台灣在地食物與品牌商品仍缺更完整 grounding

### D. item identity / variant 問題

- 已經進步，但仍值得繼續強化
- sibling variant guard 還能更細
- evidence identity consistency 還能更嚴

## Next Work

以下是目前建議的下一步，按優先順序排列。

### 1. 資料庫建置計畫

這是現在最值得優先做的主工作。

原因：

- 主路徑已經比早期穩很多
- 現在更多問題來自 grounding 不夠大、不夠深
- 持續只靠模板與 prompt 微調，邊際效益會下降

應先做：

- DB 分層設計
- schema
- source policy
- ingestion plan
- verification / refresh policy

### 2. driver applicability / confidence gate

原因：

- `top_uncertainty_drivers` 已經有價值
- 但 follow-up 過度模板化開始成為新問題

目標：

- driver 明確時才硬套模板
- driver 不夠明確時保留更貼題的問題

### 3. 更大的 knowledge grounding

原因：

- 長期準確率提升主要靠 grounding，不靠更多食物級規則

方向：

- base nutrition DB
- exact item DB
- meal pattern knowledge
- 更乾淨的 local retrieval corpus

### 4. search evidence 再收斂

原因：

- search 已證明有價值
- 但還需要更 product-aware 的品質判定

方向：

- item / product evidence 與 generic knowledge evidence 分流
- 更強的 variant identity 檢查

## What a New Agent Should Do First

新 agent 接手時，建議順序：

1. 先讀本文件
2. 再讀 [agent.md](C:\Users\User\Documents\Playground\line-liff-calorie-helper-text-meal-canary-main\agent.md)
3. 再讀 [app/usecases/text_meal.py](C:\Users\User\Documents\Playground\line-liff-calorie-helper-text-meal-canary-main\app\usecases\text_meal.py)
4. 再看最近測試結果與 `.logs/requests`

第一原則不是立刻加規則，而是先判斷：

- 這次問題是路徑問題
- follow-up 問題
- evidence / DB coverage 問題
- 還是 item identity / variant 問題

不要把所有問題都用新增模板或新增特例規則處理。
