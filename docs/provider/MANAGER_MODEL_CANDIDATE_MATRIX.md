# Manager Model Candidate Matrix

This document separates BuilderSpace model roles for engineering decisions. It is not a production manager selection record and it is not B-1 readiness evidence.

## Scope

- `routine_smoke` and build-loop cost control
- transport sanity checks for manager-critical branches
- future manager-candidate evaluation planning

This document does not change parser, schema, prompt, or readiness semantics.

## Role Split

| Model | Role | Status | Production Selected | Routine Smoke Default | Notes |
| --- | --- | --- | --- | --- | --- |
| `deepseek` | `default_build_loop` | artifact-backed | `false` | `true` | Cheap default for routine smoke and regression. BuilderSpace docs do not explicitly label it as a reasoning model. `B1-003` tool-call decision transport failed under this profile. |
| `grok-4-fast` | `low_cost_transport_probe` | artifact-backed | `false` | `false` | Low-cost alternate used to cross-check manager decision transport when `deepseek` appears model-specific. Targeted `B1-003` probe produced a valid synthetic tool-call decision trace. |
| `kimi-k2.5` | `manager_candidate_primary` | `artifact_observed` | `false` | `false` | Primary future manager candidate hypothesis based on upstream agent-task, ToolCalls, JSON Mode, and long-context suitability. First live BuilderSpace eval produced a readable artifact with 2 successful cases and 2 provider-runtime failures. |
| `gemini-3-flash-preview` | `manager_candidate_secondary` | `artifact_observed` | `false` | `false` | Secondary future manager candidate hypothesis for reasoning and long-context work. First live BuilderSpace eval produced a readable artifact with 1 successful case and 3 provider-runtime failures. |
| `gpt-5` | `expensive_manual_baseline` | manual-only | `false` | `false` | Expensive confirmation baseline only. Disabled by default and forbidden in routine smoke, full regression, and readiness gate unless explicitly approved. |

## Build-Loop Models

- `deepseek` remains the default low-cost build-loop profile.
- Routine `B-1` smoke, regression, and readiness continue to use `deepseek` unless a human explicitly requests otherwise.

## Transport Probe Models

- `grok-4-fast` is the low-cost transport sanity-check profile.
- Its current evidence only proves `B1-003` Pass 1 decision transport on the targeted probe path.
- `grok-4-fast` success must not be interpreted as semantic success or as proof that it should become the global manager model.

## Manager Candidates

Current future manager candidate order is a hypothesis, not a production decision:

1. `kimi-k2.5`
2. `gemini-3-flash-preview`

Both candidates stay outside routine smoke until repo-local evaluation artifacts exist.

## Accurate Intake MVP Deferred Kimi Validation

Accurate Intake target-model validation will use `builderspace-kimi-k2-5-accurate-intake-mvp-live-diagnostic` in a deferred slice.

PR93-PR100 should not register Kimi as an active Accurate Intake live diagnostic runtime profile. Those PRs should finish model-agnostic schema, harness, dependency inversion, and local product-loop work using fixture paths and the existing GrokFast low-cost diagnostic probe.

Kimi validation starts after the model-agnostic local web self-use loop is green. The first Kimi slice should run provider health, schema probe, fake runtime gate, selected staged probes, and cost/latency capture only.

Kimi remains `production_selected=false`, `private_self_use_approved=false`, and outside routine smoke/default manager selection until an explicit future activation decision.

### First Live BuilderSpace Candidate Observations

This first live pass upgraded `kimi-k2.5` and `gemini-3-flash-preview` from `hypothesis_only` to `artifact_observed`. It did not select a production manager. `production_selected = false` and `selection_status = not_decided` remain fixed for both candidates.

Artifacts:

- Historical local candidate-eval artifact filenames from the first BuilderSpace pass are no longer retained in tracked repo state.
- Keep the comparison table and interpretation below as the historical summary; do not treat missing local JSON files as current proof.

High-level comparison:

| Model | Transport Obeyed | Boundary Obeyed | Context Stable | Memory Posture Acceptable | Failure Families | Usage | Latency |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `kimi-k2.5` | `2/4` | `3/4` | `1/4` | `0/4` | `provider_runtime_error=2`, `none=2` | `8993` total tokens | `119643 ms` |
| `gemini-3-flash-preview` | `1/4` | `3/4` | `0/4` | `0/4` | `provider_runtime_error=3`, `none=1` | `3766` total tokens | `51356 ms` |

Dimension-backed observations:

- `tool-call decision obedience`
  - Both candidates returned readable `MC-001` artifacts, but both landed in `provider_runtime_error` rather than a completed transport-obeyed case.
- `Pass 1 / Pass 2 boundary obedience`
  - Both candidates completed `MC-002` cleanly with `transport_obeyed=true`, `schema_valid=true`, and `boundary_obeyed=true`.
- `multi-context state handling`
  - `kimi-k2.5` completed `MC-003` with `context_stable=true`.
  - `gemini-3-flash-preview` produced a readable `MC-003` artifact, but it ended in `provider_runtime_error`.
- `memory summarization posture`
  - Neither candidate completed `MC-004` cleanly in this first pass.
  - `kimi-k2.5` and `gemini-3-flash-preview` both stayed semantically honest (`fake_green_detected=false`), but each artifact still ended in `provider_runtime_error`.
- `no fake semantic green`
  - Both candidates preserved semantic honesty across all four cases in this first live pass.

## Expensive Manual Baseline

- `gpt-5` exists to answer low-frequency confirmation questions when cheaper candidates cannot resolve a capability attribution issue.
- `gpt-5` must stay `manual_only=true`.
- `allow_expensive_model_probe=false` remains the default.

## Manager Candidate Eval Lane

Manager candidate evaluation is separate from `wave1_phase_b_minimal_tool_loop_smoke`.

Recommended eval dimensions:

- tool-call decision obedience
- Pass 1 / Pass 2 boundary obedience
- multi-context state handling
- memory summarization posture
- no fake semantic green

Recommended artifact conventions:

- `scope = manager_candidate_eval`
- `candidate_model = <model>`
- `not_b1_readiness_evidence = true`
- artifact family: `artifacts/manager_candidate_eval_*.json`

### First-Round BuilderSpace-Only Case Pack

The first eval lane stays small and uses four fixed cases:

1. `MC-001`
   - `B1-003`-style synthetic tool-call decision obedience
2. `MC-002`
   - Pass 1 / Pass 2 boundary obedience
3. `MC-003`
   - multi-context state handling proxy via listed-ingredient compact evidence synthesis
4. `MC-004`
   - memory summarization posture proxy via insufficient-composition honesty and no fake semantic green

The first round is intentionally a proxy pack, not a comprehensive benchmark. It is designed to produce comparable candidate artifacts without reusing B-1 readiness semantics.

## Evidence Policy

- Public pricing and upstream docs are candidate-ranking inputs, not repo billing truth.
- A candidate remains `hypothesis_only` until repo artifacts prove behavior on the intended manager path.
- `artifact_observed` means the repo now has a readable live candidate artifact. It does not imply production selection or full manager suitability.
- Model success never implies product semantic success by itself.
