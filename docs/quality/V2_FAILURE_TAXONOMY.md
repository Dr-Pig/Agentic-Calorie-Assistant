# V2 Failure Taxonomy

## 目的

本文件定義 **V2 的 whole-product failure taxonomy**。

它的角色是：

- 把失敗從零散 bug list，整理成可追蹤、可分群、可映射到 capability families 與 product objects 的 taxonomy
- 為下游文件提供穩定結構：
  - `V2_GRADING_RUBRIC.md`
  - bundle eval packs
  - replay packs
  - regression suites
  - founder human review 標記
- 幫助 implementation 與 eval 在看到失敗時，先判斷 **這是哪一類 failure family**，再決定修法

它回答：

- 這個產品常見的 failure families 是什麼
- 每個 failure family 主要傷害哪個 product object / capability family
- 每種 failure 應在哪個 surface / layer 被偵測
- 哪些 failure 是 P0 blocker，哪些是可延後處理的品質問題
- 如何用一致 vocabulary 來標記 replay / benchmark / production failures

它不回答：

- 每個 case 的具體 pass/fail 分數（見 `V2_GRADING_RUBRIC.md`）
- 單一 journey 的完整劇本與 oracle 常數（見 `docs/quality/` bundle eval docs）
- root cause 的最終技術實作細節

---

## 關係說明

### 與 `V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md` 的關係

- capability lattice 定義「產品有哪些 capability families」
- 本文件定義「每個 capability family 可能怎麼失敗」

### 與 `UX_JOURNEY_TO_SLICE_MAP.md` 的關係

- journey map 定義使用者如何走過產品
- 本文件定義 journey 失敗時，應該落在哪個 failure family

### 與 `V2_GRADING_RUBRIC.md` 的關係

- taxonomy 提供失敗分類 vocabulary
- rubric 提供嚴重度與通過標準

---

## 使用原則

1. **先分類，再修 bug**
   - 看到失敗時，先標記 failure family，不要直接跳到 patch

2. **先看 product semantics，再看 prompt wording**
   - 若失敗會改變 product object truth、proposal state、chat/UI shared truth，優先視為 semantic failure

3. **先找 generalized family，不要先修單一案例**
   - 若某個 benchmark case 失敗，先問它屬於哪個 family，再修 family rule

4. **同一案例可多標籤，但要有 primary label**
   - 例如 correction case 可能同時有 `FAM-CORR-01` 與 `FAM-SYNC-01`
   - 但必須指定一個 primary failure family

5. **失敗分類不等於 root cause**
   - taxonomy 是產品 / eval 語義分類，不是程式層 root-cause tree

---

## Failure Record 建議欄位

每一個失敗案例，建議至少記錄：

```yaml
failure_id:
primary_failure_family:
secondary_failure_families:
severity:
capability_family:
affected_product_objects:
affected_journeys:
detection_surface:
found_in:
short_description:
user_visible_effect:
blocking_invariant:
notes:
```

欄位說明：

- `severity`: `P0_blocker | P1_major | P2_moderate | P3_minor`
- `detection_surface`: `chat | ui | trace | eval_runner | human_review | production_replay`
- `found_in`: `benchmark | replay_pack | bundle_eval | founder_gate | prod`

---

## Severity 定義

### P0_blocker
會直接破壞核心產品真相、造成錯誤 state mutation、或讓 journey 無法通過。

例如：
- commit 到錯的 meal thread
- chat / UI 數字不同
- proposal 被誤當 committed state
- 無 onboarding 卻假裝有 budget truth

### P1_major
產品仍可用，但 user-visible behavior 顯著錯誤，會讓 trust 明顯下降。

例如：
- clarify 問錯關鍵欄位
- rescue wording 把抱怨誤判為拒絕
- recommendation 與 budget 明顯衝突

### P2_moderate
功能主線仍成立，但精度、自然度、表達或次要同步有明顯缺陷。

