# L5C Safety / Guardrail Spec

## 1. 目的

這份 spec 定義系統的 safety policy、guardrail 邊界、hard fail / soft fail 分類、以及人工作業升級條件。

它要回答：

- 哪些行為是 `hard_fail`
- 哪些行為是 `soft_fail`
- 哪些 threshold 是 safety-critical
- tool fallback 有哪些合法降級方式
- human review escalation 在什麼情況下啟動
- trace / privacy 的最低安全要求是什麼

---

## 2. Safety Philosophy

安全策略的核心不是讓系統完全不動，而是讓它：

- 不越權
- 不假裝高信心
- 不落錯誤 canonical state
- 不跌破 caloric safety floor
- 不把 derived inference 當 confirmed truth

---

## 3. Failure Classes

- `hard_fail`
- `soft_fail`
- `warn_only`

### 3.1 hard_fail

必須阻止 commit、阻止 proposal 生效、或至少強制降級。

### 3.2 soft_fail

可允許完成本輪，但不能被視為高品質輸出。

### 3.3 warn_only

不需中止流程，但必須保留 warning / trace。

---

## 4. Hard-Fail / Soft-Fail Classification Table

### 4.1 Cross-flow hard_fail

- proposal 未經確認就 commit
- 低於 safety floor 的 caloric posture
- 將 derived inference 假裝成 confirmed truth
- recommendation 自動建立任何 implicit meal-intent / pending intake state
- deterministic validation 已知失敗仍落地
- tool failure 被系統表現成 tool success

### 4.2 Intake hard_fail

- meal boundary truly unresolved 仍 commit
- commit payload 核心欄位缺失
- correction 直接覆寫舊版本，不保留 version chain
- commit-critical arithmetic / schema failure 仍 commit

### 4.3 Recommendation hard_fail

- location unavailable 卻表現成 nearby certainty
- 明確違反 confirmed negative preference 仍主推
- 普通 recommendation 被當成已記錄 intake

### 4.4 Calibration hard_fail

- insufficient data 卻發出 plan-impacting proposal
- logging quality 明顯不足仍直接判定 `expenditure_shift`
- 未經確認改 active `BodyPlan`

### 4.5 Rescue hard_fail

- rescue 跌破 safety floor
- `recovery_viability = non_viable` 仍繼續分攤
- 用懲罰式方案壓縮未來攝取

### 4.6 Cross-flow soft_fail

- 信心不足卻語氣過度肯定
- stale summary 被使用但未造成 hard violation
- semantic retrieval 撈到弱相關內容

### 4.7 Intake soft_fail

- 可估但 evidence 很弱
- portion 不確定但未 clarify
- bias posture 用得太重但未直接改數字

### 4.8 Recommendation soft_fail

- 個人化不夠準
- fallback 過於 generic
- top pick 可用但不是最佳

### 4.9 Calibration soft_fail

- 更像 `monitor_only` 但提案語氣太前傾
- attribution 不夠穩
- option family 合理但排序不佳

### 4.10 Rescue soft_fail

- horizon 可行但不是最優
- 主推方案可執行但不夠低摩擦
- 生效時機說明不夠清楚

---

## 5. Cross-Flow Hard Guards

- recommendation 不得建立任何 implicit meal-intent / pending intake state
- proposal 不得未經確認直接 commit
- rescue / calibration 不得產生低於 safety floor 的 caloric posture
- low-confidence calibration 不得改動 active `BodyPlan`
- derived bias posture 不得直接覆寫 nutrition truth

---

## 6. Tool Failure Fallback Guardrails

tool failure 不等於整體流程失敗，但合法降級必須可追溯、可保守、且不可裝作成功。

### 6.1 allowed fallback modes

- `conservative_estimate`
- `needs_more_information`
- `no_commit`
- `fallback_to_safe_default`（僅 recommendation 類型）

### 6.2 forbidden fallback behavior

- 假裝 tool 已成功返回高信度結果
- 用 fallback mode 隱藏低信心
- 在核心資料不足時仍強行 commit

### 6.3 tool reason requirement

每次 tool call 與每次 fallback 都必須在 internal trace 中保留 `tool_reason` 或 `fallback_reason`。

---

## 7. Safety-Critical Thresholds

`L5C` 不重複定所有數值，但要明確指出哪些 threshold 屬於 safety-critical。

### 7.1 Intake

- `clarify_blocking`
- `commit_readiness`
- `commit-critical validation`

具體數值與門檻引用 `L3.1`。

### 7.2 Recommendation

- 不可違反 confirmed negative preference
- 不可偽裝 nearby certainty
- 不可明顯超出有效 budget posture 到失去產品可執行性

