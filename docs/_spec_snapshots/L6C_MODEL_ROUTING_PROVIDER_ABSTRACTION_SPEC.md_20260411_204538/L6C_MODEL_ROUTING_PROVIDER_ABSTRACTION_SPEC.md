# L6C Model Routing / Provider Abstraction Spec

## 1. 目的

這份 spec 定義：

- `logical model role` 如何映射到 provider adapter
- BuilderSpace 在 v1 的當前模型映射
- 未來移除 BuilderSpace 時，如何切到 direct provider
- fallback / failover 的正式邊界

本文件的角色是把：

- `L3.x` 的 pass-level logical roles
- `L6A` 的 framework / provider posture
- `L6B` 的 build strategy

收斂成真正可實作的 provider routing contract。

---

## 2. 設計前提

本文件建立在以下已定義前提上：

- runtime flow 只依賴 `logical model roles`
- provider model ID 不是 architecture truth
- BuilderSpace 是 `transitional provider facade`
- provider-specific quirks 不得上滲到 L3 contract
- fallback / failover 不得破壞 L5C safety guardrails

---

## 3. 核心原則

### 3.1 Graph-First, Role-Second

pass graph 必須先由 capability-domain spec 決定，再由本文件分配 `logical model role`。

正式治理規則見：

- [`L6E LLM Pass Design Policy Spec`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md)

本文件不應被解讀為：

- 所有 domain 都固定使用 4-pass
- 只要存在 `fast_router_model / strict_reasoner_model / response_writer_model`，每個 domain 就都必須有對應 pass
- `decision_mode: deterministic` 的 node 也應被映射到某個 LLM role

### 3.2 Role-First Routing

所有 runtime pass 先選 `logical model role`，再由 provider adapter 做最終模型決議。

禁止：

- pass 直接依賴 provider model ID
- 在 flow spec 裡寫死 `grok-4-fast` / `gpt-5` / `gemini-2.5-pro`

### 3.3 Adapter-Bounded Provider Knowledge

以下資訊只應存在 adapter / provider config：

- model name
- provider base URL
- token field 差異
- temperature quirks
- special `extra_body`
- provider-specific timeout / retry policy

### 3.4 Fallback Must Preserve Contract

failover / fallback 可以改 provider 或模型，但不能改：

- pass responsibility
- output schema
- commit boundary
- safety floor
- recommendation no-implicit-state rule

---

## 4. Logical Model Roles

v1 正式 role vocabulary：

- `fast_router_model`
- `strict_reasoner_model`
- `response_writer_model`
- `vision_parser_model`

必要時可在未來擴充：

- `tool_assisted_model`
- `cheap_review_model`

但 v1 先不把這兩個設為必要角色。

---

## 5. Pass-to-Role Mapping

本節只定義：

- 當某個 LLM-backed node 存在時，該 node 應映射到哪個 `logical model role`

本節不單獨決定：

- 每個 capability domain 的 canonical pass count
- 哪些 node 應優先由 deterministic layer 實作

若本節與 [`L6E LLM Pass Design Policy Spec`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md) 或 domain-specific `L3.x` spec 的 canonical graph 發生衝突，應以後者為準。

## 5.1 Intake

- `task_meal_link_pass` -> `fast_router_model`
- `decision_pass` -> `fast_router_model`
- `nutrition_resolution_pass` -> `strict_reasoner_model`
- `final_response_pass` -> `response_writer_model`

### 5.2 Recommendation

canonical default 依 `L6E` 採 3-node graph；以下只描述 LLM-backed node 存在時的 role mapping。

- `recommendation_context_pass` -> `fast_router_model`
- `candidate_generation_pass` -> `fast_router_model`（僅當 candidate generation 不是 deterministic retrieval/filtering，而是獨立 LLM synthesis 時）
- `ranking_and_selection_pass` -> `strict_reasoner_model`
- `recommendation_response_pass` -> `response_writer_model`

### 5.3 Calibration Proposal

canonical default 依 `L6E` 採 2-node graph；以下只映射真正的 LLM-backed nodes。

- `option_generation_pass` -> `strict_reasoner_model`
- `option_ranking_pass` -> `strict_reasoner_model`
- `proposal_response_pass` -> `response_writer_model`

