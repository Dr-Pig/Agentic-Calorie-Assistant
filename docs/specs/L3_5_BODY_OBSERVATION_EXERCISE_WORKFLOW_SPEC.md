# L3.5 Body Observation & Exercise Workflow Spec

## 1. Purpose

This spec defines the canonical runtime contract for the thin write workflows that capture:

1. `BodyObservation`
2. `ExerciseEvent`

It clarifies:

- which parts are semantic extraction versus downstream deterministic computation
- which paths should stay thin and not become intake-like multi-pass workflows
- how observation and exercise writes affect `BodyPlan`, `CurrentBudgetView`, and ledger truth
- when pure answer behavior should stay inside `general_chat + answer_only`

This file does not replace:

- `L3.3A` calibration model truth
- `L3.3B` calibration proposal truth
- onboarding/bootstrap ownership in `L0B`

---

## 2. Core Posture

### 2.1 Thin Workflow

`body_observation` and `exercise` are thin workflows.

They should not become heavy multi-pass graphs by default.

The canonical shape is:

- semantic extraction / create
- deterministic downstream recompute or writeback
- optional response presentation

### 2.2 Extraction Is LLM

Formal rule:

- body observation extraction is `decision_mode: llm`
- exercise extraction is `decision_mode: llm`

Reason:

- user utterances like `??憭?61 ?祆`, `????23%`, `??甇?30 ??`, or `??憭拚?????300 kcal` require intent recognition, value extraction, unit interpretation, and time interpretation
- those are semantic interpretation tasks, not deterministic parsing

Deterministic layers begin only after the canonical extraction result exists.

### 2.3 Deterministic Downstream

The following remain deterministic:

- TDEE recompute
- MET-based calorie-burn estimation
- ledger writeback
- canonical object legality and persistence
- read-model refresh

### 2.4 Chat-First, UI-Mirror

Chat may create observations or exercise events.
UI may mirror, display, or provide structured forms.

Neither surface should bypass the same canonical application-layer write path.

---

## 3. Body Observation Workflow

### 3.1 Entry Surfaces

- chat
- UI structured submission

### 3.2 Canonical Runtime Shape

Chat path:

1. `observation_extraction`
2. `observation_response`

Structured UI path:

- no mandatory LLM node if the request is already fully structured
- application layer may write directly after contract validation

### 3.3 Node 1: `observation_extraction`

Goal:

- interpret the user message
- identify the observation type
- extract value, unit, and occurred-at semantics
- produce a canonical observation-create decision

`decision_mode: llm`
`decision_reason: observation type identification, value extraction, unit interpretation, and occurred-at interpretation are semantic tasks`
`logical_model_role: fast_router_model`

Readable inputs:

- `raw_user_input`
- minimal recent messages
- `ActiveBodyPlanView` only when needed for contextual phrasing, not for overriding extracted values

Required outputs:

- `observation_type`
  - `weight`
  - `body_fat_percentage`
  - `other`
- `value`
- `unit`
- `occurred_at_interpretation`
- `observation_action`
  - `create_observation`
  - `cannot_extract`

Forbidden:

- recomputing TDEE
- rewriting `BodyPlan`
- deciding calibration posture

### 3.4 Deterministic Downstream Recompute

After a valid `BodyObservation` write, the application layer may deterministically:

1. update the current body profile fields when allowed
2. recompute BMR / estimated TDEE
3. refresh `ActiveBodyPlanView`
4. if allowed by the 11:00 rule, refresh the base daily budget for future-effective periods
5. refresh `CurrentBudgetView`

Formal rule:

- recompute uses formulas and current canonical state
- recompute must not reinterpret the user utterance
- any plan-changing proposal still belongs to `calibration`, not `body_observation`

### 3.5 Node 2: `observation_response`

Goal:

- present the accepted observation back to the user
- optionally mention deterministic downstream effects

`decision_mode: llm`
`decision_reason: response wording only`
`logical_model_role: response_writer_model`

Required outputs:

- `reply_text`
- optional `ui_hints`

### 3.6 Layer B Truth

- `observation_action`
  - `create_observation`
  - `answer_existing_state`
  - future `handoff_to_calibration`

---

## 4. Exercise Workflow

### 4.1 Entry Surfaces

- chat
- UI structured submission

### 4.2 Canonical Runtime Shape

Chat path:

1. `exercise_extraction`
2. `exercise_response`

Structured UI path:

- no mandatory LLM node when the request is already structured

### 4.3 Node 1: `exercise_extraction`

Goal:

- identify the exercise type
- extract duration or user-asserted burn
- decide the canonical create action for `ExerciseEvent`

`decision_mode: llm`
`decision_reason: exercise type recognition, duration extraction, user-asserted vs formula basis interpretation, and occurred-at interpretation are semantic tasks`
`logical_model_role: fast_router_model`

Readable inputs:

- `raw_user_input`
- minimal recent messages
- `ActiveBodyPlanView` only when needed for weight context in downstream deterministic math

Required outputs:

- `exercise_type`
  - `running`
  - `walking`
  - `cycling`
  - `strength_training`
  - `other`
- `duration_minutes`
- `estimated_kcal_burned`
- `calculation_basis`
  - `met_formula`
  - `user_asserted`
- `occurred_at_interpretation`
- `exercise_action`
  - `create_exercise`
  - `cannot_extract`

### 4.4 Deterministic Downstream Writeback

After a valid `ExerciseEvent` write, the application layer deterministically:

1. persists the canonical exercise event
2. writes a `LedgerEntry(exercise_bonus)` when applicable
3. updates `DayBudgetLedger.exercise_bonus_total`
4. recomputes effective budget and remaining kcal
5. refreshes `CurrentBudgetView`

If calorie burn is not user-asserted, MET estimation remains deterministic.

### 4.5 Node 2: `exercise_response`

Goal:

- confirm the recorded event
- optionally explain the budget impact

`decision_mode: llm`
`decision_reason: response wording only`
`logical_model_role: response_writer_model`

Required outputs:

- `reply_text`
- optional `ui_hints`

### 4.6 Layer B Truth

- `exercise_action`
  - `create_exercise`
  - `cannot_extract`

---

## 5. Answer Path Boundary

Pure answer behavior should not fake a new workflow.

Examples:

- `??券??之璁?撠
- `隞予????憭??梢?`
- `??券??拙?撠????

These should default to:

- `workflow_family = general_chat`
- `disposition = answer_only`

using the existing read models and canonical state.

---

## 6. Relationship To Other Specs

- `L0B` owns onboarding/bootstrap truth
- `L3.3A` owns calibration model posture
- `L3.3B` owns calibration proposal and plan-changing negotiation
- `L2` owns canonical object dictionaries and ledger fields

Formal rule:

- `body_observation` and `exercise` may trigger downstream deterministic recompute
- they do not own long-horizon plan changes
- any proposal to change plan/budget belongs to `calibration`
