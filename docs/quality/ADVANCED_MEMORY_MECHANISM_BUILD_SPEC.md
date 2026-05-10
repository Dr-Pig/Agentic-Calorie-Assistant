# Advanced Memory Mechanism Build Spec

Status: Active build contract for advanced capability memory foundation

Owner: Memory/runtime architecture

Consumer: coding agents building advanced recommendation, rescue, proactive, and long-term memory slices before runtime attachment

Scope: post-self-use advanced memory mechanism work that can be built and tested offline, by fixtures, shadow evaluators, or read-only runtime observations, without connecting to live runtime effects

Retirement trigger: replace this build contract when durable memory activation has an explicit gate-ledger entry, rollback path, user review surface, and human promotion decision

## Purpose

This document turns the weight-loss product memory mechanism into a buildable sequence.

The first goal is not to create a memory service. The first goal is to make memory behavior inspectable, testable, and bounded so that recommendation, rescue, proactive, and later personalization can share the same memory vocabulary without changing Current Shell self-use behavior.

Memory work in this phase may observe runtime behavior as evidence. It must not become runtime behavior.

## Advanced Runtime Lab Addendum

The isolated advanced lab is allowed to build complete product-capability mechanics, but the merge-back posture must stay dormant.

Locked execution decisions:

- The first advanced-lab slice is `advanced_runtime_lab_dormancy_contract`; it must not make live provider calls.
- Later lab live diagnostics may use BuilderSpace `grok-4-fast` only.
- `kimi-k2.5` is the target reasoning-model profile, but it is not live-called in this PR train.
- Model IDs must stay behind role/profile selection; provider-specific behavior must not become product semantics.
- The lab profile seam exposes `builderspace-grok-4-fast-advanced-shadow-lab-live-diagnostic` for manual live diagnostics and `builderspace-kimi-k2-5-advanced-shadow-lab-dormant-reference` as dormant target-reasoning metadata only.
- Proactive output is chat-only in the lab; inbox mirrors, push, LINE, OS notifications, and scheduler delivery remain out of scope.
- FoodDB expansion waits for real self-use. Until then, lab tests may use simulated traces, fixtures, and approved packets only.
- Isolated lab semantic memory candidate generation may be introduced after the dormancy contract is green, but mainline live semantic extraction and durable product memory writes remain forbidden until a separate activation PR.

### Long-Term Memory Stage Closure

The activation ladder now records long-term memory as `read_only_runtime` only because the manual `runtime_lab_memory_stage_promotion_decision` artifact proves the transition from `shadow` to `read_only_runtime`.

The stage decision artifact still records `current_stage: shadow` as the from-state. Do not rewrite that producer constant unless the transition schema itself is redesigned.

This closure does not promote recommendation, rescue, proactive, user-facing behavior, durable memory, scheduler delivery, production DB migration, or ManagerContextPacket injection.

### Recommendation Stage Closure

The activation ladder records recommendation as `read_only_runtime` only when the manual `recommendation_read_only_runtime_stage_decision` artifact proves the transition from `shadow` to `read_only_runtime`.

The recommendation stage decision artifact still records `current_stage: shadow` as the from-state. Do not rewrite that producer constant unless the transition schema itself is redesigned.

This closure does not serve recommendations, run live search or ranking LLMs, create intake handoffs, activate routes, send proactive messages, mutate canonical state, or promote rescue/proactive stages.

### Rescue Stage Closure

The activation ladder records rescue as `read_only_runtime` only when the manual `rescue_read_only_runtime_stage_decision` artifact proves the transition from `shadow` to `read_only_runtime`.

The rescue stage decision artifact still records `current_stage: shadow` as the from-state. Do not rewrite that producer constant unless the transition schema itself is redesigned.

This closure does not serve rescue proposals, commit proposal cards, mutate budget/body/meal/ledger state, activate routes, send proactive messages, or promote proactive.

## Direction And Dependency Classification

