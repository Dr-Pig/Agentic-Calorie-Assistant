# V2 Founder Realism Cases

## Purpose

This file defines founder-driven realism checks that complement the current Manager-style diagnostic and regression gates.

These cases are not a replacement for manager/runtime gates. They exist to prevent assistant claims that rely on narrow runner coverage while real interactive quality is still failing.

Governance mode: `Hybrid`

- correctness / provenance / sync / latency failures are blocking
- wording richness and GPT-parity explanation quality are tracked as realism quality signals

---

## Execution Contract

- founder realism must produce a machine-readable report under `runtime/evals/v2_founder_realism/`
- each case must include:
  - `case_id`
  - `request_ids`
  - `checks`
  - `passed`
  - `blocking`
  - `assistant_messages`
  - `today_snapshot`
  - `trace_refs`
- if founder realism is not run, Manager-style diagnostic reports must surface `founder_realism_status = not_run`

---

## Cases

### FR-001：無糖抹茶燕麥奶

Input:
- `喝了一杯抹茶燕麥奶無糖`

Expected:
- same-turn chat / sidecar / `/today` / trace `budget_summary` remaining are consistent
- if exact evidence is absent, explanation must not overstate component certainty
- latency must be recorded and classified as a simple anchored drink case

Blocking failures:
- same-turn remaining mismatch
- no traceable provenance summary
- no latency trace

### FR-002：蒸餃未給顆數

Input:
- `然後他晚餐吃蒸餃`

Expected:
- system does not hard finalize a single canonical estimate without count
- system asks count or gives bounded range with follow-up

Blocking failures:
- direct finalized commit without count
- high-confidence component explanation without serving basis

### FR-003：蒸餃補 12 顆

Inputs:
- `然後他晚餐吃蒸餃`
- `喔我剛剛的蒸餃吃了12顆喔`

Expected:
- second turn attaches to the prior dumpling meal
- lane is followup-resolution or correction, not disconnected new-intake semantics
- implied per-piece logic is internally consistent

Blocking failures:
- second turn commits as an unrelated new meal with no owned correction/followup lane
- contradictory per-piece logic with no explanation

### FR-004：大麥克 provenance

Input:
- `我消夜還吃了一個大麥克`

Expected:
- trace must disclose whether DB exact, web retrieval, or generic estimate was used
- if evidence is unusable, response must not masquerade as exact-like finalized truth

Blocking failures:
- finalize with `eligibility = unusable` and no explicit uncertainty posture
- no provenance summary in trace/report

### FR-005：Macro surface and visibility

Any committed case with macro values.

Expected:
- `/today/current-budget` includes `consumed_protein`, `consumed_carbs`, `consumed_fat`, `show_macro`
- chat obeys `show_macro`
- correction updates macro totals

Blocking failures:
- macro fields missing from current-budget surface
- `show_macro = false` but chat still emits macro numbers

---

## Verdict Semantics

- `pass`: all blocking checks passed
- `fail`: one or more blocking checks failed
- `shadow_quality_gap`: blocking checks passed but realism quality differs from desired GPT-like answer quality

Founder realism is part of the acceptance truth. Historical acceptance-package runners cannot be used as substitutes for this suite.
