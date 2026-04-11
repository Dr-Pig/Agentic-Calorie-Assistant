# Implementation Planning & Re-plan Protocol

## Purpose

This protocol exists to prevent long-running implementation work from drifting away from the real codebase.

It applies to:

- execution plans under `docs/exec-plans/`
- long-running implementation work across multiple phases
- any build plan that spans more than one subsystem or one coding session

This protocol is repository-level operational guidance. It is not a product spec.

Execution plans governed by this protocol must follow the canonical workflow ordering defined in:

- [`docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)

## Core Principle

`code reality > stale execution plan`

When the current codebase, file boundaries, naming, or typed contracts diverge from an older micro-plan, the plan must be revised before implementation continues.

## Planning Artifact Layers

### 1. Master Build Map

The Master Build Map is the long-range implementation map.

It may define:

- ordered phases
- phase goals
- dependencies
- acceptance criteria
- re-plan checkpoints

It must not hard-code:

- far-future file placement
- exact class/function names for distant phases
- provider/model-specific implementation details unless already canonical

It may group adjacent workflows into execution bundles, but it must not reorder the canonical workflow dependency order.

### 2. Current Execution Plan

The Current Execution Plan is the only place where micro-phase tasks should be written in fine detail.

It may define:

- the current phase
- the next phase
- short-horizon task breakdown
- concrete tests
- expected code touchpoints

It must not define micro-tasks beyond the next phase.

### 3. Re-plan Log

The Re-plan Log records what changed after a phase was completed.

It must capture:

- what the code actually became
- what assumptions expired
- which files became too large or boundary-misaligned
- what must be corrected in the next phase plan

## Hard Rules

- Do not rely on stale micro-plans once a phase boundary has been crossed.
- Do not carry forward a detailed plan for more than the current phase plus the next phase.
- Do not force new functionality into an already overburdened file just because an older plan named that file.
- If a file boundary is clearly wrong, refactor the boundary before adding more responsibility.
- If current implementation naming diverges from the plan, update the plan to match reality before continuing.
- Do not delete and recreate an existing code file at the same path as a routine editing method.

Exception cases for code files are limited to:

- explicit file retirement or move during a boundary refactor
- patch-anchor, tooling, or encoding blockers that make a safe targeted edit impractical
- deliberate conversion into a thin entrypoint or compatibility surface

When an exception is used for a boundary-sensitive file, the task artifact or re-plan note must say why targeted editing was not used.

## Plan Expiry

A micro-plan expires when any of the following is true:

- the current phase has been completed
- a key file boundary has changed
- a typed contract changed shape
- a repository or application bridge changed ownership
- a target file crossed the fat-file trigger

Expired micro-plans must be revised before further implementation.

## Phase Gate Re-read

At the end of every phase, before starting the next phase, the implementer must:

1. read the relevant code paths that were just created or changed
2. record which files and modules now own the behavior
3. record which original assumptions are no longer true
4. revise the next phase plan accordingly

Implementation must not continue into the next phase until this re-read is done.

## Reality Audit Requirements

Each phase completion must produce a reality audit that answers:

- Which files now own the current behavior?
- Which files are becoming too large?
- Which module boundaries improved?
- Which boundaries are still wrong?
- Which task descriptions are now stale?
- Which exact next-phase tasks must be rewritten?

## Fat-File Trigger

The next phase must start with boundary review instead of feature addition when any of the following is true:

- an entrypoint or usecase file exceeds roughly 350 lines and still mixes orchestration with persistence or response shaping
- a schema file exceeds roughly 450 lines and continues to absorb unrelated contracts
- a module owns more than one of:
  - orchestration
  - persistence write logic
  - deterministic math
  - final response shaping
  - provider-specific behavior

These thresholds are review triggers, not hard caps. Crossing them requires an explicit re-plan note.

## Protected Fat-File Gate

The following files are protected because they already carry too much boundary pressure:

- `app/usecases/text_meal.py`
- `app/schemas.py`
- `app/routes.py`

Rules:

- protected files must not absorb new unrelated responsibilities
- if a protected file is already above threshold, ordinary feature work must not make it larger
- changes in a protected file should be either:
  - extraction / thinning work
  - bug fixes contained inside the file's current responsibility
  - boundary-safe wiring that does not expand responsibility
- if a change needs to grow a protected file anyway, the active plan or re-plan log must say why the extraction could not happen first

Repository default thresholds for protected files:

- `app/usecases/text_meal.py`: `350` lines
- `app/schemas.py`: `450` lines
- `app/routes.py`: `400` lines

These numbers are enforcement thresholds, not design targets.

## Design Target Ranges

Preferred steady-state file sizes:

- thin entrypoints / routes: roughly `80-180` lines
- application services / read-model assemblers: roughly `120-250` lines
- policy / deterministic math modules: roughly `40-180` lines
- workflow-specific schema files: roughly `80-220` lines

Larger files may still be acceptable when they remain single-responsibility, but crossing the protected thresholds must be treated as a boundary risk.

## Enforcement Script

Use:

- [`scripts/check_fat_files.ps1`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/scripts/check_fat_files.ps1)

Modes:

- default workspace audit: reports current protected-file pressure
- staged gate: blocks staged growth of already-protected files and blocks protected files from crossing their thresholds

The staged gate is intended to run from git hooks so agents and engineers get a concrete failure instead of a soft reminder.

## File Placement And Naming Discipline

Execution planning must follow the repository placement rules in:

- [`docs/BUILD_FILE_PLACEMENT_RULES.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/BUILD_FILE_PLACEMENT_RULES.md)

Those rules define:

- where new route, schema, orchestration, domain, and persistence files belong
- which naming suffixes signal which ownership boundary
- how to split a boundary-misaligned file by change reason instead of by raw line count

Plans must not assign new work to a file whose role does not match the responsibility being added.

## Task Wording Rule

Implementation tasks must be written in behavior-first language.

Prefer:

- "connect rescue overlay at the intake entrypoint layer"
- "introduce a typed recommendation response model at the runtime contract layer"

Avoid:

- "put this logic in `text_meal.py`"
- "add this field to `schemas.py`"

unless the file location is already canonical and still valid after a reality audit.

## Required Fields For Active Execution Plans

Every active execution plan should include at least:

- `current_phase`
- `next_phase`
- `last_replan_at`
- `reality_drift_notes`
- `stale_assumptions_removed`

For boundary-sensitive work, active tasks or plans should also include:

- `allowed_touch_areas`
- `forbidden_touch_areas`
- `new_files_expected`

These may be short, but they must be explicit.

## Relationship To Other Repo Rules

- [`docs/SPEC_EDITING_PROTOCOL.md`](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/SPEC_EDITING_PROTOCOL.md)
  governs how durable spec documents are safely edited.
- This protocol governs how implementation planning is written, revised, and kept aligned with the evolving codebase.

## Harness Engineering Alignment

This protocol is aligned with OpenAI Harness Engineering in the following ways:

- `agent.md` stays short and points into durable docs
- checked-in execution plans are treated as first-class operational artifacts
- stale instructions are treated as a reliability risk
- repository truth is maintained in structured docs instead of a single oversized instruction blob

It adopts the governance method, not a literal folder-by-folder copy of any external example.
