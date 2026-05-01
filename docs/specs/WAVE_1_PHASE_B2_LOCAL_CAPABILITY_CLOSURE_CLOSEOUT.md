# Wave 1 Phase B2 Local Capability Closure Closeout

## Purpose

This closeout records the B2 local deterministic capability closure scope.

It does not claim pre-shadow readiness, user-facing readiness, mutation readiness, production DB accuracy, runtime web truth, or product rollout readiness.

Allowed claim:

- B2 local evidence, retrieval intent, source selection, packet guard, synthesis, final mapping, and active runtime lineage are covered by deterministic/local closure evidence when the listed verification commands pass.

Forbidden claims:

- shadow ready
- user-facing ready
- mutation ready
- production DB ready
- runtime web truth ready
- model-diverse ready

## Added B2 Local Case Table

| case_id | raw input | expected behavior | approved semantic register entry | new product semantics |
|---|---|---|---|---|
| B2-011 | 我吃了家常菜 | `draft`; `composition_clarification`; no accepted nutrition packet; no mutation | `homemade_food_minimum_estimability` | no |
| B2-012 | 我吃了麻辣燙 | `draft`; `composition_clarification`; self-selected basket ask-first; no mutation | `self_selected_basket_without_listed_items`, `taiwan_b2_case_law_narrow_set` | no |
| B2-013 | 我吃了麻辣臭豆腐 | `logged`; `generic_anchor_lookup`; strong refinement follow-up | `taiwan_b2_case_law_narrow_set` | no |
| B2-014 | 我吃了一份鹽酥雞 | `logged`; `generic_anchor_lookup`; portion cue resolves to generic estimable item | `salt_crispy_chicken_surface_term_resolution` | no |
| B2-015 | 我吃了鹽酥雞，有甜不辣、米血、四季豆 | `listed_item_lookup`; item-level evidence fanout; logged item outputs | `salt_crispy_chicken_surface_term_resolution` | no |

## Changed File Mapping

| file | closure slice |
|---|---|
| `app/knowledge/small_anchor_store_tw.json` | local evidence seed metadata closure |
| `app/nutrition/application/retrieval_intent.py` | approved case-law retrieval goals |
| `app/nutrition/application/small_anchor_store.py` | semantic-only clarify support boundary |
| `docs/specs/WAVE_1_PHASE_B2_SEMANTIC_DECISION_REGISTER.md` | canonical semantic freeze and superseded eval expectation record |
| `scripts/build_wave1_phase_b2_evidence_synthesis_smoke.py` | B2-011 through B2-015 active runtime diagnostic cases |
| `scripts/verify_wave1_phase_b2_evidence_synthesis_readiness.py` | seed metadata verifier boundary |
| `tests/test_wave1_phase_b2_local_p0_closure_audit.py` | local closure owner-lineage and case-law audit |
| `tests/test_wave1_phase_b2_local_synthesis.py` | semantic-only clarify without packets |
| `tests/test_wave1_phase_b2_retrieval_intent.py` | manager-owned structured retrieval intent |
| `tests/test_wave1_phase_b2_small_anchor_store.py` | seed support without mutation authority |
| `tests/test_wave1_phase_b2_semantic_register_alignment.py` | semantic register alignment regression |

## Seed Metadata Boundary

`semantic_only` seed metadata may provide:

- `semantic_hints`
- `followup_hints`

`semantic_only` seed metadata must not provide:

- kcal values
- macro candidates
- exact item truth
- web truth
- logged or draft verdicts
- final actions
- mutation intent
- mutation authority

`generic_and_semantic_only` seed metadata may provide:

- generic anchor kcal range
- likely kcal
- optional macro candidate
- semantic hints
- follow-up hints

`generic_and_semantic_only` seed metadata must not provide:

- `source_quality_label=internal_exact`
- exact same-item match authority
- brand exact truth
- runtime web truth
- logged or draft verdicts
- mutation authority

All local seed metadata remains `local_app_owned_diagnostic_seed` or local app-owned test-aligned store evidence. It is not a production nutrition DB and is not semantic authority.

## Verifier Relaxation Safety

The readiness verifier accepts `semantic_only` only when its allowed fields stay inside semantic and follow-up hints.

The readiness verifier accepts `generic_and_semantic_only` only when its allowed fields stay inside the union of generic seed fields and semantic hint fields. It still blocks exact truth by rejecting exact source quality labels, same-item exact match authority, and non-fixture exact runtime seeds.

The local closure audit separately checks owner lineage so source selection and seed metadata cannot become logged/draft or final mapping owners.

## Governance Wall

Before commit or PR, run these commands serially:

```powershell
python scripts/audit_repo_legacy_surfaces.py
python scripts/check_layer_integrity.py
python scripts/check_runtime_boundaries.py
python scripts/audit_readiness_claim_integrity.py
python scripts/audit_deterministic_semantic_ownership.py --stage zero-high-risk
python scripts/audit_architecture_dependency_debt.py
lint-imports --config .importlinter
python scripts/check_markdown_encoding.py --policy-docs --require-bom
git diff --check
```

If all commands pass, use:

- commit message: `Close B2 local capability closure diagnostics`
- PR title: `B2 Local Capability Closure`

## PR Body Draft

### Scope

This PR closes the B2 local deterministic capability slice for approved narrow Taiwan case-law coverage, local evidence seed metadata, retrieval intent ownership, packet guard closure, synthesis/final mapping boundary, and active runtime owner lineage.

### Explicit Non-Claims

This PR does not claim pre-shadow readiness, model diversity, user-facing readiness, mutation rollout readiness, production DB accuracy, or runtime web truth.

### Verification

Fresh local verification on 2026-05-01:

- `python scripts/audit_repo_legacy_surfaces.py` passed with `finding_count=0`.
- `python scripts/check_layer_integrity.py` passed.
- `python scripts/check_runtime_boundaries.py` passed.
- `python scripts/audit_readiness_claim_integrity.py` passed with `checked_artifact_count=7`.
- `python scripts/audit_deterministic_semantic_ownership.py --stage zero-high-risk` passed with `unauthorized_high_risk_finding_count=0`.
- `python scripts/audit_architecture_dependency_debt.py` passed with `new_finding_count=0`.
- `lint-imports --config .importlinter` passed with 5 kept contracts and 0 broken contracts.
- `python scripts/check_markdown_encoding.py --policy-docs --require-bom` passed.
- `git diff --check` passed.
- `$env:PYTHONPATH='.'; pytest tests/test_wave1_phase_b2_semantic_register_alignment.py tests/test_wave1_phase_b2_local_p0_closure_audit.py tests/test_wave1_phase_b2_small_anchor_store.py tests/test_wave1_phase_b2_retrieval_intent.py tests/test_wave1_phase_b2_local_synthesis.py` passed with 51 tests.

Note: direct `pytest ...` without `PYTHONPATH=.` failed during collection because this shell did not resolve repo-root imports for `app` and `scripts`. The successful run above used the repo-root import path.
