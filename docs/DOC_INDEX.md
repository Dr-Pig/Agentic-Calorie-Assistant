# Documentation Index

This is the sole active docs index for the repository.

Use [AGENTS.md](../AGENTS.md) for agent bootstrap. Use this file for document taxonomy, active-vs-legacy routing, and the current bootstrap path.

Retired duplicate index files `docs/index.md` and `docs/V2_DOC_INDEX.md` must not be recreated. Historical links should be redirected here instead of preserving thin stubs.

## Active Bootstrap

For the current default mainline:

1. [docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md](specs/APP_ENGINEERING_OPERATING_ENTRY.md)
2. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](exec-plans/active/CURRENT_EXECUTION_PLAN.md)
3. [docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md](quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md)
4. [docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml](quality/CURRENT_SHELL_SYNC_CONTRACT.yaml)
5. [docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml](quality/MANAGER_RUNTIME_GATE_LEDGER.yaml)
6. the relevant track-specific runbook or scope doc

## Active Truth Rules

- sole active docs index: `docs/DOC_INDEX.md`
- retired duplicate docs indexes must not exist: `docs/index.md`, `docs/V2_DOC_INDEX.md`
- sole active operating entry: `docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md`
- retired V2 operating and implementation stubs must not be tracked under `docs/specs/`
- retired V2 capability-map stubs must not be tracked under `docs/quality/`
- sole legacy runtime reference index: `docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md`
- canonical preservation path: `docs/_spec_snapshots/`

## Read When

| Need | Primary location |
| --- | --- |
| current bootstrap and document taxonomy | [docs/DOC_INDEX.md](DOC_INDEX.md) |
| current execution pointer | [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](exec-plans/active/CURRENT_EXECUTION_PLAN.md) |
| high-impact operating rules | [docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md](specs/APP_ENGINEERING_OPERATING_ENTRY.md) |
| current split-delivery ownership and coordination | [docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md](quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md) |
| current shell contract and gate order | [docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml](quality/CURRENT_SHELL_SYNC_CONTRACT.yaml), [docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml](quality/MANAGER_RUNTIME_GATE_LEDGER.yaml) |
| desktop local self-use dogfood boundary | [docs/quality/CURRENT_SHELL_DESKTOP_SELF_USE_DOGFOOD_CONTRACT.md](quality/CURRENT_SHELL_DESKTOP_SELF_USE_DOGFOOD_CONTRACT.md) |
| FoodDB expansion source quality, macro policy, promotion, and rebuild strategy | [docs/quality/ACCURATE_INTAKE_FOODDB_EXPANSION_SPEC.md](quality/ACCURATE_INTAKE_FOODDB_EXPANSION_SPEC.md) |
| FoodDB self-use v1 1000 packet-ready coverage target | [docs/quality/FOODDB_SELF_USE_V1_1000_PACKET_READY_COVERAGE_PLAN.md](quality/FOODDB_SELF_USE_V1_1000_PACKET_READY_COVERAGE_PLAN.md) |
| post-self-use no-runtime capability scaffolds | [docs/quality/POST_SELF_USE_NO_RUNTIME_CAPABILITY_DEVELOPMENT_FLOW.md](quality/POST_SELF_USE_NO_RUNTIME_CAPABILITY_DEVELOPMENT_FLOW.md) |
| advanced memory mechanism build order, live EDD train, context engineering train, context stress golden set, main sync audit, recommendation train, proactive train, advanced core golden-set alignment, and advanced product lab runtime closure | [docs/quality/ADVANCED_MEMORY_MECHANISM_BUILD_SPEC.md](quality/ADVANCED_MEMORY_MECHANISM_BUILD_SPEC.md), [docs/quality/advanced_memory_mechanism_contract.yaml](quality/advanced_memory_mechanism_contract.yaml), [docs/quality/advanced_product_lab_memory_live_edd_pr_train.yaml](quality/advanced_product_lab_memory_live_edd_pr_train.yaml), [docs/quality/advanced_product_lab_context_engineering_pr_train.yaml](quality/advanced_product_lab_context_engineering_pr_train.yaml), [docs/quality/advanced_product_lab_context_engineering_golden_set.yaml](quality/advanced_product_lab_context_engineering_golden_set.yaml), [docs/quality/advanced_product_lab_context_engineering_mechanism_review.yaml](quality/advanced_product_lab_context_engineering_mechanism_review.yaml), [docs/quality/advanced_product_lab_context_engineering_stress_pr_train.yaml](quality/advanced_product_lab_context_engineering_stress_pr_train.yaml), [docs/quality/advanced_product_lab_main_sync_drift_audit.yaml](quality/advanced_product_lab_main_sync_drift_audit.yaml), [docs/quality/advanced_product_lab_recommendation_pr_train.yaml](quality/advanced_product_lab_recommendation_pr_train.yaml), [docs/quality/advanced_product_lab_proactive_chat_first_pr_train.yaml](quality/advanced_product_lab_proactive_chat_first_pr_train.yaml), [docs/quality/advanced_core_golden_set_coverage_matrix.yaml](quality/advanced_core_golden_set_coverage_matrix.yaml), [docs/quality/advanced_product_lab_recommendation_golden_set.yaml](quality/advanced_product_lab_recommendation_golden_set.yaml), [docs/quality/advanced_product_lab_proactive_golden_set.yaml](quality/advanced_product_lab_proactive_golden_set.yaml), [docs/quality/advanced_product_lab_cross_journey_golden_set.yaml](quality/advanced_product_lab_cross_journey_golden_set.yaml) |
| advanced rescue Phase 1 PR train | [docs/quality/advanced_product_lab_rescue_phase1_pr_train.yaml](quality/advanced_product_lab_rescue_phase1_pr_train.yaml) |
| advanced rescue Phase 1 golden set | [docs/quality/advanced_product_lab_rescue_phase1_golden_set.yaml](quality/advanced_product_lab_rescue_phase1_golden_set.yaml) |
| runtime-lab memory EDD golden set | [docs/quality/runtime_lab_memory_edd_golden_set.yaml](quality/runtime_lab_memory_edd_golden_set.yaml) |
| advanced capability activation ladder | [docs/quality/advanced_capability_activation_ladder.yaml](quality/advanced_capability_activation_ladder.yaml) |
| historical pre-self-use runtime interpretation | [docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md](specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md) |

## Not Active Bootstrap

Do not start new implementation work from:

- Kiro steering files
- placeholder cloud/deploy workflows
- retired duplicate docs indexes: `docs/index.md`, `docs/V2_DOC_INDEX.md`
- `docs/governance/EXECUTION_OPERATING_MODEL.md`
- `docs/governance/EXECUTION_SELECTION_POLICY.md`
- retired V2 operating and implementation stubs
- `docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`
- `docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md`
- `docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`
- retired V2 capability-map stubs

Tracked files listed here may still carry canonical reference or compatibility value, but they are not the active bootstrap entry for new windows.
