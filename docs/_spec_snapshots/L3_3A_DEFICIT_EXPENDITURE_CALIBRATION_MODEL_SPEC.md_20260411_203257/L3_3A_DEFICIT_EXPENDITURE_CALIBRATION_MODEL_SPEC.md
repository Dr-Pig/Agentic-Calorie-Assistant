# L3.3A Deficit / Expenditure Calibration Model Spec

## 1. 目的

這份 spec 定義 calorie-deficit product core 下的 calibration model layer。

它先回答：

- 什麼是本產品中的 `operating total daily energy expenditure`
- 系統如何利用 intake history 與 body-weight trend 判斷赤字是否真的存在
- 何時資料品質不足，不能做出可靠 calibration judgment
- 何時應維持觀察，何時可以進入 calibration proposal flow

它暫時不回答：

- proposal option 的最終 UI 呈現
- prompt wording
- provider / model selection
- benchmark 實作細節

---

## 2. 核心定位

本產品的第一性目標不是營養完美化，而是幫助使用者穩定維持熱量赤字。

因此 calibration 的第一核心不是 proposal，而是：

1. 判斷 intake logging 是否足夠可信
2. 判斷體重變化是否足以支持趨勢判讀
3. 估計使用者目前的 `operating expenditure`
4. 判斷目前目標赤字是否真的存在
5. 只有在這些條件成立後，才進入後續 proposal policy

## 2A. 執行模式宣告

`L3.3A` 的 canonical execution mode 是 `deterministic-first`。

正式規則：

- Section 5 的五個判斷步驟均應優先以確定性規則實作
- 這五個步驟是 sequential gate，不是平行執行，也不應被映射成隱含的 LLM multi-pass chain
- 唯一合法的 LLM 介入點是 optional narrative explanation 或 user-facing explanation
- 若需要 LLM，應確認它在做的是「解釋 / 包裝結果」，而不是「做 calibration truth judgment」

---

## 3. 核心定義

### 3.1 `operating expenditure`

`operating expenditure` 是系統目前採用的工作估計值，代表：

- 使用者在當前生活型態下的實際總消耗熱量
- 它不是單純公式算出的靜態 TDEE
- 它也不是一次 observation 後立刻跳動的數字

它的來源應分成兩階段：

- `initial estimate`
  - 來自身高 / 體重 / 年齡 / 性別 / activity assumption 的初始估計
- `calibrated operating estimate`
  - 來自 intake history 與 body-weight trend 的後續校準值

### 3.2 `deficit reality`

`deficit reality` 指的是：

- 使用者實際 intake
- 與使用者實際 operating expenditure
- 在時間窗內是否真的形成能量赤字

這是本產品最重要的真相判斷之一。

### 3.3 `logging quality`

`logging quality` 指的是：

- intake logging 是否足夠完整
- body-weight observation 是否足夠穩定
- occurred_at / local_date 是否足夠可信
- 是否有太多缺漏、補記偏差、或單位不清

如果 `logging quality` 不足，系統應優先進入 `logging_quality_first` posture，而不是急著調整 plan。

---

## 4. Model Inputs

calibration model 至少應讀取：

- `BodyObservation` history
- `ActiveBodyPlanView`
- `CurrentBudgetView`
- `RecentCommittedMealsView`
- intake completeness summary
- rescue history summary
- adherence summary
- observation timing quality summary

可選輸入：

- profile-based initial estimate metadata
- activity assumption metadata
- known logging gaps

---

## 5. 判斷順序

### 5.0 執行框架

這五個步驟是 sequential gate，不是並行執行。

正式規則：

- 若任何 step 輸出 `insufficient_*` posture，後續步驟不應繼續執行
- 只有前一 step 輸出可繼續 posture，才允許跑下一 step
- 最終 posture 應是最後一個合法完成且未被前序 gate 攔截的 step 結果

### 5.1 Step 1: Observation Quality Check

先判斷：

- 近期體重資料量是否足夠
- 量測時間是否過度分散
- observation 是否集中在可比較條件下
- 是否有明顯離群值

若不足：

- 輸出 `insufficient_observation_quality`
- 不進入強校準判斷

### 5.2 Step 2: Intake Quality Check

再判斷：

- 近期 intake logging 是否連續
- 是否有大量漏記跡象
- 是否存在高比例 rough / low-confidence meals
- 是否發生大量晚補記或可疑低估

若不足：

- 輸出 `insufficient_logging_quality`
- calibration policy 應優先轉向 `logging_quality_first`

### 5.3 Step 3: Trend Window Construction

只有在 observation 與 intake quality 都達最低門檻後，才建立 trend window。

trend window 至少要定：

- 起訖日期
- observation count
- intake coverage score
- rescue overlay influence
- confidence posture

### 5.4 Step 4: Expenditure Inference

在合格 trend window 上，系統應估計：

