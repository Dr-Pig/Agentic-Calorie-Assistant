# Founder-Fit Golden Lane Set V1

## Purpose

This file replaces the previous mixed replay draft with a cleaner review set.

For this review round, the goal is not full multi-turn coverage.

The goal is to define a **Golden Standard** for the first-turn lane decision only:

- `ask_followup_only`
- `estimate_ok`

This set is intentionally designed to avoid gray-zone cases.

## Golden Standard Rule

### A. `ask_followup_only`

Use this lane only when the user input is too underspecified to produce a meaningful calorie estimate yet.

Typical properties:

- food composition is unknown
- shared meal / banquet / family-style meal
- only the meal format is known, not the actual eaten items

### B. `estimate_ok`

Use this lane when the food type is already specific enough for a reasonable estimate or interval.

Typical properties:

- food class is clear enough to anchor an estimate
- remaining variation changes quality, but does not block the estimate itself
- follow-up may improve precision, but is not required for a useful answer

## What Is Explicitly Excluded From Golden

These do **not** belong in the Golden Standard main set for this round:

- cases where both `ask_followup_only` and `estimate_ok` are defensible
- cases that mainly test state attach / switch behavior
- cases that are mainly implementation-boundary tests rather than first-turn lane judgment

Those go into a later borderline set.

## Review Instructions

For each case, only review these three things:

1. Is the lane assignment right
2. Is the example realistic enough for your actual usage
3. Does this belong in Golden, or should it move to borderline

You do **not** need to review exact kcal yet.

## Golden Set V1

Recommended size: **10 cases**

- `5` ask-first cases
- `5` estimate-ok cases

## A. Ask First, Do Not Estimate Yet

### `gs_001`

- `input`: `我吃 poke`
- `expected_lane`: `ask_followup_only`
- `expected_behavior`: do not estimate yet; ask what was actually in the bowl
- `why`: only the format is known; protein, base, sauce, and toppings are all unresolved
- `review_question`: does this feel unambiguously too vague to estimate first

### `gs_002`

- `input`: `我晚餐吃滷味`
- `expected_lane`: `ask_followup_only`
- `expected_behavior`: do not estimate yet; ask which ingredients were included
- `why`: ingredient spread is too large for a useful first estimate
- `review_question`: should this always be ask-first in your product

### `gs_003`

- `input`: `我剛剛吃合菜`
- `expected_lane`: `ask_followup_only`
- `expected_behavior`: do not estimate yet; ask which dishes and how much the user personally ate
- `why`: shared-meal intake plus personal share is unresolved
- `review_question`: does this clearly belong in the no-estimate-first lane

### `gs_004`

- `input`: `我剛跟家裡吃`
- `expected_lane`: `ask_followup_only`
- `expected_behavior`: do not estimate yet; ask what was eaten
- `why`: meal content is almost entirely unknown
- `review_question`: does this feel like a clean Golden ask-first case

### `gs_005`

- `input`: `我中午吃喜酒`
- `expected_lane`: `ask_followup_only`
- `expected_behavior`: do not estimate yet; ask what dishes were eaten and roughly how much
- `why`: banquet-style intake is highly uncertain and typically shared
- `review_question`: should this stay Golden or move to a later banquet-specific pack

## B. Estimate First Is OK

### `gs_006`

- `input`: `我剛剛喝珍珠奶茶`
- `expected_lane`: `estimate_ok`
- `expected_behavior`: can estimate immediately; asking size/sugar/ice is optional refinement, not mandatory
- `why`: the drink class is already clear enough to produce a reasonable interval
- `review_question`: do you agree this should not be blocking-clarify

### `gs_007`

- `input`: `我吃炸醬麵`
- `expected_lane`: `estimate_ok`
- `expected_behavior`: can estimate immediately; portion/style follow-up is optional refinement
- `why`: dish class is clear enough for a baseline estimate
- `review_question`: does this belong in Golden estimate-ok rather than borderline

### `gs_008`

- `input`: `我吃牛丼`
- `expected_lane`: `estimate_ok`
- `expected_behavior`: can estimate immediately; bowl size follow-up is optional refinement
- `why`: the meal type is narrow enough for a useful first estimate
- `review_question`: does this still feel clean enough for Golden

### `gs_009`

- `input`: `我吃雞腿便當`
- `expected_lane`: `estimate_ok`
- `expected_behavior`: can estimate immediately; rice amount or side dishes are optional refinements
- `why`: once the main dish is named, the form is much more stable than a generic `便當`
- `review_question`: do you want `雞腿便當` to stay Golden while bare `便當` moves to borderline

### `gs_010`

- `input`: `我中午吃炒麵跟魚`
- `expected_lane`: `estimate_ok`
- `expected_behavior`: can estimate a range immediately; cooking style or portion follow-up is optional refinement
- `why`: the core foods are already named, even though detail can still narrow the range
- `review_question`: is this still Gold, or is it already too close to gray-zone

## Borderline Set, Not Golden

These should be kept out of the Golden main set for now:

- `我吃便當`
- `我吃拉麵`
- `我喝手搖杯`
- `我吃早餐店`
- `我吃自助餐`

Reason:

- the right lane depends more on strategy and product posture
- these are not clean referee cases for the first Golden set

## Recommended Review Output

Reply in this format:

- `keep`: `gs_001`, `gs_002`, `gs_006`, `gs_009`
- `revise`: `gs_010` wording feels too gray-zone
- `move_to_borderline`: `gs_007`
- `add_more_like_this`: `gs_003`, `gs_006`

## Immediate Recommendation

For the next step:

1. review these `10` Golden cases
2. freeze the ones you accept
3. move disputed ones to borderline
4. only then ask ChatGPT to generate more variants around the accepted lane shapes

## Accepted Golden V1

Review result on `2026-04-13`:

- all `10` cases are accepted as the current Golden V1 set

Accepted case IDs:

- `gs_001`
- `gs_002`
- `gs_003`
- `gs_004`
- `gs_005`
- `gs_006`
- `gs_007`
- `gs_008`
- `gs_009`
- `gs_010`

Current rule:

- these `10` cases are now the founder-fit first-turn Golden Standard for lane judgment
- later variants generated by ChatGPT or other tooling must be treated as expansions around this accepted set, not as replacements for it

## Golden V1 Amendment — 2026-04-13

- `gs_001` (`poke`) is removed from the Golden main set
- reason:
  - it is a gray-zone strategy case
  - both `ask_followup_only` and `estimate_ok` can be product-valid depending on posture
  - it is not a clean first-turn referee case

Current Golden main set is now `9` cases:

- `gs_002`
- `gs_003`
- `gs_004`
- `gs_005`
- `gs_006`
- `gs_007`
- `gs_008`
- `gs_009`
- `gs_010`

`gs_001` remains useful as a borderline / gray-zone review case, but it no longer blocks Golden lane evaluation.