```yaml
direction_challenge_subagent: skipped
direction_challenge_skip_reason: root planning and documentation slice only; no subagent requested for this turn
current_mainline: Current Shell local self-use foundation
is_detour: true
blocked_mainline: not_applicable
detour_reason: user requested advanced capability work to stay isolated from self-use MVP while still building the shared memory foundation
detour_exit_gate: memory mechanism contract added, indexed, and tested without runtime connection or self-use mutation
exit_gate_status: this document is planning and contract evidence only, not activation evidence
return_slice_after_exit: Current Shell self-use closure remains the default mainline
strategic_verdict: allowed_detour
```

Capability dependency check:

```yaml
capability_layer: L9 Same-Truth / UI / Memory / Proactive, constrained to L4 memory read-model planning
upstream_dependencies:
  - layer: L0 Product Operating Rules
    contract_status: contract_backed
    risk_if_missing: memory could become hidden product truth
  - layer: L1 InteractionEvent / CurrentTurnContext
    contract_status: draft
    risk_if_missing: short-term context could be mistaken for durable memory
  - layer: L3 MealThread / Draft / Commit Boundary
    contract_status: contract_backed
    risk_if_missing: memory could duplicate or override canonical meal truth
  - layer: L4 RetrievalIntent / Source Selection
    contract_status: draft
    risk_if_missing: memory retrieval could leak raw history or irrelevant patterns
  - layer: L8 Mutation / Ledger / Version
    contract_status: contract_backed
    risk_if_missing: memory candidates could accidentally mutate canonical state
slice_mode:
  - diagnostic_only
  - offline_runtime
  - shadow_foundation
  - producer_honesty
user_facing_behavior_changed: false
runtime_truth_changed: false
mutation_changed: false
safe_to_proceed_now: true
why_not_local_next_step_trap: this slice only defines memory contracts and tests side-effect absence before downstream advanced features consume memory
```

High-impact boundary check:

```yaml
best_practice_evidence:
  required: true
  sources_checked:
    - docs/specs/L4A_MEMORY_MODEL_SPEC.md
    - docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md
    - docs/specs/UX_TO_SYSTEM_CAPABILITY_GAP_MATRIX.md
    - docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md
    - docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md
    - docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md
    - https://openai.github.io/openai-agents-python/sessions/
    - https://openai.github.io/openai-agents-python/sandbox/memory/
    - https://openai.github.io/openai-agents-python/guardrails/
  adopted_guidance:
    - keep raw conversation/session history separate from durable memory
    - use guardrails and validators to reject unsafe memory effects instead of letting memory silently shape runtime behavior
    - evaluate memory behavior with traceable offline cases before activation
  rejected_guidance:
    - generic vector-memory-first architecture before canonical state, summary views, and promotion rules are stable
    - background memory writers before user review and rollback exist
  conflict_with_repo_habits: existing shadow memory artifacts are useful, but this spec prevents them from becoming activation claims
  how_the_design_changed: advanced memory starts as typed candidates and derived summaries, not as a live memory provider
llm_deterministic_boundary:
  decision_surface: memory candidate extraction, summary derivation, retrieval shaping, and consumer gating
  truth_owner: hybrid
  deterministic_role: derive, validate, reject, downgrade, expire, suppress, and enforce promotion thresholds
  llm_role: synthesize semantic pattern candidates only when activation later allows it
  do_not_override:
    - canonical MealThread and MealItem truth
    - canonical budget, body, proposal, and ledger truth
    - user-confirmed memory edits and revocations
    - deterministic no-send and no-mutation guards
semantic_owner:
  user_intent: ManagerRuntime / CurrentTurnContext owner after activation, not this document
  food_semantics: canonical intake and FoodDB evidence owners
  routing_or_workflow_effect: manager and workflow contracts
  mutation_legality: mutation boundary and ledger/proposal owners
  persistence_truth: durable memory activation plan after human approval
```

## Memory Product Invariants

- Memory is not a transcript dump.
- Memory is not canonical meal, budget, body, proposal, or ledger truth.
- Memory may reference canonical objects, but it must not replace them.
- Short-term context is not durable memory.
- Pattern memory can influence future ranking or suppression only after the consumer has an approved read boundary.
- Confirmed memory requires explicit user confirmation, review, or revocation support.
- Golden orders are materialized views from canonical history, not promoted memories.
- Negative preferences and suppression memory must block or reduce suggestions before positive preferences boost them.
- Temporary preferences need explicit validity windows and expire without demotion rituals.

