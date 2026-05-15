# Wave 1 Phase B-2 P0 Execution Plan

> Default execution mode for this plan is interactive implementation. Overnight / approval-light execution is optional and, when intentionally used, should follow [docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md).

**Goal:** Build the minimum product-intelligence foundation for Wave 1 Phase B-2 without prematurely committing to live search, a giant nutrition DB, or a full ReAct retrieval agent.

**Architecture:** Start with contract correctness, packet safety, and retrieval intent. Add a small test-aligned anchor store and structured DB lookup first. Defer RAG or hybrid retrieval until contract, packet, and mismatch behavior are stable and corpus scale or recall failure justifies the extra complexity.

**Tech Stack:** Python runtime, existing Wave 1 smoke or readiness harnesses, synthetic packet tests, structured retrieval intent objects, small anchor fixtures, and optional bounded CLI/autonomy tooling only when explicitly chosen.

---

## Phase Boundary

This plan is for `Phase B-2 P0` only.

It does not include:

- live web search runtime
- live selected-extract runtime
- giant nutrition DB ingestion
- production accuracy claims
- full multi-hop ReAct retrieval

## Pre-step - B-1 Green Handoff Snapshot

Before `B2-001`, record the handoff snapshot as:

```yaml
b1_gate_scope: Phase B-1 minimal tool-loop full natural-probe
smoke_artifact:
readiness_artifact:
ready_for_phase_b1_implementation: true
blockers: []
not_claiming: whole Wave 1 completion
```

## Build Order Summary

1. freeze contracts
2. lock synthetic packet and mismatch oracles
3. add retrieval intent object
4. add small test-aligned anchor store
5. add structured DB lookup with alias and metadata filtering
6. add packet compression and deterministic hard recheck
7. add Pass 2 packet-based synthesis
8. add final logged or draft and follow-up mapping
9. reassess whether live search seam is justified
10. reassess whether large-corpus hybrid or RAG retrieval is justified

## RAG Adoption Trigger

Large-DB RAG or hybrid retrieval is not a P0 requirement.

RAG should enter only after `B2-005` and `B2-006` are stable enough that the system already knows:

- what retrieval intent object it is sending
- how candidates become packets
- how wrong-item and sibling-variant rejection works
- how final synthesis posture maps to logged vs draft

Introduce large-corpus retrieval only when one or more are true:

- alias plus metadata-filtered lookup starts missing too many valid candidates in evals
- the anchor corpus becomes large enough that manual alias or filter maintenance is no longer practical
- brand and menu corpora grow into semi-structured documents rather than simple rows
- lexical candidate generation is no longer enough for recall
- there is evidence that better retrieval recall is the actual bottleneck rather than packet policy or synthesis policy

When that trigger is reached, prefer:

- query-rewritten retrieval intent
- metadata or attribute filtering
- hybrid lexical plus semantic candidate generation
- packet-first synthesis

Do not jump directly to blind vector similarity without the existing packet and recheck layers.

## Task B2-001 - Freeze Phase B-2 Product Contracts

**Primary files:**

- [docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md)
- [docs/specs/WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md)
- [docs/specs/WAVE_1_EVIDENCE_PATH_SELECTION_MATRIX.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_EVIDENCE_PATH_SELECTION_MATRIX.md)

**Outcome:**

- contract alignment for:
  - `estimable -> logged`
  - `unresolved -> draft`
  - internal `provisional` posture
  - inference contract
  - packet usage classes
  - follow-up severity
- terminology diff table must be emitted with:
  - `term`
  - `canonical meaning`
  - `docs touched`
  - `old conflict`
  - `final wording`

**Completion criteria:**

- contract gaps are explicitly identified before edits
- no product-semantic contradiction remains across the three docs
- edits stay additive or explicit alignment only

**Verification expectation:**

- docs remain encoding-clean and semantically consistent

## Task B2-002 - Lock Synthetic Packet And Mismatch Oracles

**Primary files:**

- synthetic readiness verifier for B-2
- packet or mismatch-related tests under `tests/`
- [docs/specs/WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md)

**Outcome:**

- synthetic tests cover:
  - wrong item
  - sibling variant
  - wrong size
  - wrong modifier
  - insufficient evidence
  - snippet cannot become truth
- official producer writes both:
  - `artifacts/wave1_phase_b2_evidence_synthesis_smoke_<timestamp>.json`
  - `artifacts/wave1_phase_b2_evidence_synthesis_smoke.json`

**Completion criteria:**

- the smallest useful oracle scenario set is explicitly frozen
- tests enforce product truth instead of fixture accidents
- the slice stays limited to synthetic readiness cases and related docs or tests

**Verification expectation:**

- fake-green exact or packet paths are blocked

## Task B2-003 - Add Retrieval Intent Object

**Primary files:**

- future retrieval-intent builder module
- relevant Wave 1 B-2 synthetic tests
- [docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md)

**Outcome:**

- the system can normalize utterances into:
  - `base_dish`
  - `brand_hint`
  - `size_hint`
  - `modifier_hints`
  - `listed_items`
  - `retrieval_goal`
- `retrieval_goal` must stay an enum, not free-form natural language
- retrieval intent is not evidence verdict, not synthesis, and not mutation decision

**Completion criteria:**

- the minimal retrieval-intent field set is frozen
- this layer remains inference support, not hidden semantic rewriting
- implementation remains limited to the intent object and its tests

**Verification expectation:**

- the object covers the agreed case-law examples

