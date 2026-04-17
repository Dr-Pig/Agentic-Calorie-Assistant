# L0B Budget / Ledger Sync Happy-Path Spec

## 1. Purpose

This document defines the v1 canonical happy path for:

1. user profile bootstrap
2. deterministic daily-calorie target computation
3. today budget display
4. two-meal intake accumulation
5. ledger sync
6. remaining-budget query in chat
7. UI/chat shared truth

This is not a new routing spec and it does not replace recommendation or calibration specs.
It is a focused companion spec for the shared budget trunk used by:

- `BodyProfile`
- `BodyPlan`
- `DayBudgetLedger`
- `MealThread`
- `CurrentBudgetView`
- `ActiveBodyPlanView`

The purpose of this document is to lock the v1 shared budget truth.

---

## 2. Shared Truth Rule

v1 system behavior is:

- daily budget is deterministic truth
- intake commits write through canonical ledger state
- UI reads that shared budget state
- chat reads that same shared budget state
- UI and chat must agree because they share read models

The v1 shared truth surfaces are:

- `BodyPlan.daily_budget_kcal`
- `DayBudgetLedger`
- `CurrentBudgetView`
- `ActiveBodyPlanView`

---

## 3. Phase 1: Profile / Budget Bootstrap

### 3.1 Canonical Objects

Bootstrap must create or update:

- active `BodyProfile`
- active `BodyPlan`
- today's `DayBudgetLedger`

`BodyProfile` fields:

- `sex`
- `age_years`
- `height_cm`
- `current_weight_kg`
- `activity_level`
- `goal_type`
- `target_weight_kg`
- `weekly_target_rate_kg`
- `timezone`

`BodyPlan` fields used by this happy path:

- `estimated_tdee`
- `daily_budget_kcal`
- `safety_floor_kcal`
- `target_pace_kg_per_week`
- `goal_type` via metadata/read model
- `plan_source = onboarding_bootstrap`

### 3.2 Deterministic Budget Rule

Bootstrap must:

- compute `recommended_target_kcal` from a deterministic formula
- never let the LLM free-generate the daily target
- treat `daily_budget_kcal` as the operational bootstrap target
- seed today's `DayBudgetLedger.budget_kcal` from active `BodyPlan.daily_budget_kcal`

### 3.3 UI / Chat Boundary

UI onboarding may collect the inputs.
Chat bootstrap may collect the inputs.
Both must converge into the same deterministic budget pipeline.

Therefore:

- UI must not own target truth
- chat must not own target truth

---

## 4. Phase 2: Intake -> Ledger Sync

Use the canonical intake 4-pass:

1. `task_meal_link_pass`
2. `decision_pass`
3. `nutrition_resolution_pass`
4. `final_response_pass`

The additional writeback contract is:

- intake commit writes through canonical persistence into `DayBudgetLedger`
- budget seed should inherit from active `BodyPlan.daily_budget_kcal`
- committed meals update ledger, not just chat output

v1 `CurrentBudgetView` is the shared read model for Today UI and budget-aware chat.
It must surface at least:

- `budget_kcal`
- `consumed_kcal`
- `remaining_kcal`
- `active_meal_count`
- active meal list

---

## 5. Phase 3: Remaining Calories Query

The question "how many calories do I have left?" is treated in v1 as:

- `workflow_family = general_chat`
- `disposition = answer_only`

The query source of truth is not raw history.
It must read:

- `CurrentBudgetView`
- `ActiveBodyPlanView`

If there is no active body plan, return:

- onboarding required / budget unavailable

If there is an active body plan and today's ledger exists, return:

- `daily_target_kcal`
- `consumed_kcal`
- `remaining_kcal`
- `meal_count`

---

## 6. Shared Read Model Rule

v1 read-model rule:

- `CurrentBudgetView` is the shared today budget summary read model
- `ActiveBodyPlanView` is the shared active target-truth read model

Today UI must show:

- target
- consumed
- remaining
- meal count / meals list

Budget-aware chat must be able to answer:

- what is today's target
- how much has been eaten
- how much remains

Those answers must use the same numbers.

---

## 7. Validation Path

The canonical happy path is:

1. bootstrap body profile
2. seed active body plan
3. seed today's ledger
4. intake meal one
5. intake meal two
6. Today UI reflects cumulative numbers
7. general-chat query asks remaining budget
8. chat answer matches UI exactly

Edge checks:

- if onboarding is missing, remaining-budget query returns onboarding-required
- if active body plan exists, intake must use active budget when writing ledger
- correction / turn-2 completion must continue to update today summary from active canonical meal versions

---

## 8. Upstream Truth Alignment

This document is aligned with:

- `L0A_ONBOARDING_FLOW_SPEC.md`
- `L2_DATA_STATE_SPEC.md`
- `L3_1_INTAKE_RUNTIME_PASS_CONTRACT_SPEC.md`
- `WORKFLOW_DEPENDENCY_CONTEXT_ORDERING_SPEC.md`

Recommendation, calibration, and rescue may later depend on this budget truth,
but they are not allowed to replace the shared truth surface or re-compute today math on their own.
