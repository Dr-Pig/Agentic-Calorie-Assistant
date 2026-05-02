# Accurate Intake MVP UX Semantic Cases

## Purpose

This document is the human review record for the Accurate Intake MVP v1.7 UX semantic regression wall.

The machine-readable gate truth is `docs/quality/accurate_intake_mvp_ux_semantic_cases.json`. This Markdown file exists so product semantics, Manager-style ownership, and reviewer intent remain readable during future planning and PR review.

## Scope

```yaml
case_set: accurate_intake_mvp_ux_semantic_cases_v1
gate_group: ux_semantic_manager_decision_consumption
gate_version: "1.7"
claim_scope: local_deterministic_mvp_gate
live_llm_required: false
web_tavily_required: false
schema_migration_required: false
not_claiming:
  - product_ready
  - rollout_ready
  - live_llm_ready
  - web_ready
  - production_db_ready
```

## Ownership Rules

Manager owns:

- user intent
- workflow route / workflow effect
- target attachment proposal
- whether to call evidence tools
- natural-language correction semantics

Deterministic runtime owns:

- schema validation
- target exists / unique / writable validation
- accepted-evidence validation
- unsafe mutation rejection or downgrade
- ledger and read-model truth from canonical state

Food seed / DB owns:

- candidate evidence
- semantic hints
- portion and source provenance

Food seed / DB must not own:

- logged / draft / no-mutation disposition
- workflow route
- final mapping
- mutation legality
- ledger updates

## Forbidden Test Patterns

These cases must not be implemented as deterministic raw-text routers.

- Do not infer user intent from raw text keywords.
- Do not choose workflow route from food names or phrase fragments.
- Do not create missing `workflow_effect` after the Manager pass.
- Do not fabricate `target_attachment`.
- Do not let food seed decide `logged`, `draft`, or `no_mutation`.
- Do not silently rewrite Manager semantic decisions to make a test pass.

## Case Register

| ID | UX Scenario | Expected Runtime Behavior |
|---|---|---|
| UX-001 | tea egg single item logging | Manager emits logging workflow plus evidence tool call; runtime commits accepted estimate and updates same-truth read model. |
| UX-002 | bubble milk tea first turn logged estimate with followup | Manager emits logged estimate plus follow-up posture; runtime logs an estimate and asks for sugar/size without pretending exactness. |
| UX-003 | bubble milk tea second turn refinement | Manager attaches to prior thread/item; runtime creates a new version, supersedes the old active version, and recomputes ledger truth. |
| UX-004 | chicken bento usable estimate with followup | Manager chooses usable estimate with follow-up; runtime does not block as draft only because details are incomplete. |
| UX-005 | bare home-cooked meal drafts and asks | Manager emits draft/clarify workflow; runtime preserves a draft thread and does not mutate ledger. |
| UX-006 | home-cooked meal with listed dishes estimates with portion followup | Manager emits estimation workflow; runtime estimates from accepted evidence and keeps a high-impact portion follow-up. |
| UX-007 | bare luwei drafts and asks | Manager emits draft/ask-items workflow; runtime keeps draft state and no ledger delta. |
| UX-008 | listed luwei estimates with portion followup | Manager emits listed-basket estimation workflow; runtime accepts packetized evidence and logs with a portion follow-up. |
| UX-009 | high-variance basket distinction | Bare basket cases draft; listed basket cases estimate; seed remains evidence support only. |
| UX-010 | exact item card supports logging | Exact local diagnostic seed can support logging; final mapping still owns disposition and no production DB accuracy is claimed. |
| UX-011 | brand item variant ambiguity stays non-exact | Manager may estimate as non-exact and ask size; runtime must not claim exact truth. |
| UX-012 | query-only calories answer does not mutate | Manager emits read-only/query workflow; runtime may answer but must not mutate canonical meal or ledger truth. |
| UX-013 | explicit correction with unique target | Manager proposes target; deterministic guard validates unique writable target before correction mutation. |
| UX-014 | ambiguous correction cannot silently mutate | Manager asks or target is rejected as non-unique; runtime must not silently mutate. |
| UX-015 | no-plan logging keeps budget honesty | Runtime may log consumed kcal; budget answer must not claim remaining kcal or target kcal. |
| UX-016 | active plan same-truth across API and debug | API/debug/read model consumed and remaining values must match canonical state. |
| UX-017 | correction reload excludes superseded versions | Superseded versions must not double-count after persistence reload. |
| UX-018 | context promotion remains support evidence | Context candidates are support evidence only and do not gain mutation authority. |

## Review Notes

- v1.7 verifies deterministic/API/debug consumption of Manager structured decisions.
- v1.8 keeps this UX semantic case register as the machine-truth semantic wall, then adds scoped explicit item removal, read-only debug audit/same-truth surface coverage, and local self-use smoke closure in the MVP gate manifest.
- It intentionally does not run live LLM, Tavily, polished browser UI, full deletion/void/undo lifecycle, or production DB.
- Full delete/void/undo lifecycle remains deferred; v1.8 item removal is only a Manager-structured explicit target removal through existing versioning.
- Live Manager diagnostics should only run after this deterministic semantic wall remains green.