## Memory Taxonomy

| Layer | Role | Truth owner | Allowed now | Forbidden now | Primary consumers |
|---|---|---|---|---|---|
| L1 Typed History | Canonical product events such as committed meals, body observations, proposal outcomes, and proactive interactions | canonical product stores | read-only fixture references and source refs | duplicating canonical facts as memory truth | all advanced consumers through summaries |
| L2a Statistical Pattern | Deterministic patterns from canonical history | deterministic consolidation | shadow candidates and derived summary fields | durable writes or hidden personalization | recommendation, rescue, proactive, calibration |
| L2b Semantic Pattern | LLM-extracted pattern candidate from enough evidence | future reviewed memory pipeline | schema design and fake provider cases | live LLM extraction or promotion | recommendation and chat context after activation |
| L3 Confirmed Memory | Explicit or user-confirmed memory | future durable memory store with review surface | candidate schema and fixture review | durable write, cross-session injection, or automatic promotion | recommendation, proactive, chat context |
| Negative Preference Memory | Confirmed dislike, avoidance, opt-out, or inferred avoidance candidate | future reviewed memory store; deterministic guards for suppression | conflict cases and blocking rules | auto-demotion of confirmed negative memory | recommendation and proactive hard guards |
| Temporary Preference | Time-boxed preference or constraint | future reviewed memory store | validity-window fixtures | indefinite defaults or silent extension | recommendation and proactive ranking |
| Golden Order | Repeated store plus item bundle materialized from canonical history | canonical history materialized view | deterministic shadow view | treating it as promotion output | recommendation and proactive candidate selection |
| Archive | Old patterns or inactive golden orders retained outside hot retrieval | future archive policy | archive criteria tests | live retrieval or hidden ranking weight | audits and debug only |
| Interaction Preference / Suppression | Repeated ignore, dismiss, accept, opt-out, channel, and timing signals | interaction event history plus future reviewed memory | no-send suppression summaries | scheduler activation or notification dispatch | proactive, recommendation, rescue posture |

## Derived Summary Views

Consumers should read bounded summaries, not raw history.

| Summary | Inputs | Can answer | Must not answer |
|---|---|---|---|
| PreferenceProfileSummary | committed meals, explicit preference candidates, negative preferences, temporary preferences | likely staples, drink style, store affinity, time-of-day tendencies, blockers | final food truth, current intent, or durable preference truth |
| GoldenOrderSummary | canonical committed meal history | repeated store and bundle candidates with recency and confidence | confirmed memory, promotion, or current craving |
| SuppressionSummary | ignored nudges, dismissals, explicit opt-outs, quiet-hour and cooldown events | whether a proactive or recommendation surface should be reduced, delayed, or blocked | permission to send |
| IntakeCompletenessSummary | meal log completeness and correction history | logging gaps, likely underlogging windows, confidence gaps | budget mutation or body-plan adjustment |
| RescueHistorySummary | rescue invitations, accepted proposal outcomes, rebound attempts | whether rescue posture is useful and which style has worked | automatic proposal commit |
| AdherenceSummary | daily/weekly budget adherence and recovery outcomes | deficit sustainability, overshoot patterns, rebound risk | calibration mutation or health advice |
| CalibrationHistorySummary | weight trend evidence, accepted calibration proposals, rejected proposal history | whether a calibration suggestion is stale, repeated, or confusing | stored-action creation |
| InteractionPreferenceSummary | accept/ignore/dismiss/opt-out patterns across advanced surfaces | channel, timing, and friction posture | durable opt-out unless explicitly confirmed |

## Promotion And Demotion Rules

These rules are copied from canonical memory specs and narrowed for this build sequence.

