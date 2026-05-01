# Environment Verification Gate

This document records the narrow environment gate that blocks Phase C active-runtime refactors.
It is a development verification note, not product truth and not a readiness claim.

## Current Gate

- Repo target runtime: Python 3.12.
- CI runtime: Python 3.12.
- Dockerfile runtime: `python:3.12-slim`.
- Local Python 3.9 runs are not authoritative for active runtime, persistence, SQLAlchemy app paths, Phase C response assembly, or broader CI gates.
- Contract-only isolated tests may run locally when they do not import active Python 3.12-only runtime.

## Required Before Slice 2

Before starting `Canonical Commit UnitOfWork Adapter` or any other active Phase C persistence refactor, verify in Python 3.12 or Docker:

```bash
python -m pytest \
  tests/test_phase_c_transaction_ports_contract.py \
  tests/test_phase_c_mutation_projection.py \
  tests/test_phase_c_same_truth_gate.py \
  -q
git diff --check
```

If Docker is used, prefer a test-oriented container command over app-server boot so Alembic, uvicorn, and deployment startup do not obscure verification failures.

## Stop Conditions

Stop and resolve the environment blocker before product work if:

- Docker or Python 3.12 is unavailable.
- `pip install -r requirements.txt` fails in Python 3.12.
- Python 3.12 Phase C verification fails before the active-runtime refactor starts.
- Dockerfile or dependency setup needs a narrow dev-env fix.

Do not change product behavior to support Python 3.9.

## Out of Scope

This gate must not introduce:

- active persistence rerouting
- no-plan ledger semantic changes
- Web or Tavily activation
- live LLM work
- UI same-truth work
- proactive, memory, rescue, or recommendation activation
- readiness or rollout claims
