# L3.1 Intake Runtime Contract Spec

> **Canonical status**
>
> 本文件定義 V2 intake 主流程的 canonical runtime contract。
> V2 不再採用 legacy multi-stage intake runtime；唯一合法的 intake 語義控制面是 single manager。
>
> Architecture truth 以 [app_v2_ideal_architecture_final.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/app_v2_ideal_architecture_final.md) 為準。

## 1. 目的

本文件回答以下問題：

- intake 主流程的唯一合法 runtime shape 是什麼
- manager、tools、execution guard、sidecar 各自擁有什麼責任
- clarify、correction、followup completion、default commit 分別在哪一層合法發生
- same-turn sync、evidence honesty、macro visibility、timeout / corruption failure family 怎麼進入主流程

本文件不回答：

- prompt wording
- benchmark wording oracle
- provider 成本策略

## 2. Canonical Runtime Shape

intake 主流程固定為：

1. `state_resolver`
2. `single_manager_loop`
3. `tool_batch`
4. `manager_final_decision`
5. `execution_guard`
6. `sidecar_truth`

補充規則：

- manager 是唯一語義控制面
- tools 只提供 evidence 或 state mutation result，不得偷做最終產品決策
- execution guard 只做 legality / honesty / sync validation，不得重寫 manager 的完成語義
- sidecar 是 deterministic truth mirror，不是主要決策面
- benchmark、replay pack、runner payload shape 不是主流程 architecture truth；它們只能驗證產品 truth

## 2.1 Product-Truth-First Build Frame

V2 intake runtime 的建置順序與判斷優先權固定為：

1. user-visible product behavior and end-state truth
2. canonical architecture and domain ownership
3. manager contract and runtime invariants
4. eval bundles, benchmark fixtures, replay packs, and runner payload shapes

Hard rules：

- 不得用 benchmark fixture shape、runner vocabulary、或 replay-pack implementation detail 反向主導 manager contract
- 若測試資產綠，但產品語義仍錯，應視為產品 bug 或 eval coverage/oracle 不完整
- 後續 EDD 的任何 runtime widening，都必須先符合這個 build frame，再談測試綠燈

## 3. Runtime Ownership

### 3.1 State Resolver

責任：

- 組裝 deterministic context
- 提供當前 `CurrentBudgetView`、active meal/thread、必要 recent messages、body plan 與 time context
- 做 text integrity gate 與 request-shape normalization

不可以：

- 自行決定 workflow effect
- 自行決定 commit / no-commit
- 自行決定 exact / generic / ask-followup posture

### 3.2 Single Manager

責任：

- 理解 user intent
- 決定 same-thread ownership / correction target / followup attachment
- 產生 tool plan
- 整合 tool outputs
- 輸出 final action、answer contract、uncertainty posture、evidence honesty posture

Manager round contract 固定為 bounded rounds：

- round 1：intent / ownership / tool plan
- tool batch
- final round：final action / answer contract / uncertainty posture / evidence honesty posture

規則：

- manager 必須使用 structured output
- parse / empty-content failure 最多允許 one bounded retry
- 不允許 open-ended self-loop

### 3.2A Canonical Manager Contract

manager 的正式一級語義欄位應至少包含：

- `intent`
- `workflow_effect`
- `target_attachment`
- `manager_action = call_tools | final`
- `tool_calls[]`
- `final_action`
- `answer_contract`
- `exactness`
- `confidence`
- `evidence_posture`
- `repair_ack`

Hard rules：

- 不得把自由文字 reasoning / thoughts 當正式 runtime contract
- 不得依賴 runner-specific payload fields 作為 manager vocabulary
- 不得用 renderer 文案補註來掩蓋 exactness、ownership、或 evidence honesty 的語義錯誤

### 3.2B Branch Contract Ownership

prompt 的責任是提供 task framing、family-level rules、與正向 examples；prompt 不是 hard-boundary correctness 的唯一保證。

對於 clarification-only、tool-call、logging / intake 這類互斥 branch：