### 5.4 Rescue

canonical default 依 `L6E` 採 2-3 node graph。

正式規則：

- `rescue_trigger_pass` 與 `rescue_assessment_pass` 若對應的是 overshoot math、horizon、viability、safety floor、cooldown 等 deterministic step，則不分配 LLM role
- 只有當某個 rescue node 的責任已被 domain spec 明確標示為 LLM-backed 時，才可在本節做 role mapping

常見 LLM-backed node 映射：

- `rescue_option_pass` -> `strict_reasoner_model`
- `rescue_response_pass` -> `response_writer_model`

### 5.5 Future Vision Intake

- image / multimodal meal parse -> `vision_parser_model`

---

## 6. Provider Adapter Contract

每個 provider adapter 至少應實作：

- `readiness()`
- `complete_with_trace()`
- stage / role aware model selection
- provider trace normalization
- transport retry policy
- error normalization

建議的 provider adapter 介面能力：

1. `resolve_model(role, stage)`
2. `build_request(role, stage, prompt, payload)`
3. `execute_request(...)`
4. `normalize_response(...)`
5. `normalize_error(...)`
6. `emit_provider_trace(...)`

### 6.1 Adapter Output Contract

每次呼叫 provider 後，至少應輸出：

- parsed payload
- normalized trace
- provider name
- effective model ID
- role
- stage
- transport attempts
- fallback_used

---

## 7. BuilderSpace Current Mapping

BuilderSpace 是 v1 預設 provider facade。

### 7.1 Current Empirical Defaults

根據目前 founder testing：

- `grok-4-fast` 先作為 v1 預設主力模型
- 理由：
  - 速度快
  - 成本可控
  - 目前任務上的 founder-fit 效果佳
  - `deepseek` 在現階段較容易帶入多餘自帶推論

### 7.2 v1 Default BuilderSpace Mapping

建議預設：

- `fast_router_model` -> `grok-4-fast`
- `strict_reasoner_model` -> `grok-4-fast`
- `response_writer_model` -> `grok-4-fast`
- `vision_parser_model` -> `kimi-k2.5`（僅多模態路徑啟用時）

### 7.3 BuilderSpace Non-Default Candidates

可作為後續替換 / A-B 候選：

- `strict_reasoner_model` -> `gpt-5`
- `strict_reasoner_model` -> `gemini-2.5-pro`
- `fast_router_model` -> `gemini-3-flash-preview`
- `response_writer_model` -> `deepseek`（僅當實測確認沒有過多自帶推論時）

### 7.4 BuilderSpace Forbidden Usage

以下不應作為 v1 主流程預設：

- `supermind-agent-v1`

原因：

- 它帶內建 orchestrator / search / handoff 假設
- 容易污染我們自定義的 L3 contract 與 trace truth

---

## 8. Future Direct-Provider Mapping

當我們逐步降低 BuilderSpace 依賴時，direct provider mapping 應遵守同一組 roles。

### 8.1 OpenAI Direct

候選映射：

- `strict_reasoner_model` -> `gpt-5`

用途：

- nutrition resolution 精度不足時的升級
- calibration / rescue proposal 的高精度 reasoning

### 8.2 Gemini Direct

候選映射：

- `fast_router_model` -> `gemini-3-flash-preview`
- `strict_reasoner_model` -> `gemini-2.5-pro`
- `vision_parser_model` -> `gemini-2.5-pro` 或等價 vision-capable model

用途：

- 高速 routing
- reasoning alternative
- image / multimodal fallback

### 8.3 xAI Direct

候選映射：

- `fast_router_model` -> `grok-4-fast`
- `response_writer_model` -> `grok-4-fast`
- `strict_reasoner_model` -> `grok-4-fast`（在 founder-fit 與成本優先階段）

用途：

- 現階段主力 provider 候選

### 8.4 Moonshot / Kimi Direct

候選映射：

- `vision_parser_model` -> `kimi-k2.5`

用途：

- 多模態 intake / vision parse

---

## 9. Selection Policy

### 9.1 v1 Default Policy

v1 以：

- founder-fit
- latency
- cost
- contract stability

為優先。

因此：

