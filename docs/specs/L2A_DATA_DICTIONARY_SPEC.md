# L2A Data Dictionary Spec

## 1. 目的

本文件是 `L2 Data / State Spec` 的實作級補件。

它回答：

- canonical enums 的合法值集合
- 各欄位的型別、optional 規則、default posture
- 哪些欄位禁止 agent 自創新值
- 哪些欄位缺失不得阻止 commit

本文件的定位是：

- `L2` 定資料模型
- `L2A` 定資料字典與合法值

如果 `L2` 與 `L2A` 有衝突，以 `L2A` 的 enum / field legality 為準。

---

## 2. General Rules

### 2.1 Enum 值不可自創

對於本文件列為 enum 的欄位：

- agent 不得自創新值
- runtime 不得用自由文字替代 enum
- 若輸入無法可靠映射，必須回退到本文件指定的 `unknown` / `other` / `none` 類值

### 2.2 Optional 欄位缺失不得污染 canonical truth

以下類型欄位可缺失：

- 細分類
- preference tags
- cuisine family
- secondary explanation metadata

缺失時：

- canonical write 可繼續
- 不得用猜測值硬補

### 2.3 Canonical 欄位與 derived 欄位分離

本文件只規範 canonical fields 與 canonical enum。

像：

- UI display labels
- retrieval-only labels
- prompt-only summary labels

不是 canonical enum，不得反向寫回 canonical object。

Food knowledge mention-sense labels are evidence metadata, not canonical `MealItem` enum values. They must not be written into `item_kind`, `item_role`, `cuisine_family`, or `preference_tags` unless explicitly mapped through existing L2A values.

---

## 3. Global Primitive Conventions

### 3.1 ID 欄位

- 所有 `*_id` 為 integer primary/foreign key
- 外部 string ids 只允許出現在：
  - `user_id`（external app-facing id）
  - `request_id`
  - `trace_id`

### 3.2 Time 欄位

- `created_at`, `updated_at`, `recorded_at`, `committed_at`, `observed_at`, `occurred_at`：
  - type = timezone-aware datetime when in Python/runtime
  - persistence layer 可存 DB datetime
- `local_date`：
  - type = string
  - format = `YYYY-MM-DD`
- `timezone`：
  - type = string
  - preferred = IANA timezone id

### 3.3 JSON metadata 欄位

- `*_json`, `metadata`, `reason_payload`, `effect_payload`：
  - type = JSON object unless explicitly listed as array
- JSON metadata 只可承載 typed metadata
- 不可把整段自由文字 transcript 當 canonical metadata 存入

---

## 4. MessageEvent Dictionary

### 4.1 `channel`

合法值：

- `line`
- `liff`
- `web`
- `api`
- `system`
- `unknown`

### 4.2 `event_type`

合法值：

- `message`
- `postback`
- `quick_action`
- `system_event`
- `unknown`

### 4.3 `role`

合法值：

- `user`
- `assistant`
- `system`

---

## 5. MealThread Dictionary

### 5.1 `status`

合法值：

- `active`
- `committed`
- `superseded`
- `archived`

規則：

- v1 intake write-through 預設新 thread 可先落成 `committed`
- 若 thread 仍有 pending follow-up state，可暫為 `active`
- correction 造成舊 thread 退出活躍語境時，不直接刪除；必要時標 `superseded` 或 `archived`

### 5.2 `thread_kind`

合法值：

- `text_intake`
- `manual_entry`
- `recommendation_handoff`
- `historical_correction`

default：

- `text_intake`

### 5.3 `latest_commit_source`

合法值：

- `chat`
- `ui`
- `system`
- `import`

### 5.4 `followup_status`

合法值：

- `none`
- `open`
- `resolved`
- `abandoned`

### 5.5 `pending_question_key`

合法值：

- `meal_boundary`
- `portion_size`
- `missing_component`
- `timing`
- `brand_identity`
- `none`

default：

- `none`

---