- hard boundary 規則不得只存在 prompt wording
- schema / provider support 應在安全可行時盡量前移 impossible shape narrowing
- shared branch validation 必須拒絕 mixed-branch payload
- guard / verifier 必須保留 attribution 並防止 fake green

Provider adapters 可以：

- 套用 provider-specific response format 或 schema transport
- 呼叫 shared manager contract helpers
- 附加 provider metadata 與 attribution

Provider adapters 不可以：

- own product semantic rules
- 各自複製 hard-boundary branch policy
- auto-repair manager semantic decisions
- 把 manager contract violation 降格成 generic provider runtime noise

### 3.2C Shared Manager / Deterministic Ownership Invariant

LLM / Manager owns:

- composition sufficiency
- estimability
- whether to ask follow-up
- whether to call WebSearch
- exact/generic/component/basket posture
- attach target
- correction/removal target
- final workflow action
- user-facing response meaning

Deterministic code may only:

- validate schema
- validate source eligibility
- validate target existence / uniqueness
- enforce mutation legality
- hide unsupported kcal/macro/source facts
- reject/downgrade unsafe output
- request one bounded repair

Deterministic code must not:

- inspect raw user text or food name to decide semantic route
- classify a meal as unestimable before Manager output exists
- decide follow-up necessity
- decide WebSearch need
- create fallback kcal/macros
- rewrite Manager action to make a test pass

In short: deterministic code must not inspect raw user text, food name, case ID, or fixture label to decide semantic product behavior.

Guard, evidence policy, and validators operate after Manager-owned semantic output exists. They may reject illegal output, but they must not pre-route the turn or hide a Manager failure with deterministic product semantics.

### 3.3 Tool Batch

合法 tool outputs 包含：

- nutrition evidence candidates
- DB lookup results
- web search / extraction results
- correction / removal mutation result
- budget comparison / overshoot computation

每個 tool output 至少應包含：

- `evidence`
- `mutation_result`
- `provenance`
- `confidence`
- `failure_family`（若失敗）

### 3.3A Domain-Owned Tool Surface

manager 應優先看見 coarse domain tools，而不是大量 micro-tools。

canonical shape：

- `nutrition.lookup_or_estimate`
- `intake.resolve_attachment`
- `intake.persist_meal_mutation`
- `budget.project_and_compare`
- `runtime.build_sidecar_truth`

允許 adapter / facade 內部再委派較細 helper，但不得把 micro-tool topology 直接暴露成 manager 的長串 tool surface。

Hard rules：

- 不得用大量 micro-tools 取代 coarse domain tool surface
- 不得讓同一個 active service 同時擁有 orchestration、persistence semantics、與 rendering semantics
- 若某修復只能靠往既有 service 塞 case-specific fallback 才能過測試，該方向視為 architecture violation

### 3.4 Execution Guard

責任：

- legality 檢查
- evidence honesty 檢查
- same-turn sync 檢查
- macro/kcal coherence 的 visibility gate
- corruption / timeout / partial-report family 降級或阻擋

不可以：

- 改寫 manager 已完成的 action semantics
- 把 generic evidence 偽裝成 exact-like finalized answer

### 3.4A Guard Taxonomy

Execution Guard 固定拆成：

- `legality_guard`
- `honesty_guard`
- `sync_guard`

Guard 只允許：

- validate
- block
- downgrade
- request one bounded repair round

Guard 不允許：

- semantic rewrite
- renderer-side semantic masking

### 3.4B Semantic Ownership Boundary

Manager owns open-world food semantics. This includes composition sufficiency, whether the food is estimable now, whether a follow-up is required, exact/generic/component/basket/patterned-combo posture, target attachment, correction/removal target, and final action.

Deterministic runtime may validate only after Manager-owned structured output or Manager-requested evidence exists. It may reject an illegal commit, hide disallowed facts, downgrade visibility, block mutation, or request one bounded repair round.

Deterministic runtime must not use raw user input, food-name keyword checks, case IDs, fixture labels, or local food-family heuristics before the Manager pass to decide `composition_unknown`, `evidence_ineligible`, `ask_followup`, `estimate_allowed`, target attachment, or workflow effect. If a model cannot reliably make this first-pass decision, the allowed remedies are prompt/context/tool contract improvement, model-profile change, or post-Manager guard repair; the remedy is not a pre-Manager deterministic semantic shortcut.

