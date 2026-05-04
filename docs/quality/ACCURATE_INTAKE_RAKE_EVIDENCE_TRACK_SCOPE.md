# Accurate Intake RAKE Evidence Track Scope

This document is repo truth for the RAKE Intake Evidence Track. It narrows the FoodDB/WebSearch workstream to the evidence side of the main intake flow: FoodDB retrieval/ranking, tool-calling evidence seam, compact evidence packets, and WebSearch candidate evidence. It does not approve Webshell work, Product Loop work, Context Engineering schema work, readiness, production DB work, or user-facing activation.

## Strategic Classification

```yaml
current_mainline: Calorie Deficit Logging MVP local self-use foundation
is_detour: false
mainline_blocker_being_removed:
  - intake_evidence_recall_quality
  - tool_calling_evidence_packet_seam
  - fooddb_websearch_candidate_boundary
strategic_verdict: mainline
capability_layer: L4-L6 retrieval_intent_to_evidence_packet_to_nutrition_synthesis_seam
upstream_dependencies:
  - layer: L1-L3 intake state and commit boundary
    contract_status: contract_backed
    risk_if_missing: evidence retrieval could become hidden mutation or transcript routing
  - layer: L4 retrieval/source selection policy
    contract_status: contract_backed
    risk_if_missing: keyword, fuzzy, and web search lanes collapse into one truth path
  - layer: L5 evidence packet layer
    contract_status: tested
    risk_if_missing: raw candidates or source rows could leak into Manager synthesis
slice_mode:
  - diagnostic_only
  - offline_runtime
  - producer_honesty
user_facing_behavior_changed: false
runtime_truth_changed: false
mutation_changed: false
safe_to_proceed_now: true
why_not_local_next_step_trap: local FoodDB packets and GrokFast packet smoke already exist; this slice locks the evidence-track boundary before broadening retrieval or WebSearch
```

## Ownership Boundary

The RAKE Intake Evidence Track owns:

- FoodDB retrieval/ranking over adapter-supplied indexed evidence records.
- Tool-search evidence for the intake `estimate_nutrition` read-tool path.
- Evidence packet construction for FoodDB, listed-basket components, and WebSearch candidates.
- Diagnostic GrokFast seam smoke after deterministic packet closure.
- WebSearch candidate evidence, with snippets and extracted pages remaining candidate-only until an approved promotion path exists.

The RAKE Intake Evidence Track explicitly does not own Webshell, does not own Product Loop, does not own ManagerContextPacket, and has no runtime mutation authority. It must not change frontend rendering, Product Loop handoff behavior, Context Engineering packet shape, ledger mutation legality, or user-facing readiness claims.

## Best-Practice Basis

- SQLite FTS5 and PostgreSQL `pg_trgm` support lexical retrieval over exact tokens, aliases, and typos; this track uses keyword/fuzzy lexical retrieval before any semantic recall.
- Supabase full-text and hybrid search can later implement the same indexed-record contract; the Manager must not depend on local JSON, SQLite, or Supabase implementation details.
- FAO/INFOODS and USDA FoodData Central guidance require source provenance, source class, units, denominators, and food matching quality to be preserved.
- Open Food Facts is open and user-contributed; it may feed candidate evidence, not runtime truth by default.
- OpenAI agent eval and trace-grading guidance requires tool calls, tool outputs, guardrails, and failure location to remain trace-visible.

## LLM / Deterministic Boundary

```yaml
decision_surface: intake evidence retrieval and packet use
truth_owner: hybrid
deterministic_role:
  - normalize terms, aliases, typos, modifiers, and basket structure
  - retrieve and rank candidates
  - validate source/runtime boundary
  - build compact evidence packets
  - reject or downgrade invalid evidence
llm_role:
  - synthesize from provided evidence packets
  - choose grounded estimate versus follow-up where ambiguity remains
  - explain uncertainty
  - never create FoodDB truth
semantic_owner:
  user_intent: Manager LLM
  food_semantics: hybrid, with deterministic candidate framing and Manager synthesis
  routing_or_workflow_effect: Manager LLM
  mutation_legality: runtime guard
  persistence_truth: deterministic runtime
do_not_override:
  - deterministic code must not rewrite Manager semantic outputs by raw-text keyword
  - WebSearch snippets must not become nutrition truth
  - validator-passed candidates must not become runtime truth without promotion policy
```

## Interface Roadmap

The next RAKE evidence slices may add only additive interfaces:

- `FoodEvidenceIndexPort`: adapter boundary for local JSON, SQLite FTS, future Supabase, or other indexed evidence sources.
- `FoodEvidenceQuery`: normalized intake evidence query with aliases, modifiers, basket flags, and source-scope hints.
- `FoodEvidenceRecallPacket`: compact candidate recall packet for Manager/tool results.
- `ToolEvidenceResult`: read-tool output wrapper that carries evidence packets and trace flags without mutation authority.
- `WebSearchCandidatePacket`: source-grounded candidate packet for exact/near-exact brand or external evidence lanes.

These interfaces must not change `NutritionEvidenceStorePort`, `FoodEvidenceRecord`, `PacketReadyAnchor`, packetizer accepted/rejected format, basket semantics, estimate output format, or `ManagerContextPacket`.

## Activation Order

```yaml
activation_order:
  deterministic FoodDB first:
    purpose: prove alias, fuzzy, modifier, basket, runtime-source boundary, and compact packet behavior
    live_provider: false

  GrokFast diagnostic after deterministic closure:
    purpose: verify Manager can use FoodDB evidence packets without inventing nutrition source truth
    activation: live_diagnostic_only
    forbidden:
      - readiness
      - self_use_approval
      - runtime_mutation
      - production_model_selection

  WebSearch after local FoodDB packet seam:
    purpose: add source-quality, query, retry, cache, and candidate extraction risk only after local packet seam is stable
    runtime_truth_allowed: false

  Kimi later:
    purpose: provider comparison and end-to-end diagnostic only after local FoodDB and WebSearch packet seams are proven
```

## Micro-suite / Evidence Gate Map

| Case | Evidence path gate | Required behavior |
| --- | --- | --- |
| `B1-001` common single food | generic FoodDB lookup packet | retrieve approved common-serving evidence; packetizer truth level remains candidate/hint until Manager synthesis |
| `B1-002` high-variance drink | generic FoodDB + modifiers | use runtime anchor plus size/sugar/topping hints; keep range and uncertainty |
| `B1-003` generic meal | generic range evidence | return range/follow-up posture, not exact truth |
| `B1-004` bare basket | composition-unknown boundary | ask follow-up; no generic lookup, no web search, no estimate, no mutation |
| `B1-005` listed basket | item-level component lookup | fan out listed components; only approved component anchors can be estimated |
| `B1-006` no-mutation nutrition query | read-only evidence or llm_prior posture | answer may use evidence packet, but must not claim logged status |
| brand/store exact miss | exact DB first, WebSearch candidate second | WebSearch produces candidate packet only; snippets are not truth |

## Stop Gates

Stop and report before editing if a slice requires:

- changing `NutritionEvidenceStorePort`, `FoodEvidenceRecord`, `PacketReadyAnchor`, packetizer format, basket semantics, estimate output format, or `ManagerContextPacket`;
- making WebSearch, OFF, USDA, old-base, or raw TFDA records runtime truth;
- treating per-100g source evidence as a common serving;
- letting deterministic code infer user intent, workflow effect, or final action from raw text;
- running live provider tests before deterministic packet closure;
- claiming Product Loop, Webshell, private self-use, production DB, Kimi, shadow/canary, readiness, or mutation activation.