具體 policy 引用 `L3.2`。

### 7.3 Calibration

- 最低 trend window
- 最低 observation count
- 最低 intake coverage
- proposal eligibility gate

具體數值引用 `L3.3A / L3.3B`。

### 7.4 Rescue

- `rescue_horizon`
- 單日壓縮上限
- safety floor heuristic
- `recovery_viability` legality
- activation timing rule

具體數值引用 `L3.4`。

---

## 8. Trace / Privacy Guardrails

### 8.1 minimum time fields

每筆安全可追溯 trace 至少應記錄：

- `recorded_at`
- `timezone`
- `local_date`
- `user_local_time`

### 8.2 privacy baseline

進入長期 log / trace 儲存前，必須對下列資訊做遮罩或去識別化：

- 姓名
- 私人位置 / 精細地址
- 直接聯絡資訊
- 其他不必要 PII

### 8.3 structured logging

所有 runtime safety log、tool log、trace envelope 都應以結構化 JSON 保存，不應只保留自由文字。

---

## 9. Human Review Escalation

v1 不要求每次日常操作都進 human review。  
human review escalation 只應保留給高風險、反覆性、或接近安全底線的情況。

### 9.1 應觸發 human review / flagged escalation 的情況

- 同一使用者反覆出現 calibration hard fail
- rescue 多次進入 `non_viable`
- caloric posture 持續逼近 safety floor
- runtime 反覆產生互相矛盾的 budget / plan 結論
- 使用者明確表示不信任、困惑、或覺得建議有害
- intake bias posture 長期高風險且無法靠 `logging_quality_first` 改善

### 9.2 不需 human review，只需系統內降級的情況

- recommendation 不夠個人化
- 單次 meal estimate 不精準
- 單次 rescue top option 排得不夠好
- 單次 calibration 過於保守但未造成 hard fail

---

## 10. Guardrail Enforcement Points

guardrail 不只要被定義，也要明確知道在哪一層被執行。

### 10.1 pass-output validation

適合攔截：

- 缺 required fields
- output schema 不合法
- 明顯越權輸出

### 10.2 deterministic gate

適合攔截：

- arithmetic sanity failure
- safety floor violation
- horizon legality failure
- missing `tool_reason` / missing critical trace fields

### 10.3 persistence / application layer

適合攔截：

- unconfirmed proposal commit
- invalid version-chain write
- illegal ledger overlay write
- active `BodyPlan` illegal replacement

### 10.4 UI / action gate

適合攔截：

- unsafe one-tap action
- ambiguous confirmation action
- unavailable nearby option being rendered as certain action

### 10.5 enforcement rule

每條 hard guard 至少應有一個明確 enforcement point；高風險 guard 可有多層 enforcement。

---

## 11. Soft-Fail Runtime Action Map

soft fail 不應只是被記錄，還要映射到具體 runtime 降級動作。

### 11.1 general downgrade actions

- `add_warning`
- `lower_confidence`
- `hide_derived_field`
- `allow_response_but_block_commit`
- `switch_to_monitor_only`
- `switch_to_safe_fallback`

### 11.2 intake

- weak evidence -> `lower_confidence`
- unclear portion -> `add_warning` or `allow_response_but_block_commit`
- derived macro mismatch -> `hide_derived_field`

### 11.3 recommendation

- personalization weak -> `switch_to_safe_fallback`
- stale preference summary -> `lower_confidence`
- location ambiguity -> `switch_to_safe_fallback`

### 11.4 calibration

- attribution weak -> `switch_to_monitor_only`
- logging quality borderline -> `switch_to_monitor_only`
- proposal confidence not strong enough -> `allow_response_but_block_commit`

### 11.5 rescue

- top option not ideal -> `add_warning`
- horizon possible but not optimal -> `lower_confidence`
- timing explanation weak -> `add_warning`

### 11.6 downgrade visibility

所有 soft-fail 降級都應可在 internal trace 中被看見，必要時反映到：

- `warning_flags`
- `confidence_posture`
- `fallback_mode`

---

## 12. 與其他 specs 的關係

- 具體 safety-critical thresholds 由 `L3.1 / L3.2 / L3.3A / L3.3B / L3.4` 定義
- benchmark 對應覆蓋由 [`docs/L5B_BENCHMARK_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/L5B_BENCHMARK_SPEC.md) 定義
- trace 與 eval 消費方式由 [`docs/L5A_EVAL_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/L5A_EVAL_SPEC.md) 定義

---

## 13. 待確認問題

1. 是否要在 v1 就加入 provider / model failover 的安全分級
2. 某些 privacy redaction 是否需要區分 debug tier 與 analytics tier
3. human review escalation 是否要按 user tier 再細分