## 6. MealVersion Dictionary

### 6.1 `version_status`

合法值：

- `active`
- `superseded`
- `deleted`

v1 規則：

- correction 建立新 version 時，舊版只能變 `superseded`
- v1 不鼓勵真正 `deleted`

### 6.2 `version_reason`

合法值：

- `new_intake`
- `clarification_completion`
- `correction`
- `historical_correction`
- `system_reconciliation`

### 6.3 `resolution_status`

合法值：

- `candidate_meal`
- `draft_unresolved`
- `completed_meal`

這與舊 runtime 相容，但只允許這三個值。

### 6.4 `estimate_mode`

合法值：

- `exact_item`
- `anchored_component`
- `heuristic_fallback`
- `llm_only`
- `unknown`

### 6.5 `confidence`

合法值：

- `high`
- `medium`
- `low`

---

## 7. MealItem Dictionary

### 7.1 `item_kind`

合法值：

- `food`
- `drink`
- `condiment`
- `unknown`

禁止值示例：

- `snack`
- `dessert`
- `afternoon_tea`

這些若需要表達，應進 `item_role` 或 `preference_tags`，不是 `item_kind`。

### 7.2 `staple_type`

合法值：

- `rice`
- `noodle`
- `bread`
- `porridge`
- `dumpling_wrapper`
- `none`
- `unknown`

規則：

- 若 item 不是主食或無明確主食屬性，用 `none`
- 不得自創 `snack_base`、`tea_base` 之類值

### 7.3 `item_role`

合法值：

- `main_protein`
- `main_carb`
- `vegetable`
- `side`
- `drink`
- `dessert`
- `sauce`
- `condiment`
- `addon`
- `mixed_main`
- `other`
- `unknown`

### 7.4 `classification_confidence`

合法值：

- `high`
- `medium`
- `low`

### 7.5 `item_confidence`

合法值：

- `high`
- `medium`
- `low`

### 7.6 `cuisine_family`

合法值：

- `taiwanese`
- `chinese`
- `japanese`
- `korean`
- `western`
- `southeast_asian`
- `fast_food`
- `cafe`
- `unknown`

optional，可缺。

### 7.7 `preference_tags`

type：

- array of strings

allowed posture：

- 可為空
- tag vocabulary 可演進
- 但不得拿它取代 canonical enum

也就是：

- `high_protein`
- `sweet_drink`
- `comfort_food`

可作 tag；但不能把 `item_kind` 改成這些值。

### 7.8 `is_removed`

type：

- boolean

default：

- `false`

---

## 8. Ledger Dictionary

### 8.1 `base_budget_source`

合法值：

- `body_plan`
- `manual_override`
- `system_default`

### 8.2 `entry_type`

合法值：

- `meal_consumption`
- `rescue_overlay`
- `calibration_adjustment`
- `manual_adjustment`

### 8.3 `source_object_type`

合法值：

- `meal_version`
- `proposal_option`
- `rescue_plan`
- `system`

### 8.4 `entry_status`

合法值：

- `active`
- `superseded`
- `voided`

### 8.5 Guardrail Math Inputs

以下欄位是 deterministic math 的正式輸入：

- `base_budget_kcal`
- `consumed_kcal`
- `rescue_overlay_total`
- `calibration_adjustment_total`
- `effective_budget_kcal`
- `remaining_kcal`

這些欄位不得由 LLM 直接自由生成。

---

## 9. BodyObservation / BodyPlan Dictionary

### 9.0 `BodyProfile` fields and enums

`BodyProfile` is the canonical bootstrap input object for the v1 budget-aware happy path.

#### `sex`

合法值：

- `female`
- `male`
- `prefer_not_to_say`
- `unknown`

#### `activity_level`

合法值：

- `sedentary`
- `light`
- `moderate`
- `active`
- `very_active`
- `unknown`

#### `goal_type`

合法值：

- `lose_weight`
- `maintain_weight`
- `gain_weight`
- `unknown`

