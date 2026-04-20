# L3.6 Proactive Scheduler Spec

## 1. Purpose

This spec defines the canonical runtime contract for `ProactiveScheduler`.

It answers:

- which proactive trigger families exist in v1
- which trigger checks are deterministic
- when LLM judgment is required before delivery
- how suppression, cooldown, quiet-hours, and onboarding gating work
- how proactive dispatch hands off into the downstream workflow family

This file does not redefine:

- the internal pass graph of downstream workflows
- prompt wording
- UI-specific rendering

---

## 2. Canonical Layering

`ProactiveScheduler` is not a blind heartbeat loop.

The canonical layering is:

1. deterministic trigger gate
2. LLM contextual send / skip decision
3. chat-first delivery

### 2.1 Layer 1: Deterministic Trigger Gate

The deterministic gate owns:

- schedule checks
- event-driven trigger checks
- suppression / cooldown
- quiet hours
- onboarding gate
- coarse eligibility

No LLM should run before this layer passes.

### 2.2 Layer 2: LLM Contextual Dispatch

After the deterministic gate passes, the LLM decides:

- whether the system should actually send now
- whether it should skip
- what the dispatch reason or `skip_reason` is
- which downstream workflow family surface should receive the delivery

This is required because proactive behavior is contextual.

The system must not send every trigger mechanically just because the deterministic gate passed.

### 2.3 Layer 3: Chat-First Delivery

Delivery should be chat-first by default.

Formal rule:

- proactive does not become a standalone primary product surface
- proactive dispatch routes into the downstream workflow family
- proactive does not perform high-impact mutation inside the scheduler layer itself

---

## 3. Trigger Families

v1 trigger families:

- `meal_reminder`
- `weight_reminder`
- `rescue_nudge`
- `recommendation_nudge_meal_time`
- `recommendation_nudge_nearby`
- `swap_suggestion`
- `weekly_insight`
- `calibration_nudge`

### 3.1 Workflow Ownership

| Trigger ID | Trigger Source | Downstream Workflow |
| --- | --- | --- |
| `meal_reminder` | scheduled | `general_chat` |
| `weight_reminder` | scheduled | `general_chat` |
| `rescue_nudge` | event-driven | `rescue` |
| `recommendation_nudge_meal_time` | scheduled | `recommendation` |
| `recommendation_nudge_nearby` | event-driven | `recommendation` |
| `swap_suggestion` | event-driven | `recommendation` |
| `weekly_insight` | scheduled | weekly insight reporting surface |
| `calibration_nudge` | event-driven | `calibration` |

---

## 4. Deterministic Suppression Gate

Every proactive trigger must pass all relevant deterministic gates before any LLM call.

Required checks:

1. trigger-specific cooldown
2. quiet-hours suppression
3. recent-send cap
4. onboarding gate
5. trigger-family-specific minimum evidence

### 4.1 Cooldown

The same trigger family must not fire again inside its configured cooldown window.

### 4.2 Quiet Hours

Default quiet hours:

- `22:00` to `08:00` local time

During quiet hours:

- scheduled nudges should skip
- event-driven nudges should skip unless later specs explicitly define an exception

### 4.3 Recent-Send Cap

Default recent-send cap:

- do not send more than `2` proactive messages within the recent guard window

### 4.4 Onboarding Gate

If the trigger depends on budget, plan, or learned preferences and the user does not yet have enough onboarding state, the trigger should not dispatch.

Examples:

- recommendation nudges should not send without an active body plan or adequate candidate context
- rescue nudges should not send without valid current-budget truth

---

## 5. Trigger-Specific Rules

### 5.1 `meal_reminder`

Type:

- scheduled

Deterministic gate:

- the current local time is inside a meal-time window
- there is no recent committed meal for that target window
- cooldown passed

LLM dispatch decision:

- decide whether the reminder is still useful now
- decide whether to keep it simple versus contextual

Downstream posture:

- `general_chat + answer_only` reminder surface unless the user replies and opens a formal workflow

### 5.2 `weight_reminder`

Type:

- scheduled

Deterministic gate:

- the user has not logged a recent weight observation
- cooldown passed

LLM dispatch decision:

- decide whether to send a gentle reminder now
- produce a low-friction wording posture

Downstream posture:

- `general_chat` reminder surface, with possible handoff into `body_observation`

### 5.3 `rescue_nudge`

Type:

- event-driven

Deterministic gate:

- current budget indicates overshoot / rescue-worthy posture
- rescue cooldown passed
- the triggering event is not just a still-open intake event being answered inline

Formal boundary:

- rescue proactive messages must be independent messages
- intake reply must not inline rescue content

LLM dispatch decision:

- decide whether the user should be nudged now or whether the system should skip
- produce `skip_reason` if suppressed after contextual review

Downstream posture:

- hand off into `rescue`

### 5.4 `recommendation_nudge_meal_time`

Type:

- scheduled

Deterministic gate:

- inside a meal-time window
- no recent meal logged for that window
- enough recommendation prerequisites exist
- budget posture is still eligible

LLM dispatch decision:

- decide whether a recommendation nudge is useful now
- decide how contextual the nudge should be

Downstream posture:

- hand off into `recommendation`

### 5.5 `recommendation_nudge_nearby`

Type:

- event-driven

Deterministic gate:

- location context is available
- at least one nearby candidate cluster passes coarse similarity thresholds
- cooldown passed
- budget posture is still eligible

LLM dispatch decision:

- decide whether the nearby signal is actually useful
- produce send/skip and contextual framing

Downstream posture:

- hand off into `recommendation`

### 5.6 `swap_suggestion`

Type:

- event-driven, typically post-commit

Deterministic gate:

- a just-committed item has a meaningful lower-calorie or safer swap cluster
- the delta exceeds the configured significance threshold
- cooldown passed

LLM dispatch decision:

- decide whether the swap suggestion would feel useful rather than nagging

Downstream posture:

- hand off into `recommendation`

### 5.7 `weekly_insight`

Type:

- scheduled

Deterministic gate:

- minimum logging coverage threshold is met
- enough weekly data exists

LLM dispatch decision:

- decide whether the insight should be surfaced now
- decide the explanatory framing

Downstream posture:

- weekly insight reporting surface, chat-first

### 5.8 `calibration_nudge`

Type:

- event-driven

Deterministic gate:

- `calibration_model` has produced a candidate posture
- proposal eligibility is true
- cooldown passed

LLM dispatch decision:

- decide whether to surface the calibration proposal now
- produce skip reason if the proposal should wait

Downstream posture:

- hand off into `calibration`

---

## 6. Scheduled Check Windows

v1 default schedule windows:

- `07:00` breakfast / meal reminder check
- `08:30` weight reminder check
- `11:30` lunch / meal reminder check
- `17:00` recommendation meal-time nudge check
- `18:30` dinner / meal reminder check
- `23:00` nightly consolidation support check
- weekly `08:00` insight check

Event-driven triggers run on the corresponding state updates instead of fixed clock windows.

---

## 7. LLM Boundary Rules

### 7.1 Deterministic First

The LLM must not decide:

- whether cooldown passed
- whether quiet hours are active
- whether onboarding is complete enough
- whether the recent-send cap has already been exceeded

### 7.2 LLM Owns Contextual Send / Skip

The LLM should decide:

- whether sending now is actually helpful
- whether the message should wait
- whether this trigger would feel noisy or redundant
- what `skip_reason` best describes the contextual no-send decision

### 7.3 Required Trace Fields

Each proactive evaluation should produce trace fields for:

- `trigger_id`
- deterministic gate result
- `send_or_skip`
- `skip_reason` when skipped after contextual review
- downstream workflow family

---

## 8. Relationship To Other Specs

- recommendation nudges hand off into `L3.2`
- rescue nudges hand off into `L3.4`
- calibration nudges hand off into `L3.3B`
- meal and weight reminders default to `general_chat` unless the user opens a formal workflow

Formal rule:

- proactive may open a downstream workflow surface
- proactive must not perform hidden high-impact mutation at scheduler level

---

## 9. v1 Default Decisions

1. proactive is trigger-based, not blind heartbeat chat spam
2. every trigger must pass deterministic suppression before LLM review
3. quiet hours default to `22:00-08:00`
4. recommendation nudges remain non-mutating
5. rescue nudges are separate messages and never inline after intake
6. LLM contextual dispatch must be able to output `skip_reason`
