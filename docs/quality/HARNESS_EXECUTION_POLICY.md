# Harness Execution Policy

## Purpose

This document defines the repository's active deterministic harness wall.

Execution truth remains:

1. `git diff / commit history`
2. CI and harness output
3. the minimal active state in `CURRENT_EXECUTION_PLAN.md`

## Active Hard Gates

These scripts are strictly enforced during the build and evaluation pipeline. Failure in any of these scripts blocks progression to the next capability layer.

- **`scripts/check_git_diff_scope.py`**: Ensures bounded refactoring to prevent unreviewed architectural drift.
- **`scripts/check_encoding.ps1`**: Enforces strict `UTF-8-BOM` or `UTF-8-NO-BOM` policies for tracked markdown documents.
- **`scripts/audit_io_guard.py`**: Shared pre-run hard gate for formal audit runners; blocks Windows piped stdin and requires file-backed fixtures.
- **`docs/quality/AUDIT_RUNNER_REGISTRY.json`**: The sole registry of official formal audit runners that must obey the shared audit input contract.
- **`docs/quality/AUDIT_FIXTURE_REGISTRY.json`**: The sole registry of official formal audit fixtures that must remain valid UTF-8 and free of mojibake-risk text.
- **`scripts/check_audit_runner_contract.py`**: CI/pre-commit hard gate that scans the audit runner registry and ensures each listed runner still imports and invokes the shared `audit_io_guard`.
- **`scripts/check_audit_fixture_safety.py`**: CI/pre-commit hard gate that scans the audit fixture registry and blocks corrupted or mojibake-risk formal audit inputs before any official run starts.
- **`scripts/check_audit_safety.py`**: Post-run scan that detects mangled Chinese characters (`????`) or invalid UTF-8 in logs and artifacts.
- `scripts/check_commit_format.py`
- `scripts/check_runtime_boundaries.py`
- diff-scoped `ruff` on touched Python files
- `scripts/check_layer_integrity.py`
- `scripts/check_fat_files.ps1`
- `scripts/check_migration_discipline.py`
- smoke and integration tests in CI

## Diff Scope Contract

`check_git_diff_scope.py` enforces:

- max changed tracked files per diff
- freeze-growth growth cap
- dependency drift lock
- cross-layer contamination checks
- test mutilation guard
- anti-truncation guard for high-risk files

The script must operate on staged diff or commit/PR range, not the full dirty worktree.

## Commit Contract

`check_commit_format.py` requires:

- a non-vague subject that expresses slice intent
- `Test Run: ...`
- `Reality:` or `Drift:` for commits touching core logic

## Scope Exception Labels

Allowed `Scope-Exception:` labels:

- `freeze-allow`
- `cross-layer`
- `dependency-update`
- `test-refactor`
- `large-refactor`
- `wide-scope`

These labels are for bounded exceptional cases, not normal workflow.
