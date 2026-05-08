# Accurate Intake MVP Live Diagnostic Runbook

This runbook is the checked-in operating record for the Accurate Intake MVP live diagnostic sidecar.
This runbook belongs to the canonical `CurrentShell` track.
`ManagerRuntime`, `AppShell`, and `SharedCurrentShell` are CurrentShell owner lanes.
It is the primary CurrentShell product-pages founder gate for Chat / Today / Body browser evidence, while `ACCURATE_INTAKE_MVP_SELF_USE_RUNBOOK.md` remains operator-shell supporting evidence.

The claim scope: `live_diagnostic`.

## Scope

This runbook verifies whether an explicit diagnostic live Manager profile can drive the already-green local Accurate Intake MVP product loop:

```text
live Manager structured decision -> deterministic validation -> evidence/packet support -> final mapping -> commit/correction/removal -> same-truth debug/read model
```

This is not product readiness, private self-use approval, rollout readiness, production model selection, or mutation rollout evidence.

## Preconditions

Run deterministic gates before any provider call:

```powershell
python scripts/verify_accurate_intake_mvp.py --output artifacts/accurate_intake_mvp_gate.json
python scripts/run_accurate_intake_mvp_self_use_smoke.py --scenario-wall-v2
python scripts/run_accurate_intake_mvp_self_use_smoke.py --reopen-continuity
python -m pytest tests/test_accurate_intake_mvp_live_diagnostic.py tests/test_accurate_intake_mvp_live_decision_pack.py tests/test_accurate_intake_mvp_live_stage_manifest.py tests/test_accurate_intake_mvp_offline_shadow_replay.py tests/test_accurate_intake_mvp_live_runbook.py -q
```

Do not run live provider stages if the deterministic baseline is red.

The upstream runtime gate source is `docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml`.
Downstream browser or candidate-bundle stages should consume gate IDs from that ledger instead of recreating local names.

## Staged Live Commands

Run stages sequentially. Keep provider concurrency at one request at a time.

CLI live diagnostics intentionally reject implicit `--stage all`. Normal live evidence must be produced by the staged commands below, one artifact per provider/case probe. `--allow-live-all-diagnostic` exists only for explicit debugging and does not produce clean staged evidence by itself.

```powershell
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage provider_health_smoke --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_provider_health.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage schema_contract_probe --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_schema_probe.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage fake_provider_active_runtime_gate --output artifacts/accurate_intake_mvp_live_diagnostic_fake_runtime_gate.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage single_case_live_probe --case-id explicit_item_removal_seeded --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_seeded_removal.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage single_case_live_probe --case-id exact_item_official_label --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_exact_item.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage single_case_live_probe --case-id bubble_milk_tea_refinement --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_bubble_refinement.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage single_case_live_probe --case-id luwei_bare_to_listed_basket --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_luwei_basket.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage single_case_live_probe --case-id chinese_chicken_rice_correction_removal_debug --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_single_case.json
python scripts/build_accurate_intake_mvp_live_stage_manifest.py
python scripts/build_accurate_intake_contract_hardening_guard.py
python scripts/build_accurate_intake_mvp_offline_shadow_replay.py
python scripts/build_accurate_intake_mvp_live_robustness_matrix.py
python scripts/build_accurate_intake_mvp_live_cost_summary.py
python scripts/build_accurate_intake_mvp_live_decision_pack.py
python scripts/build_accurate_intake_mvp_private_self_use_candidate.py
```

The generated manifest, replay, and decision pack paths are:

- `artifacts/accurate_intake_mvp_live_stage_manifest.json`
- `artifacts/accurate_intake_contract_hardening_guard.json`
- `artifacts/accurate_intake_mvp_offline_shadow_replay.json`
- `artifacts/accurate_intake_mvp_live_robustness_matrix.json`
- `artifacts/accurate_intake_mvp_live_cost_summary.json`
- `artifacts/accurate_intake_mvp_live_decision_pack.json`
- `artifacts/accurate_intake_mvp_private_self_use_candidate.json`

For repeated runs, pass `--output` to the artifact builders instead of overwriting the default files:

