# Workspace Layout

This repo should separate code, runtime output, and large research datasets.

## Tracked areas

- `app/`: application code
- `scripts/`: developer scripts and tooling
- `tests/`: tests and fixtures that are intentionally versioned
- `docs/`: design notes and operating docs
- `docs/handoff/`: current runtime handoff docs for future agents

## Ignored runtime areas

- `runtime/db/`: SQLite database files
- `runtime/logs/`: request traces and audit logs
- `runtime/artifacts/session_records/`: session transcript output
- `data_build/`: generated build output
- `tmp/`, `.trash/`, `child_outputs/`: scratch output

## Ignored data workspace

- `workspace_data/`: local datasets, exports, downloaded files
- `減肥駐守/raw_data/`: legacy crawl data still kept in-place for compatibility
- `減肥駐守/*.jsonl.gz`: large compressed exports

## Rules

1. Keep application code and docs in tracked directories only.
2. Write runtime output under `runtime/`.
3. Write large downloaded or generated datasets under `workspace_data/`.
4. Do not stage or push files larger than the hook threshold unless you intentionally raise the limit.