例如：
- 回覆過長
- 不確定性表達不佳
- explanation 過硬或不夠 chat-like

### P3_minor
不影響產品主線與 shared truth，主要是 polish 問題。

例如：
- wording 稍怪
- 文案重複
- 非關鍵 metadata 缺漏

---

## Detection Surface 類型

| Surface | 說明 |
|---|---|
| `chat` | 對話回覆本身可見的失敗 |
| `ui` | Today / body-plan / proposal inbox / other UI state failure |
| `trace` | trace / sidecar / artifact 顯示的 state transition failure |
| `eval_runner` | runner contract、artifact linkage、coverage gate failure |
| `human_review` | founder / operator 人審時發現的產品違和 |
| `production_replay` | 真實使用者對話重播時發現的 failure |

---

## Whole-Product Failure Families 總覽

| Failure Family ID | Family Name | Primary Capability Family | Default Severity |
|---|---|---|---|
| FAM-BOOT | Plan Bootstrap & Fallback Failures | CF1 | P0/P1 |
| FAM-THREAD | Meal Thread Resolution Failures | CF2 | P0/P1 |
| FAM-GROUND | Grounding / Estimation Failures | CF2 | P0/P1 |
| FAM-CLARIFY | Clarification Strategy Failures | CF2 | P0/P1 |
| FAM-CORR | Correction / Versioning Failures | CF2 | P0/P1 |
| FAM-SYNC | Budget / Cross-Surface Sync Failures | CF3 | P0 |
| FAM-STATE | Proposal / Commit State Boundary Failures | CF1/CF3/CF4/CF5 | P0 |
| FAM-CAL | Body Observation & Calibration Failures | CF4 | P1 |
| FAM-RESCUE | Rescue & Coaching Failures | CF5 | P1 |
| FAM-REC | Recommendation & Preference Failures | CF6 | P1/P2 |
| FAM-PROACTIVE | Proactive Triggering Failures | CF7 | P1/P2 |
| FAM-CHANNEL | Cross-Channel / Entry Modality Failures | CF8 | P1 |
| FAM-TRACE | Trace / Eval Artifact / Governance Failures | CF9 | P0/P1 |
| FAM-UX | Response Quality / Product-Fit Failures | cross-cutting | P2/P3 |

---

## Detailed Failure Families

## FAM-BOOT — Plan Bootstrap & Fallback Failures

### 範圍
與 onboarding、body plan bootstrap、budget bootstrap、no-plan degraded behavior 相關的失敗。

### Affected Capability Family
- CF1 Plan Bootstrap & Fallback

### Common Subfamilies

#### FAM-BOOT-01 Missing-plan hallucination
系統在沒有 active body plan 時，仍假裝知道剩餘預算或每日目標。

- default severity: `P0_blocker`
- affected objects: `body_plan`, `day_budget_ledger`
- likely journeys: J

#### FAM-BOOT-02 Bootstrap truth mismatch
onboarding 完成後，chat 與 UI 對 target kcal / TDEE 的數字不一致。

- default severity: `P0_blocker`
- affected journeys: A

#### FAM-BOOT-03 Invalid fallback guidance
沒有 plan 時的引導不誠實、不完整、或讓 user 以為系統已設定目標。

- default severity: `P1_major`

#### FAM-BOOT-04 Silent bootstrap failure
應建立 `body_plan` / `day_budget_ledger` 卻沒有建立，但表面上看起來像成功。

- default severity: `P0_blocker`

---

## FAM-THREAD — Meal Thread Resolution Failures

### 範圍
與 `meal_thread` 的建立、attach、same-meal refinement、thread identity、commit candidacy 有關的失敗。

### Affected Capability Family
- CF2 Meal Thread Resolution

### Common Subfamilies

#### FAM-THREAD-01 Wrong-thread attachment
補充資訊 attach 到錯的 meal thread。

- severity: `P0_blocker`
- journeys: C, D, K, O, P