- 平均 intake posture
- 實際體重變化對應的能量平衡方向
- operating expenditure 的工作估計值

### 5.5 Step 5: Deficit Reality Check

最後判斷：

- 目前目標赤字是否真的存在
- 若不存在，是接近維持、反向盈餘，還是只是暫時噪音
- mismatch 比較像 intake estimate 問題，還是 expenditure assumption 問題

---

## 6. Confidence / Posture Classes

calibration model 至少應輸出以下 posture：

- `insufficient_data`
- `logging_quality_first`
- `monitor_only`
- `calibration_candidate`
- `high_confidence_mismatch`

### 6.1 `insufficient_data`

資料太少，不能判斷。

### 6.2 `logging_quality_first`

資料量可能夠，但 logging 品質不足，先不要調 plan。

### 6.3 `monitor_only`

目前有些訊號，但不足以支持 plan-level change。

### 6.4 `calibration_candidate`

已有足夠理由，允許進入 proposal policy。

### 6.5 `high_confidence_mismatch`

表示 intake / expenditure / body outcome 之間存在高信度不一致，需要進一步調整。

---

## 7. Mismatch Attribution

calibration model 不應只輸出「有問題」，還要盡量分辨問題類型。

至少要支援以下 attribution：

- `likely_logging_gap`
- `likely_intake_underestimate`
- `likely_expenditure_shift`
- `likely_noise_only`
- `mixed_uncertainty`

### 7.1 `likely_logging_gap`

更像是資料不完整，而不是 plan 本身錯。

### 7.2 `likely_intake_underestimate`

更像是食物熱量估計偏低、漏記、或 portion 偏差。

### 7.3 `likely_expenditure_shift`

更像是使用者實際總消耗已和初始假設不同。

### 7.4 `likely_noise_only`

更像是暫時水分波動或短期噪音。

### 7.5 `mixed_uncertainty`

多種因素混雜，不能武斷地調整 plan。

---

## 8. Intake Estimation Bias Posture

除了 `operating_expenditure_estimate`，calibration model 還應輸出一個獨立的：

- `intake_estimation_bias_posture`

它的目的不是直接改寫 nutrition truth，而是告訴 intake runtime：

- 最近 intake estimate 是否有系統性偏差跡象
- 這個偏差較像發生在哪些場景
- 這個訊號應如何影響 clarify priority 與高風險 case handling

### 8.1 為什麼要分離

若把所有 mismatch 都塞進 `operating_expenditure_estimate`，會掩蓋 intake estimation 本身的偏差。

因此 calibration model 應至少分開輸出：

- `operating_expenditure_estimate`
- `intake_estimation_bias_posture`

### 8.2 posture 類型

至少支援：

- `neutral`
- `likely_underestimate`
- `likely_overestimate`
- `mixed_uncertainty`

### 8.3 可選 scope

`intake_estimation_bias_posture` 可帶有限 scope，例如：

- `portion_heavy_meals`
- `sweet_drinks`
- `sauces_and_addons`
- `fried_or_combo_meals`
- `late_logged_meals`

### 8.4 第一版影響範圍

第一版不應讓這個 posture 直接全局改寫 nutrition 數字。

它應優先只影響：

- clarify priority
- risk tagging
- estimate conservatism posture
- internal trace / warning

只有在未來有充分驗證後，才考慮非常小幅且可追溯的 bias adjustment。

### 8.5 Functionally Correct Principle

本產品優先追求 `functionally correct`，而不是 `biologically perfect`。

也就是說：

- intake estimate 與 expenditure estimate 可以各自帶有誤差
- 但若兩者在產品上仍能穩定維持有效赤字，並與體重趨勢持續對齊
- 系統可以接受這是一個可運作的 operating model

calibration 的目標不是追求絕對真實，而是追求對赤字管理有用、可持續、可校準的工作真相。

---

## 9. `estimated_tdee` / Operating Estimate Policy

### 9.1 active `BodyPlan` 應持有 operating estimate

active `BodyPlan` 應有正式被系統採用的總消耗估計值。

建議欄位可維持為：

- `estimated_tdee`

但它的語意應理解為：

- active operating expenditure estimate

### 9.2 初始來源

初始 `estimated_tdee` 可以來自：

- profile-based formula
- activity assumption
- product onboarding estimate

### 9.3 後續來源

後續 `estimated_tdee` 不是重新跑公式，而是由 calibration model 根據：

- intake history
- body-weight trend
- logging quality

進行校準後的工作估計值。

---

## 10. 與 Proposal Policy 的邊界

這份 `L3.3A` 不直接定義 proposal option。

它只決定：

- 是否有資格進入 proposal flow
- 進入 proposal flow 時的 confidence 與 attribution
- 是該 `monitor`、`logging_quality_first`，還是 `proposal_candidate`

