# Protected Doc Rewrite Inventory 2026-04-17

## Purpose

This inventory records the protected benchmark artifact that was near-totally rewritten as part of the `L5D` suite-governance follow-through, so the rewrite can be committed with explicit semantic-coverage tracking.

## Rewritten Artifact

### `docs/quality/benchmarks/semantic_routing/semantic_routing_founder_fit_pack_v1.json`

Why it was rewritten:

- the file had already been heavily reshaped during the semantic-routing governance split
- this wave reclassified it under the new suite-governance layer as a provisional exploratory artifact rather than product-approved benchmark truth
- the rewrite was needed to keep the file internally consistent with:
  - `L6F_GLOBAL_ROUTING_GOVERNANCE_SPEC.md`
  - `SEMANTIC_ROUTING_EVAL_FOUNDATION.md`
  - `L5D_SUITE_GOVERNANCE_SPEC.md`

Semantic coverage preserved:

- semantic-routing remains eval-only, not production routing
- the pack remains founder-fit / exploratory in spirit
- the pack still preserves Rescue + Intake boundary-oriented cases
- primary oracle stays limited to:
  - target object
  - workflow ownership
  - disposition
  - workflow effect
- response-side distinctions remain secondary diagnostics only
- the pack remains non-canonical and cannot be treated as official product truth

Why this rewrite is acceptable:

- the rewrite did not collapse product semantics into new official truth
- it explicitly downgraded authority, which is safer than silently preserving a misleading canonical posture
- the official lane and candidate review queues now carry the promotion path instead