## Task B2-004 - Add Small Test-Aligned Anchor Store

**Primary files:**

- future anchor fixtures or seed files
- relevant tests
- [docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md)

**Outcome:**

- minimal anchor store covers only:
  - high-frequency single items
  - high-frequency customizable drinks
  - high-frequency generic meals
  - stable-base variable dishes
  - listed-ingredient item anchors

**Completion criteria:**

- the initial anchor list is explicitly locked
- P0 stays test-aligned and does not drift toward giant DB ambition
- anchors carry only the needed modifier or composition metadata for this slice

**Verification expectation:**

- no anchor silently becomes product truth outside its role

## Task B2-005 - Add Structured DB Lookup

**Primary files:**

- future DB lookup module or retrieval surface
- tests for alias and metadata-filtered retrieval
- [docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md)

**Outcome:**

- DB retrieval supports:
  - canonical match
  - alias match
  - metadata filters
  - candidate-list trace

**Completion criteria:**

- the slice remains a structured lookup task, not a search-engine task
- wrong-item risk is reduced rather than hidden
- retrieval changes remain paired with candidate-trace tests

**Verification expectation:**

- candidate traces remain inspectable

## Task B2-006 - Add Packet Compression And Deterministic Hard Recheck

**Primary files:**

- packetizer or evidence-compression layer
- mismatch or rejection tests
- [docs/specs/WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_EVIDENCE_AND_SYNTHESIS_GATE.md)

**Outcome:**

- candidates become typed packets
- deterministic layer performs only:
  - normalization
  - exactness hard veto
  - snippet blocking
  - serving-basis or mismatch checks

**Completion criteria:**

- the exact deterministic guardrails for this layer are named and preserved
- semantic judgment does not leak into deterministic policy
- compression and hard recheck stay bounded to packet safety behavior

**Verification expectation:**

- rejected or downgraded candidates remain trace-visible

## Task B2-007 - Add Pass 2 Packet-Based Synthesis

**Primary files:**

- packet-based synthesis lane
- relevant packet tests
- [docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/specs/WAVE_1_PHASE_B2_PRODUCT_INTELLIGENCE_ARCHITECTURE_DRAFT.md)

**Outcome:**

- LLM Pass 2 can synthesize:
  - exactness posture
  - likely kcal
  - kcal range
  - uncertainty reason
  - follow-up targets

**Completion criteria:**

- the input contract remains packet-based, not raw result prose
- synthesis stays product-aligned and does not overclaim evidence
- the synthesis path remains trace-visible and packet-referenced

**Verification expectation:**

- packet refs, posture, and follow-up outputs are trace-clean

## Task B2-008 - Add Final Logged Or Draft And Follow-up Mapping

**Primary files:**

- final mapping layer
- mutation or renderer-related tests
- [docs/_spec_snapshots/legacy_v2_wave_pack_20260515/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md](../_spec_snapshots/legacy_v2_wave_pack_20260515/V2_WAVE_1_MINIMAL_IMPLEMENTATION_CONTRACTS.md) as historical reference only

**Outcome:**

- final mapping preserves:
  - `estimable -> logged`
  - `unresolved -> draft`
  - follow-up is not a commit gate

**Completion criteria:**

- the thin logged-vs-draft mapping rule is frozen
- no third status leaks into product behavior
- implementation stays minimal and mapping-focused

**Verification expectation:**

- logged vs draft behavior matches the agreed rule

## Task B2-009 - Decide Whether A Live Search Seam Is Worth Adding

**Primary files:**

- B-2 draft and gate docs
- future search seam design notes

**Outcome:**

- explicit decision:
  - defer live search
  - or proceed to a bounded selected-search seam

**Completion criteria:**

- evidence for or against live search is explicitly collected
- search is justified only as a real bottleneck fix, not as a substitute for missing contract clarity
- this slice remains docs or contract shaping only

**Verification expectation:**

- no live search runtime is silently introduced

## Task B2-010 - Reassess Large-DB RAG Or Hybrid Retrieval

**Primary files:**

- B-2 draft
- future retrieval design notes
- eval evidence showing lookup recall limits

**Outcome:**

- explicit adoption decision:
  - stay with structured alias or filter lookup
  - add hybrid retrieval
  - add metadata-aware semantic retrieval

**Completion criteria:**

- corpus and recall evidence is explicitly gathered
- the system does not vectorize unresolved semantics by default
- the decision and next-phase shape are recorded explicitly

**Verification expectation:**

- the trigger evidence for any retrieval expansion is explicit

## Optional Overnight / Approval-Light Mode

This plan may be executed interactively by default.

If the work is intentionally run overnight or with approval-light autonomy:

- use the bounded protocol from [docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md](/C:/Users/User/Documents/Playground/Agentic-Calorie-Assistant/docs/agent/OVERNIGHT_AUTONOMY_PROTOCOL.md)
- keep continuation bounded and trace-backed
- do not run free-form unattended chains across unresolved semantics

## Stop Conditions

Stop this plan immediately when:

- product semantics need a new decision
- source-priority rules need to change
- logged vs draft mapping becomes ambiguous
- packet ownership becomes unclear
- DB retrieval shape is no longer sufficient and RAG design is not yet approved
- verification no longer provides a clear pass or fail signal

## Immediate Recommended Starting Point

The recommended starting sequence is:

1. `B2-001`
2. `B2-002`
3. `B2-003`

This keeps Phase B-2 grounded in contract and oracle quality before any data-scale or retrieval-scale growth.
