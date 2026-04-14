# L0 Product Capability Spec

## Summary

This product is not a plain calorie calculator.

It is a chat-first fat-loss agent product centered on the `meal_thread` as the primary product object.

The product core is:

- use the lowest-friction logging possible
- keep calibrating the user's operating total daily energy expenditure
- use recommendations and reminders that make adherence easier
- help the user sustain a real calorie deficit over time

The product should help the user:

- record and revise meals through conversation
- stay aware of the current daily budget
- calibrate estimated intake against real body-weight change
- receive proactive recommendations, reminders, and rescue proposals when appropriate

This layer defines product capabilities, shared objects, and high-level product states only.

This layer does not define:

- LLM pass count or model allocation
- prompt design
- tool-calling mechanics
- framework choice
- database schema details

---

## Product Interaction Model

### Chat-First

Chat is the primary surface for:

- meal logging
- clarification
- corrections
- negotiation
- proposal acceptance or rejection

Chat is the **sole primary interaction surface** for all agent-driven flows including rescue, calibration proposals, and recommendations. All agent reasoning, proposal negotiation, and user decisions happen in chat first.

### UI as Dashboard and Confirm Surface

The LIFF / dashboard surface exists to:

- visualize current state
- expose history and trends
- support confirmation and quick actions
- make active proposals visible and controllable

The UI is not the sole source of truth and is not the primary reasoning surface.

For rescue specifically: UI acts as a proposal inbox mirror only. It displays the current open rescue proposal but does not host the primary rescue negotiation flow.

### Cross-Surface Sync Rule

Chat, UI, and smart-chip interactions must operate on the same underlying product objects.

Any confirmation, correction, or commit performed in one surface must be reflected in the others.

---

## Core Product Objects

### 1. `meal_thread`

The central product object.

A `meal_thread` represents the full lifecycle of one meal-like eating event from first mention to clarification, correction, and final commit.

It should capture:

- original user input
- follow-up turns related to the same meal
- current interpreted meal state
- food items or meal components contained inside the same event
- unresolved questions
- finalized nutrition record
- correction lineage and version relationship

Product rules:

- intake, clarification, correction, and refinement should first be interpreted as updates to a `meal_thread`
- a `meal_thread` is an eating event that may contain multiple food items; it is not equivalent to one message or one single food item
- when the system cannot safely decide whether the user is still discussing the same meal, thread ambiguity may remain open temporarily
- a `meal_thread` may be created in chat and later reviewed, corrected, or confirmed in the UI

### 2. `day_budget_ledger`

Represents the effective budget for a given day and the history of how it changed.

It should capture:

- base daily budget
- consumed amount
- remaining amount
- budget adjustments
- temporary overlays
- committed changes and their source

Product rules:

- the daily budget is dynamic rather than fixed
- the effective budget may be influenced by logged meals, rescue plans, and body calibration
- all budget changes must be traceable to a source object or confirmed proposal

### 3. `body_plan`

Represents the user's current body-goal and calibration state.

It should capture:

- body-weight observations
- body trend interpretation
- current goal direction
- estimated TDEE or equivalent calibration state
- intake estimation bias assumptions where applicable

Product rules:

- body-weight entries are observations, not immediate plan rewrites
- body calibration may influence recommendations and budgets
- meaningful plan changes should become active through a confirmation flow rather than silent overwrite

### 4. `proposal`

Represents an agent-created candidate action that has not yet become committed state.

Examples:

- spreading an overshoot over the next three days
- adjusting the daily budget after body calibration
- recommending a next meal strategy
- prompting the user to confirm a likely missing meal

Product rules:

- proposals are separate from committed state
- proposals may be discussed in chat and confirmed in chat, UI, or smart chips
- only accepted proposals may become committed state

### 5. `proactive_trigger`

Represents why the system initiated contact and how that outreach is controlled.

It should capture:

- trigger type
- trigger time
- target object
- cooldown or suppression state
- whether a proposal was already created
- whether the user acknowledged or dismissed it

Product rules:

- proactive behavior is a product capability, not a standalone workflow
- proactive behavior may target `meal_thread`, `day_budget_ledger`, or `body_plan`
- proactive behavior must be explainable and suppressible

---

## Capability Domains

### A. Meal Thread Resolution

Goal: turn food-related user input into an interpretable, revisable, and eventually committed `meal_thread`.

Includes:

- new meal logging
- multi-turn clarification
- same-meal refinement
- same-meal correction
- historical recall and correction
- final commit and synchronization to dashboard views