#### FAM-THREAD-02 False new-thread creation
本應更新既有 meal thread，卻錯誤新建一個新 thread。

- severity: `P1_major`

#### FAM-THREAD-03 Missing-thread carryover
多輪 clarify 時，第二輪回答沒有延續第一輪 draft state。

- severity: `P0_blocker`

#### FAM-THREAD-04 Invalid commit candidacy
在資訊不足時 commit；或資訊已足夠時仍不 commit。

- severity: `P0_blocker`

---

## FAM-GROUND — Grounding / Estimation Failures

### 範圍
與 exact lookup、generic estimate、range honesty、evidence use、macro plausibility 相關的失敗。

### Affected Capability Family
- CF2 Meal Thread Resolution

### Common Subfamilies

#### FAM-GROUND-01 False exactness
把 heuristic / sibling variant / rough estimate 假裝成 exact truth。

- severity: `P0_blocker`
- journeys: B, C, D, O, P

#### FAM-GROUND-02 Missed exact grounding
明明可 exact lookup，卻走成 generic estimate 或 clarify。

- severity: `P1_major`

#### FAM-GROUND-03 Unreasonable estimate range
估值範圍過窄、過寬、或中心值明顯不合理。

- severity: `P1_major`

#### FAM-GROUND-04 Evidence omission
可用的 brand / category / user-provided signal 沒有納入估算。

- severity: `P1_major`

#### FAM-GROUND-05 Macro-calorie incoherence
protein/carbs/fat 與 kcal 關係明顯不合理，卻仍當可靠 truth 展示。

- severity: `P1_major`

---

## FAM-CLARIFY — Clarification Strategy Failures

### 範圍
與 clarify-before-estimate、estimate-with-followup、followup quality、是否過問 / 漏問有關的失敗。

### Affected Capability Family
- CF2 Meal Thread Resolution

### Common Subfamilies

#### FAM-CLARIFY-01 Missing required followup
應追問卻不追問。

- severity: `P0_blocker`
- journeys: C, D

#### FAM-CLARIFY-02 Unnecessary followup
資訊已足夠仍硬追問，造成 friction。

- severity: `P1_major`

#### FAM-CLARIFY-03 Wrong clarify mode
應走 `clarify_before_estimate` 卻給數字；或應走 `estimate_with_followup` 卻完全不給範圍。

- severity: `P0_blocker`

#### FAM-CLARIFY-04 Low-value question
追問內容太開放、不可回答、或沒抓到高影響變因。

- severity: `P1_major`

---

## FAM-CORR — Correction / Versioning Failures

### 範圍
與 correction、supersede、item removal、non-target preservation、version lineage 相關的失敗。

### Affected Capability Family
- CF2 Meal Thread Resolution

### Common Subfamilies

#### FAM-CORR-01 Non-target corruption
修正 A item，卻連帶改壞 B item。

- severity: `P0_blocker`
- journeys: K

#### FAM-CORR-02 No new version lineage
應建立新 version / supersede 舊版本，卻直接覆寫。

- severity: `P1_major`

#### FAM-CORR-03 Failed item removal semantics
說「我沒喝」卻刪掉整個 meal thread，或狀態沒更新。

- severity: `P1_major`

#### FAM-CORR-04 Correction not propagated
chat 顯示已修正，但 ledger / UI / later query 仍是舊數字。

- severity: `P0_blocker`

---

## FAM-SYNC — Budget / Cross-Surface Sync Failures

### 範圍
與 ledger truth、remaining / overshoot、chat / UI same-number invariant 相關的失敗。

### Affected Capability Family
- CF3 Budget & Cross-Surface Sync

### Common Subfamilies

#### FAM-SYNC-01 Chat/UI numeric mismatch
chat 的 consumed / remaining / overshoot 與 UI 不同。

- severity: `P0_blocker`
- journeys: A, B, E, G, H, J, K

#### FAM-SYNC-02 Ledger mutation mismatch
meal commit / correction 後，ledger truth 沒有更新或更新錯誤。

