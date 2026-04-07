# Live Trace Triage Workflow

## Purpose

All real dashboard failures must be triaged before patching. The goal is to identify the first bad pass and root-cause bucket before any implementation work starts.

## Fixed Triage Format

Each failing case must be recorded with:

- `user_input`
- `expected_behavior`
- `actual_reply`
- `first_bad_pass`
- `raw_provider_output`
- `normalized_output`
- `fallback_or_degraded_reason`
- `suspected_root_cause_bucket`
- `owner_file`

## Root-Cause Buckets

Use only these buckets:

1. `encoding_corruption`
2. `schema_drift`
3. `context_contamination`
4. `tool_routing_gap`
5. `fallback_pollution`
6. `persistence_pollution`

## Repair Discipline

- Only fix the first bad pass.
- If the upstream pass is still bad, do not patch downstream behavior.
- Every repaired real failure must become a regression fixture.
- Do not use dish-specific prompt examples or hardcoded heuristics to force a pass.

## Tooling

- `app/observability/trace_triage.py`
  - canonical triage classifier
- `scripts/trace_triage.py`
  - CLI for latest request traces
- `tests/fixtures/live_trace_triage_cases.json`
  - regression fixtures for root-cause classification

## Typical Usage

```bash
python scripts/trace_triage.py --latest 3
python scripts/trace_triage.py --request-id <request_id>
```