rules：

- onboarding/bootstrap may write these fields from UI input or structured chat extraction
- deterministic target computation must consume canonical `BodyProfile` values rather than prompt-only summaries
- when `goal_type = gain_weight`, bootstrap may still seed `BodyPlan` and `DayBudgetLedger`, but rescue trigger activation should remain disabled

### 9.1 `observation_type`

合法值：

- `weight`

v1 先只允許 `weight`。

### 9.2 `plan_status`

合法值：

- `active`
- `superseded`
- `archived`

### 9.2A `safety_floor_kcal`

type：
- integer

canonical posture：
- active `BodyPlan.safety_floor_kcal` 是 `safety_floor(user)` 的正式 deterministic source

rules：
- v1 runtime 不可在 canonical state 缺值時隱性猜測 sex/gender 來決定 rescue floor
- onboarding / body-plan setup 可先以 external input 或 accepted proposal 寫入這個欄位
- rescue / recommendation / calibration guardrail math 應優先讀取這個欄位，而不是自行重建使用者屬性推論

### 9.2B `plan_source`

合法值：

- `onboarding_bootstrap`
- `accepted_proposal`
- `manual_override`
- `system_reconciliation`

v1 rule：

- the canonical happy path introduced in `L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md` should surface `onboarding_bootstrap` through metadata/read model when the first active body plan is seeded

### 9.2C Shared budget-aware read models

`CurrentBudgetView` and `ActiveBodyPlanView` are shared read surfaces, not alternate canonical stores.

rules：

- UI and chat may read them
- UI and chat must not treat them as independent writable truth
- they must derive from canonical `BodyPlan` and `DayBudgetLedger`

### 9.3 `proposal_type`

合法值：

- `monitor_only`
- `logging_quality_first`
- `budget_adjustment`
- `pace_adjustment`
- `plan_reset`

### 9.4 `proposal_status`

合法值：

- `open`
- `accepted`
- `rejected`
- `dismissed`
- `expired`

語意：

- `rejected` = 使用者明確拒絕此 proposal 或其核心方案語意。
- `dismissed` = 使用者先不要當前 proposal instance；它不是 permanent opt-out，不是 snooze，也不得被寫成長期偏好或 suppression truth。

### 9.5 `option_type`

合法值：

- `monitor_only`
- `logging_quality_first`
- `budget_adjustment`
- `pace_adjustment`
- `plan_reset`

### 9.6 `trigger_type`

合法值：

- `rescue_followup`
- `calibration_check`
- `recommendation_nudge`
- `logging_nudge`

### 9.7 `trigger_status`

合法值：

- `created`
- `delivered`
- `suppressed`
- `cancelled`

---

## 10. Commit-Critical vs Optional Fields

### 10.1 Meal commit-critical fields

下列欄位缺失時不得 commit：

- `meal_thread_id` or new thread creation path
- `meal_title`
- `estimated_kcal`
- `resolution_status`
- `occurred_at`
- `local_date`

### 10.2 Meal optional fields

下列欄位缺失時可 commit：

- `protein_g`
- `carb_g`
- `fat_g`
- `cuisine_family`
- `preference_tags`
- `staple_type`
- `item_role`

但若存在，必須符合本文件合法值。

---

## 11. Forbidden Drift Rules

以下行為明確禁止：

- 新增未定義 enum 值進 canonical object
- 把 UI label 寫回 canonical enum 欄位
- 把 prompt-only labels 存成 canonical classification
- 以自由文字取代 enum 欄位
- 因為來源模糊就亂猜高信度分類值

當映射不確定時：

- 使用 `unknown` / `other` / `none`
- 並透過 confidence 降級表達

---

## 12. Implementation Rule

任何 agent 在實作：

- SQLAlchemy models
- Pydantic models
- repository methods
- deterministic validators
- benchmark fixtures

時，若涉及本文件欄位，必須直接依本文件合法值集合編碼，不得自行擴展。
