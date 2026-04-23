# Bundle V2 Eval Stability Analysis

Date: `2026-04-21`  
Scope: `Bundle 1` and `Bundle 2` live eval artifacts under [runtime/evals/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals)

## Summary

The current issue is not "we have not forced all 10 Bundle 2 cases to pass yet."  
The real issue is that `Bundle 2` still contains a small number of **state-effect unstable lanes**.

The evidence supports this split:

- `Bundle 1` is currently stable enough for its defined gate.
- `Bundle 2` is **partially converged**:
  - many cases are now consistently passing
  - some earlier failures were pure infrastructure / harness problems
  - the remaining important failures are not just harmless LLM fuzziness
  - they are **workflow-effect instability**

The main conclusion is:

> Bundle 2 instability is not primarily caused by "LLMs are naturally fuzzy."  
> It is primarily caused by incomplete runtime measures around **commit threshold** and **state mutation preconditions**.

That means the remaining failures should be treated as **fixable contract gaps**, not accepted product variability.

## Dataset

Artifacts reviewed:

- `Bundle 1`
  - [bundle1_live_eval_20260421_023953.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle1_live/bundle1_live_eval_20260421_023953.json)
- `Bundle 2`
  - full-suite reports and single-case probes under [runtime/evals/v2_bundle2_live/](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live)

Observed counts:

- `Bundle 1` full-suite reports: `1`
- `Bundle 2` full-suite reports (`total_cases = 10`): `14`
- `Bundle 2` single-case probe reports (`total_cases = 1`): `37`

Important reference reports:

- first strong near-pass full run:
  - [bundle2_live_eval_20260421_164621.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live/bundle2_live_eval_20260421_164621.json)
- repeated near-pass full runs:
  - [bundle2_live_eval_20260421_171855.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live/bundle2_live_eval_20260421_171855.json)
  - [bundle2_live_eval_20260421_175021.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live/bundle2_live_eval_20260421_175021.json)
- latest full run:
  - [bundle2_live_eval_20260421_180911.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live/bundle2_live_eval_20260421_180911.json)

## Method

This analysis distinguishes three failure families:

1. `Infrastructure / harness failure`
   - connection refused
   - remote host closed connection
   - response-shape error such as missing `audit`
   - runner-level failure before product semantics can be judged

2. `Acceptable semantic variability`
   - bounded wording differences
   - slightly different range center while preserving the same workflow effect
   - LLM uncertainty expression that does not change:
     - `commit vs no_commit`
     - `followup vs no followup`
     - `ledger updated vs not updated`

3. `Unacceptable workflow-effect instability`
   - same semantic case sometimes commits and sometimes does not
   - same correction sometimes updates canonical state and sometimes remains draft
   - same overshoot case sometimes mirrors into `today`, sometimes does not
   - state mutation preconditions are not reliably enforced

The key evaluation principle is:

> If variability changes the workflow effect or canonical state mutation outcome, it is not acceptable fuzziness.

## Bundle 1

`Bundle 1` currently shows a stable pass result for its defined gate:

- [bundle1_live_eval_20260421_023953.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle1_live/bundle1_live_eval_20260421_023953.json)
  - `9 / 9 passed`

There is no evidence in the reviewed artifacts that `Bundle 1` is currently suffering from the same kind of live instability as `Bundle 2`.

## Bundle 2 Historical Trend

### Phase A: early instability

Early full-suite Bundle 2 runs were dominated by broad failure:

- [bundle2_live_eval_20260421_033218.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live/bundle2_live_eval_20260421_033218.json)
  - `3 / 10 passed`
- [bundle2_live_eval_20260421_073303.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live/bundle2_live_eval_20260421_073303.json)
  - `0 / 10 passed`

At this stage, failures were not useful signals of product semantics. They were mixed with:

- server availability failures
- runner failures
- response-shape failures
- missing trace / missing `audit`

Conclusion:

- these runs should **not** be used to judge whether Bundle 2 workflow design is sound
- they are mostly pre-stability infrastructure noise