Product requirements:

- the system may produce provisional understanding before all details are settled
- a single event may contain multiple food items or components
- blocking ambiguity should trigger natural follow-up
- breakfast / lunch / dinner are view-layer labels rather than primary data-model slots
- corrections such as "I only ate half of that rice" should preferentially update the existing meal thread rather than create a new meal
- once the meal is committed, the dashboard must reflect the latest committed state

### B. Contextual Recommendation

Goal: help the user decide what to eat next in a way that is consistent with current constraints and goals.

Includes:

- recommendation based on remaining budget and already logged meals
- ranking based on safe defaults, favorite stores, and preferred patterns
- contextual filtering such as high-protein, light, or recovery-oriented choices
- exposing explicit intake actions such as `幫我記這個 / 我吃這個 / 加到今天`, which route the selected candidate into intake flow rather than creating recommendation state

Product requirements:

- recommendation is not an isolated search feature; it consumes `meal_thread`, `day_budget_ledger`, and `body_plan`
- recommendation should be allowed to learn from historical `MealItem` classification signals such as drink preference, staple preference, and recurring item patterns
- chat should usually surface a small number of high-confidence suggestions
- UI should support broader browsing and filtering
- recommendations must align with the currently effective budget and plan state
- ordinary next-meal suggestions are `recommendation`; only plan-changing or budget-affecting suggestions should become `proposal`

### C. Body Calibration

Goal: align estimated intake with observed body-weight change over time.

Includes:

- recording body-weight observations
- aggregating short- and medium-term trends
- estimating calibration state
- generating TDEE or budget-adjustment proposals
- feeding calibration effects back into recommendations and budgets

Product requirements:

- body-weight may be entered through chat or UI
- trend analysis is primarily background product behavior
- calibration outputs should generally appear first as proposals
- once confirmed, calibration changes must affect both dashboard state and future recommendations

### D. Rescue and Coaching

Goal: help the user recover from overshoot or drift without turning the product into a punishment system.

Includes:

- detecting likely overshoot or high-risk days
- generating short-horizon rescue proposals
- negotiating rescue options in chat
- applying confirmed short-term budget overlays
- providing actionable next steps instead of merely reporting failure

Product requirements:

- rescue is future-oriented rather than blame-oriented
- rescue should default to a proposal-first model
- confirmation may happen in chat, UI, or smart chips
- accepted rescue plans must affect future budget views and downstream recommendations
- rescue is delivered as an independent chat message, never embedded inside an intake reply
- rescue interaction in chat is a single-spread model: the system proposes a number of days to spread the recovery, and the user can adjust intensity (shorter/more aggressive or longer/gentler)
- UI acts as a proposal inbox mirror for rescue; it does not host the primary rescue interaction

---

## High-Level Product States

These are product-semantic states, not low-level runtime states.

### `meal_thread` states

- `open`
- `needs_clarification`
- `provisional`
- `committed`
- `corrected`
- `superseded`

### `proposal` states

- `drafted`
- `presented`
- `negotiating`
- `accepted`
- `rejected`
- `expired`

### `proactive_trigger` states

- `eligible`
- `suppressed`
- `fired`
- `acknowledged`
- `dismissed`

---

## Core Product Rules

- `meal_thread` is the primary product object
- all capability domains must resolve to shared product objects rather than parallel truths
- chat is the primary negotiation surface
- UI is the dashboard, review, and confirm surface
- the agent may proactively create proposals, but proposals and committed state must remain distinct
- proactive behavior must support suppression and cooldown
- body calibration may influence recommendations and budgets, but committed plan changes must remain confirmable
- budget, calibration, and rescue changes must remain attributable and traceable

---

## Explicitly Deferred To Later Specs

The following are intentionally out of scope for L0 and should be defined in later architecture specs:

- whether the runtime remains exactly four passes
- exact pass responsibilities and handoff contracts
- model selection per pass
- deterministic gate placement
- retrieval and memory architecture details
- data schema and storage design
- proactive trigger policy and frequency policy
- framework choice such as custom harness, OpenAI SDK, OpenClaw, or hybrid reuse

---

## Assumptions

- the product remains chat-first
- UI acts primarily as a dashboard and confirmation layer
- `meal_thread` is the primary anchor object for future architecture work
- budget, calibration, and rescue should follow a `proposal -> confirm -> commit` pattern
- confirmation may happen in chat, UI, or smart chips, and all surfaces must stay synchronized
- proactive behavior should be moderately autonomous rather than fully automatic