```powershell
python scripts/build_accurate_intake_mvp_live_stage_manifest.py --output artifacts/accurate_intake_mvp_live_stage_manifest_run_i.json
python scripts/build_accurate_intake_contract_hardening_guard.py --output artifacts/accurate_intake_contract_hardening_guard_run_i.json
python scripts/build_accurate_intake_mvp_offline_shadow_replay.py --stage-manifest artifacts/accurate_intake_mvp_live_stage_manifest_run_i.json --output artifacts/accurate_intake_mvp_offline_shadow_replay_run_i.json
python scripts/build_accurate_intake_mvp_live_robustness_matrix.py --output artifacts/accurate_intake_mvp_live_robustness_matrix_run_i.json
python scripts/build_accurate_intake_mvp_live_cost_summary.py --output artifacts/accurate_intake_mvp_live_cost_summary_run_i.json
python scripts/build_accurate_intake_mvp_live_decision_pack.py --output artifacts/accurate_intake_mvp_live_decision_pack_run_i.json --contract-hardening-guard-artifact artifacts/accurate_intake_contract_hardening_guard_run_i.json
python scripts/build_accurate_intake_mvp_private_self_use_candidate.py --output artifacts/accurate_intake_mvp_private_self_use_candidate_run_i.json
```

## Contract Hardening Anti-Overfit Gate

`live full-suite failure unlocks attribution/audit only`.

`live failure alone cannot justify prompt/schema/contract hardening`.

Before any prompt, schema, or Manager contract hardening can be treated as merge-ready, build the contract hardening guard:

```powershell
python scripts/build_accurate_intake_contract_hardening_guard.py --output artifacts/accurate_intake_contract_hardening_guard.json
```

The guard records `contract_hardening_debt`. Any debt keeps decision packs diagnostic-only and blocks private self-use candidate preparation.

Required guard fields include:

- `fixed_case_ids`
- `legal_flows_broken`
- `canonical_rule_exists`
- `legal_flow_matrix_updated`
- `holdout_tests_added`
- `raw_text_routing_risk`
- `provider_overfit_risk`
- `merge_allowed`

`merge_allowed` may appear only when canonical product-rule backing exists, the legal-flow matrix is updated, holdout tests are present, no raw-text routing risk remains, no high provider-overfit risk remains, and `legal_flows_broken` is empty.

The current PR74-PR84 audit is repo-tracked as:

- `docs/quality/accurate_intake_pr74_84_semantic_drift_audit.json`
- `docs/quality/accurate_intake_contract_legal_flow_matrix.json`
- `docs/quality/accurate_intake_contract_change_manifest_pr84.json`

## Full Suite Gate

`full_suite_live_diagnostic remains blocked` until all prior stages meet this threshold:

- provider health smoke passes.
- schema contract probe passes.
- fake-provider active runtime gate passes.
- seeded explicit-removal single-turn probe passes as `strict_pass_first_attempt`.
- exact-item official-label single-turn probe passes as `strict_pass_first_attempt`.
- bubble-tea optional-refinement single-case probe passes as `strict_pass_first_attempt`.
- luwei bare/listed basket single-case probe passes as `strict_pass_first_attempt`.
- original multi-turn single-case probe passes as `strict_pass_first_attempt`.
- offline replay artifact is present and marked `strict_replay_ready`.
- zero timeout and zero retry-dependent evidence.
- provider robustness matrix marks `model_inversion_evidence_passed` and leaves `contract_overfit_risk` absent/false.

One clean staged live window is enough to unlock the next diagnostic decision. Do not repeat the same staged window three times during early live probing. If the staged window is strict but slow, run latency root-cause attribution before running broader live suites.

Do not run the full suite when a prior stage is missing, failed, timed out, only passed after retry, or when the offline replay gate would return `offline_replay_required`.

Full-suite diagnostic command, only after the gate above is green:

```powershell
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage full_suite_live_diagnostic --offline-replay-artifact artifacts/accurate_intake_mvp_offline_shadow_replay.json --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_full_suite.json
```

## Full-Suite Evidence Window

One strict full-suite artifact is diagnostic evidence only. It does not prepare private self-use.

Before a decision pack may select `prepare_private_self_use_candidate`, the offline replay window must show:

- `full_suite_replay_ready`.
- at least three full-suite runs in the replay window.
- every full-suite run is `strict_pass_first_attempt`.
- zero full-suite timeout, retry-dependent pass, repaired pass, or failed case.
- provider/model diversity evidence is present; GrokFast-only evidence remains `model_diversity_missing`.

