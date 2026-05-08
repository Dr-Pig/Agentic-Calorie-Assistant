# UX to System Capability Gap Matrix

## Purpose

This document records product-semantics decisions that translate ideal UX moments into system capabilities.

It exists to prevent detailed UX workflows from becoming ad hoc prompts, hardcoded deterministic flows, or parallel truth. Each UX moment should map to typed product state, semantic ownership, guardrails, and downstream capability dependencies.

## Non-Goals

- Do not define visual UI layout, animation, typography, or brand direction.
- Do not implement runtime behavior, schemas, endpoints, background workers, provider calls, or UI components.
- Do not replace owner specs such as recommendation, proactive scheduler, memory, rescue, or calibration contracts.
- Do not use eval fixture shape as product truth.

## Upstream Docs

- `docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md`
- `docs/specs/L0_PRODUCT_CAPABILITY_SPEC.md`
- `docs/quality/UX_JOURNEY_TO_SLICE_MAP.md`
- `docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md`
- `docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md`
- `docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md`
- `docs/specs/L4A_MEMORY_MODEL_SPEC.md`
- `docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md`
- `docs/specs/UI_CANONICAL_TRUTH_SURFACE_MATRIX.md`

## Downstream Use

- Required before turning UX moments into new tools, manager actions, prompts, memory writes, proactive triggers, proposal flows, smart chips, or UI actions.
- Use this as a product-semantics matrix first; implementation plans must still resolve owner specs and tests.
- If this matrix conflicts with an owner spec, update the owner spec with a targeted patch before implementation.

## Strategic Gate

```yaml
current_mainline: CurrentShell self-use MVP local desktop dogfood
is_detour: true
blocked_mainline: not_blocked
detour_reason: Product-semantics inventory for later-wave UX moments; no runtime, schema, API, UI, or mutation behavior is added.
detour_exit_gate: UX moments map to state category, owner object, allowed action, forbidden shortcut, and unresolved gap.
exit_gate_status: in_progress
return_slice_after_exit: CurrentShell self-use MVP local desktop dogfood
strategic_verdict: allowed_detour
```

## Capability Dependency Check

```yaml
capability_layer: L9 Same-Truth / UI / Memory / Proactive, with L3-L8 owner dependencies
upstream_dependencies:
  - layer: L0 Product Operating Rules
    contract_status: contract_backed
    risk_if_missing: UX semantics could make UI or proactive behavior primary over chat-first interaction.
  - layer: L1-L3 InteractionEvent, MealThread, Draft/Commit Boundary
    contract_status: contract_backed
    risk_if_missing: UX actions could bypass manager/guard/commit boundaries.
  - layer: L4 Memory and Recommendation
    contract_status: draft_to_contract_backed
    risk_if_missing: Preference, pattern, or recommendation semantics could become untraceable prompt behavior.
  - layer: L7-L8 Mapping, Proposal, Ledger Mutation
    contract_status: draft_to_contract_backed
    risk_if_missing: Plan-changing interactions could mutate budget or ledger without explicit confirmation.
slice_mode:
  - diagnostic_only
  - product_semantics_mapping
  - architecture_mapping
user_facing_behavior_changed: false
runtime_truth_changed: false
mutation_changed: false
safe_to_proceed_now: true
why_not_local_next_step_trap: This is a read-only semantics inventory. It records owner boundaries and stop conditions before implementation.
```

## Translation Rule

Detailed UX workflows should translate through this chain:

```text
UX moment
-> product semantic contract
-> structured LLM decision
-> typed state or command
-> deterministic guard
-> human confirmation when mutation-bearing
-> trace and eval evidence
```

LLMs may judge ambiguous user language, natural response framing, and contextual usefulness. Deterministic layers own legality, mutation permission, cooldown, suppression, safety floors, budget math, and canonical owner boundaries.

## State Categories

| State Category | Meaning | Canonical Impact | Examples |
| --- | --- | --- | --- |
| `no_state` | Pure reply or transient rendering | none | "換一個", "看低熱量" when only reranking current candidates |
| `short_term_context` | Context that helps the assistant follow up naturally | no budget or ledger mutation | "等等吃這個", pending meal intent |
| `temporary_preference` | Time-limited preference or constraint | memory, expires | "今天不想喝有糖", "這週少吃澱粉" |
| `pattern_memory` | Derived behavior or language pattern | recommendation/proactive ranking only | repeated avoidance, golden meal-time patterns |
| `confirmed_memory` | User-declared or user-confirmed preference/suppression | high-weight memory | "以後不要推薦炸物", "不要再提醒我記午餐" |
| `proposal_candidate` | Discussed future plan not accepted yet | no mutation until accepted | planned-event reduction discussion, rescue adjustment candidate |
| `canonical_write` | Actual committed fact or accepted plan | writes owner object | eaten meal, body observation, accepted rescue overlay |

## Locked Decisions

### 1. Pending Meal Intent

When the user says "就這個", "等等吃這個", or "就去這家" after a recommendation or menu scan:

- Create `short_term_context`, not intake, proposal, or ledger truth.
- Purpose: support later references and proactive strategy.
- It may help the assistant understand "剛剛那個", "我吃完了", "我沒吃", or "換成別的".
- It may expire.
- It may be visible as a lightweight chat/UI mirror, but it must not look like a formal task or proposal.
- Only "我吃了這個", "幫我記這個", or equivalent actual-consumption language enters intake.

### 2. Mutation Authority

```text
past_or_actual_fact -> canonical write path
future_intent_or_plan -> context, memory, or proposal first
```

Allowed direct canonical writes:

- "我剛吃了 X" -> `MealThread` / intake commit path.
- "我今天 62 公斤" -> `BodyObservation`.
- "剛剛那杯我只喝一半" -> correction path.

Not direct canonical writes:

- "等等吃 X" -> pending meal context.
- "今天想吃麵" -> current context or temporary preference.
- "以後不要推薦炸物" -> confirmed memory, not meal/budget truth.
- "幫我接下來三天少吃" -> proposal discussion and explicit acceptance before ledger mutation.

### 3. Memory Signal Strength

Use the existing three-layer memory model:

```text
L1 Typed History / Observation
L2 Pattern Memory
L3 Confirmed Memory
```

No fourth `inferred stable preference` layer is introduced. High-confidence inferred stability remains an L2 pattern with confidence, reinforcement, freshness, and stability posture.

Rules:

- User explicit statements such as "記住", "以後", "不要再", "我不吃" may write L3 confirmed memory.
- Repeated behavior or repeated wording creates or reinforces L2 pattern memory.
- L2 stable patterns may influence recommendation and proactive ranking.
- L2 -> L3 requires user confirmation, either user-initiated or system-suggested in a natural moment.
- The system should not send standalone memory-confirmation messages only to improve its own memory hygiene.
- Confirmation should appear only inside a useful interaction, for example recommendation, proactive, rescue, calibration, or user-initiated memory review.

### 4. Interaction Preference Memory

Assistant interaction preferences use the same memory system but a separate domain from food preference.

Examples:

- L1: ignored proactive message, dismissed reflection prompt, clicked explain, accepted coaching, asked fewer questions.
- L2: tends to ignore meal reminders, responds well to soft hooks, prefers minimal follow-up, dislikes long analysis.
- L3: confirmed no meal reminders, confirmed minimal questions, confirmed no weight reminders.

Adjustment policy:

- Repeated proactive-message ignore or reflection-prompt dismissal first causes soft adaptation: lower frequency and lower-pressure wording.
- Continued proactive/reflection ignore, or explicit dismissal of that proactive category, may create temporary or category suppression.
- Permanent or broad suppression requires explicit user language.
- Suppressed capabilities remain user-callable.

This interaction-preference rule does not apply to `ProposalContainer.status = dismissed`. Proposal dismissal is scoped to the current proposal instance and must not become durable preference or suppression truth by itself.

### 5. Overshoot Soft Coaching Hook

When a just-committed intake makes the day overshoot, the intake reply may include awareness plus a low-pressure coaching hook.

Allowed:

- Show current consumed and overshoot amount.
- Offer two low-pressure paths:
  - reflection: "要不要一起看今天主要超在哪裡?"
  - action: "要不要我幫你抓一個明天不太硬的調整?"

Forbidden:

- Do not create a rescue proposal inside the intake reply.
- Do not commit future budget or ledger changes.
- Do not give a mutation-bearing plan as if accepted.
- Do not produce long reflection analysis unless the user asks.

Preferred posture:

```text
overshoot intake reply
-> awareness + soft hook
-> user engages
-> reflection or rescue negotiation
-> explicit accept
-> proposal/ledger mutation path
```

### 6. Reflection Capability

If the user asks "幫我看今天為什麼超", the system should perform nutrition leverage analysis, not generic scolding.

Preferred output:

- Identify the highest-leverage calorie drivers.
- Suggest realistic swaps or portion changes within the same meal style.
- Ask at most one high-impact follow-up when data is insufficient.
- Do not expand this analysis proactively by default.

Examples:

- "飯從兩碗變一碗" is a useful leverage suggestion.
- "炸的換成烤/滷" is a useful leverage suggestion.
- "買炸臭豆腐但只吃三顆" is usually not realistic and should not be framed as the main suggestion.

### 7. General Event Guidance vs Planned-Event Rescue

General event guidance:

- User says "今晚有聚餐，我不知道怎麼吃".
- This is pre-meal strategy, not proposal.
- Ask or infer cuisine/meal type when useful.
- Provide concrete eating guidance such as vegetables first, rice portion, alcohol/drink caution, protein priority, and high-calorie dish awareness.
- No ledger or future budget mutation.

Planned-event rescue:

- User says "週六吃到飽，我想提前減量" or "幫我預留 800 kcal".
- This starts chat-first planning negotiation.
- Discuss likely surplus, timeline, current budget, and comfortable adjustment.
- Only accepted settings become proposal/ledger overlay.

### 7A. Proposal Card Primary Actions

Proposal cards are mutation-confirmation surfaces, not full control panels.

Rules:

- Primary actions should be limited to accepting the proposal or dismissing it for now.
- Strength adjustment and explanation remain available through chat negotiation or secondary App/Web affordances.
- "緩一點", "短一點", and "為什麼這樣算" are valid semantic commands, but they should not be peer primary buttons on the proposal card by default.
- A clear complaint such as "這樣也太硬了吧" is negotiation, not dismiss.
- A clear "不要", "算了", or "先不要" dismisses the proposal and should not require the system to ask for a reason.
- Dismiss applies to the current proposal instance only. It is not a permanent opt-out from rescue, and it is not a timed snooze. The system may generate a new proposal only after material context changes or the user reopens the discussion.
- Dismissed proposals should leave the active proposal inbox, remain visible in user-facing history/audit, and should not be resent through LINE or other channel adapters as the same proposal instance.
- User-facing history should show a concise human-readable summary plus an expandable explanation. It should not expose raw trace, sidecar diagnostics, or internal chain-of-thought-like reasoning as product UI.

Preferred primary actions:

```text
accept_rescue_plan
dismiss_rescue_plan
```

This keeps LINE and chat cards lightweight while preserving natural chat-first adjustment.

### 8. Proactive Contract

Proactive behavior should consider whether it reduces user friction or increases user burden.

| Tier | Category | Default Posture |
| --- | --- | --- |
| Tier 1 | Low-risk reminder/follow-up | Can be on by default with cooldown and suppression |
| Tier 2 | Friction-reducing recommendation | Can be moderately proactive when quality is high |
| Tier 3 | Soft coaching | Low frequency, low pressure, never long-form by default |
| Tier 4 | Plan-changing proactive | Requires user engagement or explicit acceptance |

Examples:

- Pending meal follow-up: Tier 1.
- Meal logging reminder: Tier 1.
- Dinner recommendation that reduces decision cost: Tier 2.
- Overshoot reflection hook: Tier 3.
- Rescue plan or calibration plan change: Tier 4.

### 9. Proactive Recommendation Quality

Proactive dinner recommendation uses adaptive intensity:

```text
high_quality_context -> send 1 primary + 1 backup
medium_quality_context -> low-friction offer
low_quality_context -> no proactive recommendation
```

Hard gates:

- quiet hours and cooldown pass.
- not suppressed.
- meal-time relevant.
- calorie target / budget gate passes.
- confirmed negative preferences are not violated.
- candidate is realistically executable.

Quality signals:

- availability or likely availability.
- budget fit.
- frequent choice / golden order.
- meal-time pattern match.
- known chain or known store.
- preference pattern.
- evidence quality.
- interaction tolerance.

### 10. Frequent Choice and Golden Orders

Frequent choice is a strong recommendation signal even without inferred liking.

Rationale:

- People often choose foods because they are convenient, cheap, nearby, familiar, or acceptable.
- These reasons are valid for recommendation.
- Wording should say "你之前常吃" or "這個對你比較穩", not "你喜歡".

Rules:

- Frequent choice boosts ranking only after hard gates pass.
- A frequent item that fails the calorie gate must not be proactively recommended.
- If a historically realistic portion pattern passes the gate, it may be recommended.
- Do not recommend unnatural restraint variants just to force a favorite item through the gate.

### 11. Evidence Standard for Proactive Recommendation

Proactive recommendation candidates must be specific enough to act on and bounded enough to pass the calorie gate.

Allowed:

- Exact item evidence.
- Narrow anchored item evidence.
- Specific item with a bounded estimate from menu, photos, blog descriptions, historical records, store patterns, or similar anchored sources.

Not allowed as proactive concrete recommendation:

- Generic category-only suggestions such as "吃個便當".
- Wide uncertainty items that cannot pass budget gate.
- Unknown portion-risk items when available evidence suggests unusually large servings.

### 12. Live Search and Background Cost Boundary

Proactive recommendation should not start with expensive live search by default.

Preferred architecture:

```text
nightly / periodic preparation
-> lightweight proactive gate
-> optional live enrichment after user engagement
```

Version posture:

- V1: use golden orders, frequent items, known chains, safe fallback candidates, preference profile, budget, and suppression. No live web search proactive.
- V2: when the user asks "附近有什麼" or taps "幫我找", run Google Places, web search, menu lookup, or anchored candidate enrichment.
- V3: maintain candidate caches for frequent locations, frequent stores, and popular chains. Background refreshes cache, not per-user expensive live proactive search.
- V4: enable proactive live enrichment only for high-value, cost-controlled, permission-backed contexts.

Rules:

- Live search is user-engaged by default.
- No qualified candidate means no proactive recommendation.
- Background work should prepare candidates and summaries; it should not become an unbounded autonomous search loop.

## Open Gaps

- Exact schema for `PendingMealIntent` as short-term context.
- Exact `interaction_preference` fields and suppression thresholds.
- Exact quality score weights for proactive recommendation.
- Candidate cache ownership and invalidation policy.
- Host-specific location capability differences between Native App and LINE/LIFF.
- Eval cases for soft coaching hook, reflection trigger, proactive recommendation skip, and no-qualified-candidate silence.
