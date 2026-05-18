# Current Shell Self-Use Golden Set

Status: active eval contract

Owner: SharedCurrentShell

Consumers:

- ManagerRuntime live and offline trace gates
- AppShell browser and same-truth gates
- FoodDB packet-ready handoff checks
- human/operator dogfood review

This document defines the Current Shell v1 desktop local self-use Golden Set. It is not a readiness claim, not a production activation, and not a replacement for ManagerRuntime, AppShell, or FoodDB ownership. It exists to stop fake pass by making every claimed self-use behavior traceable from the real entrypoint through Manager decisions, tools, guards, mutation, read models, UI, response text, latency, and feedback.

The machine-readable contract is [current_shell_self_use_golden_set_manifest.yaml](current_shell_self_use_golden_set_manifest.yaml).

## Product Truth

The product truth is the user-visible desktop self-use behavior: a person can record calories in Chat, inspect Today and Body, submit feedback in context, and later use Review to turn real failures into regression candidates. Eval assets validate that behavior; they do not design runtime semantics.

No fake pass is allowed. Fixtures may seed body plans, meal history, FoodDB packets, pending questions, and browser state. Fixtures must not decide intent, action, attach target, mutation outcome, or response meaning. The actual owner must run through the real runtime or a correlated browser trace.

## Global Invariants

These invariants apply to every Golden Set case.

- Manager owns semantic intent, tool choice, correction/removal target, attach decision, and final action.
- Deterministic code may validate, reject, downgrade, derive, or request bounded repair. It must not silently rewrite Manager semantics.
- Context packets must provide the current turn, session summary, pending question, recent meal threads, target candidates, and read-model summaries where relevant. Context chooses no final intent or target.
- Nutrition truth must come from user facts, FoodDB/evidence packets, approved synthesis, or canonical read models.
- Active runtime must not produce fallback/shadow 400 nutrition packets. Missing approved evidence produces an evidence-unavailable packet with no kcal or macro facts, then Manager decides the next user-facing action.
- Macro facts are evidence-gated. Missing macro remains hidden, unknown, or partial.
- ReAct trace layers must include pass1, tool plan, executed tools, compact packets, pass2, guard, mutation result, renderer basis, and final response basis.
- Ask-followup and answer-only actions do not commit intake.
- Versioned meal corrections/removals must update the ledger from active included items only.
- Response text must be natural zh-TW assistant language and must match state.
- Chat, Today, Body, Feedback, and Review consume backend/read-model truth only.
- Pending and queued messages must survive navigation.
- Dogfood traces must record timing, call topology, state changes, final visible response, and feedback linkage.
- Exact-utterance-only passes, keyword shortcuts, and fixture-shaped semantic shortcuts are blockers. A case pass must represent the failure family behind the case, not only the literal text in the manifest.

## Manager Semantic Ownership Boundary

Composition sufficiency, estimability, and follow-up necessity are Manager semantic decisions. The Manager LLM owns whether the user's food description is clear enough to estimate, whether the turn should ask a composition question, whether an item is an exact/generic/component/basket/patterned-combo case, how assumptions should be stated, and whether the final action is commit, answer-only, correction, removal, or ask-followup.

Deterministic runtime may validate a Manager-proposed action or evidence object after the Manager has produced it. It may reject an illegal commit, hide disallowed evidence fields, downgrade visibility, block mutation, or request one bounded repair round when evidence eligibility or mutation legality fails.

LLM / Manager owns:

- composition sufficiency
- estimability
- whether to ask follow-up
- whether to call WebSearch
- exact/generic/component/basket posture
- attach target
- correction/removal target
- final workflow action
- user-facing response meaning

Deterministic code may only:

- validate schema
- validate source eligibility
- validate target existence / uniqueness
- enforce mutation legality
- hide unsupported kcal/macro/source facts
- reject/downgrade unsafe output
- request one bounded repair

Deterministic code must not:

- inspect raw user text or food name to decide semantic route
- classify a meal as unestimable before Manager output exists
- decide follow-up necessity
- decide WebSearch need
- create fallback kcal/macros
- rewrite Manager action to make a test pass

In short: deterministic code must not inspect raw user text, food name, case ID, or fixture label to decide semantic product behavior.