## Retry And Timeout Policy

- Retry only the failed provider request.
- Never rerun the whole workflow and label that as retry success.
- `strict_pass_first_attempt` is the only clean live stability evidence.
- `pass_after_retry is not strict evidence`.
- `timeout_after_retry remains a blocker`.
- Any timeout, provider error, schema error, runtime error, or retry-dependent pass keeps the decision at `stay_diagnostic` or `repeat_single_profile_diagnostic`.

## Cost Summary Policy

Build a live cost summary after staged live artifacts are produced:

```powershell
python scripts/build_accurate_intake_mvp_live_cost_summary.py --output artifacts/accurate_intake_mvp_live_cost_summary.json
```

The cost summary is diagnostic-only. It aggregates provider-reported token usage and provider-reported cost fields from local live artifacts. `token counts are not billing truth`; billing truth must come from provider-reported artifact fields or external billing records.

The cost summary must preserve:

- `billing_truth_source=provider_reported_artifact_fields_only`
- set `cost_unavailable_without_pricing` when token usage exists but no provider-reported cost field is present
- no repo-local pricing table override
- `latency_root_cause_hints` for request count, stage latency, prompt-token volume, cache metric visibility, cache-hit visibility, and output-token share
- `latency_optimization_priorities` before repeating the same live diagnostic window
- `latency_breakdown` with provider-call attribution by diagnostic stage, case, turn, Manager loop scope, and slowest provider invocation
- missing `cached_tokens` reporting is an optimization signal, not a live diagnostic failure, because not every provider exposes compatible cache usage fields

Do not infer paid cost from tokens inside this repo. Do not stage generated cost summary artifacts as repo truth.

The live diagnostic timeout values are diagnostic failure boundaries, not acceptable product latency targets. If a staged run is strict but slow, first inspect provider invocation count, per-stage latency, per-case/per-turn attribution, Manager loop scope, slowest provider invocations, stage overhead, prompt-token volume, and cache reporting before adding more repetition.

## Post-PR88 phase checkpoint

GrokFast remains a diagnostic contract probe only. It is not the production/default Manager, not model-portability evidence, and not a private self-use approval source.

After PR85-PR88, stop GrokFast full-suite hardening and return to the Accurate Intake local self-use shell. The portable baseline is the contract hardening guard, legal-flow matrix, basket holdout, remove-item target-evidence boundary, and live cost/replay hygiene.

The next live provider work should be a future target-model diagnostic slice after the local self-use shell is green and a human explicitly chooses the target profile. That future slice must reuse the staged live harness and preserve all non-claim flags.

The checkpoint artifact is `docs/quality/accurate_intake_post_pr88_phase_checkpoint.json`. It is not a private self-use approval and does not claim product readiness, production model selection, model portability, shadow/canary, or mutation rollout.

## Kimi Deferred Target-Model Validation

Kimi target-model validation will use `builderspace-kimi-k2-5-accurate-intake-mvp-live-diagnostic` in a deferred target-model validation slice.

Do not run Kimi provider calls during PR93-PR100. PR93-PR100 should finish the model-agnostic schema, harness, dependency inversion, and local product-loop baseline using fixture paths and the existing GrokFast low-cost diagnostic probe only.

Kimi failure creates attribution and review records only. It must not directly trigger prompt, schema, Manager contract, product semantic, Food KB, or runtime truth changes.

Do not run a Kimi full-suite hardening loop before the deferred target-model validation slice. Future Kimi artifacts must stay diagnostic-only and must not claim production/default selection or private self-use approval.

After every 3-5 live/provider-affecting stages, and before any prompt/schema/contract hardening, open a read-only reviewer pass. The reviewer checks canonical rule source, legal-flow or holdout coverage, raw-text routing risk, provider overfit risk, readiness overclaim, and alignment with the calorie-deficit logging MVP.

Example deferred validation commands, only after the model-agnostic local web self-use loop is green and the target-model validation slice is explicitly opened:

```powershell
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage provider_health_smoke --provider-profile-id builderspace-kimi-k2-5-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_kimi_provider_health.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage schema_contract_probe --provider-profile-id builderspace-kimi-k2-5-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_kimi_schema_probe.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage single_case_live_probe --case-id explicit_item_removal_seeded --provider-profile-id builderspace-kimi-k2-5-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_kimi_seeded_probe.json
```

