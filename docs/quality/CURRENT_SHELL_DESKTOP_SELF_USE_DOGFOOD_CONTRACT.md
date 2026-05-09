# Current Shell Desktop Self-Use Dogfood Contract

Status: active contract boundary

Owner: SharedCurrentShell

Consumers:

- ManagerRuntime closeout and trace review
- AppShell desktop local shell and browser evidence
- FoodDB evidence-track contract seeds
- human/operator dogfood review

Scope: desktop local self-use dogfood for Current Shell v1.

This document records the contract boundary for turning the local desktop shell into a useful dogfood loop. It is not a new readiness artifact family, not a new product claim, and not a replacement for the existing closeout chain.

## Direction Boundary

The next implementation work still returns to the existing Current Shell closeout blockers:

- `fixture_full_product_loop_e2e`
- `current_shell_compatibility_local_mvp_candidate_bundle`

This contract exists only to keep those closeout slices aligned with the user's intended desktop dogfood loop: Chat / Today / Body / Feedback / Review Queue, local persistence, trace-backed feedback, and bounded FoodDB macro evidence.

## Desktop Dogfood Scope

In scope for this phase:

- desktop browser usage on the local machine
- local API plus browser-based Current Shell entrypoint
- Chat / Today / Body / Feedback / Review Queue navigation
- date-scoped diary behavior through `local_date`
- local SQLite persistence
- local backup/export of product truth, trace summaries, feedback, and review records
- trace-linked issue capture for UI bugs, Manager behavior, nutrition estimate problems, macro gaps, latency, and product feedback

Out of scope for this phase:

- mobile-grade UX polish
- LIFF or native mobile app behavior
- production DB
- broad FoodDB expansion
- automatic FoodDB promotion from dogfood feedback
- automatic golden-set promotion from raw feedback
- readiness, production, or private self-use approval claims

## Data Classes

Dogfood storage must keep these classes separate.

### Canonical product truth

`canonical product truth` includes meal threads, meal versions, committed items, day budget ledgers, body observations, active body plan state, and canonical read models. This is the source that Chat, Today, and Body must mirror.

### Manager trace

`manager trace` includes request/session IDs, prompt/schema/tool versions, pass 1 decision, requested tools, filtered tool plan, executed tools, compact packets, pass 2 synthesis, guard result, mutation result, renderer input basis, final response basis, latency, token usage, and provider/cache metadata when available.

### UI/session event

`UI/session event` includes page route, selected date, user ID, clicked control, submitted feedback trigger, endpoint, status code, API duration, browser console/network summary, and screenshot or visual QA reference when available. UI/session events are evidence, not product truth.

### Feedback triage record

`feedback triage record` includes user-written feedback, issue category, timestamp, page, selected date, linked trace ID, linked message or meal ID when available, severity, review status, and routing target. `feedback is triage input, not product truth`.

### Golden-set candidate

`golden-set candidate` is a reviewed case derived from feedback or trace evidence. It must name provenance, redaction scope, expected product behavior, trace surface, grader type, and owner approval before it can become a regression or golden-set fixture.

Raw dogfood feedback must not directly create product semantics, benchmark labels, Manager routing rules, FoodDB truth, or prompt hardening.

## Feedback Issue Taxonomy

The first feedback UI should support these categories:

- `manager_behavior`: intent, context, target attachment, follow-up, correction, or response quality problem
- `nutrition_estimate`: kcal, range, uncertainty, source use, or portion estimate problem
- `macro_gap`: missing, hidden, or incorrectly visible protein/carbs/fat
- `fooddb_gap`: missing food, wrong match, wrong serving basis, or source-quality problem
- `ui_ux`: layout, navigation, copy, accessibility, date switching, or desktop workflow friction
- `bug`: API error, persistence error, reload loss, stale state, or crash
- `latency`: turn, API, renderer, or tool latency concern
- `product_feedback`: broader feature or workflow feedback

Feedback capture must attach enough context to reproduce and triage, but it must not inject raw review artifacts into Manager context.

## Observability Contract

Dogfood observability should use stable correlation IDs:

- `session_id`: one desktop dogfood session
- `trace_id`: one user turn or API request
- `span_id`: one LLM pass, tool call, DB read/write, route handler, renderer load, or feedback submit
- `feedback_id`: one feedback item
- `golden_case_id`: one reviewed promoted eval candidate

Trace and event storage may follow OpenTelemetry-style naming and GenAI span concepts where useful, but local storage remains the contract for this phase. Provider-reported cached tokens are optional because not every provider exposes them; cache metrics should record unavailable values explicitly instead of inventing them.

## Feedback To Eval Promotion

Promotion from dogfood feedback to evals is manual and reviewed:

1. Capture feedback with trace/session/UI context.
2. Triage category, severity, and owner.
3. Decide whether it is a bug, UX task, FoodDB gap, product decision, regression candidate, or golden-set candidate.
4. Redact or scope any user-specific content.
5. Define expected user-visible behavior and trace surface.
6. Add a deterministic or human-reviewable regression only after owner approval.

This protects the eval suite from fixture-shape drift and prevents feedback wording from becoming product truth.

## FoodDB Macro Expansion Boundary

The FoodDB macro expansion boundary for this phase is calorie-first, macro-aware, and evidence-gated.

Allowed before full closeout:

- schema and packet contract alignment for `protein_g`, `carbs_g`, `fat_g`, `macro_basis`, `macro_confidence`, `macro_source_strength`, and `macro_visibility_status`
- small exact-item macro-present seed
- small macro-missing seed where macro fields may be null
- optional listed-component seed if needed for `fixture_full_product_loop_e2e`
- review-only FoodDB gap capture from dogfood feedback

Forbidden before full closeout:

- broad FoodDB expansion is out of scope
- FoodDB candidate promotion into runtime truth
- WebSearch snippets as truth
- LLM-invented protein/carbs/fat
- macro display when `show_macro=false`
- automatic data expansion from feedback frequency

FoodDB may provide candidate evidence and approved packet-ready seed evidence. ManagerRuntime remains responsible for synthesis and response honesty; runtime guards and read models remain responsible for mutation legality and shared product truth.

## Activation And Non-Claims

This contract does not change activation stage.

```yaml
non_claims:
  product_readiness_claimed: false
  private_self_use_approved: false
  production_ready: false
  live_llm_ready: false
  fooddb_truth_promoted: false
```

## Return-To-Mainline Gate

The `return-to-mainline gate` is intentionally narrow.

After this contract lands, the next mainline slice must return to the existing closeout chain:

1. wire `fixture_full_product_loop_e2e`
2. wire or generate `current_shell_compatibility_local_mvp_candidate_bundle`
3. only then implement desktop feedback capture, local export, and dogfood review UI

Do not open another planning or readiness-artifact slice unless a concrete contradiction in this contract blocks the closeout path.

## Best-Practice Basis

- OpenAI Agent Evals and Trace Grading: workflow-level quality should be evaluated from traces, not only final answers.
- Anthropic evaluation guidance: define success criteria and empirical task-specific evaluations before prompt changes.
- OpenTelemetry GenAI semantic conventions: model/tool spans, token usage, and trace attributes should be named consistently when available.
- LangSmith observability concepts: traces, runs, threads, feedback, metadata, and datasets should remain distinct surfaces.
