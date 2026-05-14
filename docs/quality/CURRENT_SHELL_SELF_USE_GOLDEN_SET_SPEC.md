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
- No fallback 400 can become canonical product truth.
- Macro facts are evidence-gated. Missing macro remains hidden, unknown, or partial.
- ReAct trace layers must include pass1, tool plan, executed tools, compact packets, pass2, guard, mutation result, renderer basis, and final response basis.
- Ask-followup and answer-only actions do not commit intake.
- Versioned meal corrections/removals must update the ledger from active included items only.
- Response text must be natural zh-TW assistant language and must match state.
- Chat, Today, Body, Feedback, and Review consume backend/read-model truth only.
- Pending and queued messages must survive navigation.
- Dogfood traces must record timing, call topology, state changes, final visible response, and feedback linkage.

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
