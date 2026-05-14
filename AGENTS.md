`AGENTS.md` is the only bootstrap file in this repository.

Use it as a map, not a handbook. Load the minimum path first, then retrieve deeper docs only when the task shape requires them.

[docs/DOC_INDEX.md](docs/DOC_INDEX.md) owns document taxonomy, file-role mapping, and longer navigation guidance. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md) owns the minimal current execution pointer. [docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md](docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md) owns the product-wide anti-drift operating layer. `AGENTS.md` only owns bootstrap order, always-on repo rules, and conditional-read triggers.

## Workflow Triage

Use the lightest workflow that still protects repo truth.

Fast path applies when the task is local, reversible, and does not change canonical product semantics, architecture boundaries, eval truth, migrations, provider/tool orchestration, memory/proactive behavior, or protected/freeze-growth files.

Fast path requirements:

- read `AGENTS.md` and the directly relevant files only
- state the scope classification in one sentence when useful
- run targeted checks only
- do not load the full bootstrap pack, emit full planning schemas, or perform best-practice research unless the task escalates
- if evidence shows semantic, architecture, eval, or protected-file impact, stop and switch to the full workflow

Full workflow applies to architecture-sensitive, PR-producing, canonical spec, eval-governance, mutation, provider/tool, memory, proactive, migration, or protected/freeze-growth work.

Before any non-trivial plan or edit, classify whether the task may be a capability-order trap, architecture-boundary trap, both, or neither. Use the relevant skill only when that risk is present; do not turn cosmetic, typo, local fixture, or narrow test edits into full governance work.

## Branch Invariants

This branch may be `codex/advanced-product-lab`, a long-lived isolated product-lab branch for the complete advanced product.

- Inside the lab branch, build the complete advanced product surface: runtime integration, UX, E2E, Grokfast diagnostics, control loop, recommendation/rescue/proactive loop, long-term memory, and simulated dogfood traces.
- Lab runtime capability flags may be `true` when scoped to the isolated product lab; do not disable lab capabilities merely because mainline activation must remain walled off.
- Merge-back to main/self-use V1 must keep production activation walled off unless a separate explicit activation PR enables route mounting, scheduler delivery, production DB migration, canonical mutation, durable product memory, or default runtime connection.
- Lab reports must distinguish `lab_enabled=true` from `mainline_activation_enabled=false`.
- Stable repo branches are `main` and `codex/advanced-product-lab`; do not create additional long-lived implementation branches for advanced-product work.
- Advanced product-lab and Current Shell work must converge on the same Manager-style agent contract, shared truth-owner map, and shared tool vocabulary.
- Current Shell manager/runtime contracts are the upstream alignment target; extend them additively for later-wave lab capabilities.
- Treat `pass1/pass2`, scripted manager loops, and direct fixture runners as harness shapes only. The target runtime remains one bounded Manager-style ReAct loop with shared capability planning, shared tool registry, shared truth owners, and deterministic legality guards.
- Long-term memory must expose auditable human-readable surfaces such as `user.md` and provenance files such as `source.md`; they are not raw transcript dumps.
- Repeated or reusable meals are shared product objects such as `UserFoodEntity` or `RecurringMealTemplate`; memory is only a retrieval hint, recall summary, or promotion evidence.

## Truth Rules

Default truth families:

1. [docs/specs/](docs/specs) owns canonical product, runtime, and architecture truth.
2. [docs/quality/](docs/quality) owns eval bundle gates and E2E acceptance criteria.
3. CI and harness output provide execution evidence.
4. `git diff` and commit history provide change evidence.

Do not use preservation snapshots under [docs/_spec_snapshots/](docs/_spec_snapshots), completed task artifacts, or handoff docs as default truth.

Product end-state and real user interaction truth outrank eval fixture shape. When architecture, runtime, manager contracts, tools, guards, or EDD plans are designed, use this precedence:

1. user-visible product behavior and end-state truth
2. canonical architecture and domain ownership
3. runtime invariants and manager contract
4. eval bundles, benchmarks, replay packs, and runner implementations

Eval assets validate product truth; they do not design it. If test assets are green but product behavior is wrong, treat product behavior as the bug and eval assets as incomplete or misaligned evidence.

Semantic contracts must be wide enough to represent ambiguity, multi-capability turns, no-op/no-mutation outcomes, false positives, and holdouts. Keep schema, provenance, mutation, and activation contracts narrow, but do not narrow user-intent or workflow enums because a fixture set is easier to pass.

## Planning Gates

Use these gates for non-trivial or PR-producing work. Skip them for fast-path edits unless the task escalates.

