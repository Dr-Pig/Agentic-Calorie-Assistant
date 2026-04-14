# Turn-2 Hybrid Replay Protocol

## Purpose

This protocol defines the standard low-cost workflow for second-turn intake evaluation.

It exists to answer:

- how to test turn 2 without paying full two-turn live cost every time
- what must be saved from turn 1
- what counts as a valid turn-2 replay

## Standard Flow

Use this order:

1. run `turn1` once with a real provider
   - via the checked-in runner and file-backed cases only
   - never through inline PowerShell pipe input on Windows
2. save the full artifact:
   - final payload summary
   - full `trace_contract`
   - full `llm_traces`
   - persistence decision
   - user id / request id
3. keep the same persisted runtime state
4. rerun only `turn2` against that saved state
5. evaluate second-turn attachment and closure quality

This is the default `2.2h` evaluation method.

## Why Hybrid Replay

Compared with full two-turn live:

- cheaper
- easier to iterate on turn-2 behavior
- less polluted by first-turn randomness

Compared with replay-only:

- still exercises the real turn-2 runtime path
- still validates same-intake attachment and persistence behavior

## Required Turn-1 Artifact

Every saved turn-1 artifact must retain:

- `case_id`
- `turn_id`
- `user_id`
- `request_id`
- full payload
- full `trace_contract`
- full `llm_traces`
- persistence decision

If any of these are missing, the replay artifact is not valid.

## Acceptance

At minimum, `2.2h` must support:

- `ask_followup_only -> completion`
- `estimate_with_followup -> refinement`

For each replayed second turn, confirm:

- it attaches to the same intake / meal boundary
- it does not create a duplicate meal thread
- it does not require durable memory or retrieval deepening
- final commit posture matches the turn-1 contract

## Current Environment Gate

Real replay runs require a configured live provider.

If provider readiness is not configured:

- do not treat fallback-only runs as true live replay evidence
- keep the protocol and runner ready
- defer real replay verdicts until provider configuration is restored
