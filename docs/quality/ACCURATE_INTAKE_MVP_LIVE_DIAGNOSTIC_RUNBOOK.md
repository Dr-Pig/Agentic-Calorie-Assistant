# Accurate Intake MVP Live Diagnostic Runbook

This runbook is the checked-in operating record for the Accurate Intake MVP live diagnostic sidecar.

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

## Staged Live Commands

Run stages sequentially. Keep provider concurrency at one request at a time.

```powershell
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage provider_health_smoke --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_provider_health.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage schema_contract_probe --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_schema_probe.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage fake_provider_active_runtime_gate --output artifacts/accurate_intake_mvp_live_diagnostic_fake_runtime_gate.json
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage single_case_live_probe --case-id explicit_item_removal_seeded --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_seeded_removal.json
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

`merge_allowed=true` requires canonical product-rule backing, an updated legal-flow matrix, holdout tests, no raw-text routing risk, no high provider-overfit risk, and `legal_flows_broken=[]`.

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
- original multi-turn single-case probe passes as `strict_pass_first_attempt`.
- offline replay artifact is present and `strict_replay_ready=true`.
- zero timeout and zero retry-dependent evidence.
- provider robustness matrix has `model_inversion_evidence_passed=true` and `contract_overfit_risk=false`.

Do not run the full suite when a prior stage is missing, failed, timed out, only passed after retry, or when the offline replay gate would return `offline_replay_required`.

Full-suite diagnostic command, only after the gate above is green:

```powershell
python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage full_suite_live_diagnostic --offline-replay-artifact artifacts/accurate_intake_mvp_offline_shadow_replay.json --provider-profile-id builderspace-grok-4-fast-accurate-intake-mvp-live-diagnostic --provider-timeout-ms 180000 --output artifacts/accurate_intake_mvp_live_diagnostic_full_suite.json
```

## Full-Suite Evidence Window

One strict full-suite artifact is diagnostic evidence only. It does not prepare private self-use.

Before a decision pack may select `prepare_private_self_use_candidate`, the offline replay window must show:

- `full_suite_replay_ready=true`.
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
- `cost_unavailable_without_pricing=true` when token usage exists but no provider-reported cost field is present
- `pricing_table_applied=false`

Do not infer paid cost from tokens inside this repo. Do not stage generated cost summary artifacts as repo truth.

## Post-PR88 phase checkpoint

GrokFast remains a diagnostic contract probe only. It is not the production/default Manager, not model-portability evidence, and not a private self-use approval source.

After PR85-PR88, stop GrokFast full-suite hardening and return to the Accurate Intake local self-use shell. The portable baseline is the contract hardening guard, legal-flow matrix, basket holdout, remove-item target-evidence boundary, and live cost/replay hygiene.

The next live provider work should be a future target-model diagnostic slice after the local self-use shell is green and a human explicitly chooses the target profile. That future slice must reuse the staged live harness and preserve all non-claim flags.

The checkpoint artifact is `docs/quality/accurate_intake_post_pr88_phase_checkpoint.json`. It is not a private self-use approval and does not claim product readiness, production model selection, model portability, shadow/canary, or mutation rollout.

## Kimi Deferred Target-Model Validation

Kimi target-model validation will use `builderspace-kimi-k2-5-accurate-intake-mvp-live-diagnostic` in a deferred target-model validation slice.

Do not run Kimi provider calls during PR93-PR100. PR93-PR100 should finish the model-agnostic schema, harness, dependency inversion, and local product-loop baseline using fixture paths and the existing GrokFast low-cost diagnostic probe only.

Kimi failure creates attribution and review records only. It must not directly trigger prompt, schema, Manager contract, product semantic, Food KB, or runtime truth changes.

Do not run a Kimi full-suite hardening loop before the deferred target-model validation slice. Future Kimi artifacts must keep `production_selected=false` and `private_self_use_approved=false`.

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

## Non-Claim Boundaries

Every live diagnostic artifact and decision pack must preserve:

- `private_self_use_approved=false`
- `product_readiness_claimed=false`
- `production_selected=false`
- `mutation_rollout_approved=false`
- `live_provider_used_as_truth=false`

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

This pack is not a live run and must keep `live_llm_invoked=false`, `live_canary_approved=false`, `kimi_active_runtime_default_allowed=false`, `product_readiness_claimed=false`, and `runtime_web_activation_approved=false`.

The required evidence keys are:

- `phase_c_gate`
- `accurate_intake_mvp_gate`
- `browser_shell_smoke`
- `chat_history_reload_gate`
- `free_text_manual_target_gate`
- `dogfood_review_queue`
- `local_dogfood_data_hygiene`

The `browser_shell_smoke` evidence must have `browser_executed=true` before the pack can select `ready_for_human_limited_live_canary_decision`. Missing evidence keeps the selected option at `stay_local_self_use`.

## Semantic Ownership Boundary

The live Manager owns intent, workflow effect, target proposal, and tool-decision posture.

The deterministic runtime may validate schema, target uniqueness/writeability, evidence acceptance, commit boundary, persistence truth, and read-model same-truth. It must not infer intent, workflow, target attachment, logged/draft/no-mutation disposition, or final action from raw text.
