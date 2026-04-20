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
| `2.6 Calibration` | `in progress` | recommendation truth-sync and 5-node alignment are landed, so calibration + body observation is now the active bounded wave |
| `2.7 Memory / Retrieval Deepening` | `completed enough` | suite-governance groundwork, metadata-runnable runners, and first agent-governed capability suites are complete enough for the current wave |
| `2.8 Recommendation` | `completed enough` | truth-sync plus 5-node candidate-spec, retrieval, ranking, and non-mutating response alignment are landed for the current wave |
| `2.9 Proactive Nudges` | `not started` | downstream of recommendation and current mainline maturity |

## Global Pointer

- `current_pointer_bundle`: `2.6 Calibration`
- `current_pointer_reason`: `workflow truth v2 sync is landed and recommendation now matches its 5-node owner truth, so the next bounded wave is calibration + body observation alignment before rescue/proactive widening`
- `deferred_bundles[]`:
  - `2.9 Proactive Nudges`
- `deferred_bundle_reason`: `proactive remains downstream because it depends on stable recommendation, calibration, body observation, and rescue ownership truth`

## Current Execution Dashboard

- `current_status`: `2.2/2.3 remain complete enough, 2.5d rescue is complete enough, 2.7 suite-governance follow-through is complete enough for this wave, the budget-aware happy path is landed, workflow truth v2 sync is landed, recommendation now matches its 5-node runtime shape, and the active branch is now calibration + body observation alignment`
- `current_workflow_family`: `2.6 Calibration + 2.4 Weight / Body Observation`
- `current_slice`: `2.6a-calibration-and-body-observation-alignment`
- `current_goal`: `keep calibration model deterministic-first, keep calibration proposal inside calibration family, and align body observation / exercise extraction-create paths to llm-owned thin workflows with deterministic downstream recompute`
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
  - `workflow truth v2 approved: recommendation 5-node, rescue 4-node expanded, body observation extraction llm, proactive deterministic gate plus llm contextual dispatch`
  - `workflow truth v2 sync landed in owner docs and execution truth`
  - `recommendation 5-node runtime alignment landed: candidate_spec_generation, spec-driven retrieval, ranking/synthesis, and non-mutating response/handoff`
  - `2.7c official text-surface guard hardening is complete enough to unblock the next semantic-routing hardening wave`
- `legal_next_slices[]`:
  - `2.6a-calibration-and-body-observation-alignment`
- `recommended_next_slice`: `2.6a-calibration-and-body-observation-alignment`
- `why_this_next`: `recommendation is aligned, so the next bounded wave is to keep body observation extraction thin-and-llm-owned, keep downstream recompute deterministic, and keep calibration proposal firmly inside the calibration family`
- `human_gate`: `high-impact-only`
- `human_gate_scope`: `high_impact_only`
- `autonomous_execution_default`: `continue_until_high_impact_decision`
- `blocked_only_if[]`:
  - `new_global_pass_or_architecture_decision`
  - `new_cross_workflow_product_semantics`
  - `new_utterance_governed_official_truth`
- `owner_mode`: `local`
- `delegation_posture`: `prefer_workers_for_non_semantic_followthrough`
- `key_files_or_subsystem`: `work should stay inside calibration model/gate/response, body observation and exercise write paths, related routes, and targeted tests; do not widen into rescue/proactive implementation yet`
- `required_harness`:
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy`
  - relevant targeted, smoke, integration, benchmark, or eval commands for the actual slice
- `verification_status`: `workflow truth v2 sync has passed and recommendation targeted runtime tests are green; calibration/body-observation route-level verification is partially blocked by readiness drift in unrelated dirty files`
- `verification_reason`: `owner docs and execution truth are aligned, recommendation targeted tests and compile checks passed, and repo-level layer/encoding/fat-file checks passed. The remaining friction observed in weight-route tests comes from startup readiness requirements in unrelated dirty files, not from the workflow truth itself`
- `last_verified_at`: `2026-04-19`

## Selection State

- `active_critical_path_segment`: `shared budget/body-plan truth -> recommendation 5-node runtime alignment -> calibration/body observation wave -> rescue wave -> proactive wave`
- `current_domain_gate_status`: `2.1, 2.2, 2.3, onboarding/body-plan bootstrap, workflow truth v2 sync, and recommendation alignment are sufficient enough for calibration/body observation follow-through`
- `mainline_validation_status`: `sufficient_for_domain_advance`
- `selected_best_next_slice`: `2.6a-calibration-and-body-observation-alignment`
- `selection_reason`: `recommendation is no longer the highest-risk drift point; calibration/body observation now provide the next bounded implementation surface that can advance without reopening rescue or proactive semantics`
- `selection_reason_detail`: `the repo already has deterministic calibration model/gate foundations and typed body-observation persistence, so the next leverage point is to align thin llm extraction ownership and calibration-family proposal surfaces without crossing into proactive scheduling or rescue redesign`
- `deferred_legal_slices[]`:
  - `2.6 next calibration slice`
- `deferred_selection_reason`: `proactive remains legal later, but calibration/body observation should land first because proactive dispatch depends on stable downstream workflow ownership`
- `execution_surface`: `planner-local`
- `execution_surface_reason`: `this wave is application-and-route bounded: keep calibration/body observation follow-through local, and leave rescue/proactive for the next slices once these foundations are stable`
- `last_replan_at`: `2026-04-19`

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