proposal 的內容、選項數量、UI 呈現，留給 `L3.3B Calibration Proposal Policy / Runtime Contract Spec`。

---

## 11. 與 Rescue 的邊界

### 11.1 rescue 的角色

rescue 是短期恢復赤字的操作層。

### 11.2 calibration 的角色

calibration 是重新估計：

- 赤字是否真的存在
- 現行 operating expenditure 是否仍可信

### 11.3 rescue non-viable

這裡不建議用固定「失敗幾次」判斷。

應改用：

- `rescue horizon`
- `recovery viability`

當短期 rescue 已不再可行時，calibration policy 才允許升級到 plan-level reconsideration。

---

## 12. 對 Recommendation 的影響

calibration 的影響應分成兩層：

### 12.1 immediate budget posture

直接影響：

- 當前剩餘熱量
- recommendation 可接受的熱量上限

### 12.2 delayed strategy posture

較慢地影響：

- 推薦偏向更穩定、較不易爆卡的選項
- 減少高風險液體熱量
- 調整晚餐或下午茶的策略傾向

若產品當前核心只聚焦熱量赤字，第一版可先只強依賴 `immediate budget posture`，而把 `delayed strategy posture` 保持為弱訊號。

---

## 13. 對 Intake Runtime 的影響

`intake_estimation_bias_posture` 不應直接變成對 nutrition LLM 的自由文字暗示。

它應以受控 calibration context 的形式提供給 intake runtime，並遵守：

- 可提高 clarify priority
- 可提高高風險 case 的保守度
- 可增加 internal warning / trace
- 不可直接全局覆寫 nutrition truth
- 不可在沒有 scope 與 confidence 的情況下任意調數

---

## 14. Important Outputs

`L3.3A` 至少應輸出：

- `observation_quality_posture`
- `logging_quality_posture`
- `trend_window_summary`
- `operating_expenditure_estimate`
- `intake_estimation_bias_posture`
- `deficit_reality_status`
- `mismatch_attribution`
- `calibration_confidence`
- `proposal_eligibility`

---

## 15. 對齊關係

### 對 L0

本產品核心目標是穩定維持熱量赤字，而 calibration 是為了校準赤字真實性。

### 對 L1

`BodyObservation` 可直接寫入，但 active `BodyPlan` 不可無聲改寫。

### 對 L2

需要依賴：

- `BodyObservation`
- `BodyPlan.estimated_tdee`
- `DayBudgetLedger`
- `LedgerEntry`
- `MealThread / MealVersion`

### 對 L3.1

intake logging quality 直接影響 calibration confidence。

`intake_estimation_bias_posture` 應只作為 intake runtime 的受控輔助訊號，而不是直接改寫 nutrition truth。

### 對 L3.2

recommendation 應優先使用校準後的 budget posture 來維持熱量赤字。

---

## 16. 測試情境

後續至少應覆蓋：

- observation 太少時，不產生 calibration candidate
- intake logging 缺漏明顯時，輸出 `logging_quality_first`
- 體重趨勢與 intake 形成穩定 mismatch 時，輸出 `calibration_candidate`
- 短期噪音不被誤判成 expenditure shift
- `estimated_tdee` 可從初始估計走向校準後 operating estimate
- `intake_estimation_bias_posture` 可與 `operating_expenditure_estimate` 分離輸出
- bias posture 第一版只影響 clarify / risk handling，不直接全局改 nutrition 數字
- rescue 長期失去可行性時，允許升級到 plan-level reconsideration
- recommendation 至少能吃到 `immediate budget posture`

---

## 17. v1 Default Decisions

為避免 calibration model 在實作時仍有過大裁量空間，v1 預設採以下固定決策：

1. trend window：
   - 最低使用 `14` 天滾動視窗
   - 最低需要 `5` 次有效 `BodyObservation`
   - 未達門檻時，最高只能輸出 `insufficient_data` 或 `monitor_only`
2. logging quality：
   - intake coverage 最低門檻採 `80%`
   - 若 14 天內有效 intake coverage 低於 `80%`，預設進 `logging_quality_first`
3. mismatch attribution heuristic：
   - 預設採 `behavior first`
   - 在 logging quality 未達標、或 observation 不穩定時，不得優先判定 `likely_expenditure_shift`
   - 只有在 logging quality 達標、trend 穩定、且 mismatch 持續存在時，才可前排考慮 `likely_expenditure_shift`
4. 初始 `estimated_tdee`：
   - onboarding 階段先由 `height / weight / age / sex / activity_assumption` bootstrap
   - 一旦進入穩定紀錄期，active `BodyPlan` 應逐步切換到校準後的 operating estimate
5. `delayed strategy posture`：
   - v1 只保留弱訊號
   - 不可單獨觸發 recommendation 大幅改風格
   - 主要只作排序微調與未來策略觀察，不作主要 caloric gate
