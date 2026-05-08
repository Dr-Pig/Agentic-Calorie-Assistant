`AGENTS.md` is the only bootstrap file in this repository.

Use it as a map, not a handbook. Load the minimum path first, then retrieve deeper docs only when the task shape requires them.

[docs/DOC_INDEX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/DOC_INDEX.md) owns document taxonomy, file-role mapping, and longer navigation guidance. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md) owns the minimal current execution pointer. [docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md) owns the product-wide anti-drift operating layer. `AGENTS.md` only owns bootstrap order, always-on repo rules, and conditional-read triggers.

Before any plan or edit, first classify whether this is a capability-order trap, architecture-boundary trap, both, or neither; if either may apply, pause and use the relevant skill before choosing files, tests, classes, eval fixes, or local next steps.

## Truth Hierarchy

Default truth families are:

1. [docs/specs/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs) — canonical product, runtime, and architecture truth
2. [docs/quality/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality) — eval bundle gates and E2E acceptance criteria
3. CI and harness output
4. `git diff / commit history`

Do not use preservation snapshots under [docs/_spec_snapshots/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/_spec_snapshots), completed task artifacts, or handoff docs as default truth.

## Product Truth Priority

Product end-state and real user interaction truth are higher-order than eval fixture shape.

Apply this precedence when architecture, runtime, manager contracts, tools, guards, or EDD plans are being designed:

1. user-visible product behavior and end-state truth
2. canonical architecture and domain ownership
3. runtime invariants and manager contract
4. eval bundles, benchmarks, replay packs, and runner implementations

Hard rules:

- do not treat benchmark fixture shape, runner vocabulary, or replay-pack implementation detail as product architecture truth
- eval assets are validators of product truth, not designers of product truth
- when eval assets and intended product behavior diverge, resolve the product invariant first, then realign eval governance and oracles explicitly
- manager, tool, and guard design must be justified in terms of user-visible behavior, truth ownership, latency, and honesty, not merely by making a fixture pass

## Strategic Sequencing Gate

Before approving, planning, or implementing any non-trivial slice, first decide whether the slice is on the current mainline or is a detour.

Do not approve a slice only because it is locally correct.

Every non-trivial plan must declare:

```yaml
current_mainline:
is_detour: true | false
blocked_mainline:
detour_reason:
detour_exit_gate:
exit_gate_status:
return_slice_after_exit:
strategic_verdict: mainline | allowed_detour | stop_and_return
```

If `is_detour=false`, detour-only fields such as `blocked_mainline`, `detour_reason`, and `detour_exit_gate` should be `null` or `not_applicable`; record the active risk as `mainline_blocker_being_removed` instead.

If a detour exit gate is green, return to the blocked mainline unless new evidence proves another blocker.

## Capability Dependency Build Order

Do not use product journey order or local slice momentum as implementation order.

Implementation order must follow the product capability dependency pyramid:

- `L0 Product Operating Rules`
- `L1 InteractionEvent / CurrentTurnContext`
- `L2 AttachmentDecision / TransitionGuardResult`
- `L3 MealThread / Draft / Commit Boundary`
- `L4 RetrievalIntent / Source Selection`
- `L5 Evidence / Packet Layer`
- `L6 Nutrition Synthesis`
- `L7 Final Mapping Boundary`
- `L8 Mutation / Ledger / Version`
- `L9 Same-Truth / UI / Memory / Proactive`

Before implementing any non-trivial slice, the planner must state:

1. which pyramid layer the slice belongs to
2. which upstream layers it depends on
3. whether each required upstream layer has a contract-backed baseline
4. whether the slice changes user-facing behavior, runtime truth, or mutation
5. whether the slice is diagnostic-only, fixture-only, producer-honesty-only, offline-runtime, user-facing, or mutation-bearing
6. why the slice is safe to do now instead of being a local next-step trap

Required slice dependency check:

```yaml
capability_layer:
upstream_dependencies:
  - layer:
    contract_status: missing | draft | contract_backed | tested
    risk_if_missing:
slice_mode:
  - diagnostic_only
user_facing_behavior_changed: true | false
runtime_truth_changed: true | false
mutation_changed: true | false
safe_to_proceed_now: true | false
why_not_local_next_step_trap:
```

