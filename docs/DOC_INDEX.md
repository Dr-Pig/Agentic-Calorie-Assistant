# Documentation Index

This is the sole active docs index for the repository.

Use [AGENTS.md](../AGENTS.md) for agent bootstrap. Use this file for document taxonomy, active-vs-legacy routing, and the current bootstrap path.

Retired duplicate index files `docs/index.md` and `docs/V2_DOC_INDEX.md` must not be recreated. Historical links should be redirected here instead of preserving thin stubs.

## Active Bootstrap

For the current default mainline:

1. [docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md](specs/APP_ENGINEERING_OPERATING_ENTRY.md)
2. [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](exec-plans/active/CURRENT_EXECUTION_PLAN.md)
3. [docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md](quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md)
4. [docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml](quality/CURRENT_SHELL_SYNC_CONTRACT.yaml)
5. [docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml](quality/MANAGER_RUNTIME_GATE_LEDGER.yaml)
6. the relevant track-specific runbook or scope doc

## Active Truth Rules

- sole active docs index: `docs/DOC_INDEX.md`
- retired duplicate docs indexes must not exist: `docs/index.md`, `docs/V2_DOC_INDEX.md`
- sole active operating entry: `docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md`
- retired V2 operating and implementation stubs must not be tracked under `docs/specs/`
- sole legacy runtime reference index: `docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md`
- canonical preservation path: `docs/_spec_snapshots/`

## Read When

| Need | Primary location |
| --- | --- |
| current bootstrap and document taxonomy | [docs/DOC_INDEX.md](DOC_INDEX.md) |
| current execution pointer | [docs/exec-plans/active/CURRENT_EXECUTION_PLAN.md](exec-plans/active/CURRENT_EXECUTION_PLAN.md) |
| high-impact operating rules | [docs/specs/APP_ENGINEERING_OPERATING_ENTRY.md](specs/APP_ENGINEERING_OPERATING_ENTRY.md) |
| current split-delivery ownership and coordination | [docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md](quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md) |
| current shell contract and gate order | [docs/quality/CURRENT_SHELL_SYNC_CONTRACT.yaml](quality/CURRENT_SHELL_SYNC_CONTRACT.yaml), [docs/quality/MANAGER_RUNTIME_GATE_LEDGER.yaml](quality/MANAGER_RUNTIME_GATE_LEDGER.yaml) |
| historical pre-self-use runtime interpretation | [docs/specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md](specs/LEGACY_PRE_SELF_USE_RUNTIME_REFERENCE_INDEX.md) |

## Not Active Bootstrap

Do not start new implementation work from:

- Kiro steering files
- placeholder cloud/deploy workflows
- retired duplicate docs indexes: `docs/index.md`, `docs/V2_DOC_INDEX.md`
- `docs/governance/EXECUTION_OPERATING_MODEL.md`
- `docs/governance/EXECUTION_SELECTION_POLICY.md`
- retired V2 operating and implementation stubs
- `docs/specs/V2_WAVE_1_CODING_AGENT_BOOTSTRAP.md`
- `docs/specs/V2_EXECUTION_ARCHITECTURE_AND_WAVE_PLAN.md`
- `docs/specs/V2_WHOLE_PRODUCT_CAPABILITY_LATTICE.md`
- `docs/quality/V2_CAPABILITY_MAP.md`

Tracked files listed here may still carry canonical reference or compatibility value, but they are not the active bootstrap entry for new windows.