Active intake runtime must not produce shadow/stub fallback nutrition facts. When exact, FoodDB, component, and approved web evidence are all unavailable, the estimate tool returns an `evidence_unavailable` packet with `estimated_kcal=0`, macros hidden, and canonical write denied. This packet is not a user-facing answer and not a mutation authority; Manager decides whether to ask follow-up, answer only, or attempt another allowed tool path.

若 manager 宣稱 `exact`，但 evidence 只支撐 `anchored` / `heuristic` / `unknown`：

- `honesty_guard` 必須 fail
- guard 必須回 `repair_request`
- 若 repair 後仍未降級 exactness posture，必須 hard block 或 degraded no-commit / ask-followup
- 不得用 renderer 自動加註「這只是估計」來混過 exactness conflict

### 3.5 Sidecar Truth

責任：

- mirror `/today`、budget、macro visibility、meal mutation result
- 提供 UI payload

規則：

- sidecar 必須服從 post-commit truth
- same-turn remaining / consumed / macro visibility 必須與 trace 與 `/today` 一致

## 4. Inputs and Outputs

### 4.1 Minimal Inputs

- `raw_user_input`
- `user_id`
- `message_event_id`
- `recorded_at`
- `timezone`
- `CurrentBudgetView`
- `ActiveMealView`
- `RecentCommittedMealsView`
- 必要 recent messages
- selected retrieval context

### 4.2 Final Outputs

主流程至少應產出：

- `manager_rounds`
- `tool_batch`
- `manager_final_decision`
- `guard_outcome`
- `answer_contract`
- `sidecar_truth`
- `trace_envelope`

### 4.3 Observability Minimum

每次 foreground run 的 trace 至少必須記錄：

- `manager_round_count`
- `manager_round_latency_ms[]`
- `tool_batch_latency_ms`
- `guard_latency_ms`
- `total_latency_ms`
- `tool_call_count`
- `repair_round_used`
- `request_failure_family`
- `latency_lane`

## 5. Clarify, Correction, and Commit Semantics

### 5.1 Clarify

若 portion / count / target attachment 不足以 commit：

- manager 應輸出 `ask_followup`
- sidecar 不得假裝已 commit
- macro 在不可信時不得顯示

### 5.2 Correction

correction contract 必須保證：

- same-thread ownership 正確
- target item replaced / removed 正確
- non-target items preserved
- corrected total 能由 preserved items + target delta 重組

### 5.3 Commit

default commit 僅在 evidence 與 target attachment 足夠時合法。

若 evidence posture 為：

- `exact`
- `near_exact`
- `generic_with_explicit_uncertainty`

則可依 guard 規則進入 commit；否則必須 ask-followup 或 degraded answer。

### 5.4 Downgrade Contract

`parse_failure`、`empty_content`、或 `repair_request` 都只允許一次 bounded retry。

第二次仍失敗時：

- 若 `ownership_reliable = true` 且 `target_attachment_reliable = true`
  - 可降級為 `draft_unresolved`
  - 必須回具體 follow-up
  - sidecar 必須明確反映 draft state，不得假裝 commit
- 若 `ownership_reliable = false` 或 `target_attachment_reliable = false`
  - 必須 `no_commit`
  - 只允許 degraded answer + concrete follow-up
  - 不得做 meal mutation

manager loop 在 second failure 後必須停止，不得再 open-ended self-loop。

## 6. Evidence Honesty

下列情況不得輸出 exact-like finalized answer：

- `eligibility = unusable`
- `exact_count = 0` 且沒有可信替代 posture
- `search_attempt_count = 0` 且 item 明顯需要 external evidence

manager 與 guard 必須共同保證：

- explanation 不可過度自信
- component breakdown 不可偽裝為 exact DB item
- generic estimate 必須明示 uncertainty
- `exactness` 必須由 evidence posture 支撐；不得以 renderer wording 掩蓋 honesty gap

