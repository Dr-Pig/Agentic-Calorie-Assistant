# Agent Entry

`AGENTS.md` is the only bootstrap file in this repository.

Use it as a map, not a handbook. Load the minimum path first, then retrieve deeper docs only when the task shape requires them.

## Truth Hierarchy

Default truth families are:

1. [docs/specs/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs) — canonical product, runtime, and architecture truth
2. [docs/quality/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality) — eval bundle gates and E2E acceptance criteria
3. CI and harness output
4. `git diff / commit history`

Do not use [docs/archive/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/archive), [artifacts/docs-snapshots/](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/artifacts/docs-snapshots), completed task artifacts, or handoff docs as default truth.

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

## Read First

1. [docs/V2_DOC_INDEX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/V2_DOC_INDEX.md)
2. [docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md)

If the task needs architecture context or eval gate status, read next:

3. [docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md)
4. [docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md)
5. task-specific canonical spec
6. task-specific micro-suite / eval gate

Default planner path is:

`AGENTS.md -> docs/V2_DOC_INDEX.md -> docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md -> docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md -> docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md -> task-specific canonical spec -> task-specific micro-suite / eval gate`

## EvoMap Operating Rule

EvoMap usage is a conditional repo operating policy, not a mandatory per-slice ritual.

Use EvoMap when the current slice introduces a reusable capability need, a generic workflow gap, or a problem likely to recur across models, providers, or repos. For repo-local blocker work already explained by current docs, artifacts, readiness reports, and tests, start from repo truth first and skip EvoMap unless reuse value is likely.

When EvoMap is relevant:

- use local recall (`gep_recall`) first
- use external Skills or community GEP assets only when the need is generic enough to justify capability lookup
- record reusable lessons (`gep_record_outcome`) only when the slice produced durable guidance worth reusing

Read:

- [docs/agent/EVOMAP_WORKFLOW.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/EVOMAP_WORKFLOW.md)
- [docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md) for bounded autonomy, planner/evaluator/worker workflow, and stop-gate rules
- [docs/specs/WAVE_1_ARCHITECTURE_TRANSITION_LADDER.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_ARCHITECTURE_TRANSITION_LADDER.md) for staged dependency inversion, seam timing, and migration boundaries

Hard rules:

- EvoMap is not a patch log
- EvoMap records reusable lessons, workflow guides, and durable architecture rules
- do not read or search EvoMap mechanically on every slice
- external Skills and GEP assets are capability aids, not canonical repo truth
- EvoMap does not replace current repo docs, code, or artifacts as source of truth
- if EvoMap is unavailable, say so explicitly and continue with repo truth

## Best Practice Search

Before implementing high-impact code, you MUST search for current best practices.

A steering file is auto-loaded for all Python work: `.kiro/steering/best-practice-search.md`

This file is automatically included in context when editing `.py` files. It requires you to search for best practices before implementing:

- Agent runtime (manager, tools, orchestration)
- Retrieval (RAG, knowledge lookup)
- Database patterns (ORM, migrations)
- API design
- Testing patterns
- Security

Use `remote_web_search` to find current best practices. Apply what you find to your implementation.

When the task is architecture-sensitive and a human is not expected to approve every micro-slice manually, the planner and evaluator must also follow:

- [docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md)

The evaluator should prioritize long-term architecture benefit, ownership boundaries, and future build quality, not only local implementation correctness.

## BuilderSpace Provider Contract

The BuilderSpace provider surface is part of the runtime contract. Before changing provider adapters, structured transport, tool/function calling transport, `response_format`, `tools` / `tool_choice`, model-specific token or temperature handling, or provider capability attribution, agents must read:

- [docs/provider/builderspace_openapi.txt](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider/builderspace_openapi.txt)
- [docs/provider/BUILDERSPACE_PROVIDER_PROFILE.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider/BUILDERSPACE_PROVIDER_PROFILE.md)
- [docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md)

Important known facts from the current OpenAPI:

- `/v1/chat/completions` is OpenAI-compatible.
- `ChatCompletionRequest` includes `tools`.
- `ChatCompletionRequest` includes `tool_choice`.
- `ChatCompletionRequest` has `additionalProperties: true`, so provider-specific OpenAI-compatible fields may be accepted, but support must be proven by artifacts.
- `gpt-5` uses `max_completion_tokens` handling instead of raw `max_tokens`; the backend may convert automatically.
- `kimi-k2.5` and `gpt-5` have enforced `temperature=1.0` constraints.
- `response_format.type=json_schema` support must be artifact-proven, not assumed from compatibility claims.
- Forced `tool_choice` obedience must be artifact-proven, not assumed from schema shape alone.

Hard rules:

- treat BuilderSpace structured output support as a capability probe, not assumed truth
- if a request is accepted but the provider returns prose instead of the expected structured payload, classify it as a transport/capability issue when appropriate; do not silently widen parser recovery
- if `tools/tool_choice` is used for synthetic decision transport, the synthetic tool arguments schema must come from shared branch-contract helpers, not an adapter-local schema copy
- adapter code may choose transport mode, but must not own product semantics
- any fallback from `json_schema` or tool-call transport must be trace-visible
- artifacts must preserve transport attribution fields such as `structured_output_transport_*` and `decision_transport_*`

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

## Eval Bootstrap Contract

This section applies only when claiming a legacy bundle / E2E acceptance verdict. It is not the default implementation start path for Wave 1 work.

Before claiming any bundle eval result, you MUST execute the bootstrap order below:

1. load owner truth
   - [docs/specs/APP_V2_IMPLEMENTATION_PLAN.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/APP_V2_IMPLEMENTATION_PLAN.md)
   - the corresponding bundle eval pack
2. run spec-to-runner parity audit
3. run the bundle eval runner
4. verify trace roundtrip and text integrity
5. run or explicitly classify founder realism status

Hard rules:

- if parity audit is incomplete or has blocking gaps, do not claim bundle pass
- if founder realism status is unknown, only report `founder_realism_status = not_run`
- do not collapse these verdicts into a single assistant judgment
- pass / fail claims must be backed by:
  - full bundle report
  - parity audit report
  - founder realism report or explicit `not_run`

Required bundle verdict fields:

- `runner_case_status`
- `coverage_status`
- `founder_realism_status`
- `bundle_ready_for_human_e2e`

Assistant claim policy:

- do not say `全部通過`, `可以人工 E2E`, `bundle 完成`, or `可以切下一階段`
  unless coverage is complete, blocking gaps are zero, and founder realism is not failing
- when official runner is green but parity/founder checks are not, say so explicitly

## Planner Default

- `APP_V2_IMPLEMENTATION_PLAN.md` is a legacy / historical implementation plan unless reconciled
- `V2_EVAL_BUNDLE_X_CASES.md` are acceptance / regression reference, not build order
- `app_v2_ideal_architecture_final.md` is the canonical architecture truth (replaces APP_V2_TARGET_ARCHITECTURE_SPEC.md)
- governance docs are exception tools, not default routing

V2 uses **eval-first** execution model:
- system capabilities determine implementation order
- product capabilities determine acceptance scope
- eval-first ≠ schema-first
- bundle-first ≠ implementation order
- synthetic readiness gate ≠ runtime product pass
- Phase B gates do not complete Wave 1 unless Phase C mutation / ledger / same-truth integration passes
- Eval bundles are acceptance / regression references, not build order
- Bundle pass does not imply Wave 1 completion unless the relevant Wave 1 product closure and trace-backed runtime integration gates are also satisfied

When claiming a legacy bundle / E2E acceptance result, run the Eval Bootstrap Contract. When implementing Wave 1, start from the Read First planner path and task-specific canonical specs, not from bundle order.

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
- product truth is higher-order than eval shape
  - do not design architecture, manager contracts, tool surfaces, or guards around the incidental shape of benchmark fixtures, replay packs, or runner payloads
  - first decide the intended user-visible behavior and truth ownership, then use evals to verify that behavior
  - if a test asset is green but the resulting product behavior is wrong, treat the product behavior as the bug and the eval asset as incomplete or misaligned evidence
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
- hard-boundary manager branch rules must live in shared manager contract helpers, not individual provider adapters
- provider/model capability must be artifact-proven; endpoint-level support does not imply model-level reliability
- model dependence should be isolated through profile and transport seams, not spread into product contract ownership
- provider adapters must stay transport-aware, not product-semantic
- high-impact agent runtime work must start from current official best practice and a high-capability baseline
  - for agent runtime, retrieval, tool orchestration, and structured extraction work, check current official best-practice guidance before constraining the design
  - when official guidance and current repo habits conflict, build the strongest reasonable baseline first, then use eval / latency / cost traces to converge
  - do not prematurely hard-cap iteration budgets, retrieval budgets, or model capability before an eval-backed baseline exists
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

- provider/runtime transport work:
  - [docs/provider/builderspace_openapi.txt](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider/builderspace_openapi.txt)
  - [docs/provider/BUILDERSPACE_PROVIDER_PROFILE.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider/BUILDERSPACE_PROVIDER_PROFILE.md)
  - [docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/provider/MANAGER_MODEL_CANDIDATE_MATRIX.md)
- agent memory / reusable-lesson workflow:
  - [docs/agent/EVOMAP_WORKFLOW.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/EVOMAP_WORKFLOW.md)
- bounded autonomy / planner-evaluator-worker workflow:
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
- Legacy bundle / E2E regression work only:
  - [docs/specs/APP_V2_IMPLEMENTATION_PLAN.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/APP_V2_IMPLEMENTATION_PLAN.md)
  - [docs/quality/V2_EVAL_BUNDLE_1_CASES.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/V2_EVAL_BUNDLE_1_CASES.md)
  - [docs/quality/V2_EVAL_BUNDLE_2_CASES.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/quality/V2_EVAL_BUNDLE_2_CASES.md)
- onboarding / budget / today-sync happy-path work:
  - [docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L0B_BUDGET_LEDGER_SYNC_HAPPY_PATH_SPEC.md)
  - [docs/specs/L2_DATA_STATE_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L2_DATA_STATE_SPEC.md)
  - [docs/specs/L2A_DATA_DICTIONARY_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L2A_DATA_DICTIONARY_SPEC.md)
- body observation, weight update, or exercise input work:
  - [docs/specs/L3_5_BODY_OBSERVATION_EXERCISE_WORKFLOW_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L3_5_BODY_OBSERVATION_EXERCISE_WORKFLOW_SPEC.md)
- proactive scheduler, trigger conditions, suppression, or nudge design:
  - [docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md)
- eval / benchmark / suite-governance work:
  - [docs/archive/quality/L5A_EVAL_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/archive/quality/L5A_EVAL_SPEC.md)
  - [docs/archive/quality/L5B_BENCHMARK_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/archive/quality/L5B_BENCHMARK_SPEC.md)
  - [docs/archive/quality/L5D_SUITE_GOVERNANCE_SPEC.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/archive/quality/L5D_SUITE_GOVERNANCE_SPEC.md)
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