- severity: `P0_blocker`

#### FAM-SYNC-03 Overshoot display mismatch
overshoot 已存在，但 chat 沒說、UI 沒警告、或兩邊數字不同。

- severity: `P0_blocker`

#### FAM-SYNC-04 Wrong degraded sync behavior
在 degraded mode 下 UI / chat 對「是否有目標」給出矛盾訊號。

- severity: `P1_major`

---

## FAM-STATE — Proposal / Commit State Boundary Failures

### 範圍
與 draft、proposal、accepted、committed state 被混淆有關的失敗。

### Affected Capability Families
- CF1, CF3, CF4, CF5

### Common Subfamilies

#### FAM-STATE-01 Proposal treated as committed
proposal 尚未接受，卻已改動 committed truth。

- severity: `P0_blocker`

#### FAM-STATE-02 Draft treated as committed
clarify draft 尚未確認就進 ledger / UI committed state。

- severity: `P0_blocker`

#### FAM-STATE-03 Committed state mislabeled as draft
明明已接受 / 已 commit，但 product surface 仍顯示未生效。

- severity: `P1_major`

#### FAM-STATE-04 Ambiguous state transition
使用者接受 / 拒絕後，state transition 不明確，導致後續 flow 不可預期。

- severity: `P1_major`

---

## FAM-CAL — Body Observation & Calibration Failures

### 範圍
與體重觀測、trend interpretation、校準候選、校準 proposal、confirmed recalibration 有關的失敗。

### Affected Capability Family
- CF4 Body Observation & Calibration

### Common Subfamilies

#### FAM-CAL-01 Observation not reflected
新體重被記錄，但後續 chat / UI 讀不到最新值。

- severity: `P1_major`
- journeys: G, H

#### FAM-CAL-02 Silent recalibration
系統未經 proposal / confirm 就直接重寫 body plan。

- severity: `P0_blocker`
- journey: I

#### FAM-CAL-03 Premature calibration proposal
資料不足仍提出 calibration proposal。

- severity: `P1_major`

#### FAM-CAL-04 Calibration result not propagated
proposal 接受後，budget / recommendation context 未更新。

- severity: `P1_major`

---

## FAM-RESCUE — Rescue & Coaching Failures

### 範圍
與 rescue proposal、spread、negotiation、future overlay 有關的失敗。

### Affected Capability Family
- CF5 Rescue & Coaching Negotiation

### Common Subfamilies

#### FAM-RESCUE-01 Rescue embedded in intake reply
rescue 應獨立一則訊息，卻被塞進 intake 回覆裡。

- severity: `P1_major`
- journeys: E, F

#### FAM-RESCUE-02 Wrong negotiation interpretation
把抱怨當拒絕，或把拒絕當接受。

- severity: `P1_major`

#### FAM-RESCUE-03 Wrong spread semantics
spread days / daily adjustment 算錯或與 proposal 描述不一致。

- severity: `P1_major`

#### FAM-RESCUE-04 Accepted rescue not applied
proposal 已接受，但 future overlay / inbox mirror 沒更新。

- severity: `P1_major`

---

## FAM-REC — Recommendation & Preference Failures

### 範圍
與 recommendation ranking、budget fit、preference learning、recommendation-to-intake handoff 有關的失敗。

### Affected Capability Family
- CF6 Recommendation & Preference Learning

### Common Subfamilies

#### FAM-REC-01 Budget-unaware recommendation
推薦與剩餘預算或 body plan 明顯衝突。

- severity: `P1_major`

#### FAM-REC-02 Preference miss
已知偏好未被反映，或明確忌口被忽略。

- severity: `P1_major`

#### FAM-REC-03 False memory write
系統把暫時偏好誤寫成長期偏好，或把模糊訊號當確定偏好。

- severity: `P1_major`

#### FAM-REC-04 Broken handoff to intake
使用者說「幫我記這個」但沒有正確進入 intake flow。