The active estimate tool must not fall back to a shadow/stub nutrition estimate. A missing exact, FoodDB, component, or approved web evidence packet is represented as `evidence_unavailable` with `estimated_kcal=0`, macro hidden, and `can_write_canonical=false`. The Manager may use that packet to ask a question or explain missing evidence, but deterministic code cannot turn the missing evidence into a default 400 kcal estimate.

Golden Set replay must also prove that nutrition retrieval was requested from a Manager-owned evidence target. A targetless `estimate_nutrition` call is not a valid path, even if the literal user text names a food. The Manager must provide a usable target shape such as `base_dish`, aliases, exact brand/size identity, or multiple `listed_items`; raw user text must not be the retrieval query and must not select exact/generic/listed posture by itself.

Deterministic runtime must not inspect raw user text, food names, case IDs, fixture labels, keyword lists, or food-family heuristics before the Manager pass to decide:

- the food is not estimable
- composition is unknown
- the system should ask a follow-up
- a specific follow-up wording
- a food posture such as exact, generic, component, basket, or patterned combo
- a correction/removal target
- a final action or workflow effect

This boundary follows the trace-level eval practice of grading the actual agent decision path, not only the final answer, and the context-engineering rule that deterministic context supplies candidates and evidence while the Manager decides semantics. A Golden Set pass must prove that any ask-followup, no-commit, estimate, correction, or removal decision came from the Manager output or from a bounded post-Manager guard repair, not from a pre-Manager deterministic shortcut.

## Golden Set Matrix

The v1 Golden Set has nineteen cases:

- GS1 clear component meal
- GS2 user-provided kcal-only entry
- GS3 implausible named food kcal
- GS4 generic common food
- GS5 patterned breakfast teppan combo without approved anchor
- GS6 bare self-selected basket
- GS7 listed basket follow-up
- GS8 optional drink refinement
- GS9 estimate-basis inquiry
- GS10 teppan combo follow-up
- GS11 correction with supersede
- GS12 removal
- GS13 ambiguous target clarification
- GS14 remaining budget query
- GS15 no-plan degraded query
- GS16 body observation and persistent BodyPlan UI
- GS17 inline feedback with automatic context
- GS18 long teppan session
- GS19 correlated browser UI E2E

Cases are defined in the manifest so runners can consume the same truth that humans review. The manifest is intentionally explicit about expected runtime effect, UI assertions, response rubric, latency budget, and dogfood trace requirements.

Each case is also a representative of a broader failure family. Passing the literal input text is not enough when trace evidence shows keyword routing, fixture-owned semantics, or case-specific prompt patching.

### GS9 Basis-Inquiry Rule

GS9 is an estimate-basis inquiry, not a correction or re-estimation request. The expected answer must be grounded in stored runtime basis:

- active meal/version estimate basis
- evidence packet summary
- selected or rejected candidates
- prior tool result compact packet
- mutation/read-model state
- final response basis trace

Manager action should be `estimate_basis_inquiry` or an equivalent answer-only path. Mutation is forbidden. A tool call is normally unnecessary; it is allowed only when the stored basis is missing and a read/review tool is needed. The response must explain the basis in zh-TW, without correction, re-estimate, or new commit unless the user explicitly asks for it.

## Holdout Browser Variants

Core GS1-GS19 pass is necessary but not sufficient for self-use closeout. The manifest also defines a small holdout extension that must run through the same browser entrypoint before closeout. Holdouts use different natural wording for the same product capabilities instead of new semantics:

- clear component logging
- generic common-food estimation with uncertainty basis
- patterned combo clarification without pre-Manager estimability shortcuts
- estimate-basis inquiry with no mutation
- correction with version/ledger recompute
- remaining-budget read-only query

Holdout cases are not allowed to change product truth, fixture ownership, or Manager boundaries. They are an anti-overfit check: if a holdout fails, the fix must target the underlying capability family and trace owner, not the literal wording.

## WebSearch Stage 2 Addendum

WebSearch is not part of the core GS1-GS19 closeout gate. The current WebSearch extension rows are draft alignment seeds only until they are recalibrated against `Whole Product Stage 2 Food Evidence And Reusable Meal Calibration Draft` and implemented through the real Manager/WebSearch path.

