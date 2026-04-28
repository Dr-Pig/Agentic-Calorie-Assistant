# Overnight Autonomy Protocol

## Purpose

This document defines the bounded-autonomy workflow for long-running implementation sessions, especially overnight runs where a human does not want to approve every micro-slice manually.

It exists to preserve three things at the same time:

- continuity with existing repo truth
- explicit use of current best practice and strong external references
- safe stop conditions when product-semantics ambiguity or architecture risk appears

This protocol is operational guidance. It is not a product spec.

## Core Principle

Always align with prior repo truth, but never follow it blindly.

For every important decision:

1. load the current repo truth that already owns the behavior
2. check whether older assumptions still fit the present codebase and product goals
3. check current best practice and strong external references
4. choose the best current judgment explicitly
5. record the boundary and stop conditions before implementation continues

Repo truth is the baseline. Best practice and external references are required inputs for high-impact decisions, not optional decoration.

## Required Workflow

Every important implementation slice must flow through:

1. planner
2. evaluator
3. worker
4. verifier

The human may approve the protocol and phase boundary up front, but the agent must still execute the internal planner/evaluator loop on every non-trivial slice.

## Planner Contract

The Planner owns slice selection and boundary control.

Before proposing a slice, the Planner must:

- load the minimum current repo truth for the task
- identify the current first blocker or next dependency in the active phase
- check current best practice for high-impact topics
- check strong external references when the topic is product-critical, architecture-sensitive, or not fully settled in repo truth

The Planner output must contain:

- why this slice is next
- what existing repo truth it aligns with
- what best-practice or external references shaped the decision
- what is explicitly out of scope
- what conditions should stop further autonomous continuation

The Planner must prefer one narrow slice at a time. It must not bundle together unrelated fixes just because they are nearby.

## Evaluator Contract

The Evaluator is not only a code-reviewer.

The Evaluator's primary responsibility is to judge whether the current slice helps the long-term build and keeps the architecture on the right path.

The Evaluator must focus first on:

- long-term architecture benefit
- ownership boundaries
- dependency inversion direction
- product-truth vs runner-truth separation
- model/provider seam quality
- whether the current slice creates future cleanup debt unnecessarily
- whether the slice overfits a model, a benchmark fixture, or a narrow artifact

The Evaluator may also inspect implementation risk, but technical nitpicks are secondary to architecture trajectory.

The Evaluator should be skeptical, but calibrated.

It must classify concerns as:

- `must_block`
- `approve_condition`
- `cleanup_debt`

Reject only for `must_block`.
Use `approve_with_conditions` when the slice is directionally correct but needs explicit guardrails.
Record reversible, checkpointed, trace-visible local debt as `cleanup_debt` instead of automatically blocking.

The Evaluator must answer:

- does this slice move the system toward the intended long-term architecture?
- is the ownership split correct?
- is the slice prematurely hard-coding product semantics into deterministic layers, provider adapters, or eval vocabulary?
- is the agent trying to solve a product-semantics question with an implementation shortcut?
- is the scope still appropriately narrow?

Allowed Evaluator verdicts:

- `approve`
- `approve_with_conditions`
- `approve_with_narrower_boundary`
- `reject`

If the slice is architecture-negative, even if technically feasible, the Evaluator should reject it.

## Worker Contract

The Worker implements only the approved slice.

Hard rules:

- do not expand scope silently
- do not "fix one more thing" in the same round
- do not rewrite product semantics because a model or tool is inconvenient
- do not convert a temporary workaround into product truth

If the Worker discovers a new blocker outside the approved boundary, it must surface that blocker instead of silently pivoting.

## Verifier Contract

The Verifier owns evidence, not optimism.

The Verifier must:

- run the targeted tests or checks defined by the slice
- run the required smoke/readiness gates when the slice touches active phase truth
- report what changed in artifacts, traces, or readiness state
- verify evaluator conditions were actually satisfied
- classify the outcome clearly

Allowed result classes:

- `fixed`
- `narrower_blocker_exposed`
- `semantic_ambiguity_reached`
- `verification_incomplete`

The Verifier must not treat "different failure" as success unless the slice objective was to move the blocker deeper and that movement actually happened.

## External Reference Policy

For important work, external references are mandatory.

This applies especially to:

- agent runtime
- tool orchestration
- retrieval and evidence pipelines
- database and schema design
- testing strategy
- security-sensitive behavior
- user-facing correction or follow-up patterns

Preferred source order:

1. official documentation
2. strong primary-source framework docs
3. strong product references
4. high-quality open-source implementations

The agent must not rely on blogs or commentary when primary sources are available.

External references inform decisions. They do not override product semantics or canonical repo truth automatically.

## Best-Practice Check Requirement

For every high-impact slice, the Planner and Evaluator must explicitly confirm:

- which best-practice references were checked
- which parts were adopted
- which parts were intentionally not adopted and why

This is especially important when repo habits and current best practice diverge.

## Continuation Rules

Autonomous multi-slice continuation is allowed only when all of the following are true:

- the phase boundary is already approved
- the next slice is a direct continuation from the latest verified blocker
- no new product-semantics decision is required
- no new global architecture commitment is required
- the Evaluator still approves the direction

Mini-slices remain the preferred unit of work. The point of this protocol is not to eliminate slices; it is to eliminate unnecessary human approval between safe slices.

## Execution Surfaces

Overnight autonomy should not assume one surface can do everything safely.

Preferred split:

- `desktop control plane`
  - owns human setup
  - owns next-morning inspection
  - may still host planner-local or evaluator-local work when a detached pilot is not yet ready
- `CLI planner`
  - owns detached next-slice selection for approved pilot loops
- `CLI evaluator`
  - owns detached architecture and product-journey review for approved pilot loops
- `CLI worker`
  - owns bounded implementation slices
  - should receive explicit scope and prompt files
- `CLI verifier`
  - owns bounded verification passes and checkpoint closeout

Detached roles are bounded runtime actors. They do not replace canonical repo truth or human product authority.

## Planner-Local vs CLI-Worker

Default mode remains `planner-local`.

Use `planner-local` when:

- the slice is architecture-heavy
- the slice is semantics-heavy
- the slice is docs-only or governance-only
- the scope is still converging
- the very next action depends immediately on the previous result

Use a bounded CLI worker when most are true:

- the slice is already formalized
- touched files are explicit enough to name
- the work is mainly implementation or mechanical follow-through
- isolating noisy execution would protect planner quality
- the worker can return a standard artifact-backed result

Do not open workers by reflex. Use them when context isolation is genuinely valuable.

## Sub-Agent Policy

Inside a live interactive session, sub-agents may still be useful for bounded sidecar tasks such as:

- implementation on a narrow write scope
- spec review
- code quality review

For overnight continuation, prefer a role split that mirrors the same idea operationally:

- planner
- evaluator
- worker
- verifier

The important rule is role separation, not whether the role runs through an in-thread sub-agent or a detached CLI process.

Do not promote autonomous nutrition subagents into product runtime just because detached implementation workers are convenient.

## CLI Runner Pattern

This repo contains a bounded Codex CLI wrapper:

- [scripts/run_codex_exec_with_prompt.py](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/scripts/run_codex_exec_with_prompt.py)

Current confirmed shape:

- accepts `--prompt-file`
- accepts `--cd`
- accepts `--mode planner|evaluator|worker|verifier`
- resolves a local `codex` binary
- executes `codex exec` with workspace-write sandbox

Recommended overnight use:

1. control plane writes or refreshes prompt files
2. CLI planner selects the next slice
3. CLI evaluator approves, narrows, or rejects it
4. CLI worker runs a bounded implementation slice
5. CLI verifier closes the slice with evidence and checkpoint data
6. control plane inspects whether the next slice is still safe

This is intentionally not a free-running infinite loop. It is a bounded continuation loop with explicit checkpoints.

## Prompt File Discipline

Detached CLI work should always run from explicit prompt files rather than raw ad hoc shell strings.

Each prompt file should contain:

- role
- current slice id
- in-scope files
- forbidden changes
- required tests
- expected output format
- stop conditions

This keeps detached runs inspectable and resumable.

## Detached Work Ledger

Overnight work should maintain a simple task ledger outside the chat stream.

Minimum recommended fields:

```yaml
task_id: string
role: planner | evaluator | worker | verifier
status: queued | running | completed | failed | blocked
input_prompt_file: string
output_artifact: string | null
started_at_utc: string | null
ended_at_utc: string | null
next_action: string | null
```