- severity: `P1_major`

---

## FAM-PROACTIVE — Proactive Triggering Failures

### 範圍
與 proactive trigger eligibility、suppression、cooldown、explainability 相關的失敗。

### Affected Capability Family
- CF7 Proactive Triggering

### Common Subfamilies

#### FAM-PROACTIVE-01 Unexplainable outreach
系統主動發訊，但無法說明為何現在觸發。

- severity: `P1_major`

#### FAM-PROACTIVE-02 Suppression ignored
使用者已靜音或 cooldown 中，仍收到觸發。

- severity: `P1_major`

#### FAM-PROACTIVE-03 Wrong target object
本應針對 meal log reminder，卻錯打到 rescue / recommendation flow。

- severity: `P1_major`

#### FAM-PROACTIVE-04 Trigger without safe handoff
觸發發生了，但沒有對應 proposal / chat / actionable next step。

- severity: `P2_moderate`

---

## FAM-CHANNEL — Cross-Channel / Entry Modality Failures

### 範圍
與 Native / Web / LINE / LIFF / image / voice 入口之間的 shared truth 對齊失敗有關。

### Affected Capability Family
- CF8 Cross-Channel / Entry Modality Integration

### Common Subfamilies

#### FAM-CHANNEL-01 Channel-specific truth fork
某個 channel 長出獨立 state，沒有回到 shared product objects。

- severity: `P0_blocker`

#### FAM-CHANNEL-02 Lost normalization
voice / image / quick action 入口沒有被正規化進相同 product object workflow。

- severity: `P1_major`

#### FAM-CHANNEL-03 Invalid capability promise
在不支援的 channel 假裝支援某項 native-only capability。

- severity: `P1_major`

#### FAM-CHANNEL-04 Surface handoff break
從 notification / UI action / recommendation card 點入後，無法延續原本上下文。

- severity: `P1_major`

---

## FAM-TRACE — Trace / Eval Artifact / Governance Failures

### 範圍
與 request trace、artifact linkage、runner evidence、claim integrity 相關的失敗。

### Affected Capability Family
- CF9 Trace, Explainability & Governance Surface

### Common Subfamilies

#### FAM-TRACE-01 Missing trace linkage
有 user-visible state change，但缺少 request / artifact linkage。

- severity: `P0_blocker`

#### FAM-TRACE-02 Claimed pass without evidence
bundle 宣稱通過，但沒有對應 artifact / runner / parity evidence。

- severity: `P0_blocker`

#### FAM-TRACE-03 State/trace divergence
trace 顯示的 state transition 與實際 product truth 不一致。

- severity: `P1_major`

#### FAM-TRACE-04 Non-auditable proposal transition
proposal created / accepted / rejected 但 trace 無法重建。

- severity: `P1_major`

---

## FAM-UX — Response Quality / Product-Fit Failures

### 範圍
與功能 correctness 無關，但會影響產品感受、chat-first fit、產品信任的失敗。

### Affected Capability Families
- cross-cutting

### Common Subfamilies

#### FAM-UX-01 Overlong response
回覆把完整分析全倒給使用者，不像聊天。

- severity: `P2_moderate`

#### FAM-UX-02 Under-informative response
回覆太短，漏掉必要資訊或 next step。

- severity: `P2_moderate`

#### FAM-UX-03 Wrong uncertainty expression
明明不確定卻太自信；或本可直接回答卻過度保守。

- severity: `P2_moderate`

#### FAM-UX-04 Non-product tone
語氣像 generic assistant，不像這個產品的 chat-first companion。

- severity: `P3_minor`

#### FAM-UX-05 Proposal wording friction
proposal / rescue / calibration 的 wording 讓 user 感到被責備、被命令、或過度教條。

- severity: `P2_moderate`

---

## Cross-Family Invariant Violations

以下 invariants 一旦被打破，通常應視為高優先級 failure：

