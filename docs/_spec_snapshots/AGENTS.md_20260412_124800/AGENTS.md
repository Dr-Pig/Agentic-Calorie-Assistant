# Agent Entry

`AGENTS.md` is the only bootstrap file in this repository.

Use it as a map, not a handbook. Read the minimum path first, then retrieve more docs only when the task shape requires them.

## Read First

1. [docs/index.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/index.md)
2. [docs/AGENT_LOADING_PATH.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/AGENT_LOADING_PATH.md)
3. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

## Execution Truth Trio

Default execution truth comes from:

1. `git diff / commit history`
2. CI and harness output
3. the minimal active state in [CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

Do not recreate this same information in large task or handoff narratives unless a real exception path requires it.

## Default Working Mode

- single-stream `planner-local` is the default
- search and load docs on demand; do not preload governance documents unless they are needed
- treat task and handoff docs as optional exception tools, not default workflow requirements
- if a slice is complete enough to verify, prefer recording it through git plus harness rather than handwritten execution metadata

## Default Harness Wall

Default deterministic guardrails include:

- diff scope and freeze-growth checks
- commit traceability checks
- runtime boundary and layer integrity checks
- fast lint plus existing encoding, fat-file, migration, and test gates

## Hard Rules Summary

- source-of-truth sync is mandatory when canonical understanding changes
- protected legacy files must stay thin:
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- freeze-growth files must not grow and must carry explicit justification when touched:
  - `app/application/evidence_assembly.py`
  - `app/application/context_assembly.py`
  - `app/agent/knowledge_packets.py`
- schema-sensitive ORM changes must ship with Alembic migrations
- do not use `docs/archive/` or `docs/_spec_snapshots/` as default truth

## Follow-On Reads

- spec or architecture work: use the canonical specs linked from [docs/index.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/index.md)
- implementation work: use [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md), harness docs, and the relevant code area
- delegation decisions only: use [docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/PLANNER_LOCAL_VS_WORKER_WORTHY_POLICY.md)
- optional resume or emergency transfer only: use [docs/HANDOFF_CONTRACT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/HANDOFF_CONTRACT.md)