Required high-impact best-practice and semantic-owner check:

```yaml
best_practice_evidence:
  required: true
  sources_checked:
    - official_or_primary_source:
  adopted_guidance:
  rejected_guidance:
  conflict_with_repo_habits:
  how_the_design_changed:
llm_deterministic_boundary:
  decision_surface:
  truth_owner: LLM | deterministic | hybrid | human
  deterministic_role: validate | derive | reject | downgrade | repair | none
  llm_role: judge | synthesize | classify | explain | none
  do_not_override:
semantic_owner:
  user_intent:
  food_semantics:
  routing_or_workflow_effect:
  mutation_legality:
  persistence_truth:
```

For any high-impact runtime, retrieval, tool orchestration, evaluation, semantic routing, mutation, provider seam, structured extraction, or architecture-boundary slice, missing `best_practice_evidence`, `llm_deterministic_boundary`, or `semantic_owner` is a stop condition before implementation.

`slice_mode` is a list, not a single enum. A slice may legitimately be more than one thing at once, for example `diagnostic_only + offline_runtime` or `fixture_only + producer_honesty`.

Hard rule:

- downstream diagnostic-only work may proceed before every upstream layer is fully closed
- downstream user-facing behavior, runtime truth, or mutation must not proceed before required upstream context, ownership, and transition boundaries are contract-backed
- if a local next step conflicts with the capability dependency pyramid, stop and re-plan

## Read First

1. [docs/DOC_INDEX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/DOC_INDEX.md)
2. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md)
3. [docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md)
4. [docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md)

If the task needs architecture context or eval gate status, read next:

5. [docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml)
6. [docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml)
7. task-specific canonical spec or runbook
8. [docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md) only when historical pre-self-use runtime reference is explicitly needed

Bootstrap read path is:

`AGENTS.md -> docs/DOC_INDEX.md -> docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md -> docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md -> docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md -> docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml -> docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml -> track-specific canonical runbook / gate -> task-specific spec`

Default workflow is repo-truth-first interactive implementation. Unattended / overnight autonomy is optional and should only be loaded when the task is intentionally using an approval-light continuation protocol.

## Operating Triggers

Use deeper process docs only when the task shape requires them:

- EvoMap:
  - conditional only
  - use [docs/agent/EVOMAP_WORKFLOW.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/EVOMAP_WORKFLOW.md) when the slice introduces reusable capability or cross-repo workflow value
  - start from repo truth first for repo-local blockers
- Best practice search:
  - before high-impact runtime, retrieval, database, API, testing, or security work, check current official or primary sources
  - record adopted and rejected guidance under `best_practice_evidence`
- Product-wide anti-drift entry:
  - read [docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md) before high-impact provider, retrieval, DB, packet, mutation, or architecture-boundary slices
  - use it to identify owner docs, required planning fields, and forbidden shortcut patterns before editing
- Provider/runtime transport:
  - BuilderSpace transport is a runtime contract
  - before touching adapters, structured transport, or provider capability attribution, read the provider docs listed in Conditional Reads
  - treat model capability as artifact-proven, not assumed from endpoint compatibility
- Legacy acceptance-package / E2E claims:
  - legacy Bundle Version 1 / Bundle Version 2 packages are not repo truth, build order, semantic owners, or manager/runtime authority
  - if an old acceptance runner or oracle conflicts with manager-style contracts, rebuild the harness around active runtime traces instead of adapting product architecture to the old package
  - historical bundle naming in active runtime files is compatibility vocabulary only until the entrypoint rename lands
- Ownership / debt / reviewer triage:
  - architecture-sensitive slices must make selector ownership, debt triage, and reviewer `proceed / narrow / stop` framing explicit
  - use [docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md) only for unattended / overnight / approval-light execution

## Encoding Evidence Contract

Terminal rendering is not encoding evidence. PowerShell, console fonts, code pages, and subprocess pipes may display valid UTF-8 bytes as mojibake.

Hard rules:

- do not classify a file as corrupted because `Get-Content`, `type`, shell output, or terminal transcript looks garbled
- prove encoding status with byte-level verification only
- for canonical markdown, run `python scripts/check_markdown_encoding.py --policy-docs --require-bom`
- if byte-level verification passes but terminal output looks garbled, classify it as `terminal_rendering_issue`, not `encoding_corruption`
- if byte-level verification fails, report the exact failing path and reason from the verifier
- do not use PowerShell inline non-ASCII probes as formal evidence; use UTF-8 files or Python byte reads