### Phase B: contract convergence

Later full-suite runs became much more meaningful:

- [bundle2_live_eval_20260421_164621.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live/bundle2_live_eval_20260421_164621.json)
  - `9 / 10 passed`
  - only `K-002` failed
- [bundle2_live_eval_20260421_171855.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live/bundle2_live_eval_20260421_171855.json)
  - `9 / 10 passed`
  - only `K-002` failed
- [bundle2_live_eval_20260421_175021.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live/bundle2_live_eval_20260421_175021.json)
  - `9 / 10 passed`
  - only `K-002` failed

Conclusion:

- Bundle 2 is not globally broken
- most of the architecture is already functioning
- the remaining problems are concentrated in a few unstable lanes

### Phase C: latest full run

Latest full-suite run:

- [bundle2_live_eval_20260421_180911.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live/bundle2_live_eval_20260421_180911.json)
  - `8 / 10 passed`
  - failed:
    - `C-001`
    - `K-002`
  - `bundle_gate = fail`

This latest report matters because it shows the instability is still present even after many runtime improvements.

## Case Stability Summary

Across the reviewed Bundle 2 artifacts:

- `C-001`
  - pass: `13`
  - fail: `11`
- `C-002`
  - pass: `10`
  - fail: `8`
- `D-001`
  - pass: `13`
  - fail: `6`
- `D-002`
  - pass: `13`
  - fail: `5`
- `E-001`
  - pass: `9`
  - fail: `15`
- `E-002`
  - pass: `6`
  - fail: `10`
- `E-003`
  - pass: `13`
  - fail: `4`
- `K-001`
  - pass: `10`
  - fail: `8`
- `K-002`
  - pass: `4`
  - fail: `13`
- `K-003`
  - pass: `5`
  - fail: `11`

These raw counts include early infrastructure noise, so they should not be interpreted naively.  
The more useful signal is which cases remain unstable **after** the runner and trace contracts were hardened.

## What Is Acceptable Instability

The following variability is acceptable for this product:

- slight wording differences in followup prompts
- slightly different estimate center within the same approved range
- natural language phrasing differences in correction acknowledgement
- exact macro omission when `show_macro == false`

Why this is acceptable:

- the workflow effect is unchanged
- canonical state mutation is unchanged
- `today` / trace / chat still agree

This is LLM ambiguity in a form the product can tolerate.

## What Is Not Acceptable Instability

The following is **not** acceptable:

- `followup resolution` sometimes commits and sometimes does not
- `setup meal` for a correction journey sometimes commits and sometimes stays draft
- `item removal correction` sometimes updates the canonical meal and sometimes does not
- overshoot note sometimes reaches `today` and sometimes not
- response shape sometimes omits mandatory audit fields

Why this is not acceptable:

- it changes workflow ownership and state effect
- it breaks eval reproducibility
- it makes external audit impossible

This is not "normal LLM fuzziness."  
This is incomplete runtime contract enforcement.

## Main Findings

### 1. The remaining instability is concentrated in commit-threshold lanes

The two clearest examples are:

- `C-001`
  - pearl milk tea followup resolution
- `K-002`
  - item removal correction

In both cases, the unstable question is not:
- "which wording did the LLM choose?"

It is:
- "did the system cross the line into canonical commit or not?"

That means the weak point is the **commit threshold**, not just the prompt.

### 2. Bundle 2 failures are not primarily caused by the inherent nature of workflow ambiguity

It would be reasonable to accept instability if the only difference were:

- different plausible kcal range wording
- different but compatible uncertainty phrasing

But the observed failures include:

- `turn2_commit = false`
- `setup_committed = false`
- `consumed_changed = false`
- `today_has_meal = false`

These are not harmless surface differences.  
They show the system has not fully stabilized the workflow effect.

### 3. Earlier runs were heavily contaminated by infrastructure and runner problems

Examples seen in historical failures:

- `http_ok = false`
- `runner_ok = false`
- `error:'audit'`
- connection refused
- remote host closed connection

