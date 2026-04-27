# BuilderSpace Provider Profile

## Source of Truth

- Raw OpenAPI: [docs/provider/builderspace_openapi.txt](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider/builderspace_openapi.txt)
- Runtime evidence:
  - [artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T152106.173839Z_natural-probe_targeted_B1-003_77b311.json](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T152106.173839Z_natural-probe_targeted_B1-003_77b311.json)
  - [artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T152106.176917Z_natural-probe_full_B1-001-B1-002-B1-003-B1-004-B1-005-B1-006_9344e9.json](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T152106.176917Z_natural-probe_full_B1-001-B1-002-B1-003-B1-004-B1-005-B1-006_9344e9.json)
  - [artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T171316.914759Z_natural-probe_full_B1-001-B1-002-B1-003-B1-004-B1-005-B1-006_5f54bf.json](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T171316.914759Z_natural-probe_full_B1-001-B1-002-B1-003-B1-004-B1-005-B1-006_5f54bf.json)
  - [artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T172310.969052Z_natural-probe_targeted_B1-006_242ece.json](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T172310.969052Z_natural-probe_targeted_B1-006_242ece.json)
  - [artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T180042.469158Z_natural-probe_targeted_B1-005_b176c8.json](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T180042.469158Z_natural-probe_targeted_B1-005_b176c8.json)
  - [artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T181457.009924Z_natural-probe_full_B1-001-B1-002-B1-003-B1-004-B1-005-B1-006_b5362b.json](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/wave1_phase_b_minimal_tool_loop_smoke_20260427T181457.009924Z_natural-probe_full_B1-001-B1-002-B1-003-B1-004-B1-005-B1-006_b5362b.json)
  - [artifacts/manager_candidate_eval_20260427T163744.232384Z_kimi-k2-5_MC-001-MC-002-MC-003-MC-004_f30b8a.json](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/manager_candidate_eval_20260427T163744.232384Z_kimi-k2-5_MC-001-MC-002-MC-003-MC-004_f30b8a.json)
  - [artifacts/manager_candidate_eval_20260427T163956.258231Z_gemini-3-flash-preview_MC-001-MC-002-MC-003-MC-004_a6ed6e.json](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/manager_candidate_eval_20260427T163956.258231Z_gemini-3-flash-preview_MC-001-MC-002-MC-003-MC-004_a6ed6e.json)

## Current Capability Status

| Capability | Status | Evidence |
| --- | --- | --- |
| OpenAI-compatible chat completions | documented | OpenAPI |
| `tools` request field | documented | OpenAPI |
| `tool_choice` request field | documented | OpenAPI |
| request `additionalProperties: true` | documented | OpenAPI |
| `response_format.type=json_object` | artifact-proven | current adapter/runtime artifacts |
| `response_format.type=json_schema` request acceptance | artifact-observed | B-1 targeted/full smoke artifacts |
| forced synthetic decision tool transport | contract-breach observed | `B1-003` targeted/full smoke artifacts |
| `gpt-5` token parameter conversion | documented | OpenAPI |
| `kimi-k2.5` / `gpt-5` temperature constraint | documented | OpenAPI |
| provider obeys forced `tool_choice` | unknown / probe-needed | no compliant artifact yet |

## Rules

- Do not infer provider capability from OpenAI compatibility alone.
- Every new transport capability must be proven by targeted artifact.
- If the provider accepts a request but violates the expected shape, record a contract breach or capability gap.
- Do not hide fallback behavior; fallbacks must stay trace-visible.
- Adapter code may choose transport mode, but shared branch-contract helpers remain the schema source of truth.
- Adapter code must not own product semantics.

## Current Interpretation

BuilderSpace exposes an OpenAI-compatible `/v1/chat/completions` surface, but runtime evidence still distinguishes:

- request-shape acceptance
- schema-adherent structured response
- forced tool-call obedience

Treat `json_schema` and synthetic decision tool transport as separate capability probes. Acceptance of the request surface alone is not proof that the model/provider will return the required structured payload.

## Manager Strategy Split

Provider capability and manager-model suitability are tracked separately.

