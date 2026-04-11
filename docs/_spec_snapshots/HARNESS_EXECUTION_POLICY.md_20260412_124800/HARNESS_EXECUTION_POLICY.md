# Harness Execution Policy

## Purpose

This document defines the repository's active deterministic harness wall.

Execution truth remains:

1. `git diff / commit history`
2. CI and harness output
3. the minimal active state in `CURRENT_EXECUTION_PLAN.md`

## Active Hard Gates

Default hard gates now include:

- `scripts/check_git_diff_scope.py`
- `scripts/check_commit_format.py`
- `scripts/check_runtime_boundaries.py`
- diff-scoped `ruff` on touched Python files
- `scripts/check_layer_integrity.py`
- `scripts/check_encoding.ps1`
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