- Strategic sequencing: state whether the slice is current-mainline or an allowed detour, why it is safe now, and what returns work to the mainline.
- Capability order: do not use product journey order or local momentum as implementation order.
- Capability pyramid: `L0 Product Operating Rules`, `L1 InteractionEvent / CurrentTurnContext`, `L2 AttachmentDecision / TransitionGuardResult`, `L3 MealThread / Draft / Commit Boundary`, `L4 RetrievalIntent / Source Selection`, `L5 Evidence / Packet Layer`, `L6 Nutrition Synthesis`, `L7 Final Mapping Boundary`, `L8 Mutation / Ledger / Version`, `L9 Same-Truth / UI / Memory / Proactive`.
- Slice classification: state capability layer, upstream dependencies, contract status, slice mode, user-facing/runtime/mutation impact, and why this is not a local-next-step trap.
- High-impact runtime, retrieval, database, API, testing, security, provider, tool-orchestration, memory, proactive, or mutation work must record best-practice evidence from current official or primary sources.
- High-impact runtime, retrieval, tool orchestration, evaluation, semantic routing, mutation, provider seam, structured extraction, or architecture-boundary work must name `best_practice_evidence`, `llm_deterministic_boundary`, and `semantic_owner` before implementation.
- `slice_mode` is a list, not a single enum. A slice may be `diagnostic_only + offline_runtime` or `fixture_only + producer_honesty`.
- Downstream diagnostic-only work may proceed before every upstream layer is fully closed. Downstream user-facing behavior, runtime truth, or mutation must wait for required upstream context, ownership, and transition boundaries to be contract-backed.

## Minimum Read Path

Bootstrap read path is:

1. `AGENTS.md`
2. directly relevant task files
3. [docs/DOC_INDEX.md](docs/DOC_INDEX.md) only when document ownership, active-vs-legacy routing, or file placement is uncertain
4. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md) only for PR-producing, plan-changing, or execution-state-sensitive work
5. [docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md](docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md) only for high-impact or architecture-boundary work
6. [docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md](docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md), [docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml](docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml), and [docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml](docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml) only when eval gate status, Current Shell coordination, or acceptance evidence matters
7. task-specific canonical spec, quality gate, or runbook
8. [docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md](docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md) only when historical pre-self-use runtime reference is explicitly needed

Default workflow is repo-truth-first interactive implementation. Unattended / overnight autonomy is optional and should only be loaded when the task intentionally uses an approval-light continuation protocol.

## Spec And Document Editing

Use the lightest safe edit method: `apply_patch` for manual local edits, deterministic/native tooling for mechanical or generated changes, and parser-based updates for structured data when practical. Existing specs, architecture docs, and governance docs must stay section-level and coverage-preserving unless an explicit approved rewrite path exists. Never delete-and-recreate existing canonical docs as a routine edit.

For existing specs, architecture docs, governance docs, and canonical markdown:

- do not delete-and-recreate an existing file as a routine edit
- do not silently rewrite a full document when the request is targeted
- prefer minimal additive edits and section-level patches
- typo, link, formatting, and small additive edits may use the fast path if the diff is clearly local
- use [docs/governance/SPEC_EDITING_PROTOCOL.md](docs/governance/SPEC_EDITING_PROTOCOL.md) for canonical spec edits, high-risk restructures, patch-anchor failures, or near-total rewrites
- if a rewrite is explicitly approved, first make a content inventory and preserve semantic coverage unless the user explicitly approves a semantic change
- mechanical/parser-safe transformations may use deterministic tooling only when the diff is reviewed and semantic coverage is preserved

## Encoding Evidence

Terminal rendering is not encoding evidence. PowerShell, console fonts, code pages, and subprocess pipes may display valid UTF-8 bytes as mojibake.

- Do not classify a file as corrupted because `Get-Content`, `type`, shell output, or terminal transcript looks garbled.
- Prove encoding status with byte-level verification.
- For canonical markdown, run `python scripts/check_markdown_encoding.py --policy-docs --require-bom` when editing canonical docs, investigating encoding, or making a final encoding claim.
- If byte-level verification passes but terminal output looks garbled, classify it as `terminal_rendering_issue`, not `encoding_corruption`.
- Do not use PowerShell inline non-ASCII probes as formal evidence; use UTF-8 files or Python byte reads.

## Destructive Git Command Ban

禁止在未得到明確人工確認前執行：

- `git clean`
- `git clean -fd`
- `git clean -fdx`
- `git reset --hard`
- `git checkout .`
- `git restore .`
- `git rebase`
- force push

如果真的需要清理，必須先執行並回報：

- `git status --short --branch`
- `git clean -n -d`
- `git diff --name-status`
- `git diff --cached --name-status`
- `git ls-files --others --exclude-standard`

任何會刪除 untracked files 的操作，必須先建立 repo snapshot。Coding agents must not use destructive git commands to solve conflicts; if a branch conflict appears, output a conflict report instead of resetting or cleaning.

## Always-On Rules