These are important, but they should be separated from semantic instability.

The current codebase has already improved this area:

- trace artifacts exist
- text integrity checks exist
- response-shape validation in the runner has been hardened

So future failures are more meaningful than the earliest ones.

### 4. `K-002` is the clearest remaining unstable case family

`K-002` has the worst persistent signal:

- pass: `4`
- fail: `13`

Observed failure shapes include:

- setup meal does not commit
- correction target exists but no canonical base meal is available
- consumed kcal does not change
- occasional response-shape / runner issues in earlier runs

Interpretation:

- this is not just a bad example sentence
- this is a correction-lane contract gap
- specifically:
  - setup precondition stability
  - item removal application
  - canonical writeback consistency

### 5. `C-001` is a second important unstable lane

Latest full run shows:

- turn 1 correct:
  - range given
  - followup asked
  - no commit
- turn 2 incorrect:
  - no commit
  - `today` unchanged

Interpretation:

- the system can correctly identify `estimate_with_followup`
- but it still does not reliably promote a completed followup answer into commit

That is again a commit-threshold problem.

## Root Cause Judgment

The instability is better explained by **incomplete measures** than by the irreducible nature of the workflow.

### Incomplete measures

Most likely incomplete measures are:

- insufficient deterministic promotion rules from followup completion to commit
- insufficient deterministic preconditions for correction setup
- insufficient deterministic protection around item-removal correction application
- remaining live-response shape validation gaps

### Workflow nature

The workflow itself does contain ambiguity:

- drink customization
- partial correction language
- meal composition uncertainty

But the current failures are not mainly about uncertainty expression.  
They are about whether the runtime produces the same state effect for the same journey.

So the correct diagnosis is:

> The remaining instability is mostly a runtime contract problem layered on top of a legitimately fuzzy workflow, not a proof that the workflow itself is impossible to stabilize.

## Practical Acceptance Boundary

For this product, instability is acceptable only if:

- it stays inside the same workflow family
- it stays inside the same mutation class
- `chat`, `trace`, and `today` still agree

Instability is **not** acceptable if it changes:

- `commit vs no_commit`
- `correction_applied vs ask_followup`
- `ledger_updated vs not updated`
- `today` sync vs no sync

By this boundary:

- current `C-001` instability is not acceptable
- current `K-002` instability is not acceptable

## Recommendation

### Product / architecture decision

Do **not** interpret the current instability as proof that Bundle 2 should accept broad non-determinism.  
That would be lowering the bar too early.

Instead, treat the product as:

- okay with bounded linguistic variability
- not okay with unstable workflow effect

### Engineering decision

The next work should focus on:

1. `C-001 followup resolution -> commit`
2. `K-002 setup commit + item removal correction`
3. repeated same-day full-suite reruns after those fixes

Recommended promotion rule:

> Bundle 2 should not be considered stable until the same full suite passes repeatedly, not just once.

A reasonable near-term gate would be:

- `3 consecutive full-suite passes`
- same code revision
- no `runner_ok/http_ok/response_shape` failures

## Current Status

As of the latest reviewed evidence:

- `Bundle 1`: stable enough for its defined gate
- `Bundle 2`: not yet promotion-ready

Latest formal status:

- [bundle2_live_eval_20260421_180911.json](/C:/Users/User/Documents/Playground/line-liff-calorie-helper-text-meal-canary-main/runtime/evals/v2_bundle2_live/bundle2_live_eval_20260421_180911.json)
  - `8 / 10 passed`
  - failed:
    - `C-001`
    - `K-002`
  - `bundle_gate = fail`

## Final Judgment

The observed instability should be interpreted as:

- **partly expected** at the language surface
- **not acceptable** at the workflow-effect surface

So the correct answer to the founder question is:

> Yes, some Bundle 2 cases are currently unstable.  
> But the instability is mainly because the runtime measures are not complete enough yet, not because the workflow is inherently too fuzzy to stabilize.

