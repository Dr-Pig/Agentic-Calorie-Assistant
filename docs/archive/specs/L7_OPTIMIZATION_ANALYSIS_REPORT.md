# L7 Optimization Analysis Report

> Archived on 2026-04-14.
>
> This analysis report was removed from `docs/specs/` because several reported
> gaps had already been resolved in the active owner specs. Keep it only as
> historical analysis, not as a source of current architectural truth.

## Comprehensive Review of L0-L6 Specs

**Generated**: 2026-04-13
**Author**: Claude Code Analysis

---

## Executive Summary

After reviewing all L0-L6 specs, the memory mechanism is indeed the most architecturally complex component. The workflow specs (L1-L3) are well-defined with clear contracts. The main risks are gaps in type definitions, cold-start handling, and feedback signal paths.

**Key Finding**: The app's core value proposition — proactive food recommendations that understand user preferences — depends heavily on closing the feedback loop between recommendations and memory updates. This loop is currently undefined.

---

## 1. Logical Problems Identified

### 1.1 `default-commit` vs `proposal_first` Conflict

**Location**: L3_1 Section 2.2 vs L3_3B / L3_4

**Problem**: L3_1 states "主流程預設 default-commit" but L3_3B (Calibration) and L3_4 (Rescue) both require proposal → confirm → commit flow.

**Impact**: Ambiguous when a user intake requires proposal vs auto-commit.

**Resolution**:
```
default-commit applies ONLY to: Fresh meal logging (new meal, no calibration/rescue needed)
proposal_first ALWAYS applies to: Rescue events, Calibration adjustments
```

### 1.2 `utterance_override` Lifecycle Gap

**Location**: Referenced in L1, L4, but never fully defined

**Problem**: No explicit state machine for:
- When it activates
- How long it persists
- When it expires
- Interaction with new user inputs

**Resolution**: Add to L1_RUNTIME_OWNERSHIP_SPEC:
```
utterance_override states:
  - INACTIVE: No override in effect
  - ACTIVE: Override生效 (session-scoped)
  - EXPIRED: Session ended, awaiting potential confirmation

Transitions:
  INACTIVE → ACTIVE: User explicit statement in current turn
  ACTIVE → EXPIRED: Session ends
  EXPIRED → (deleted or promoted to ConfirmedMemory): User confirms in next session
```

### 1.3 Calibration Window Boundary Logic

**Location**: L3_3A Section 3

**Problem**: "14-day window, 5 observations, 80% coverage" — what happens at exact boundary?

**Resolution**: Add hysteresis rule:
```
Re-calibration triggers when:
  - 连续3个新observation都在threshold以下
  - OR 80% coverage持续跌破超过48小时

NOT triggered by:
  - 单日单次threshold跌破
  - 边界exact day的计算争议
```

### 1.4 `occurred_at` Immutability for Corrections

**Location**: L3_1 Section 8.4, L2 Data Model

**Problem**: When user corrects one item in a yesterday meal, should `occurred_at` be preserved or updated?

**Resolution**: Add rule:
```
occurred_at is IMMUTABLE across MealVersion chain
correction only affects: recorded_at, version_chain, MealItem content
```

### 1.5 ProposalContainer Ownership Ambiguity

**Location**: L1_RUNTIME_OWNERSHIP_SPEC vs L3_3B / L3_4

**Problem**: `proposal_container` is canonical in L1 but `proposal_family` lives in separate passes.

**Resolution**:
```
ProposalContainer = runtime envelope (L1 layer)
ProposalFamily = factory method that produces ProposalOption instances
proposal_family决定proposal_type, not proposal_container identity
```

---

## 2. Critical Gaps

### Gap 2.1: No Explicit `FeedbackSignal` Type

**Severity**: P0 — blocks recommendation learning

**Location**: Referenced in L3_2 but never defined

**Impact**: Feedback loop from recommendation → memory update is undefined

**Required Addition** (to L3T_TYPED_RUNTIME_CONTRACT_SPEC):
```python
@dataclass
class FeedbackSignal:
    signal_id: str
    user_id: str
    recommendation_id: str | None  # If came from recommendation
    meal_thread_id: str | None     # If came from meal logging

    feedback_type: Literal["accept", "reject", "ignore", "modify"]
    feedback_target: str  # What was accepted/rejected
    feedback_detail: str | None  # User-provided reason if any

    context: str  # e.g., "lunch", "snack", "evening"
    occurred_at: datetime

    # Signal path
    confidence_boost: float  # Positive for accept, negative for reject
    created_at: datetime
```

### Gap 2.2: Proactive Scheduler Implementation Undefined

**Severity**: P0 — blocks proactive features

**Location**: L1 defines `ProactiveTrigger` but no scheduler mechanism

**Missing**:
- Event loop or cron mechanism
- Trigger evaluation frequency
- What conditions create `ProactiveTrigger` from `ActiveContext`
- Nightly vs real-time trigger distinction

