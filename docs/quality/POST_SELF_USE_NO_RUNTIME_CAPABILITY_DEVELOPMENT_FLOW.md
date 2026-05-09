# Post-Self-Use No-Runtime Capability Development Flow

Status: Active development flow

Owner: Product/runtime architecture

Consumer: coding agents building post-self-use capability scaffolds before runtime attachment

Scope: post-self-use capability work that may be calibrated offline, by fixtures, shadow artifacts, or read-only runtime observations, without connecting to live runtime effects

Retirement trigger: retire or replace this flow per capability domain when that domain receives an explicit runtime activation plan, gate-ledger entry, rollback path, and human promotion decision

## Purpose

This document formalizes how to build post-self-use capability scaffolds without connecting them to runtime.

The goal is to let us calibrate behavior early while preventing future-wave work from silently changing the Current Shell self-use mainline, manager context, mutation path, scheduler, provider calls, UI truth, or durable memory.

No-runtime work may observe runtime behavior as evidence. It must not become runtime behavior.

## Direction And Dependency Classification

```yaml
direction_challenge_subagent: skipped
direction_challenge_skip_reason: root planning task only; no subagent requested
current_mainline: Current Shell local self-use foundation
is_detour: true
blocked_mainline: not_applicable
detour_reason: user requested a formal post-self-use no-runtime development flow
detour_exit_gate: document added and indexed without changing Current Shell runtime gates
exit_gate_status: this document is process guidance, not activation evidence
return_slice_after_exit: Current Shell self-use closure remains the default mainline
strategic_verdict: allowed_detour
```

Capability-order classification:

```yaml
capability_order_trap: yes
architecture_boundary_trap: yes
risk: later-wave L9 behavior can appear locally useful before L1-L8 contracts are stable
rule: downstream diagnostic-only work may proceed; downstream user-facing behavior, runtime truth, or mutation must wait for required upstream contracts
```

## Global Guardrails

These guardrails apply to every capability domain in this document.

Allowed now:

- offline fixtures, deterministic case matrices, shadow evaluators, no-send simulations, review packs, and read-only case banks
- trace-derived cases copied from runtime output when they are anonymized or scoped to self-use evidence
- deterministic validators that reject, downgrade, suppress, or request bounded repair
- LLM-shaped fake outputs when the harness is explicitly diagnostic and does not infer product semantics by keyword
- documentation of competing interpretations, ambiguity clusters, and unresolved decisions

Forbidden now:

- scheduler activation, push delivery, LINE delivery, notification dispatch, or app-open recommendation serving
- live provider calls, live search, live Places lookup, live LLM routing, or automatic tool execution
- mutation of meal ledger, body plan, budget ledger, proposal state, durable memory, preference memory, or proactive trigger records
- injection into `ManagerContextPacket`, manager turn context, runtime tool surfaces, route handlers, or production UI routes
- UI computation of canonical food, budget, proposal legality, memory truth, or proactive eligibility
- readiness claims such as production-ready, live-ready, user-facing-ready, or activation-approved

Every no-runtime artifact must state:

```yaml
owner:
consumer:
capability_domain:
slice_mode:
  - diagnostic_only
runtime_connected: false
user_facing_behavior_changed: false
runtime_truth_changed: false
mutation_changed: false
side_effects_allowed: false
retirement_trigger:
non_claims:
  - not runtime activation evidence
  - not product readiness evidence
```

## Standard Development Flow

1. Classify the slice.

   State the capability pyramid layer, upstream dependencies, semantic owner, deterministic owner, and why the work is safe before runtime attachment.

2. Choose the smallest existing artifact surface.

   Extend an existing domain test, builder, matrix, or review pack first. Create a new artifact only when the existing family cannot represent the capability, and only with owner, consumer, and retirement trigger.

3. Define the no-runtime behavior contract.

   The contract must say what the artifact can classify, suppress, score, or explain. It must also say what it cannot write, send, recommend, or mutate.

