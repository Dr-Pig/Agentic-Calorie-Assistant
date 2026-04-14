# Harness Engineering Reorg v2

## Planning Status

- `current_phase`: `Phase E build-ready closure`
- `next_phase`: `move reorg record to completed and begin Phase 1 canonical persistence follow-through`
- `last_replan_at`: `2026-04-11`
- `reality_drift_notes`:
  - repo reorg is complete enough for implementation work, so this plan is now mostly a closure record
  - active implementation work has shifted into canonical persistence, typed contracts, and intake vertical-slice hardening
- `stale_assumptions_removed`:
  - reorg is no longer treated as the main active engineering track
  - future implementation detail should live in newer execution plans rather than this reorg note

## Goal

Reshape the repository into an agent-readable harness where:

- `AGENTS.md` is the short entry
- `docs/index.md` is the navigation map
- `docs/specs/` holds canonical specs
- `docs/quality/` holds eval / benchmark / safety docs
- `docs/references/` holds research and external-reference material
- `docs/archive/` isolates superseded material

## Active Work Items

1. inventory existing root and `docs/` documents
2. move canonical specs and quality docs into stable locations
3. create docs index and manifests
4. create `app/` target-state blueprint
5. repair canonical cross-links
6. verify agent navigation from `AGENTS.md`

## Success Criteria

- a new agent can reach `L3.1`, `L5B`, and `L6B` within three navigation steps
- archive content no longer appears to be current truth
- canonical docs have stable, obvious locations
- no existing spec was rebuilt via delete-and-recreate during reorg

## Follow-Up

After reorg closure:

- move this file to `docs/exec-plans/completed/`
- record any remaining path drift or orphan docs in tech debt
