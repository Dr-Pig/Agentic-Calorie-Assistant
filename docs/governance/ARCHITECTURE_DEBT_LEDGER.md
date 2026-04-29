# Architecture Debt Ledger

## Purpose

This ledger records architecture debt that is known, trace-visible, and intentionally not fixed in the current slice.

Use it to stop future work from silently copying concrete shortcuts forward as if they were canonical product architecture.

This is an operational ledger, not a full ADR archive.

As of the Wave 1 decoupling audit, it also serves as the phase-grouped audit ledger for already-built Wave 1 surfaces.

---

## Entry Format

Record debt items using:

```yaml
debt_id:
phase:
owner_surface:
found_in_slice:
current_location:
path_classification:
debt_type:
severity_class:
risk:
why_not_fixed_now:
retirement_gate:
target_cleanup_slice:
blocking_level:
```

Recommended `debt_type` values:

- `concrete_shape_leak`
- `provider_coupling`
- `db_coupling`
- `compatibility_surface`
- `test_oracle_risk`
- `fat_file_boundary_risk`

Recommended `path_classification` values:

- `active_product_path`
- `compatibility_surface`

Recommended `severity_class` values:

- `P0` blocks the current next slice
- `P1` must be fixed before live provider or live Tavily activation
- `P2` must be fixed before Phase C / mutation-facing work
- `P3` compatibility debt; may defer if not being copied forward

Recommended `blocking_level` values:

- `advisory`
- `narrow_before_expanding`
- `blocking`

Optional retirement fields:

- `resolution_status`
- `resolved_in_slice`

---

## Wave 1 Audit Findings

### Phase A

#### PA-DEBT-001

```yaml
debt_id: PA-DEBT-001
phase: Phase A
owner_surface: shared manager branch contract and validation layer
found_in_slice: Wave 1 decoupling debt audit
current_location: app/runtime/agent/manager_branch_contract.py and app/runtime/agent/manager_branch_validation.py
path_classification: active_product_path
debt_type: fat_file_boundary_risk
severity_class: P3
risk: Shared runtime contract files currently embed B-1-specific branch constraint logic, which increases the chance that local Wave 1 diagnostic policy gets copied forward as canonical manager architecture.
why_not_fixed_now: The current audit slice does not change runtime behavior, and no immediate next slice requires broad manager-branch reuse beyond the current Wave 1 scope.
retirement_gate: before generalizing shared manager branch selection or validation beyond current Wave 1 local contract usage
target_cleanup_slice: Shared manager branch boundary cleanup
blocking_level: advisory
```

### B-1

#### B1-DEBT-001

```yaml
debt_id: B1-DEBT-001
phase: B-1
owner_surface: Phase B-1 provider/profile routing and local diagnostic selection
found_in_slice: Wave 1 decoupling debt audit
current_location: app/runtime/agent/phase_b1_selection.py, app/runtime/agent/phase_b1_selection_specs.py, app/runtime/agent/phase_b1_profile_route_rules.py, and scripts/run_wave1_phase_b_minimal_tool_loop_smoke.py
path_classification: compatibility_surface
debt_type: provider_coupling
severity_class: P1
risk: Branch-local provider/profile routing, artifact-backed overrides, and explicit case-id diagnostic debt could be mistaken for general manager-profile policy if reused outside the B-1 local diagnostic loop.
why_not_fixed_now: retired
retirement_gate: completed before generalizing provider/profile routing outside the B-1 local diagnostic and smoke harness path
target_cleanup_slice: B-1 provider profile routing normalization
blocking_level: retired
resolution_status: retired
resolved_in_slice: B-1 provider profile routing normalization
```

Resolution note:

- B-1 auto-route exceptions now live in a dedicated local diagnostic route registry
- targeted profile allowlist checks and B1-004 legacy CLI defaults now consume the same local diagnostic policy module
- selector callers no longer inject artifact-basis metadata
- `route_scope = b1_local_diagnostic` remains explicit in selection and smoke trace output
- B1005 and B1006 case-id debt remains quarantined as local diagnostic debt, not generalized runtime routing policy

#### B2-DEBT-001

```yaml
debt_id: B2-DEBT-001
phase: B-1/B-2 shared retrieval dispatch
owner_surface: shared web search and extract tool dispatch
found_in_slice: B2 web/search governance prep
current_location: app/nutrition/application/tool_dispatch.py
path_classification: compatibility_surface
debt_type: concrete_shape_leak
severity_class: P3
risk: This module still branches on concrete adapter capabilities such as search_candidates and extract_structured_page_data, so it remains a risky compatibility surface if future work rewires it into runtime or copies its pattern forward.
why_not_fixed_now: Current Wave 1 intake runtime no longer routes active estimation through this module, so it should be treated as dormant compatibility debt rather than an active-path blocker.
retirement_gate: before any future runtime rewiring that reactivates this dispatch surface or copies its concrete branching pattern into new product-owned code
target_cleanup_slice: Dormant tool dispatch quarantine or removal
blocking_level: advisory
```

### B-2

#### B2-DEBT-002 (Resolved)