4. Add offline cases before changing logic.

   Cases should come from canonical specs, self-use traces, manual review notes, or deliberately constructed ambiguity sets. A fixture must not become product truth by itself.

5. Implement bounded calibration only.

   Prefer typed policies, gates, or review artifacts over new services. Avoid background workers, queues, adapters, route handlers, or database models unless the domain has an approved activation plan.

6. Verify side-effect absence.

   Tests must assert that runtime connection flags and effect flags remain false, especially for proactive, recommendation, proposal, memory, and mutation-bearing domains.

7. Write a narrow handoff note.

   Completion evidence should list changed files, tests run, non-claims, remaining ambiguity, and the runtime gate that would be required before activation.

## Capability Domain Goals

| Capability domain | Goal | Can build now without runtime | Guardrail | Exit evidence |
|---|---|---|---|---|
| Runtime-observed case bank | Use real self-use/runtime traces to improve offline calibration | read-only trace summaries, anonymized case rows, ambiguity clusters, replay seeds | must not alter live runtime, inject context, or auto-create pass/fail semantics | case source, redaction scope, reviewed ambiguity labels |
| Short-term contextual intent | Calibrate how current-turn context changes interpretation | contextual interaction matrices, conditioned intent walls, attachment and transition fixtures | deterministic code must not invent user intent, workflow effect, route target, or final action | cases prove attach, detach, ask, correction, and future-intent boundaries |
| Pending meal and future intent | Separate actual intake, future plan, candidate proposal, and temporary context | fixture cases for "later", "maybe", planned meal, skipped meal, and replacement language | future intent must not become ledger mutation or proposal state | expected state category and no-mutation assertions |
| Rescue and proposal negotiation | Calibrate when to invite rescue and how acceptance must be gated | rescue read-model shadow, proposal invitation cases, acceptance/reject/dismiss fixtures | no proposal creation, no rescue mutation, no plan rewrite, no budget correction | invitation boundary cases plus explicit non-commit outcomes |
| Body observation, exercise, and effective budget | Calibrate body/exercise input contracts and effective-budget previews | contract fixtures, read-model preview math, manual review examples | no body plan mutation, no exercise bonus ledger write, no budget source-of-truth change | preview-only evidence and mutation-denied assertions |
| Calibration proposal | Calibrate when weight or trend evidence should suggest a stored action | proposal candidate scoring fixtures, inbox/read-model examples, stored-action boundary tests | no stored action creation, no calibration mutation, no UI acceptance path | candidate quality labels and no-write proof |
| Recommendation quality | Calibrate candidate quality, fallback behavior, and silence thresholds | prepared-candidate quality gates, 1-primary-plus-backup simulations, offer-vs-silent shadow | no live search, no Places lookup, no runtime ranking LLM, no served recommendation | high/medium/low examples and suppression proof |
| Memory and preference shadow | Calibrate typed preference, pattern, suppression, and forget behavior | local shadow artifacts, typed memory case reviews, conflict cases | no durable memory write, no cross-session personalization, no hidden preference truth | read-only memory candidate pack and conflict handling |
| Proactive no-send scheduler | Calibrate deterministic brakes and LLM-shaped dispatch decisions without sending | no-send simulations, trigger-family fixtures, copy-safety review packs | no scheduler, no push, no LINE send, no manager context injection, no proactive trigger persistence | all effect flags false and review decision taxonomy |
| Multimodal and voice input | Calibrate contracts for photo, OCR, barcode, and voice-derived meal evidence | fixture payloads, ambiguity handoff cases, confidence downgrade policies | no media adapter, no transcription provider, no automatic food truth or commit | handoff contract and ask-first cases |
| Cross-surface same-truth UI | Calibrate how later-wave facts would be mirrored in UI | read-model contract examples, proposal inbox fixture states, smart-chip display cases | UI must not rank, rewrite, mutate, compute budget, or become primary truth owner | renderer-only assertions and canonical-owner mapping |

## Domain-Specific Build Rules

### Runtime-Observed Case Bank

