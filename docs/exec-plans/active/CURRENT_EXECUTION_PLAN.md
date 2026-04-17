﻿# Current Execution Plan

> [!WARNING]
> **Authority Limit**: this file is the active execution dashboard and global build state machine.
> It does not replace canonical workflow order, slice legality, or product/runtime truth.
> For those, use:
> - [WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
> - [WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)

## Purpose

This file is the single execution state machine.

It should answer:

- where the project currently sits on the global build ladder
- which bundle is active now
- which bundles are completed, deferred, blocked, or not started
- which next slices are legal now
- which next slice is the best next slice now
- whether a human gate currently blocks the current branch
- why other legal branches are deferred
- which harness checks still matter right now

Detailed historical drift belongs in [REPLAN_LOG.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md), completed tasks, completed handoffs, and git history.

## Execution Truth Trio

Default execution truth comes from:

1. `git diff / commit history`
2. CI and harness output
3. this active execution dashboard

Task artifacts and handoff docs are optional exception tools. They are not required for routine local execution.

## Global Build Ladder

| Bundle | State | Note |
| --- | --- | --- |
| `2.1 Single-turn Intake` | `completed enough` | canonical single-turn intake foundation exists |
| `2.2 Multi-turn Intake + Correction` | `completed enough` | accepted Golden first-turn live evidence and turn-2 replay evidence are in place for the current wave |
| `2.3 Today UI / Read Models` | `completed enough` | prior follow-through plus `2.3c` replay-driven confidence checks now reconfirm current-budget/today behavior for the current wave |
| `2.4 Weight / Body Observation` | `completed enough` | available and not blocking current mainline work; still required before `2.6` |
| `2.5 Rescue` | `completed enough` | `2.5d` rescue response surface is complete enough to serve as a semantic-routing source family |
| `2.6 Calibration` | `deferred` | not best-next while `2.2` mainline validation remains incomplete |
| `2.7 Memory / Retrieval Deepening` | `completed enough` | suite-governance groundwork, metadata-runnable runners, and first agent-governed capability suites are complete enough for the current wave |
| `2.8 Recommendation` | `not started` | downstream of intake, rescue, and calibration maturity |
| `2.9 Proactive Nudges` | `not started` | downstream of recommendation and current mainline maturity |

## Global Pointer

- `current_pointer_bundle`: `0 Onboarding`
- `current_pointer_reason`: `the next bounded trunk is the deterministic budget happy path: bootstrap BodyProfile/BodyPlan, seed today ledger, keep intake synced to ledger truth, and expose shared /today + /body-plan + remaining-budget surfaces before higher-level workflow design resumes`
- `deferred_bundles[]`:
  - `2.6 Calibration`
- `deferred_bundle_reason`: `calibration remains legal later, but the budget/bootstrap trunk is now the best next slice because recommendation, rescue, and calibration all depend on it`

## Current Execution Dashboard

- `current_status`: `2.2/2.3 remain complete enough, 2.5d rescue is complete enough, 2.7 suite-governance follow-through is complete enough for this wave, and the active branch has now shifted to the budget-aware happy path: BodyProfile bootstrap, active BodyPlan read model, today-ledger seeding, intake-to-ledger budget fallback, /body-plan surface, and deterministic remaining-budget answer contract`
- `current_workflow_family`: `0 Onboarding`
- `current_slice`: `0.a-onboarding-ui-and-body-plan-bootstrap`
- `current_goal`: `run the canonical budget trunk end to end: bootstrap BodyProfile + BodyPlan + DayBudgetLedger, keep intake commits synced to the active budget, expose /today and /body-plan as shared read surfaces, and lock the deterministic remaining-budget answer contract for later chat use`
- `completed_so_far`:
  - `2.2a active-meal continuation foundation`
  - `2.2c cross-midnight attribution foundation`
  - `2.2d follow-up closure validation foundation`
  - `2.2f founder-fit multi-turn replay pack and accepted Golden V1`
  - `2.2g generic drink soft-avoid exact plus post-pass override cleanup`
  - `2.2h turn-2 hybrid replay runner, pack, and summary contract foundation`
  - `2.2j boundary-first turn-2 persistence continuity hardening`
  - `2.2k closure-complete turn-2 replay pack tightening and clean 9-case live rerun`
  - `9-case Golden single-turn live audit passed with true provider readiness`
  - `turn-2 hybrid replay evidence passed for both official lanes`
  - `2.3a/2.3b read-model follow-through for the current wave`
  - `2.3c read-side confidence follow-through after confirmed multi-turn replay evidence`
  - `2.5b rescue proposal artifact foundation`
  - `2.5c deterministic rescue option ranking and activation-mode shaping`
  - `2.5c thin rescue runtime entrypoint integration`
  - `2.5c rescue proposal-container persistence skeleton integration`
  - `2.5c open rescue proposal read-side / retrieval path`
  - `2.5d chat-first single-plan rescue response foundation`
  - `2.5d rescue chat/proactive surface entrypoint plus accept/reject state transition foundation`
  - `2.5d accept-side rescue overlay writeback and dedicated rescue web/chat routes`
  - `2.5d rescue surface text integrity cleanup plus route/state regression hardening`
  - `2.5d defer reminder contract and thin reject/defer reason bridge`
  - `repo-level user-facing mojibake guard for application/web/test surfaces`
  - `2.5d rescue response surface is now complete enough to act as a semantic-routing source family`
  - `2.7a semantic-routing taxonomy, founder-fit pack, state-pack quality note, eval runner, and initial mock/live evidence`
  - `2.7b semantic-routing founder-fit pack cleanup, drift-cluster expansion, triage artifact contract, and dormant style-profile owner note`
  - `2.7c official text-surface guard registry, shared mojibake detector, fixture semantic-field validation, and pre-commit/CI enforcement`
  - `2.7d canonical target-vocabulary prompt tightening and normalized semantic-routing state-pack shaping`
  - `independent global routing governance spec for routing-vs-response boundaries, anti-premature-taxonomy guard, and deterministic-gate responsibility`
  - `2.7d semantic-routing provisional-vs-official benchmark split plus candidate review queue foundation`
  - `L5D suite-governance layer, suite inventory v1, and first migration mapping table for existing benchmark/test/runner assets`
  - `first approved intake/rescue candidate batches promoted into workflow-specific official canonical packs`
  - `derived intake/rescue executable action-pack contracts that stay subordinate to official utterance truth`
  - `L5D test-suite archetype policy so tri-layer utterance packs are only used where utterance truth and runtime input genuinely diverge`
  - `first agent-governed capability/service official packs for retrieval candidate selection, context-packing sufficiency, and bounded-repair gate behavior`
  - `batch authoring templates plus a benchmark-artifact scaffolding helper for candidate/offical/executable pack surfaces`
  - `runnable rescue/intake executable workflow smoke runners plus suite-wave orchestration that can execute them by registry metadata`
  - `budget-aware happy path foundation: BodyProfile persistence, active body-plan read model, deterministic onboarding bootstrap service, /body-plan surface, active-budget fallback for intake ledger writes, and remaining-budget answer contract`
  - `2.7c official text-surface guard hardening is complete enough to unblock the next semantic-routing hardening wave`
- `legal_next_slices[]`:
  - `0.a-onboarding-ui-and-body-plan-bootstrap`
- `recommended_next_slice`: `0.a-onboarding-ui-and-body-plan-bootstrap`
- `why_this_next`: `the repo now has enough suite-governance and runner machinery for this wave, and the next stable trunk is the deterministic budget/bootstrap path that recommendation, calibration, rescue, and budget-aware chat all depend on`
- `human_gate`: `high-impact-only`
- `human_gate_scope`: `high_impact_only`
- `autonomous_execution_default`: `continue_until_high_impact_decision`
- `blocked_only_if[]`:
  - `new_global_pass_or_architecture_decision`
  - `new_cross_workflow_product_semantics`
  - `new_utterance_governed_official_truth`
- `owner_mode`: `local`
- `delegation_posture`: `prefer_workers_for_non_semantic_followthrough`
- `key_files_or_subsystem`: `work should stay inside onboarding/bootstrap, canonical state, body-plan/today read surfaces, intake-ledger sync, and execution truth sync; do not widen into recommendation/calibration/rescue workflow redesign`
- `required_harness`:
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy`
  - relevant targeted, smoke, integration, benchmark, or eval commands for the actual slice
- `verification_status`: `the budget-aware happy-path implementation wave is in progress: canonical bootstrap/writeback surfaces exist locally and targeted route/read-model/persistence tests already prove the main trunk, but execution-truth sync and full harness completion are still required before this branch is fully landed`
- `verification_reason`: `the branch has already added BodyProfile persistence, active BodyPlan read surfaces, deterministic onboarding bootstrap, /body-plan routes, active-budget fallback for intake commits, and a remaining-budget answer contract. The remaining work is to sync planner/spec truth and then rerun the targeted + harness gates for this trunk`
- `last_verified_at`: `2026-04-18`

## Selection State

- `active_critical_path_segment`: `0 onboarding/bootstrap deterministic target -> intake-to-ledger sync -> shared /today and /body-plan read surfaces -> deterministic remaining-budget answer contract -> later recommendation/calibration/rescue budget-aware workflow design`
- `current_domain_gate_status`: `2.1, 2.2, 2.3, and onboarding/body-plan bootstrap are sufficient enough for the budget-aware happy-path trunk`
- `mainline_validation_status`: `sufficient_for_domain_advance`
- `selected_best_next_slice`: `0.a-onboarding-ui-and-body-plan-bootstrap`
- `selection_reason`: `the user explicitly redirected from governance expansion to the canonical budget happy path, and the repo now needs the deterministic target/ledger trunk in place before higher-level workflow or pass-graph design can be trusted`
- `selection_reason_detail`: `the product needs one concrete, shared source of truth for daily target, consumed calories, remaining calories, and UI/chat sync. That makes onboarding/bootstrap plus intake-to-ledger sync the most leverage-heavy bounded slice before recommendation, calibration, or broader routing work`
- `deferred_legal_slices[]`:
  - `2.6 next calibration slice`
- `deferred_selection_reason`: `calibration remains legal later in the broad order, but the active branch now belongs to onboarding/bootstrap because it establishes the budget truth that calibration and recommendation will depend on`
- `execution_surface`: `planner-local`
- `execution_surface_reason`: `this wave is product-trunk-first and mostly deterministic: keep high-impact workflow design local, but allow bounded non-semantic follow-through across read-model, route, persistence, and test surfaces`
- `last_replan_at`: `2026-04-18`

## Working Rules

- keep this file minimal but explicit; it owns current execution state, not long historical narrative
- keep the global build ladder and current pointer current whenever best-next selection changes
- if a task completes without a commit, the working tree or staged diff must still make the write boundary legible
- if required harness has not run, keep `verification_status` explicit instead of implying completion
- if a real handoff is needed, use [docs/governance/HANDOFF_CONTRACT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/HANDOFF_CONTRACT.md) as an exception path
- use [docs/governance/EXECUTION_OPERATING_MODEL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/EXECUTION_OPERATING_MODEL.md) as the single execution-governance owner doc

## Pointer Map

- recent planning drift and corrections: [REPLAN_LOG.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/REPLAN_LOG.md)
- completed task history: [docs/exec-plans/completed/tasks/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/completed/tasks)
- completed handoff history: [docs/exec-plans/completed/handoff/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/completed/handoff)