```yaml
debt_id: B2-DEBT-002
phase: B-2
owner_surface: Tavily live search and extract adapter/profile policy
found_in_slice: B2 web/search governance prep
current_location: app/nutrition/infrastructure/web_search/tavily_adapter.py
path_classification: active_product_path
debt_type: provider_coupling
severity_class: P1
risk: Tavily profile knobs such as search_depth, extract_depth, chunks_per_source, and include_raw_content still live inside the concrete adapter without a separate live port/profile retirement seam, so live web activation could still leak adapter policy into product-facing decisions.
why_not_fixed_now: The current app-layer candidate and packet slices intentionally stopped before live Tavily activation.
retirement_gate: before the first live Tavily port-backed runtime smoke
target_cleanup_slice: Tavily profile and port cleanup
blocking_level: narrow_before_expanding
resolution_status: retired
resolved_in_slice: Tavily profile and port cleanup
```

Resolution note:

- request knobs now live in infra-local Tavily profile policy
- public adapter methods no longer expose `include_raw_content`, `extract_depth`, or `chunks_per_source`
- `TavilySearchPort` remains thin and semantics-free
- live Tavily smoke and `WebExtractPort` remain deferred

#### B2-DEBT-003

```yaml
debt_id: B2-DEBT-003
phase: B-2
owner_surface: Pass 2 provider seam, fake provider, and oracle parity gate
found_in_slice: B2 pass2 seam audit
current_location: app/nutrition/application/b2_pass2_provider_bridge.py and tests/test_wave1_phase_b2_pass2_oracle_parity.py
path_classification: compatibility_surface
debt_type: test_oracle_risk
severity_class: P1
risk: Fake-provider and parity helpers could expand into a hidden semantic owner or silent runtime fallback if the live Pass 2 seam is activated before runtime ownership is explicitly narrowed.
why_not_fixed_now: retired
retirement_gate: completed before the first live provider-backed Pass 2 pilot
target_cleanup_slice: Provider seam runtime-owner hardening
blocking_level: retired
resolution_status: retired
resolved_in_slice: B2 provider seam runtime-owner hardening
```

Resolution note:

- `item_results_owner_class` is now trace/readiness-only ownership diagnostics, not product semantics
- explicit Pass 2 payloads are classified as `runtime_payload`
- answer-contract bridge traces are classified as `compatibility_bridge` and fail readiness
- runner-derived item results remain blocked as fallback-owned output

#### B2-DEBT-004

```yaml
debt_id: B2-DEBT-004
phase: B-2
owner_surface: official B2 evidence-synthesis smoke producer and readiness compatibility generator
found_in_slice: B2 producer-first runtime alignment
current_location: scripts/build_wave1_phase_b2_evidence_synthesis_smoke.py
path_classification: compatibility_surface
debt_type: compatibility_surface
severity_class: P2
risk: retired
why_not_fixed_now: retired
retirement_gate: completed before any claim that official B2 producer artifacts are fully runtime-backed
target_cleanup_slice: B2-006 selected extract exact-positive runtime lane
blocking_level: retired
resolution_status: retired
resolved_in_slice: B2-006 selected extract exact-positive runtime lane
```

Progress note:

- `B2-007`, `B2-009`, and `B2-010` now use honest runtime-backed producer paths
- `B2-005` now uses runtime-backed listed-item fanout with per-item report/readiness diagnostics
- `B2-006` now uses an offline, fixture-backed selected-extract exact-positive runtime lane
- `producer_trace` is constrained to report/readiness provenance only and does not grant product semantics or Phase C mapping authority
- `extract_policy` remains a report/readiness diagnostic, not a nutrition-domain or Phase C input

---

## Severity Summary

- `P3`
  - `B2-DEBT-001` is now dormant compatibility debt because the active Wave 1 intake runtime no longer routes through `tool_dispatch.py`, but the concrete branching pattern must not be copied forward.
  - `PA-DEBT-001` is real but does not block the current next slice if no new work copies B-1-specific branch logic into broader shared runtime policy.

- `Resolved`
  - `B1-DEBT-001` is retired. Phase B-1 provider/profile auto-route policy is now registry-owned and stays explicitly scoped to `b1_local_diagnostic`.
  - `B2-DEBT-002` is retired. Tavily request knobs now live behind infra-local profile policy while the active app/runtime contract stays unchanged.
  - `B2-DEBT-003` is retired. Pass 2 ownership is now explicit in trace/readiness, and answer-contract bridge output no longer satisfies runtime-owner readiness.
  - `B2-DEBT-004` is retired as the official B-2 producer honesty debt. This does not imply live Tavily rollout, full web extraction runtime completion, or broader source-priority completion.

---

## Recommended Next Cleanup Slice

Recommended next cleanup slice:

- no active producer-honesty cleanup slice remains; any next web/runtime work should be framed as a new live-runtime or extract-threading slice, not as `B2-DEBT-004`

Why this is next:

- generic-anchor, clarify-support, exact-item-card, and web-search rejection cases now have report-visible runtime-backed provenance
- listed-item decomposition for `B2-005` now runs through runtime fanout plus the B2 local runtime synthesis path
- `B2-006` now runs through a selected-search-packet -> `web_extract` packet -> B2 local runtime synthesis path
- `B1-DEBT-001` remains retired and `B2-DEBT-003` is no longer the active next cleanup gate

What this audit does **not** recommend:

- blanket full Wave 1 cleanup before all other work
- immediate live Tavily activation
- immediate live provider-backed Pass 2 activation
- pausing all Wave 1 work when the current slice does not touch the `P0` surface