## Artifact Policy

Generated live artifacts are local diagnostic evidence, not repo truth.

Do not stage:

- `artifacts/accurate_intake_mvp_live_diagnostic_provider_health.json`
- `artifacts/accurate_intake_mvp_live_diagnostic_schema_probe.json`
- `artifacts/accurate_intake_mvp_live_diagnostic_fake_runtime_gate.json`
- `artifacts/accurate_intake_mvp_live_diagnostic_seeded_removal.json`
- `artifacts/accurate_intake_mvp_live_diagnostic_exact_item.json`
- `artifacts/accurate_intake_mvp_live_diagnostic_bubble_refinement.json`
- `artifacts/accurate_intake_mvp_live_diagnostic_luwei_basket.json`
- `artifacts/accurate_intake_mvp_live_diagnostic_single_case.json`
- `artifacts/accurate_intake_mvp_live_diagnostic_full_suite.json`
- `artifacts/accurate_intake_mvp_live_stage_manifest.json`
- `artifacts/accurate_intake_contract_hardening_guard.json`
- `artifacts/accurate_intake_mvp_offline_shadow_replay.json`
- `artifacts/accurate_intake_mvp_live_robustness_matrix.json`
- `artifacts/accurate_intake_mvp_live_cost_summary.json`
- `artifacts/accurate_intake_mvp_live_decision_pack.json`
- `artifacts/accurate_intake_mvp_private_self_use_candidate.json`
- local SQLite files
- provider raw traces

Repo truth for this sidecar is the runbook, scripts, tests, source code, and canonical specs.

## Model, Prompt Cache, And Trace Policy

Each staged probe is a single-profile live run: one provider profile must drive Manager pass 1, Manager pass 2, and final response synthesis for that run. Use GrokFast first, Kimi later as a separate replay after the local/web loop is green and a human explicitly opens the target-model validation slice. Do not mix GrokFast and Kimi inside one clean-success artifact; fallback/profile mixing is failure or fallback evidence, not strict success evidence.

Prompt cache policy: keep the static system/tool/schema prefix before dynamic context packets, current-turn user text, read-model summaries, and FoodDB/WebSearch evidence packets. Keep tool order stable. Log `cached_tokens` when the provider exposes usage fields, but do not require a cache hit for pass/fail. Prompt caching is an optimization and must not change output semantics.

Trace Grading Layers for every live diagnostic case:

- `provider_profile_and_prompt_versions`
- `current_turn_context_packet`
- `manager_pass_1_decision`
- `requested_tools`
- `filtered_tool_plan`
- `executed_tools`
- `compact_packets`
- `manager_pass_2_synthesis`
- `guard_result`
- `mutation_result`
- `renderer_input_basis`
- `final_response_basis`
- `latency_cost_cache_usage`

## Non-Claim Boundaries

Every live diagnostic artifact and decision pack must stay non-promotional. They must not claim private self-use approval, product readiness, production/default selection, mutation rollout, or live provider truth ownership.

Explicit non-goals:

- No Tavily/web product truth.
- No production DB.
- No shadow/canary.
- No user-facing rollout.
- No production/default Manager selection.
- No mutation rollout.

## Pre-Live Local Web Self-Use Decision Pack

Before any limited live canary is considered by a human reviewer, build a pre-live local web self-use decision pack from offline evidence:

```powershell
python scripts/build_accurate_intake_pre_live_self_use_decision_pack.py --evidence-json artifacts/accurate_intake_pre_live_evidence.json --output artifacts/accurate_intake_pre_live_self_use_decision_pack.json
```

This pack is not a live run. It must stay offline/offline-review only and must not claim live-canary approval, Kimi default activation, product readiness, or runtime-web activation.

The required evidence keys are:

- `phase_c_gate`
- `accurate_intake_mvp_gate`
- `browser_shell_smoke`
- `chat_history_reload_gate`
- `free_text_manual_target_gate`
- `dogfood_review_queue`
- `local_dogfood_data_hygiene`
- `local_operator_data_hygiene_bundle`
- `current_shell_compatibility_local_review_decision_pack` (legacy compatibility input alias: `pl_ce_local_review_decision_pack`)
- `product_pages_self_use_flow_gate`
- `ui_context_alignment_pack`
- `browser_activation_evidence_gate`
- `manager_tool_surface_inventory`
- `non_fooddb_manager_tool_contract`
- `manager_tool_choice_regression_wall`
- `context_conditioned_intent_wall`
- `non_fooddb_read_only_tool_loop_fake_smoke`
- `non_fooddb_mutation_tool_guard_smoke`
- `manager_intent_readiness_review_pack`
- `context_live_diagnostic_case_matrix`
- `context_live_diagnostic_anti_overfit_guard`
- `context_live_diagnostic_holdout_plan`
- `context_live_provider_input_preflight`
- `context_live_response_contract_dry_run`
- `context_live_diagnostic_gate`

The `browser_shell_smoke` evidence must have `browser_executed=true` before the pack can select `ready_for_human_limited_live_canary_decision`. Missing evidence keeps the selected option at `stay_local_self_use`.

The product-page evidence is required in addition to the older `browser_shell_smoke`.
`product_pages_self_use_flow_gate`, `ui_context_alignment_pack`, and `browser_activation_evidence_gate` must prove Chat, Today, and Body are browser-executed, same-truth, render-only product pages before live diagnostics can be considered.
Blocked optional browser evidence is allowed for local review artifacts, but it is not pass evidence for activation.

Non-FoodDB Manager tool diagnostics remain app-state only and must not use FoodDB/WebSearch evidence.
`manager_tool_surface_inventory`, `non_fooddb_manager_tool_contract`, `manager_tool_choice_regression_wall`, `context_conditioned_intent_wall`, `non_fooddb_read_only_tool_loop_fake_smoke`, and `non_fooddb_mutation_tool_guard_smoke` must prove the Manager can choose among budget/body/calibration/app-help tool postures without deterministic raw-text routing, FoodDB/WebSearch usage, runtime nutrition truth changes, or UI semantic ownership.

The `context_live_diagnostic_case_matrix` evidence must be generated before any Stage 4 or Stage 5 live diagnostic. It is a plan-only anti-overfit gate: live probes must select from the fixed matrix instead of ad hoc easy cases. The matrix must remain offline planning evidence only: no live LLM/provider invocation, no FoodDB usage, no mutation change, and no ManagerContextPacket schema change.

The matrix must include at least one compound log-and-modify case. Missing matrix evidence, provider-invoked matrix evidence, FoodDB-backed matrix evidence, or a matrix with too few cases keeps the selected option at `stay_local_self_use`.

The `context_live_diagnostic_holdout_plan` evidence must prove the fixed live diagnostic matrix has withheld holdout utterance variants that are not used as default provider prompts. It must stay offline planning evidence only: no live LLM/provider invocation, no ad hoc or provider-optimized case selection, no FoodDB usage, no mutation change, and no ManagerContextPacket schema change.

The `context_live_diagnostic_gate` evidence must be generated in no-live mode before this pre-live pack can select `ready_for_human_limited_live_canary_decision`. If the gate shows actual live invocation, allows ad hoc case selection, lacks the anti-overfit or holdout evidence, skips the response-contract dry-run, uses FoodDB/WebSearch, mutates runtime state, or changes the ManagerContextPacket schema, the selected option stays `stay_local_self_use`.

The pre-live pack does not require `context_live_diagnostic_stage_gate`. That artifact is generated only after human approval when a live probe actually runs, and it exists to enforce single-case before full-matrix live order rather than to unblock pre-live local self-use review.

The `context_live_diagnostic_stage_gate` evidence controls live diagnostic order after human approval. Stage 4 `single-case` may invoke only one fixed matrix case and cannot claim readiness. Stage 5 `full-matrix` requires a prior `context_live_single_case_probe_pass` artifact before the full matrix can be accepted. Both stages remain context-only, diagnostic-only, FoodDB/WebSearch-free, non-mutation, and non-readiness evidence.

## Semantic Ownership Boundary

The live Manager owns intent, workflow effect, target proposal, and tool-decision posture.

The deterministic runtime may validate schema, target uniqueness/writeability, evidence acceptance, commit boundary, persistence truth, and read-model same-truth. It must not infer intent, workflow, target attachment, logged/draft/no-mutation disposition, or final action from raw text.
