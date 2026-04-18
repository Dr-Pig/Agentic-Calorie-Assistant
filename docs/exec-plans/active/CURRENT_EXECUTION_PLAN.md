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
| `2.8 Recommendation` | `in progress` | `2.8a` foundation is landed and `2.8b` ranking/response is the active bounded wave |
| `2.9 Proactive Nudges` | `not started` | downstream of recommendation and current mainline maturity |

## Global Pointer

- `current_pointer_bundle`: `2.8 Recommendation`
- `current_pointer_reason`: `the recommendation context and candidate foundation is landed, so the next bounded wave is recommendation 2.8b: ranking candidates by soft preference under hard constraints and surfacing a non-mutating chat response with intake hint handoff`
- `deferred_bundles[]`:
  - `2.6 Calibration`
- `deferred_bundle_reason`: `calibration remains legal later, but recommendation 2.8b is now the best next slice because the repo already has deterministic context and candidate retrieval, and can now add ranking/response without reopening proposal or routing semantics`

## Current Execution Dashboard

- `current_status`: `2.2/2.3 remain complete enough, 2.5d rescue is complete enough, 2.7 suite-governance follow-through is complete enough for this wave, the budget-aware happy path is landed, recommendation 2.8a context/candidate foundation is landed, and the active branch is now recommendation 2.8b: deterministic-first ranking plus non-mutating chat response on top of the existing shared read-model surfaces`
- `current_workflow_family`: `2.8 Recommendation`
- `current_slice`: `2.8b-recommendation-ranking-and-response`
- `current_goal`: `rank legal recommendation candidates by soft preference after hard-constraint filtering, produce a chat-first non-mutating response with 1 top pick plus 1-2 backups, and expose intake handoff only through hint_packet quick actions`
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
  - `2.7f general_chat one-pass runtime surface plus official runnable suite for budget/goal/open-workflow queries`
  - `workflow graph / official truth v1 locked for general_chat, intake, rescue, recommendation, calibration, and body_observation`
  - `2.8a recommendation context packet plus deterministic candidate retrieval/filtering foundation`
  - `2.8b recommendation ranking/response wave started`
  - `2.7c official text-surface guard hardening is complete enough to unblock the next semantic-routing hardening wave`
- `legal_next_slices[]`:
  - `2.8b-recommendation-ranking-and-response`
- `recommended_next_slice`: `2.8b-recommendation-ranking-and-response`
- `why_this_next`: `the repo now has stable shared budget/body-plan truth, locked workflow graph truth, and the 2.8a context/candidate foundation, so recommendation 2.8b is the next bounded implementation wave that can advance without reopening high-impact routing or proposal semantics`
- `human_gate`: `high-impact-only`
- `human_gate_scope`: `high_impact_only`
- `autonomous_execution_default`: `continue_until_high_impact_decision`
- `blocked_only_if[]`:
  - `new_global_pass_or_architecture_decision`
  - `new_cross_workflow_product_semantics`
  - `new_utterance_governed_official_truth`
- `owner_mode`: `local`
- `delegation_posture`: `prefer_workers_for_non_semantic_followthrough`
- `key_files_or_subsystem`: `work should stay inside recommendation context shaping, deterministic candidate retrieval/filtering, sparse-safe preference summary inputs, and recommendation tests; do not widen into recommendation response surfaces, proposal semantics, or calibration/rescue redesign`
- `required_harness`:
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy`
  - relevant targeted, smoke, integration, benchmark, or eval commands for the actual slice
- `verification_status`: `the recommendation 2.8a implementation wave is in progress: context shaping and deterministic candidate retrieval/filtering now exist locally with targeted tests passing, but execution-truth sync and broader slice-level follow-through are still required before the wave is fully landed`
- `verification_reason`: `the branch now includes recommendation context shaping, sparse-safe preference summary loading, and deterministic candidate retrieval/filtering with targeted regressions passing. The remaining work is to complete truth sync, review any worker follow-through, and then rerun the relevant gates for the recommendation slice`
- `last_verified_at`: `2026-04-18`

## Selection State

- `active_critical_path_segment`: `shared budget/body-plan truth -> recommendation 2.8a context + deterministic candidate retrieval -> recommendation response surface -> calibration proposal/chat surfaces`
- `current_domain_gate_status`: `2.1, 2.2, 2.3, onboarding/body-plan bootstrap, and workflow graph truth are sufficient enough for recommendation 2.8a`
- `mainline_validation_status`: `sufficient_for_domain_advance`
- `selected_best_next_slice`: `2.8a-recommendation-context-and-candidate-foundation`
- `selection_reason`: `the shared target/ledger trunk is now in place and the workflow graph truth is locked, so recommendation 2.8a is the first bounded workflow wave that can move from design truth into implementation without reopening product semantics`
- `selection_reason_detail`: `recommendation can now safely read CurrentBudgetView, ActiveBodyPlanView, and sparse-safe preference signals to produce a deterministic-first candidate set. That makes 2.8a the highest-leverage next slice before response surfaces, calibration proposal chat, or broader routing work`
- `deferred_legal_slices[]`:
  - `2.6 next calibration slice`
- `deferred_selection_reason`: `calibration remains legal later in the broad order, but recommendation 2.8a now has the required shared truth and can proceed without reopening proposal or commit semantics`
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