- 預設先用單一主力模型跑通主流程
- 不先做多 provider 智能路由
- 不先追求理論最強模型組合

### 9.2 Upgrade Policy

只有在以下情況才應升級某角色模型：

1. Tier 1 benchmark 在該 role 對應 flow 上持續不達標
2. founder-fit 實測顯示明顯品質瓶頸
3. strict reasoning 任務出現 repeated soft-fail / regression

### 9.3 Downgrade / Cost Policy

若品質仍合格，且：

- latency 壓力過高
- cost 壓力過高

則可先考慮把：

- `response_writer_model`
- `fast_router_model`

降為更便宜 / 更快模型。

不應優先動：

- `strict_reasoner_model`

除非 benchmark 已證明不受影響。

---

## 10. Fallback / Failover Policy

## 10.1 Failure Classes

provider failure 至少分成：

- `transport_failure`
- `provider_timeout`
- `provider_http_error`
- `schema_parse_failure`
- `contract_validation_failure`
- `quality_degradation`

### 10.2 Allowed Failover Directions

#### `fast_router_model`

允許：

- BuilderSpace `grok-4-fast` -> direct Gemini fast router
- BuilderSpace `grok-4-fast` -> other fast low-cost router

#### `strict_reasoner_model`

允許：

- BuilderSpace current strict reasoner -> direct `gpt-5`
- BuilderSpace current strict reasoner -> direct `gemini-2.5-pro`

#### `response_writer_model`

允許：

- current response writer -> cheaper fast model

#### `vision_parser_model`

允許：

- BuilderSpace `kimi-k2.5` -> direct Gemini vision-capable model

### 10.3 Forbidden Failover Behavior

禁止：

- 因 failover 改變 pass output schema
- 因 failover 把 no-commit 變成 commit
- 因 failover 啟用 provider-native hidden orchestrator
- 因 failover 建立 implicit meal-intent / pending intake state
- 因 failover 繞過 safety floor / guardrail

### 10.4 Fallback Order

v1 建議順序：

1. same provider, same role, retry
2. same role, alternate mapped model
3. same role, alternate provider adapter
4. degrade output mode
   - abstain from commit
   - lower confidence
   - no derived macro
   - ask for clarification

### 10.5 Role-Specific Degrade Rule

- `fast_router_model` fail：
  - 可降級到保守 routing / clarify-first
- `strict_reasoner_model` fail：
  - 可降級到 no-commit / lower-confidence estimate
  - 不可用弱模型假裝高信心完成
- `response_writer_model` fail：
  - 可由 strict reasoner 代打簡化回應
- `vision_parser_model` fail：
  - 回退到 text-only intake path，要求使用者補文字

---

## 11. Trace Requirements for Routing

每次 model routing 都必須記：

- `logical_model_role`
- `effective_provider`
- `effective_model_id`
- `fallback_chain`
- `transport_attempt_count`
- `provider_specific_flags`
- `degrade_mode`

這些欄位應進入：

- pass trace
- release eval
- provider quality review

---

## 12. Build Phasing

### Phase 1-2

- 先只支援 BuilderSpace adapter
- 但已採 logical role routing

### Phase 3-5

- recommendation / calibration / rescue 全部接上 role-based routing
- 補齊 failover trace

### Phase 8

- 實作 direct provider adapters
- 驗證 BuilderSpace removal 不破壞 domain runtime

---

## 13. 與其他 specs 的關係

### 對 L3.x

- L3 只定 pass-to-role
- 不定 provider model ID

### 對 L5A / L5B / L5C

- eval / benchmark / safety 應以 role behavior 為主
- provider 切換不應破壞 benchmark case 與 safety oracle

### 對 L6A

- L6A 決定 framework / provider posture
- L6C 把 posture 轉成可實作 routing contract

### 對 L6B

- L6B 決定在何 phase 接入哪些 adapters
- L6C 決定 adapter 應長什麼樣

---

## 14. v1 Final Decision

v1 正式採：

- `role-first routing`
- `BuilderSpace as transitional facade`
- `grok-4-fast as empirical default primary mapping`
- `future provider removability as non-negotiable constraint`

若只用一句話總結：

`先把模型角色定穩，再讓 provider 去適配；不要讓 provider 名稱反過來定義 runtime。`