## 7. Sync Contract

若 `canonical_commit = true`，以下四面必須一致：

- chat answer contract
- sidecar truth
- `/today/current-budget`
- trace budget summary

任一不一致即為 hard failure family。

## 8. Failure Families

主流程必須顯式分類以下 failure family：

- `encoding_corruption`
- `empty_content`
- `malformed_json`
- `tool_routing_gap`
- `evidence_honesty_gap`
- `same_turn_sync_gap`
- `timeout`
- `interrupted`
- `partial_report`

規則：

- `partial_report` 只能標 incomplete，不得假綠
- shard run 只能做定位；最終驗收必須有 full integration mode

### 8.1 Runner Timeout Contract

每個 eval / benchmark runner report 必須包含：

- `report_status`：`complete` 或 `incomplete`
- `execution_complete`：是否所有 expected cases 都完成，且沒有 runner interruption
- `expected_total_cases`
- `completed_cases`
- `full_integration`：只有非 sharded final run 才能為 true
- `shard_run`：`--case-id` 或 partial-selection run 必須為 true
- `final_gate_eligible`：只有 complete 且 full integration 時才可為 true
- `request_failure_family`：`timeout`、`interrupted`、`partial_report` 或 null

Hard rules：

- partial report 不得維持 green
- timeout report 必須是 `report_status = incomplete`
- shard report 可以用於定位，但不得當 final gate
- full EDD acceptance 必須要求 `final_gate_eligible = true`
- 產品能力 failure 與 runner infrastructure failure 必須分開分類

Mechanical implementation：

- `scripts/runner_timeout_contract.py`

Runner integration：

- current Manager-style intake-entry diagnostic runner
- current Manager-style intake-depth diagnostic runner
- `scripts/run_v2_founder_realism_eval.py`
- current promoted benchmark / Founder diagnostic runner

Guard tests：

- `tests/test_runner_timeout_contract.py`

### 8.2 Foreground Safety Ceiling

在沒有 eval-backed latency baseline 前，先固定 safety ceiling，不先把 lane budget 鎖死。

先固定：

- `max_manager_rounds`
- `max_repair_rounds = 1`
- `provider_timeout <= overall_foreground_timeout`
- `tool_timeout <= overall_foreground_timeout`
- `overall_foreground_timeout`
- 完整 latency trace

先不要固定：

- 每個 lane 的最終 hard latency budget

正式流程：

1. 先有 safety ceiling
2. 先收完整 trace
3. 再根據 baseline trace 收斂 lane-level budget
4. budget 成熟後再升 blocking gate

### 8.3 Timeout-After-Mutation Rule

若 timeout 發生在 persistence 前後，trace / sidecar / report 必須能區分 mutation 是否已經落地。

Hard rules：

- 不得讓 timeout 導致 duplicate commit 風險無法判讀
- 不得讓使用者看到語義不明的「可能有記到、也可能沒記到」狀態
- timeout family 與產品能力 failure 必須分開分類

## 9. Eval Alignment

official bundle、founder realism、promoted benchmark blocking regression 應統一驗：

- same-thread ownership
- non-target item preservation
- corrected total recomposition
- same-turn sync
- evidence honesty
- macro semantic truth
- text integrity
- timeout / partial-report status

## 10. Encoding Verification Rule

不要只靠 terminal / PowerShell 顯示判定 markdown 是否編碼污染。

正式判定順序：

1. 讀 file bytes
2. 以 UTF-8 / UTF-8 BOM decode 驗證
3. 掃描 replacement character、private-use characters、mojibake pattern
4. 只有 byte-level verifier 失敗，才可判定檔案污染

Terminal 顯示亂碼但 byte-level verifier 通過時，不得宣稱 file corruption。

## 11. Decommission Rule

任何舊多階段 intake runtime 的 vocabulary、schema、triage、tests、bootstrap path 都不得再成為 V2 canonical truth。

舊多階段文件與 artifacts 不得留在 active repo truth path，也不得被 active code、runners、tests 或 bootstrap path 引用。