Manager decides whether a turn needs external search. Deterministic code must not route to WebSearch from raw user text, brand keywords, food names, case IDs, or fixture labels before the Manager pass. It may validate the Manager-requested search plan, execute an allowed retrieval adapter, filter source eligibility, and reject or downgrade candidate packets after the tool returns.

`SearchCandidatePacket` is candidate evidence only. A selected extract plus deterministic admissibility may produce a same-turn `TurnWebEvidencePacket`; that packet may support Manager synthesis and normal mutation guards for that turn, but it is still not permanent FoodDB truth. Raw snippets, search result titles, and extracted page text are not canonical nutrition truth.

Wrong-brand or near-match WebSearch candidates must not be promoted. They are mismatch evidence for clarification, refusal to commit, or review-only candidate capture.

Before WebSearch is reactivated as a blocking Golden Set extension, it must cover the Stage 2 evidence families:

- an exact FoodDB hit where Manager should not search
- an exact-item FoodDB miss where Manager chooses WebSearch and admissible selected extract can become turn-scoped evidence
- a web composition case where composition can support estimate or follow-up without fake exact kcal
- a wrong-context, wrong-brand, sibling, frozen, ecommerce, or weak-source result that must be rejected or downgraded
- a branded multi-item combo that uses component-level evidence rather than a generic combo black box
- a wrong-brand or near-match case where candidates must not be promoted
- a generic/common food where Manager should prefer FoodDB/generic anchors and should not search the web by default
- an exact macro item where protein, carbs, and fat are visible only from official or approved evidence

Every WebSearch extension pass must prove the real Manager decision path, requested search/evidence tools, compact packets, final response basis, no raw candidate-as-truth, no snippet-as-truth, and no frontend nutrition math. A sidecar WebSearch packet or status gate is insufficient by itself; the extension must validate the user-visible Current Shell path. Until this recalibration lands, GS1-GS19 plus holdout browser variants define the Current Shell core closeout scope.

## Response Quality

Path correctness is not judged by another model. Trace, read model, mutation result, and UI state decide path correctness.

LLM-as-judge may be used only for scoped content and naturalness:

- explanation completeness
- understandable zh-TW
- natural uncertainty wording
- clear follow-up question
- assistant-like tone

The judge must not decide mutation legality, target attachment, kcal truth, macro truth, FoodDB evidence sufficiency, or UI/read-model sync.

## UI And Dogfood Requirements

Chat must support queued-next pending messages. A user can send another message while a run is processing; the queued message remains visible, survives navigation, and runs as the next Manager turn. Current Shell v1 does not require interrupt-and-replan cancellation.

Today must show meal-level and day-level macro when backend evidence allows it. Partial day macro totals must show a partial warning. The frontend must not infer nutrition facts from text.

BodyPlan remains a persistent profile and goal surface. Body fields should be prefilled from saved active truth. Weight check-ins are dated observations; BodyPlan itself is not a daily form.

Feedback is captured through inline entry points on Chat, Today, and Body. The user should never fill trace IDs or request IDs. Review is builder-facing and should show structured trace, feedback, replay, triage, and regression-promotion material.

Structured trace is the primary review surface. Raw provider and tool payloads may be stored as local deep-debug references, not as the default Review display. Export is optional backup/tooling, not the daily access path.

## FoodDB And Model Boundary

Patterned combo anchors are posture-driven. If no approved anchor exists, the runtime asks a composition follow-up and does not commit. If an anchor exists but is high-variance or low-confidence, the runtime may draft or ask confirmation. Only anchors with an approved estimable posture may estimate and commit with disclosed assumptions.

FoodDB packet-ready records must expose runtime posture, composition posture, commit posture, macro visibility, and source strength. WebSearch snippets are candidate evidence only. LLMs must not invent protein, carbs, fat, kcal, source exactness, or packet approval.

Grokfast is the primary self-use live gate. Kimi remains a non-blocking cross-model diagnostic until a separate model-profile validation promotes it.

## Non-Claims

```yaml
product_readiness_claimed: false
private_self_use_approved: false
whole_product_mvp_ready: false
production_ready: false
fooddb_truth_promoted: false
```
