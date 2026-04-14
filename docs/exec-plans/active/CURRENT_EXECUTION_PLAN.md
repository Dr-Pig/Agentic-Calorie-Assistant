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
| `2.5 Rescue` | `active` | `2.5c` is completed enough; the user has explicitly opened `2.5d` rescue response surface work |
| `2.6 Calibration` | `deferred` | not best-next while `2.2` mainline validation remains incomplete |
| `2.7 Memory / Retrieval Deepening` | `not started` | downstream of current mainline and later-domain work |
| `2.8 Recommendation` | `not started` | downstream of intake, rescue, and calibration maturity |
| `2.9 Proactive Nudges` | `not started` | downstream of recommendation and current mainline maturity |

## Global Pointer

- `current_pointer_bundle`: `2.5 Rescue`
- `current_pointer_reason`: `the user explicitly approved implementation of the 2.5d rescue response surface plan`
- `deferred_bundles[]`:
  - `2.6 Calibration`
  - `2.7 Memory / Retrieval Deepening`
- `deferred_bundle_reason`: `these bundles are legal later-domain branches, but rescue now owns the active best-next slice`

## Current Execution Dashboard

- `current_status`: `2.2/2.3 are complete enough for the current wave; rescue owns the active branch, 2.5c is complete enough, and 2.5d is now active for chat-first rescue response work`
- `current_workflow_family`: `2.5 Rescue`
- `current_slice`: `2.5d-rescue-response-surface`
- `current_goal`: `surface rescue as a single chat-first recovery plan with adjustable intensity while keeping intake separate and UI mirror-only`
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
- `legal_next_slices[]`:
  - `2.5d-rescue-response-surface`
- `recommended_next_slice`: `2.5d-rescue-response-surface`
- `why_this_next`: `the user selected a single-plan, chat-first rescue response model, which opens the rescue response surface as the next bounded slice`
- `human_gate`: `cleared for 2.5d by explicit user approval`
- `owner_mode`: `local`
- `key_files_or_subsystem`: `work should stay inside rescue deterministic shaping, rescue overlay alignment, and targeted rescue harness surfaces`
- `required_harness`:
  - `python scripts/check_layer_integrity.py`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings`
  - `powershell -ExecutionPolicy Bypass -File scripts/check_encoding.ps1 -AuditDocsPolicy`
  - relevant targeted, smoke, integration, benchmark, or eval commands for the actual slice
- `verification_status`: `2.2/2.3 wave evidence remains sufficient; 2.5d now passes targeted rescue response, rescue chat surface, accept-side overlay writeback, and rescue route integration tests`
- `verification_reason`: `the rescue branch now includes a checked-in single-plan response layer, a real rescue chat/proactive entrypoint, accept-side overlay writeback, and dedicated rescue web/chat routes while still preserving chat-first delivery, intake separation, and UI mirror-only boundaries`
- `last_verified_at`: `2026-04-15`

## Selection State

- `active_critical_path_segment`: `2.5d rescue response surface -> later rescue accept/writeback -> later 2.6/2.7`
- `current_domain_gate_status`: `2.2 and 2.3 are sufficient for the current wave; rescue now owns the active branch`
- `mainline_validation_status`: `sufficient_for_domain_advance`
- `selected_best_next_slice`: `2.5d-rescue-response-surface`
- `selection_reason`: `the user explicitly approved the 2.5d rescue response plan and fixed the key product semantics`
- `selection_reason_detail`: `2.5d now owns the active rescue branch, while accept-side writeback remains outside the current slice`
- `deferred_legal_slices[]`:
  - `2.6 next calibration slice`
- `deferred_selection_reason`: `calibration remains legal later in the broad order, but 2.5d rescue response surface now owns the active branch`
- `execution_surface`: `planner-local`
- `execution_surface_reason`: `this wave is a narrow runtime continuity hardening step plus truth-sync, not a broad workflow or product-scope branch`
- `last_replan_at`: `2026-04-14`

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