Tasks are the ledger for detached work. They are not the scheduler itself.

## Checkpoint Package

Every completed bounded slice must end with a checkpoint package.

Preferred form:

- one intentional git commit per completed slice

Fallback form when a commit is intentionally deferred:

- diff snapshot
- status snapshot
- checkpoint markdown artifact

Minimum checkpoint fields:

```yaml
checkpoint_id: string
phase: string
task_id: string
git_base_sha: string | null
git_head_sha: string | null
files_changed:
  - path
tests_run:
  - command: string
    result: pass | fail | not_run
artifacts:
  - path
decision_log:
  - repo_truth_used: string
    external_references_used:
      - string
    adopted_guidance: string
    rejected_guidance: string | null
rollback_plan:
  - step: string
revert_unit:
  type: commit | diff_snapshot | docs_only
  safe_revert_command: string | null
  affected_runtime_behavior: true | false
next_safe_action: continue | stop | human_review
stop_conditions_checked:
  - string
architecture_debt_delta:
  - string
human_review_required: true | false
architecture_boundary_touched:
  - product_contract
  - runtime_contract
  - provider_profile
  - retrieval_policy
  - eval_only
```

Checkpoint packages exist so the next morning a human can answer:

- what changed
- why it changed
- what was verified
- how to revert it
- whether it was still safe to continue
- whether the slice was docs-only or changed runtime behavior

Do not bundle unrelated changes into one checkpoint package.

## Rollback And Safe Revert Expectation

Each checkpoint must include explicit rollback instructions.

Preferred rollback surface:

- revert the single slice commit

Fallback rollback surface:

- apply reverse diff manually
- restore named files only

Rollback instructions must not rely on destructive cleanup commands.

If untracked or unrelated local work is present, the checkpoint must say so explicitly before recommending any revert action.

## Human-Review Flags

The agent must mark `human_review_required = true` for any slice that touches:

- product semantics
- source priority policy
- DB schema ownership
- mutation policy
- model or provider policy beyond already-documented local routing use
- runtime-wide parser or schema behavior
- architecture boundary migration that changes long-term ownership

When `human_review_required = true`, the next safe action must default to `human_review` unless the user has already pre-approved that exact transition class.

## Recovery And Resume

Detached work must be resumable without trusting chat memory alone.

Recovery should restore from:

- canonical docs
- current task ledger
- latest prompt files
- latest verification artifacts
- git diff

The agent should not rely on transcript archaeology to determine where overnight work stopped.

## Budget And Loop Guard

Overnight autonomy must stay budget-aware.

Minimum guardrails:

- max implementation slices per unattended run
- max verification retries per slice
- stop on repeated non-progress
- stop on unresolved semantics
- stop when verification becomes ambiguous

Cost and token guardrails should act before runaway looping, not after the fact.

## Stop Gates

Autonomous continuation must stop when any of the following appears:

- unresolved product-semantics decision
- unresolved source-priority policy
- unresolved evidence-threshold policy
- unresolved mutation-policy change
- unresolved database schema ownership question
- unresolved provider/model policy decision
- need for a global parser/schema/runtime rewrite
- architecture-negative drift identified by the Evaluator

When a stop gate triggers, the agent should produce:

- current truth summary
- blocking decision
- recommended options
- no further implementation beyond the safe boundary

## Current Repo-Specific Guardrail

Until Wave 1 Phase B-2 product-intelligence contracts are explicitly approved for live runtime implementation:

- docs, contract drafts, and synthetic tests are allowed
- live DB runtime, live search runtime, and production evidence mutation behavior are not allowed by default during autonomous continuation

This prevents the agent from silently turning a planning phase into a product-semantics implementation phase.

## Reporting Shape

At the end of a slice, the agent should report:

- what repo truth it aligned with
- what external references influenced the slice
- what the Evaluator concluded
- what the Verifier proved
- whether the next slice is still safe for autonomy

## Reference Starter Set

The following families are the default best-practice baselines for this repo's current autonomy and retrieval work:

- OpenAI reasoning best practices
- OpenAI retrieval and query rewriting guidance
- OpenAI web search guidance
- LangGraph graph/state separation guidance
- Anthropic tool-use definition guidance

These references must still be re-checked when the decision is high-impact or the official guidance may have changed.
