# Agent Entry

`AGENTS.md` is the only bootstrap file in this repository.

Use it as a map, not a handbook. Load the minimum path first, then retrieve deeper docs only when the task shape requires them.

## Truth Hierarchy

Default truth families are:

1. [docs/specs/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs)
2. [docs/exec-plans/active/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active)
3. CI and harness output
4. `git diff / commit history`

Do not use [docs/archive/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/archive), [artifacts/docs-snapshots/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/artifacts/docs-snapshots), completed task artifacts, or handoff docs as default truth.

## Read First

1. [docs/index.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/index.md)
2. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)

If the task needs legality, slice detail, or next-slice selection, read next:

3. [docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/exec-plans/WORKFLOW_SLICE_REGISTRY.md)
4. [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
5. [docs/governance/EXECUTION_OPERATING_MODEL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/EXECUTION_OPERATING_MODEL.md)

Default planner path is:

`AGENTS.md -> CURRENT_EXECUTION_PLAN.md -> WORKFLOW_SLICE_REGISTRY.md -> ordering spec -> EXECUTION_OPERATING_MODEL.md`

## Planner Default

- `CURRENT_EXECUTION_PLAN.md` is the execution clock and global build state machine
- `WORKFLOW_SLICE_REGISTRY.md` is the slice table
- the ordering spec is the legality and dependency truth
- `EXECUTION_OPERATING_MODEL.md` is the execution-governance owner doc
- task and handoff docs are exception tools, not default routing

If the dashboard says execution is at a human gate, stop only when the gate is a high-impact gate:
- global pass / architecture decisions
- new cross-workflow product semantics
- new `Utterance-Governed Suite` official canonical truth

Otherwise, continue execution by default.
Official suite authoring, runner work, registry work, fixture work, promotion, regression, plumbing, and other non-semantic follow-through should continue unless the dashboard explicitly marks them blocked.

When work is bounded, non-semantic, and parallelizable, prefer worker/delegation posture over keeping all implementation and verification on the main thread.
If the planner is selecting the next slice, the default planner path above is required reading, not a conditional governance read.

## Hard Rules Summary

- source-of-truth sync is mandatory when canonical understanding changes
- deterministic layers must not override completed LLM decision outputs
  - do not deterministically rewrite `action_taken`, `response_mode_hint`, `follow_up_needed`, `followup_question`, `exactness`, or `resolution_mode` after a pass completes
  - deterministic layers may validate, reject, downgrade, derive, or request one bounded repair round
- unapproved product semantics must not enter eval truth
  - do not write unapproved product semantics into eval packs, benchmark oracles, semantic taxonomies, or pass/fail rubrics
  - evidence collection may record competing interpretations or ambiguity clusters, but it must not silently canonize unresolved product decisions
- do not promote response-side distinctions into primary routing taxonomy unless they change workflow effect
  - do not encode `inquiry vs explain`, tone, style, reluctance wording, explanation density, or similar response-realization differences as primary routing labels unless they change target attachment, workflow ownership, disposition, or state mutation semantics
- prompt and evidence-policy fixes must target generalized estimation behavior, not one-off item patches
  - do not optimize prompts around a single SKU, menu item, or one benchmark example unless the canonical spec explicitly requires that item-specific behavior
  - prefer generalized rules based on evidence class, identity resolution, portion ambiguity, packaging cues, and uncertainty topology
  - when a benchmark exposes a failure, first look for the broader estimation-family rule that should govern that case class; fix the family rule, not just the surfaced example
- chat is the primary interaction surface for the product
  - rescue, proposal, and calibration interactions should default to chat-first behavior unless a canonical spec explicitly defines a different primary surface
  - UI should default to mirror / inbox behavior rather than becoming the primary interaction path
- protected legacy files must stay thin:
  - `app/routes.py`
  - `app/schemas.py`
  - `app/usecases/text_meal.py`
- freeze-growth files must not grow and must carry explicit justification when touched:
  - `app/application/evidence_assembly.py`
  - `app/application/context_assembly.py`
  - `app/agent/knowledge_packets.py`
- schema-sensitive ORM changes must ship with Alembic migrations
- governance docs are conditional reads; pull them only when the task touches repo process, spec editing, task protocol, or handoff protocol

## Default Harness Wall

Default deterministic guardrails include:

- diff scope and freeze-growth checks
- commit traceability checks
- layer integrity and migration discipline checks
- encoding, fat-file, smoke, integration, and targeted test gates
- advisory repo-hygiene scans when structure or docs ontology changes

## Conditional Reads

- spec or architecture work:
  - [docs/specs/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs)
  - [docs/governance/SPEC_EDITING_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/SPEC_EDITING_PROTOCOL.md)
  - [docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)
- onboarding / budget / today-sync happy-path work:
  - [docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md)
  - [docs/specs/L2_DATA_STATE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2_DATA_STATE_SPEC.md)
  - [docs/specs/L2A_DATA_DICTIONARY_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L2A_DATA_DICTIONARY_SPEC.md)
  - [docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md)
- routing design, semantic taxonomy, or eval label design:
  - [docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md)
  - [docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/specs/L6E_LLM_PASS_DESIGN_POLICY_SPEC.md)
- eval / benchmark / suite-governance work:
  - [docs/quality/L5A_EVAL_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5A_EVAL_SPEC.md)
  - [docs/quality/L5B_BENCHMARK_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5B_BENCHMARK_SPEC.md)
  - [docs/quality/L5D_SUITE_GOVERNANCE_SPEC.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/quality/L5D_SUITE_GOVERNANCE_SPEC.md)
- implementation task start (before writing code):
  - [docs/governance/ANTI_SLOP_CATALOG.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/ANTI_SLOP_CATALOG.md)
- repo rules or file placement:
  - [docs/governance/BUILD_FILE_PLACEMENT_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/BUILD_FILE_PLACEMENT_RULES.md)
  - [docs/governance/LAYER_DEPENDENCY_RULES.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/LAYER_DEPENDENCY_RULES.md)
- task artifact use:
  - [docs/governance/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/TASK_CHECKIN_PROTOCOL.md)
- optional resume or emergency transfer only:
  - [docs/governance/HANDOFF_CONTRACT.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/HANDOFF_CONTRACT.md)
- touching a freeze-growth file:
  - [docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md)