**Required Addition** (to L1 or new L4C):
```
ProactiveScheduler {
  trigger_evaluation_interval: int = 300  # seconds
  nightly_run_time: TimeOfDay = 23:00

  evaluation_order:
    1. budget_alert_check (real-time)
    2. meal_reminder_check (every 30 min during eating hours)
    3. calibration_needed_check (nightly)
    4. pattern_insight_check (nightly)
}
```

### Gap 2.3: No `DeterministicValidationResult` Schema

**Severity**: P0 — listed in L3_1 Section 9 but never defined

**Required Addition** (to L3T):
```python
@dataclass
class DeterministicValidationResult:
    validation_id: str

    passed: bool
    failure_mode: Literal["none", "schema_violation", "arithmetic_error",
                          "invariant_violation", "version_conflict"] | None

    checked_invariants: list[str]
    violations: list[str] = field(default_factory=list)

    # For bounded self-correction
    can_self_correct: bool
    self_correction_attempted: bool = False
    self_correction_success: bool | None = None

    # Metadata
    checked_at: datetime
    computation_time_ms: float
```

### Gap 2.4: User Preference Learning Loop undefined

**Severity**: P1 — degraded recommendation quality over time

**Missing**:
- How preferences are extracted from committed meals
- How feedback updates `PreferenceProfileSummary`
- Reinforcement signal path from `FinalResponseResult` back to memory

**Required Flow**:
```
1. User accepts recommendation → FeedbackSignal.accept
2. PatternMemory.reinforcement_count++ (memU-style)
3. If reinforcement_count >= 5 → upgrade to ConfirmedMemory
4. PreferenceProfileSummary regenerated
5. Next recommendations use updated profile
```

### Gap 2.5: No TDEE/BMR Estimation Library Integration Point

**Severity**: P1 — calibration accuracy depends on this

**Location**: L3_3A references `operating_expenditure_estimate`

**Missing**:
- Which TDEE formula (Mifflin-St Jeor, Harris-Benedict, Katch-McArdle)
- How to integrate with BodyPlan calibration data
- User-asserted vs model-inferred expenditure priority