1. **Shared truth violated**
   - chat / UI / trace / later query 不一致

2. **Proposal boundary violated**
   - proposal / draft / committed state 被混淆

3. **Honest degradation violated**
   - 缺資料時假裝精準

4. **Non-target preservation violated**
   - correction 破壞 unrelated truths

5. **Chat-first violated**
   - 主要互動被推回 UI，或 UI 成為唯一能完成的 agent-driven flow

6. **Explainable proactive violated**
   - 主動介入無法解釋或無法 suppress

---

## Journey-to-Failure Hotspots

| Journey | Likely Failure Families |
|---|---|
| A | FAM-BOOT, FAM-SYNC, FAM-TRACE |
| B | FAM-THREAD, FAM-GROUND, FAM-SYNC |
| C | FAM-CLARIFY, FAM-THREAD, FAM-STATE |
| D | FAM-CLARIFY, FAM-THREAD, FAM-GROUND |
| E | FAM-SYNC, FAM-STATE, FAM-RESCUE |
| F | FAM-RESCUE, FAM-STATE, FAM-SYNC |
| F2 | FAM-RESCUE, FAM-STATE |
| G | FAM-CAL, FAM-SYNC |
| H | FAM-CAL, FAM-SYNC, FAM-CHANNEL |
| I | FAM-CAL, FAM-STATE, FAM-PROACTIVE |
| J | FAM-BOOT, FAM-SYNC |
| K | FAM-CORR, FAM-THREAD, FAM-SYNC |
| L | FAM-REC, FAM-SYNC |
| M | FAM-REC, FAM-STATE |
| N | FAM-PROACTIVE, FAM-TRACE |
| O | FAM-CHANNEL, FAM-THREAD, FAM-GROUND |
| P | FAM-CHANNEL, FAM-THREAD, FAM-GROUND |

---

## 標記規則建議

### 單一案例標記規則

- 每個失敗案例 **必須有 1 個 primary failure family**
- 可有 0~3 個 secondary failure families
- 若 primary 與 severity 衝突，以 user-visible product harm 為準，不以實作難度為準

### Regression 收錄優先級

優先收錄：
- 所有 `P0_blocker`
- 反覆出現的 `P1_major`
- founder 特別在意的 `FAM-UX-05`, `FAM-CLARIFY-03`, `FAM-SYNC-01`

### Founder Review 建議標欄

```yaml
founder_review:
  pass: true | false
  primary_failure_family:
  severity:
  product_fit_notes:
  should_promote_to_regression: true | false
```

---

## 如何使用本文件

### 用於 bundle eval 設計
每個 bundle eval 應明確標註：
- 主要覆蓋哪些 failure families
- 哪些 families 是 hard-fail

### 用於 replay pack triage
production replay 或 founder replay 發現問題時，先標 taxonomy，再決定：
- 改 spec
- 改 runtime policy
- 改 tool contract
- 改 renderer
- 改 eval oracles

### 用於 deep capability spec
current-wave deep spec 應明確列出每個子 capability 最常見的 failure families。

---

## Definition of Done for This Document

本文件完成，表示：

- whole-product 主要 failure families 已完整定義
- journeys A–P 都可對應到主要 failure hotspots
- shared product object / capability family / failure family 三者之間已有穩定 vocabulary
- 下游 grading rubric 可直接引用本文件作為失敗分類基底

本文件完成，不表示：

- 每一個 subfamily 都已有完整 automated detector
- bundle eval 已全部覆蓋所有 failure families
- production replay taxonomy 已凍結

---

## 下一步

1. 建立 `V2_GRADING_RUBRIC.md`
2. 在 current-wave deep capability spec 中，為 F1/F2/F3 列出對應常見 failure families
3. 在 bundle eval packs 中加入 failure-family coverage 欄位

---

## 歷史

- 2026-04-24: v1 初始版本，建立 whole-product failure taxonomy，供 rubric、bundle eval、replay triage 使用