- Repeated store and item creates a pattern candidate after the same store plus item repeats at least 3 times.
- Repeated item kind creates a pattern candidate after the same item kind repeats at least 5 times.
- Repeated time preference creates a pattern candidate after the same time preference repeats at least 5 times.
- Golden order appears when the same normalized store plus bundle repeats at least 3 times in 30 days and has an observation within 60 days.
- Pattern to confirmed memory requires reinforcement count at least 5, confidence at least 0.8, consistency for 30 days, and user confirmation.
- LLM extraction may propose a semantic pattern candidate only after the evidence threshold exists; it may not complete promotion.
- Confirmed negative memory does not auto-demote. It changes only through explicit user cancellation or correction.
- Temporary preference defaults to a maximum 14-day validity window unless a narrower user-stated window exists.
- Pattern memory not observed for 30 days is downgraded to needs_attention, archived at 60 days, and deleted at 90 days unless refreshed by new evidence.
- Golden order inactive for 60 days is inactive, archived at 90 days, and may reactivate if the same bundle reappears.

## Consumer Dependency Map

Build consumers against the summary views, not against memory storage.

| Consumer | Reads first | Needs later | Must not do in this phase |
|---|---|---|---|
| Recommendation shadow | PreferenceProfileSummary, GoldenOrderSummary, negative and temporary preference candidates | candidate generation and user-visible offer/silence gate | live search, served recommendation, durable memory write |
| Rescue shadow | RescueHistorySummary, AdherenceSummary, IntakeCompletenessSummary, suppression posture | proposal invitation and acceptance boundary | proposal commit, plan rewrite, budget correction |
| Proactive no-send | SuppressionSummary, InteractionPreferenceSummary, GoldenOrderSummary, PreferenceProfileSummary | deterministic trigger gate and no-send dispatch decision | scheduler activation, push/LINE send, trigger persistence |
| Long-term chat context | selected PreferenceProfileSummary and confirmed-memory candidates | context packing activation plan | ManagerContextPacket injection |
| Calibration shadow | CalibrationHistorySummary, AdherenceSummary, IntakeCompletenessSummary | proposal candidate scoring | stored-action creation or body-plan mutation |

## Build Sequence

1. Memory mechanism build contract.

   Add this spec, the machine-readable contract, and tests proving no runtime connection or self-use bootstrap takeover.

2. Memory candidate schema.

   Define offline candidate shapes for explicit preference, negative preference, temporary preference, statistical pattern, semantic pattern candidate, golden order view, and interaction suppression candidate.

3. Derived summary shadow views.

   Extend or reuse existing derived summary artifacts so each consumer reads a bounded summary with source refs and freshness metadata.

4. Promotion and demotion validator.

   Add deterministic validators for thresholds, expiry, archive state, conflict handling, and no-promotion-without-confirmation.

5. Dogfood fixture review pipeline.

   Convert selected real self-use traces into anonymized review cases without canonizing new product semantics.

6. Recommendation shadow consumer.

   Use memory summaries to rank prepared candidates and choose high/medium/low quality outcomes. Keep runtime serving false.

7. Rescue shadow consumer.

   Use rescue and adherence summaries to prepare invitation candidates only. Keep proposal commit false.

8. Proactive no-send consumer.

   Use suppression and interaction summaries to simulate trigger outcomes. Keep scheduler, sends, and persistence false.

9. Activation planning.

   Only after the above is stable, draft a separate durable memory activation plan with rollback, user review, revocation, context packing, and human promotion gate.

## Do Not Build Yet

- durable memory service
- database migrations for memory tables
- background consolidation worker
- live LLM semantic extraction
- vector memory index or RAG provider
- ManagerContextPacket memory injection
- scheduler activation
- push, LINE, email, or app-open recommendation delivery
- user-visible memory settings surface
- cross-session personalization
- live search or Places lookup for recommendation

## First Slice Acceptance

The first slice is complete only when:

- this spec is indexed as conditional advanced memory guidance, not active bootstrap
- the machine-readable contract exists
- tests assert no runtime connection, no user-facing behavior change, no mutation, no durable memory write, no scheduler activation, and no ManagerContextPacket injection
- tests assert golden orders remain materialized views
- tests assert pattern-to-confirmed promotion requires user confirmation
- markdown encoding passes the policy-doc BOM guard

## Non-Claims

This document does not claim:

- runtime activation
- product readiness
- private self-use approval
- durable memory readiness
- recommendation serving readiness
- rescue proposal readiness
- proactive sending readiness
- any change to Current Shell self-use behavior