- This file stays focused on BuilderSpace capability and transport evidence.
- Manager-role selection hypotheses live in [docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md).

Current working split:

- `deepseek` = default build-loop model
- `grok-4-fast` = low-cost transport probe
- `kimi-k2.5` = primary future manager candidate hypothesis
- `gemini-3-flash-preview` = secondary future manager candidate hypothesis
- `gpt-5` = expensive manual baseline only

Manager-candidate artifacts must stay in a separate family such as `artifacts/manager_candidate_eval_*.json` and must always remain outside B-1 readiness claims.

## B1-006 Structured-Decision Observation

Recent B-1 runtime evidence now distinguishes `B1-006` more clearly:

- full smoke with `deepseek` under the corrected `common_commercial_drink` branch still failed at Pass 1 with `failure_family = non_json_model_output`
- targeted `B1-006` with `builderspace-grok-4-fast-b1006-probe` produced a legal Pass 1 decision:
  - `manager_action = call_tools`
  - `interaction_family = nutrition_info_query`
  - `response_mode = info_answer`
  - `tool_calls = [lookup_generic_food]`
- the same targeted probe continued into Pass 2 without a provider runtime blocker

Current interpretation:

- `deepseek` remains acceptable as a cheap build-loop baseline
- `deepseek` is now likely unsuitable for at least some B-1 structured-decision branches
- `grok-4-fast` has stronger artifact support as a low-cost structured-decision comparison model
- this evidence supports diagnosis only; it does not by itself authorize same-slice full-smoke routing expansion

## B1-005 Listed-Ingredient Tool-Selection Observation

Recent B-1 runtime evidence now distinguishes `B1-005` more clearly:

- latest full-smoke artifacts still show `deepseek` can drift into `search` on the listed-ingredient branch instead of canonical item-level lookup requests
- targeted `B1-005` with `builderspace-grok-4-fast-b1005-probe` produced a legal Pass 1 listed-ingredient decision:
  - `manager_action = call_tools`
  - `requested_read_tools = [lookup_generic_food, lookup_generic_food, lookup_generic_food]`
  - `tool_calls` stayed item-level for `豆干`, `海帶`, and `貢丸`
- the same targeted probe continued into Pass 2 without a provider runtime blocker

Current interpretation:

- `deepseek` remains acceptable as a cheap build-loop baseline
- `deepseek` is now likely unreliable for `B1-005` Pass 1 listed-ingredient tool selection
- `grok-4-fast` has stronger artifact support as a low-cost structured-decision comparison model for this branch
- the follow-up full-smoke artifact now supports a branch-scoped route limited to `B1-005 Pass 1`
- this evidence does not mean `B1-005` is semantically complete; readiness remains blocked by separate Pass 2 trace/latency gaps elsewhere

## First Live Candidate Eval Observations

The first BuilderSpace-only `manager_candidate_eval` pass produced readable artifacts for both current manager candidates:

- `kimi-k2.5`
  - `manager_candidate_status`: `artifact_observed`
  - clean completion on `MC-002` and `MC-003`
  - provider-runtime failures on `MC-001` and `MC-004`
  - aggregate usage: `8993` total tokens
  - aggregate latency: `119643 ms`
- `gemini-3-flash-preview`
  - `manager_candidate_status`: `artifact_observed`
  - clean completion on `MC-002`
  - provider-runtime failures on `MC-001`, `MC-003`, and `MC-004`
  - aggregate usage: `3766` total tokens
  - aggregate latency: `51356 ms`

Current interpretation from these artifacts:

- Both candidates are now artifact-backed observations rather than pure hypotheses.
- Neither candidate is production-selected.
- `MC-002` shows both candidates can complete a basic Pass 1 / Pass 2 boundary-obedient manager path under BuilderSpace.
- `kimi-k2.5` currently has the stronger artifact on the multi-context proxy (`MC-003`).
- `MC-004` still exposes unresolved provider/runtime instability for both candidates, so memory-posture suitability remains inconclusive.
- These artifacts remain candidate-eval evidence only and must not be reused as B-1 readiness proof.
