# Harness Go / No-Go

Use this before starting a new build wave. It should take about 30 seconds.

## Go

- `main` branch protection requires the current CI job names from `.github/workflows/ci.yml`: `repo-hygiene-and-architecture`, `pre-edd-readiness`, `runtime-contract-tests`, `wave1-phase-a-contracts`, and `wave1-phase-b-contracts`
- `python scripts/check_layer_integrity.py` passes
- `python scripts/check_runtime_boundaries.py` passes
- `powershell -ExecutionPolicy Bypass -File scripts/check_fat_files.ps1 -AuditAll -NoFailOnWarnings` passes
- `python scripts/pre_edd_readiness.py --timeout-seconds 180` returns `ready_for_edd`
- the retained pytest wall for `runtime-contract-tests` passes on a fresh checkout
- governance docs and workflow job names are synchronized in the same branch

## No-Go

- any required check is missing or red
- branch protection still references retired workflow job names
- any protected legacy file is growing
- any freeze-growth file exceeds its frozen line count
- `python scripts/pre_edd_readiness.py --timeout-seconds 180` returns `not_ready_for_edd`
- the retained CI jobs require ignored local-only assets such as `data_build/`

## Fast Decision

- `GO` if every item above is true
- `NO-GO` if any item above is false
