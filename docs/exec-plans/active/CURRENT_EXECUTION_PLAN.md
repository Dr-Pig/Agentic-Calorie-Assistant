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
| `2.7 Memory / Retrieval Deepening` | `active` | `2.7d` is now using semantic-routing fallout to establish the product-wide suite-governance layer and migration groundwork before more official boundary truth is promoted |
| `2.8 Recommendation` | `not started` | downstream of intake, rescue, and calibration maturity |
| `2.9 Proactive Nudges` | `not started` | downstream of recommendation and current mainline maturity |

## Global Pointer

- `current_pointer_bundle`: `2.7 Memory / Retrieval Deepening`
- `current_pointer_reason`: `semantic-routing officialization exposed a broader eval-governance gap, so the next bounded step is to align whole-product suite governance with L5A/L5B before further official benchmark promotion`
- `deferred_bundles[]`:
  - `2.6 Calibration`
- `deferred_bundle_reason`: `calibration remains legal later, but semantic routing now owns the active best-next slice`

## Current Execution Dashboard

- `current_status`: `2.2/2.3 remain complete enough, 2.5d rescue is complete enough as a source family, 2.7a/2.7b semantic-routing evidence exists, 2.7c hardened the official text surfaces, L6F now governs routing-vs-response boundaries, and 2.7d now includes suite-governance groundwork, first approved intake/rescue official golden packs, derived executable action-pack contracts, first agent-governed capability/service official suites, and runnable intake/rescue executable workflow smoke lanes`
- `current_workflow_family`: `2.7 Memory / Retrieval Deepening`
- `current_slice`: `2.7d-semantic-routing-prompt-state-pack-hardening`
- `current_goal`: `establish the whole-product suite-governance layer, align it explicitly with L5A/L5B, map existing benchmark/test/runner assets into suite taxonomy, and keep semantic-routing artifacts in their proper provisional/official lanes under that governance`
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
  - `2.7c official text-surface guard hardening is complete enough to unblock the next semantic-routing hardening wave`
- `legal_next_slices[]`:
  - `2.7d-semantic-routing-prompt-state-pack-hardening`
- `recommended_next_slice`: `2.7d-semantic-routing-prompt-state-pack-hardening`
- `why_this_next`: `the user explicitly redirected from premature router officialization to a whole-product golden-suite inventory, and the repo now needs to keep converting that governance layer into agent-runnable suite/runner surfaces before moving back to high-impact workflow/pass design`
- `human_gate`: `high-impact-only`
- `human_gate_scope`: `high_impact_only`
- `autonomous_execution_default`: `continue_until_high_impact_decision`
- `blocked_only_if[]`:
  - `new_global_pass_or_architecture_decision`
  - `new_cross_workflow_product_semantics`
  - `new_utterance_governed_official_truth`
- `owner_mode`: `local`
- `delegation_posture`: `prefer_workers_for_non_semantic_followthrough`
- `key_files_or_subsystem`: `work should stay inside quality/spec/governance surfaces, benchmark inventories, migration mapping, and execution truth sync without touching production routing or application runtime`
- `required_harness`:
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy`
  - relevant targeted, smoke, integration, benchmark, or eval commands for the actual slice
- `verification_status`: `suite-governance groundwork and the first autonomous follow-through wave are now in place: registries carry suite metadata, intake/rescue official utterance packs remain gated, agent-allowed capability/service packs exist, derived executable-action contracts are validated, and suite-wave orchestration can now execute the intake/rescue smoke runners by metadata rather than manual script selection`
- `verification_reason`: `whole-product suite-governance truth, migration mapping, registry metadata, candidate-to-official promotion flow, executable-action derivation rules, suite archetype selection rules, capability/service official packs, executable workflow runners, and metadata-filtered orchestration now exist together; the next work should keep defaulting to autonomous non-semantic follow-through unless it introduces new architecture, new cross-workflow semantics, or new utterance-governed official truth`
- `last_verified_at`: `2026-04-18`

## Selection State

- `active_critical_path_segment`: `2.7a semantic routing eval foundation -> 2.7b evidence hardening -> 2.7c official text-surface guard hardening -> 2.7d suite-governance and migration groundwork -> later official golden promotion by workflow -> later 2.7 routing/memory design -> later 2.6/2.8`
- `current_domain_gate_status`: `2.2, 2.3, and 2.5d are sufficient enough for semantic-routing eval work`
- `mainline_validation_status`: `sufficient_for_domain_advance`
- `selected_best_next_slice`: `2.7d-semantic-routing-prompt-state-pack-hardening`
- `selection_reason`: `the user explicitly redirected the branch from router-first benchmark work to whole-product golden-suite governance, and the repo still needs more agent-runnable suite/runner follow-through before returning to new high-impact workflow design`
- `selection_reason_detail`: `semantic-routing fallout exposed the broader governance gap: L5A and L5B already define mechanics and bucket taxonomy, but suite inventory, authority tiers, asset migration, and metadata-runnable execution surfaces were still implicit. The bounded next step is to keep expanding those runnable surfaces rather than prematurely switch back to new semantic design`
- `deferred_legal_slices[]`:
  - `2.6 next calibration slice`
- `deferred_selection_reason`: `calibration remains legal later in the broad order, but semantic routing now owns the active branch`
- `execution_surface`: `planner-local`
- `execution_surface_reason`: `this wave is still eval-first and LLM-led: keep architecture and semantic truth in the main thread, but default the remaining non-semantic follow-through to worker-worthy execution where the write scopes can be cleanly separated`
- `last_replan_at`: `2026-04-15`

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