This contract exists because CJK mojibake can happen before the agent sees command output. The repo truth is bytes and JSON artifacts, not terminal rendering.

## Destructive Git Command Ban

* 禁止在未得到明確人工確認前執行：
  * `git clean`
  * `git clean -fd`
  * `git clean -fdx`
  * `git reset --hard`
  * `git checkout .`
  * `git restore .`
  * `git rebase`
  * force push
* 如果真的需要清理，必須先執行並回報：
  * `git status --short --branch`
  * `git clean -n -d`
  * `git diff --name-status`
  * `git diff --cached --name-status`
  * `git ls-files --others --exclude-standard`
* 任何會刪除 untracked files 的操作，必須先建立 repo snapshot。
* coding agent 不得用 destructive git commands 來「解決衝突」。
* 如果遇到 branch conflict，先輸出 conflict report，不得自行 reset / clean。

## Hard Rules Summary

- source-of-truth sync is mandatory when canonical understanding changes
- Current Shell default is repo-truth-first interactive implementation, not detached autorun
- product truth is higher-order than eval shape
  - do not design architecture, manager contracts, tool surfaces, or guards around the incidental shape of benchmark fixtures, replay packs, or runner payloads
  - first decide the intended user-visible behavior and truth ownership, then use evals to verify that behavior
  - if a test asset is green but the resulting product behavior is wrong, treat the product behavior as the bug and the eval asset as incomplete or misaligned evidence
- deterministic layers must not override completed LLM decision outputs
  - deterministic diagnostic mode means offline, reproducible, and no live provider call; it does not grant deterministic semantic ownership
  - do not deterministically create, rewrite, or default semantic fields such as `intent`, `workflow_effect`, `action_taken`, `response_mode_hint`, `follow_up_needed`, `followup_question`, `route_target`, `exactness`, or `resolution_mode` after a pass completes
  - deterministic layers may validate, reject, downgrade, derive, or request one bounded repair round
  - fake providers in deterministic diagnostics may simulate LLM / manager structured outputs, but the harness must not infer user intent, food semantics, workflow effect, or final mapping by keyword or obsolete oracle
- unapproved product semantics must not enter eval truth
  - do not write unapproved product semantics into eval packs, benchmark oracles, semantic taxonomies, or pass/fail rubrics
  - evidence collection may record competing interpretations or ambiguity clusters, but it must not silently canonize unresolved product decisions
- do not promote response-side distinctions into primary routing taxonomy unless they change workflow effect
  - do not encode `inquiry vs explain`, tone, style, reluctance wording, explanation density, or similar response-realization differences as primary routing labels unless they change target attachment, workflow ownership, disposition, or state mutation semantics
- prompt and evidence-policy fixes must target generalized estimation behavior, not one-off item patches
  - do not optimize prompts around a single SKU, menu item, or one benchmark example unless the canonical spec explicitly requires that item-specific behavior
  - prefer generalized rules based on evidence class, identity resolution, portion ambiguity, packaging cues, and uncertainty topology
  - when a benchmark exposes a failure, first look for the broader estimation-family rule that should govern that case class; fix the family rule, not just the surfaced example
- hard-boundary manager branch rules must live in shared manager contract helpers, not individual provider adapters
- provider/model capability must be artifact-proven; endpoint-level support does not imply model-level reliability
- model dependence should be isolated through profile and transport seams, not spread into product contract ownership
- provider adapters must stay transport-aware, not product-semantic
- high-impact agent runtime work must start from current official best practice and a high-capability baseline
  - for agent runtime, retrieval, tool orchestration, and structured extraction work, check current official best-practice guidance before constraining the design
  - when official guidance and current repo habits conflict, build the strongest reasonable baseline first, then use eval / latency / cost traces to converge
  - do not prematurely hard-cap iteration budgets, retrieval budgets, or model capability before an eval-backed baseline exists
