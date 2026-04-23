# Macro Reconciliation Test Plan

## Purpose
- Validate that macro shown in UI is consistent with the product truth hierarchy.
- Confirm the system treats `estimated_kcal` as primary truth and `display_macro_breakdown` as a guarded presentation artifact.
- Ensure raw vs display macro separation is stable before retrieval / external search optimization.

## Scope
This plan covers:
- deterministic macro derivation
- reconciliation thresholds
- payload shaping for UI
- trace / guard metadata

This plan does **not** evaluate:
- final response wording
- retrieval quality
- external search escalation quality
- follow-up decision quality

## Product Truth Rules Under Test
- `estimated_kcal` remains the primary truth.
- `raw_macro_breakdown` is internal trace data.
- `display_macro_breakdown` is the only macro payload the UI should use.
- `macro_breakdown` remains a compatibility alias and must mirror `display_macro_breakdown`.
- Large macro/kcal mismatch must suppress macro display rather than override kcal.

## Case Types
### 1. Exact Label Pass-through
Expected behavior:
- `raw_macro_breakdown.macro_source = exact_label`
- `display_macro_breakdown.macro_source = exact_label`
- `display_macro_breakdown` equals `raw_macro_breakdown`
- no reconciliation

### 2. Anchored Consistent
Expected behavior:
- component-derived macro exists
- macro kcal delta is within `<= 10%`
- `display_macro_breakdown.macro_source = derived_consistent`
- display macro equals raw macro

### 3. Anchored Reconciled
Expected behavior:
- component-derived macro exists
- macro kcal delta is within `> 10%` and `<= 20%`
- `display_macro_breakdown.macro_source = derived_reconciled`
- `macro_reconciled = true`
- `reconciliation_scale` is present
- display macro is scaled toward `estimated_kcal`

### 4. Anchored Hidden
Expected behavior:
- component-derived macro exists
- macro kcal delta is `> 20%`
- `display_macro_breakdown.macro_source = unavailable`
- display macro fields are hidden (`None`)
- raw macro is still preserved in trace

### 5. Heuristic / Unknown Hidden by Default
Expected behavior:
- weak component support or weak consistency
- `display_macro_breakdown.macro_source = unavailable`
- raw macro may exist or be absent
- UI does not receive displayable macro

### 6. Payload Separation
Expected behavior:
- top-level `protein_g / carb_g / fat_g` come from `display_macro_breakdown`
- raw macro remains separately available in payload
- compatibility field `macro_breakdown` matches display macro, not raw macro

### 7. Trace Integrity
Expected behavior:
- guard metadata includes:
  - `raw_macro_kcal`
  - `display_macro_kcal`
  - `delta_kcal`
  - `delta_pct`
  - `macro_reconciled`
  - `reconciliation_scale`
- macro suppression/reconciliation is observable in trace

## Acceptance Criteria
- All 7 case types above are covered by automated tests.
- No test allows display macro to visibly contradict `estimated_kcal`.
- Exact label cases never get downgraded to derived display macro.
- Compatibility field does not leak raw macro into UI-facing payload.

## Current Automated Coverage
Covered now:
- exact label pass-through
- anchored reconciled
- anchored hidden
- heuristic hidden
- basic anchored derived path

Covered indirectly:
- compatibility alias `macro_breakdown`

## Current Coverage Gaps
- No focused test yet for `Anchored Consistent` using an actually `<= 10%` delta case.
- No focused payload-builder test asserting top-level `protein_g / carb_g / fat_g` come from `display_macro_breakdown`, not raw macro.
- No focused test asserting `macro_breakdown == display_macro_breakdown` for UI compatibility.
- No focused benchmark-level assertion yet on raw/display split in end-to-end payload.

## Recommended Test Order
1. Unit tests for reconciliation thresholds
2. Unit tests for payload-builder raw/display split
3. Contract benchmark spot-check for representative exact / anchored / heuristic cases
4. Only after that, move on to retrieval / external search mechanism tests

## Exit Gate
Macro reconciliation is considered stable enough to move on when:
- threshold behavior is fully covered
- payload separation is explicitly covered
- compatibility alias behavior is explicitly covered
- contract benchmark still passes after raw/display split
