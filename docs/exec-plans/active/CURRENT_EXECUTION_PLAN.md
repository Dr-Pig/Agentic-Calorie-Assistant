# Current Execution Plan

This file is the minimal active execution pointer for new agent windows.

It is not a task tracker, handoff log, or detailed micro-plan. Keep it short.

## Current Mainline

```yaml
current_mainline: Current Shell self-use MVP local desktop dogfood
mainline_goal: make the app usable for daily calorie logging on the local desktop shell
active_capability: Calorie Deficit Logging MVP local self-use foundation
is_detour: false
```

## Active State Sources

Read these for current truth instead of reviving old Product Loop, PLCE, V2, or execution-dashboard docs:

1. [docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md)
2. [docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml)
3. [docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml)
4. [docs/quality/ACCURATE_INTAKE_MVP_LIVE_DIAGNOSTIC_RUNBOOK.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/ACCURATE_INTAKE_MVP_LIVE_DIAGNOSTIC_RUNBOOK.md)

## Ownership

```yaml
canonical_track: CurrentShell
owner_lanes:
  - ManagerRuntime
  - AppShell
  - SharedCurrentShell
separate_truth_owner_tracks:
  - FoodDB
  - MergeGovernance
harness_role: keep repo context, CI, docs, naming, and legacy surfaces from misleading agents
```

Execution ownership may consolidate in one agent window, but architecture ownership stays separate:

- ManagerRuntime owns upstream runtime truth and manager contracts.
- AppShell consumes runtime truth and verifies browser/user-visible surfaces.
- FoodDB owns nutrition evidence truth and remains outside CurrentShell.
- Harness work removes misleading repo context and keeps mandatory hard walls small.

## Do Not Start From

- Kiro steering files
- placeholder cloud/deploy workflows
- retired duplicate docs indexes such as `docs/index.md` or `docs/V2_DOC_INDEX.md`
- `docs/specs/APP_V2_IMPLEMENTATION_PLAN.md`
- `docs/quality/V2_CAPABILITY_MAP.md`
- legacy Product Loop / PLCE planning prose unless explicitly using compatibility paths

## Update Rule

Update this file only when the current mainline, active state sources, or owner-lane model changes.
Do not add PR-by-PR task logs here; use git, CI, and the active state sources above.