- legacy Bundle Version 1 / Bundle Version 2 artifacts, runners, and oracle vocabulary must not drive product semantics, build order, manager contracts, or readiness claims
- ownership-sensitive slices must make selector ownership and debt triage explicit before editing
- reviewer steering remains `proceed / narrow / stop` for architecture-sensitive work
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
- fat-file growth is a local-first hard wall, not a CI-only advisory
  - before commit, `check-fat-files-staged` must reject staged growth across protected, freeze-growth, and active Python cap rules
  - if it fails, extract or shrink the change instead of adding transition overrides or deferring the failure to CI
- schema-sensitive ORM changes must ship with Alembic migrations
- governance docs are conditional reads; pull them only when the task touches repo process, spec editing, task protocol, or handoff protocol

## Default Harness Wall

Default deterministic guardrails include:

- diff scope and freeze-growth checks
- staged fat-file hard gate via `check-fat-files-staged`
- commit traceability checks
- layer integrity and migration discipline checks
- encoding, fat-file, smoke, integration, and targeted test gates
- advisory repo-hygiene scans when structure or docs ontology changes

## Conditional Reads

- provider/runtime transport work:
  - [docs/provider/builderspace_openapi.txt](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider/builderspace_openapi.txt)
  - [docs/provider/BUILDERSPACE_PROVIDER_PROFILE.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider/BUILDERSPACE_PROVIDER_PROFILE.md)
  - [docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md)
- agent memory / reusable-lesson workflow:
  - [docs/agent/EVOMAP_WORKFLOW.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/EVOMAP_WORKFLOW.md)
- optional unattended / overnight autonomy protocol:
  - [docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md)
- spec or architecture work:
  - [docs/specs/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs)
  - [docs/governance/SPEC_EDITING_PROTOCOL.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/governance/SPEC_EDITING_PROTOCOL.md)
  - [docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/governance/IMPLEMENTATION_PLANNING_REPLAN_PROTOCOL.md)
  - [docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md) when the work touches Wave 1 Phase B-2 product-intelligence, retrieval intent, packet compression, follow-up policy, or small-anchor planning
  - [docs/specs/WAVE_1_PHASE_B2_P0_EXECUTION_PLAN.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_P0_EXECUTION_PLAN.md) when the work is selecting or executing the B-2 P0 build order
- Wave 1 implementation work:
  - [docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md)
  - [docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md)
  - [docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md)
  - [docs/specs/app_v2_ideal_architecture_final.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/app_v2_ideal_architecture_final.md)
  - task-specific canonical spec
  - task-specific micro-suite / eval gate
- legacy acceptance-package / E2E regression work only:
  - use current Manager-style Founder E2E diagnostics and Wave 1 capability micro-suites
  - do not resurrect deleted Bundle Version 1 / Bundle Version 2 docs, runners, parity audits, or obsolete oracles
- onboarding / budget / today-sync happy-path work:
  - [docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md)
  - [docs/specs/L2_DATA_STATE_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L2_DATA_STATE_SPEC.md)
  - [docs/specs/L2A_DATA_DICTIONARY_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L2A_DATA_DICTIONARY_SPEC.md)
- body observation, weight update, or exercise input work:
  - [docs/specs/L3_5_BODY_OBSERVATION_EXERCISE_WORKFLOW_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L3_5_BODY_OBSERVATION_EXERCISE_WORKFLOW_SPEC.md)
- proactive scheduler, trigger conditions, suppression, or nudge design:
  - [docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md)
- eval / benchmark / suite-governance work:
  - [docs/quality/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality)
  - task-specific eval gate or benchmark manifest under the active quality docs
- founder human gate testing or UX journey validation:
  - [docs/quality/UX_JOURNEY_TO_SLICE_MAP.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/UX_JOURNEY_TO_SLICE_MAP.md)
- repo rules or file placement:
  - [docs/specs/app_v2_ideal_architecture_final.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/app_v2_ideal_architecture_final.md)
  - [docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md)
- task artifact use:
  - [docs/governance/TASK_CHECKIN_PROTOCOL.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/governance/TASK_CHECKIN_PROTOCOL.md)
- optional resume or emergency transfer only:
  - [docs/governance/HANDOFF_CONTRACT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/governance/HANDOFF_CONTRACT.md)
- touching a freeze-growth file:
  - [docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/governance/FREEZE_GROWTH_EXTRACTION_MAP.md)