Purpose: learn from Current Shell behavior without changing it.

Allowed sources:

- completed self-use traces
- manager result artifacts
- browser-shell observations
- manual operator notes
- anonymized transcript snippets when needed for ambiguity review

Rules:

- case rows may record what happened, what was ambiguous, and what a reviewer expected
- case rows must not declare new product semantics unless the owning spec already supports them
- trace-derived examples must be replay-only until a domain owner promotes them into a canonical fixture

### Contextual Intent And Attachment

Purpose: protect the boundary between current-turn interpretation and workflow mutation.

Build order:

1. current-turn context categories
2. attachment and detachment conditions
3. transition guard outcomes
4. response-mode hints only after workflow effect is owned

Forbidden shortcuts:

- keyword-only classification
- deterministic rewrite of completed LLM semantic fields
- response-style labels promoted into routing taxonomy
- using old benchmark oracle vocabulary as current product truth

### Rescue, Calibration, Recommendation, And Proactive

These domains may share evidence, but they must not share hidden mutation authority.

Boundary rule:

```yaml
rescue:
  may: detect need, invite, explain, prepare no-commit proposal shape
  must_not: rewrite day plan or mutate proposal
calibration:
  may: score candidate, explain confidence, prepare inbox example
  must_not: create stored action or change body plan
recommendation:
  may: score prepared candidates, choose offer_vs_silent in shadow
  must_not: search live, serve, rank through runtime, or write preference
proactive:
  may: simulate trigger eligibility and no-send dispatch
  must_not: schedule, send, persist trigger, or inject manager context
```

### Memory And Preference

Purpose: design what could become memory without accidentally making memory.

Allowed memory artifacts are candidates only:

- explicit user-stated preference candidates
- repeated behavior pattern candidates
- suppression candidates
- conflict and expiration cases

Forbidden memory artifacts:

- durable writes
- hidden global defaults
- unreviewed cross-session personalization
- background promotion from trace frequency alone

### Multimodal, Voice, And Cross-Surface UI

Purpose: make future input and display surfaces contract-ready without changing truth ownership.

Rules:

- multimodal and voice artifacts may produce evidence candidates, uncertainty, and ask-first triggers
- they must not produce committed meal facts without the normal meal-thread and commit boundary
- UI artifacts may mirror canonical read models and pending commands
- UI artifacts must not compute canonical facts or become the primary interaction owner

## Promotion Boundary

No capability in this flow may be connected to runtime merely because offline tests pass.

Runtime attachment requires a separate activation decision with:

- owner and runtime gate ID
- upstream dependency status through the capability pyramid
- typed manager/runtime contract
- side-effect inventory
- rollback or disable path
- canary or shadow comparison plan
- targeted tests and trace review
- human promotion decision

The promotion artifact must explicitly say which no-runtime artifact is being retired, narrowed, or kept as diagnostic-only support.

## Anti-Over-Engineering Guardrail

Before adding any new file, builder, runner, or review pack, answer:

```yaml
does_an_existing_artifact_cover_this_domain:
why_existing_artifact_is_insufficient:
new_artifact_owner:
new_artifact_consumer:
retirement_trigger:
which_blocked_capability_it_unlocks:
what_old_artifact_it_replaces:
why_this_is_not_a_harness_layer_added_instead_of_capability_closure:
```

If those fields cannot be answered, do not add the artifact.

Prefer:

- one new case in an existing suite over a new suite
- one explicit field in an existing artifact over a new artifact family
- one domain-specific policy object over a generic orchestration framework
- read-only fixtures over background jobs
- local review packs over activation claims

## Required Completion Note

Every no-runtime slice should close with:

```yaml
capability_domain:
capability_layer:
slice_mode:
  - diagnostic_only
runtime_connected: false
files_changed:
tests_run:
side_effect_assertions:
non_claims:
remaining_ambiguity:
next_runtime_gate_required:
promotion_status: not_requested
```

This completion note is evidence of bounded calibration only. It is not approval to activate the capability.
