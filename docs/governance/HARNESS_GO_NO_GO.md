# Harness Go / No-Go

Use this before starting a new build wave. It should take about 30 seconds.

## Go

- `main` branch protection requires the current CI job names from `.github/workflows/ci.yml`: `repo-hygiene-and-architecture`, `runtime-contract-tests`, and `product-pages-browser-e2e`
- `python scripts/check_layer_integrity.py` passes
- `python scripts/check_runtime_boundaries.py` passes
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings` passes
- the retained pytest wall for `runtime-contract-tests` passes on a fresh checkout
- the retained browser smoke wall for `product-pages-browser-e2e` passes on a fresh checkout
- deeper environment, MVP, and phase-labeled audit walls may still be run from `.github/workflows/ci-advisory.yml`, but they are not merge blockers
- merge-governance reports are manual diagnostics only; they do not decide queue eligibility or merge readiness by themselves
- governance docs and workflow job names are synchronized in the same branch

## No-Go

- any required check is missing or red
- branch protection still references retired workflow job names
- any protected legacy file is growing
- any freeze-growth file exceeds its frozen line count
- any fixture, fake-provider, deterministic, live-diagnostic, shadow, or canary artifact claims a broader readiness stage than its evidence supports
- the retained CI jobs require ignored local-only assets such as `data_build/`

## False-Green Claim Boundary

Fixture-first remains valid, but each stage may only claim the evidence it actually proves.

| Stage | Can prove | Must not claim |
| --- | --- | --- |
| `fixture / fake provider` | schema, tool-loop, guard, trace, and persistence scaffold can run | Manager truly understands user intent or food semantics |
| `deterministic runtime` | active path is repeatable, no live LLM is invoked, and no runtime crash occurs | live provider readiness or product semantics are verified |
| `live diagnostic` | real Manager/LLM tool selection and semantic judgment can be observed | production, user-facing, or mutation-bearing readiness |
| `shadow / canary` | stability under real traffic can be compared or sampled | whole-product completion |

Hard rules:

- `fixture_scaffold_pass` may unlock deterministic checks only; it cannot claim B1/B2 handoff readiness, live readiness, user-facing readiness, or mutation readiness.
- `deterministic_runtime_pass` may unlock live diagnostic only when upstream contract gates are green.
- `live_diagnostic_pass` may unlock shadow evaluation only; it cannot write canonical state or claim production readiness.
- readiness artifacts must expose `readiness_claim` and pass `python scripts/audit_readiness_claim_integrity.py`.
- legacy Bundle Version 1 / Bundle Version 2 artifacts, archived artifacts, obsolete eval oracles, or completed handoff docs must not be evidence lineage for readiness.

## Windows Pytest Isolation

Do not run multiple pytest processes in parallel in this repo on Windows. The test suite uses `.pytest_tmp_local`; parallel pytest runs can race on cleanup and produce `PermissionError` or missing-path failures unrelated to product behavior.

If broad verification is needed, run pytest groups sequentially or give each process an isolated base temp directory before treating a failure as real evidence.

## Fast Decision

- `GO` if every item above is true
- `NO-GO` if any item above is false