- Source-of-truth sync is mandatory when canonical understanding changes.
- Current Shell default is repo-truth-first interactive implementation, not detached autorun.
- Deterministic layers must not override completed LLM decision outputs. They may validate, reject, downgrade, derive, or request one bounded repair round.
- Fake providers in deterministic diagnostics may simulate LLM/manager structured outputs, but the harness must not infer user intent, food semantics, workflow effect, or final mapping by keyword or obsolete oracle.
- Unapproved product semantics must not enter eval packs, benchmark oracles, semantic taxonomies, or pass/fail rubrics.
- Do not promote response-side distinctions such as `inquiry vs explain`, tone, style, reluctance wording, or explanation density into primary routing taxonomy unless they change workflow effect.
- Prompt and evidence-policy fixes must target generalized estimation behavior, not one-off item patches.
- Hard-boundary manager branch rules must live in shared manager contract helpers, not individual provider adapters.
- Ownership-sensitive slices must make selector ownership and debt triage explicit before editing.
- BuilderSpace transport is a runtime contract.
- Provider/model capability must be artifact-proven; endpoint-level support does not imply model-level reliability.
- Model dependence should be isolated through profile and transport seams, not spread into product contract ownership.
- Provider adapters must stay transport-aware, not product-semantic.
- Legacy Bundle Version 1 / Bundle Version 2 artifacts, runners, and oracle vocabulary must not drive product semantics, build order, manager contracts, or readiness claims.
- Reviewer steering remains `proceed / narrow / stop` for architecture-sensitive work.
- Chat is the primary interaction surface unless a canonical spec defines a different primary surface; UI defaults to mirror/inbox behavior.
- Schema-sensitive ORM changes must ship with Alembic migrations.
- Governance docs are conditional reads; pull them only when the task touches repo process, spec editing, task protocol, or handoff protocol.

## Protected And Freeze-Growth Files

Protected legacy files must stay thin:

- `app/routes.py`
- `app/schemas.py`
- `app/usecases/text_meal.py`

Freeze-growth files must not grow and must carry explicit justification when touched:

- `app/application/evidence_assembly.py`
- `app/application/context_assembly.py`
- `app/agent/knowledge_packets.py`

Fat-file growth is a local-first hard wall, not a CI-only advisory. Before commit, `check-fat-files-staged` must reject staged growth across protected, freeze-growth, and active Python cap rules; if it fails, extract or shrink the change instead of adding transition overrides or deferring the failure to CI.

## Default Harness Wall

Default deterministic guardrails include diff scope, freeze-growth checks, staged fat-file checks, commit traceability, layer integrity, migration discipline, encoding checks, smoke/integration/targeted tests, and advisory repo-hygiene scans when structure or docs ontology changes.

## Conditional Reads

- Provider/runtime transport work: [docs/provider/builderspace_openapi.txt](docs/provider/builderspace_openapi.txt), [docs/provider/BUILDERSPACE_PROVIDER_PROFILE.md](docs/provider/BUILDERSPACE_PROVIDER_PROFILE.md), [docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md](docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md).
- Agent memory or reusable-lesson workflow: [docs/agent/EVOMAP_WORKFLOW.md](docs/agent/EVOMAP_WORKFLOW.md).
- Optional unattended / overnight autonomy protocol: [docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md](docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md).
- Spec or architecture work: [docs/specs/](docs/specs), [docs/governance/SPEC_EDITING_PROTOCOL.md](docs/governance/SPEC_EDITING_PROTOCOL.md), [docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md).
- Legacy pre-self-use runtime reference only: [docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md](docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md).
- Legacy acceptance-package / E2E regression work only: use current shell artifacts and active runtime traces first; do not resurrect deleted Bundle Version 1 / Bundle Version 2 docs, runners, parity audits, or obsolete oracles.
- Onboarding / budget / today-sync happy-path work: [docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md](docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md), [docs/specs/L2_DATA_STATE_SPEC.md](docs/specs/L2_DATA_STATE_SPEC.md), [docs/specs/L2A_DATA_DICTIONARY_SPEC.md](docs/specs/L2A_DATA_DICTIONARY_SPEC.md).
- Body observation, weight update, or exercise input work: [docs/specs/L3_5_BODY_OBSERVATION_EXERCISE_WORKFLOW_SPEC.md](docs/specs/L3_5_BODY_OBSERVATION_EXERCISE_WORKFLOW_SPEC.md).
- Proactive scheduler, trigger conditions, suppression, or nudge design: [docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md](docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md).
- Eval / benchmark / suite-governance work: [docs/quality/](docs/quality) and the task-specific eval gate or benchmark manifest.
- Founder human gate testing or UX journey validation: [docs/quality/UX_JOURNEY_TO_SLICE_MAP.md](docs/quality/UX_JOURNEY_TO_SLICE_MAP.md).
- Repo rules or file placement: [docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md](docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md), [docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md](docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md).
- Task artifact use: [docs/governance/TASK_CHECKIN_PROTOCOL.md](docs/governance/TASK_CHECKIN_PROTOCOL.md).
- Optional resume or emergency transfer only: [docs/governance/HANDOFF_CONTRACT.md](docs/governance/HANDOFF_CONTRACT.md).
- Touching a freeze-growth file: [docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md](docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md).