**Recommended**: Use [`calcut/tdee`](https://github.com/calcut/tdee) for reference formulas

### Gap 2.6: No Food Naming Database Integration

**Severity**: P1 — item classification requires canonical food names

**Missing**:
- USDA/FDC or OpenFoodFacts integration point
- Food item canonicalization
- `item_kind` → `food_name` mapping

**Recommended**: [`openfoodfacts/openfoodfacts-python`](https://github.com/openfoodfacts/openfoodfacts-python)

### Gap 2.7: Multi-Turn Conversation Memory Scope

**Severity**: P1 — context overflow risk

**Missing**:
- Conversation context window size
- Expiration rules
- ActiveContext vs conversation history boundary

**Required Addition**:
```
RecentMessagesView {
  max_messages: int = 50
  max_window_hours: int = 24
  eviction_policy: Literal["fifo", "importance_weighted"]
}
```

### Gap 2.8: No Cross-Surface State Divergence Prevention

**Severity**: P1 — L0 says chat/UI/smart-chip share canonical objects

**Missing**:
- Which surface can write which fields
- Conflict resolution when same object modified from multiple surfaces

---

## 3. Framework Borrowing Recommendations

| Spec Area | Framework | What to Borrow | Integration Point |
|-----------|-----------|----------------|------------------|
| Memory | **Hindsight** | 4-path retrieval (semantic + BM25 + graph + temporal) | L4 retrieval pipeline |
| Memory | **Graphiti** | `valid_at`/`invalid_at` temporal windows | TemporalPreference (already in L4) |
| Memory | **memU** | reinforcement_count + content_hash dedupe | PatternMemory (already in L4) |
| Memory | **Letta** | Core/Working memory separation | L1 vs L4 separation (already in L4) |
| Calibration | **Hindsight** | Disposition traits | `intake_estimation_bias_posture` |
| Recommendation | **Graphiti** | Entity/Relationship/Episode graph | Future food entity graph (v2) |
| Feedback | **memU** | Resource reinforcement | FeedbackSignal → PatternMemory upgrade |

---

## 4. GitHub Resources

### Calibration & Math
- [`calcut/tdee`](https://github.com/calcut/tdee) — TDEE calculator with Mifflin-St Jeor, Harris-Benedict, Katch-McArdle formulas

### Food Data
- [`openfoodfacts/openfoodfacts-python`](https://github.com/openfoodfacts/openfoodfacts-python) — OpenFoodFacts API client
- [`sergioarguello/usda-food-data`](https://github.com/sergioarguello/usda-food-data) — USDA FoodData Central wrapper

### Memory Frameworks (already reviewed in L4)
- [`memFreeO/memU`](https://github.com/memFreeO/memU) — reinforcement_count, content_hash dedupe
- [`vectorize-io/hindsight`](https://github.com/vectorize-io/hindsight) — reflect, 4-path retrieval
- [`MinorChange/Graphiti`](https://github.com/MinorChange/Graphiti) — temporal facts, entity graph
- [`Letta/Letta`](https://github.com/Letta/Letta) — Core Memory Blocks
- [`mem0ai/mem0`](https://github.com/mem0ai/mem0) — User/Session/Agent layers

### Context Engineering (see below)
- LlamaIndex — context management and retrieval
- LangChain — memory modules
- GPTCache — LLM response caching

### Agent Orchestration (L6A references)
- [`LangChain/LangGraph`](https://github.com/langchain-ai/langgraph) — for v2+ durability
- [`AgentaAI/agenta`](https://github.com/agenta-ai/agenta) — prompt A/B testing

---

## 5. Context Engineering Analysis

### Is Context Engineering Needed?

**Answer**: YES, for two specific areas:

1. **Recommendation context assembly** (L3_2) — assembling preference context from multiple memory layers
2. **Proactive trigger evaluation** — determining which memories are relevant for a given moment

### Context Engineering Frameworks to Consider

| Framework | Best For | Consider If |
|-----------|----------|-------------|
| **LlamaIndex** | RAG, context retrieval, sentiment analysis | Need sophisticated context window management |
| **LangChain Memory** | Simple session memory, entity tracking | Need basic conversation memory only |
| **GPTCache** | LLM response caching, semantic caching | Need to reduce LLM API costs |
| **CrewAI Memory** | Multi-agent shared memory | v2 multi-agent phase |

### Recommendation for This App

**Current Assessment**: Your existing L4 memory spec + L1 runtime ownership is sufficient for v1. You do NOT need a full context engineering framework because:

1. Your memory is domain-specific (calorie tracking), not general-purpose
2. Your retrieval patterns are well-defined in L4B/L4 specs
3. You have explicit type contracts in L3T

**When to Add Context Engineering**:
- v2 when adding multi-agent (Letta-style agents)
- v2 when needing sophisticated RAG over user documents
- v2 when adding semantic food search beyond keyword matching

### If You Do Add Context Engineering Later

Consider:
- **LlamaIndex** for RAG over food knowledge base
- **GPTCache** for caching LLM responses to repeated queries
- **Anthropic's context management** techniques (if using Claude)

---

## 6. Priority Recommendations

### P0 (Block MVP)

| Priority | Action | Location |
|----------|--------|----------|
| P0-1 | Define `DeterministicValidationResult` schema | L3T_TYPED_RUNTIME_CONTRACT_SPEC.md |
| P0-2 | Clarify `default-commit` scope (fresh meals only) | L3_1 or L1 |
| P0-3 | Implement `utterance_override` state machine | L1_RUNTIME_OWNERSHIP_SPEC.md |
| P0-4 | Define ProactiveScheduler mechanism | L1 or new L4C |

### P1 (MVP degraded without)

| Priority | Action | Location |
|----------|--------|----------|
| P1-1 | Define `FeedbackSignal` type | L3T |
| P1-2 | Add food database integration point | L2 or L3_1 |
| P1-3 | Clarify `occurred_at` immutability | L3_1 |
| P1-4 | Define multi-turn conversation window | L1 or L2 |

### P2 (Proactive features)

| Priority | Action | Location |
|----------|--------|----------|
| P2-1 | Implement Hindsight-style reflect for NightlyInsight | L4 + scheduler |
| P2-2 | Build food entity graph (Graphiti-style) | Future extension |
| P2-3 | Implement memU-style feedback → preference upgrade | L4 + L3_2 |

---

## 7. Architecture Risk Summary

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Calibration math drift | Medium | High | Add deterministic audit log per L3M |
| Cold-start new user | High | Medium | Implement Letta-style core memory priming from onboarding |
| Multi-turn context overflow | Medium | Low | Implement sliding window in RecentMessagesView |
| Cross-surface state divergence | Medium | High | Canonical meal_thread as single source of truth per L1 |
| Recommendation feedback loop not closed | High | High | Define explicit FeedbackSignal → PreferenceProfileSummary path |
| Proactive scheduler undefined | High | High | Implement ProactiveScheduler per Gap 2.2 |

---

## 8. Summary: Memory is Complex, Workflows are Self-Contained

**Finding**: YES, your assessment is correct.

The **memory mechanism** (L4) is the most architecturally complex component because it must:
- Handle multiple memory layers with different decay/upgrade rules
- Support temporal tracking of preferences
- Enable proactive insight generation
- Close the feedback loop from recommendations to memory updates

The **workflow specs** (L1-L3) are relatively self-contained with clear contracts:
- L1: Well-defined layer ownership and state transitions
- L2: Complete type system for all canonical objects
- L3.1: Clear 4-pass intake flow
- L3.2: 3-node recommendation architecture
- L3.3A/B: Sequential calibration gates
- L3.4: Rescue families with clear compression rules
- L3.5: Prompt contract is well-structured
- L3M: Guardrail math is deterministic and complete

**The remaining gaps are mostly P0 type definitions and feedback loop closures — not fundamental architectural problems.**

---

## 9. Next Steps

1. **Immediate**: Add `DeterministicValidationResult` and `FeedbackSignal` to L3T
2. **This week**: Implement ProactiveScheduler mechanism
3. **This week**: Clarify `default-commit` scope vs proposal-first rule
4. **Before v1**: Implement cold-start onboarding memory priming
5. **v2 consideration**: Food entity graph, LlamaIndex for RAG

---

*Report generated by Claude Code Analysis*
