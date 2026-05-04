# Accurate Intake MVP Parallel Tracks Status

This file is the shared context pack for parallel Accurate Intake MVP work.
It is project coordination truth, not product runtime truth.

Agents should read this file before starting a new Accurate Intake slice.
Agents should not replay full cross-window chat history by default.

## Current MVP Goal

Calorie Deficit Logging MVP local self-use foundation.

Goals:
- local web fake-LINE can log food
- daily kcal target can be set
- today consumed and remaining kcal can be queried
- chat history reload works
- Manager uses bounded current-session and current-day context
- FoodDB provides approved packet-ready evidence
- dogfood traces can be reviewed

Non-goals:
- no Kimi
- no GrokFast
- no live provider
- no LLM extraction
- no production DB
- no long-term memory
- no proactive, rescue, or recommendation behavior
- no product, web, private self-use, or production readiness claim

## Track Ownership

### Track FDB: FoodDB / Evidence Pipeline

Owns:
- raw source inventory
- FoodEvidenceCandidate schema
- adapters
- validators
- source quality and provenance
- auto-eligible and packet-ready candidate batches
- approved packet-ready evidence artifact

Must not touch:
- Product Loop UI
- Manager context runtime
- runtime mutation legality
- frontend behavior

Outputs consumed by:
- Product Loop via approved packet-ready evidence artifact
- runtime via stable NutritionEvidenceStorePort

### Track PL: Product Loop / Browser Shell

Owns:
- browser-executed local shell smoke
- TodaySummary, meal list, and pending draft display
- chat history reload UX
- fixture-evidence browser dogfood
- local dogfood export and backup UX

Must not touch:
- FoodEvidenceRecord schema
- PacketReadyAnchor schema
- NutritionEvidenceStorePort contract
- FoodDB truth
- Manager context policy

Outputs consumed by:
- integration dogfood later
- human/operator review

### Track CE: Context Engineering

Owns:
- ManagerContextPacket runtime integration
- context_policy_version in trace
- loaded_context_summary and omitted_context_summary
- pending follow-up and draft pins
- correction/removal target candidates

Must not touch:
- FoodDB truth
- Product Loop UI behavior beyond trace/read surfaces
- long-term memory
- proactive, rescue, or recommendation behavior

Outputs consumed by:
- Product Loop debug/review panel
- dogfood trace review
- Manager runtime

## Shared Interface Contracts

### Food Evidence Contract

Product Loop may consume only:
- approved packet-ready generic anchors/cards
- fixture packet-ready evidence for local diagnostic only

Product Loop must not consume:
- raw source files
- staging candidates
- validator-only candidates
- dogfood corrections
- food gap candidates as truth

### Context Contract

Manager input may include:
- current turn
- bounded recent chat
- pending follow-up and draft pins
- active day state
- budget summary
- target candidates

Manager input must exclude:
- debug artifacts
- dogfood review artifacts
- raw trace dumps
- FoodDB gap candidates
- full-day transcript by default
- long-term memory
- proactive, rescue, or recommendation context

### Product Loop Contract

Frontend may render:
- chat bubbles
- TodaySummary
- active meals/items
- pending draft/follow-up
- debug/review summaries from backend

Frontend must not infer:
- intent
- workflow
- target attachment
- kcal
- consumed/remaining
- mutation truth

## Shared Contract Change Gate

Stop and ask for human approval before changing any of:
- NutritionEvidenceStorePort
- FoodEvidenceRecord schema
- PacketReadyAnchor schema
- ManagerContextPacket schema
- packetizer accepted/rejected evidence format
- estimate output format
- basket semantics
- Food Evidence promotion policy

Do not use another track's missing output as permission to modify its internals.
Use fixture/mock evidence for local diagnostic work, or stop and wait for the producing track.

## Artifact Compatibility Gate

Every track output intended for another track must report:
- artifact name
- artifact path
- schema version
- fixture_or_real
- producer track
- intended consumers
- ready_for_other_tracks
- non_claims

If Product Loop uses fixture evidence, it must report:
- fixture_evidence_used: true
- real_fooddb_pass_claimed: false

If FoodDB produces packet-ready evidence, it must report:
- approved_packet_ready_evidence_artifact.path
- approved_packet_ready_evidence_artifact.schema_version
- approved_packet_ready_evidence_artifact.fixture_or_real
- approved_packet_ready_evidence_artifact.source_quality
- approved_packet_ready_evidence_artifact.ready_for_product_loop

If Context Engineering produces trace fields, it must report:
- context_trace_fields
- context_policy_version
- ready_for_review_panel

## Current Active Branches

### FDB Status

track: FDB
branch: not_reported_in_this_status_pack_yet
current_slice: not_reported_in_this_status_pack_yet
status: not_reported_in_this_status_pack_yet
expected_output: approved packet-ready evidence artifact
shared_contract_changed: false
blocked_by: not_reported_in_this_status_pack_yet

### PL Status

track: PL
branch: codex/pl1-browser-shell-smoke
current_slice: PL1-PL7_product_loop_local_web_shell_train
status: implemented_as_separable_commits_local_review_pending_not_merged
expected_output: artifacts/accurate_intake_browser_shell_smoke.json; artifacts/accurate_intake_browser_one_day_fixture_dogfood.json; artifacts/accurate_intake_browser_realistic_web_dogfood_v2.json; artifacts/accurate_intake_dogfood_operator_review_v2.json; artifacts/accurate_intake_product_loop_handoff_v3.json; local-only dogfood export/import-preview manifests
shared_contract_changed: false
blocked_by: none

### CE Status

track: CE
branch: not_reported_in_this_status_pack_yet
current_slice: not_reported_in_this_status_pack_yet
status: not_reported_in_this_status_pack_yet
expected_output: Manager context trace/read-surface fields
shared_contract_changed: false
blocked_by: not_reported_in_this_status_pack_yet

## Cross-Track Blockers

- If any track needs to change NutritionEvidenceStorePort, stop and ask.
- If any track needs to change PacketReadyAnchor schema, stop and ask.
- If any track needs to change ManagerContextPacket schema, stop and ask.
- If any track wants to claim dogfood pass, verify whether fixture evidence or real FoodDB evidence was used.
- If any track wants to promote FoodDB truth, require human approval gate.
- If any track wants to claim product, web, private self-use, or production readiness, stop and ask.

## Sync Protocol

Before starting a new slice:
1. Pull latest main or the agreed integration base.
2. Read this file.
3. Check whether your slice touches another track's owned area.
4. If yes, stop and ask.
5. If no, implement only your track's scope.

After finishing a slice:
1. Update only your track status block in this file if relevant.
2. Report branch, changed files, test results, artifact outputs, and interface changes.
3. Do not merge unless explicitly approved.

Agents may update only their own track status block:
- FoodDB agents may update only FDB Status.
- Product Loop agents may update only PL Status.
- Context Engineering agents may update only CE Status.

Agents must not change Track Ownership, Shared Interface Contracts, Shared Contract Change Gate, Artifact Compatibility Gate, or Cross-Track Blockers without human approval.

## Standard Slice Report

Use this shape when reporting a completed slice:

```yaml
track:
slice_id:
branch:
changed_files:
shared_contract_changed: true | false
artifact_outputs:
dependencies_for_other_tracks:
blocked_by:
tests:
non_claims:
pushed_sha:
```

## Startup Message For Parallel Agents

Use this prompt when starting any FDB, PL, or CE window:

```text
You are working in one track of the Accurate Intake MVP parallel-track plan.

Before implementation, read:
docs/quality/ACCURATE_INTAKE_PARALLEL_TRACKS_STATUS.md

You may modify only your track's ownership area.
If your work needs to change any shared contract, stop and report instead of editing:
- NutritionEvidenceStorePort
- FoodEvidenceRecord schema
- PacketReadyAnchor schema
- ManagerContextPacket schema
- packetizer accepted/rejected evidence format
- estimate output format
- basket semantics
- Food Evidence promotion policy

Do not run Kimi, GrokFast, live providers, LLM extraction, or production DB work.
Do not claim product, web, private self-use, or production readiness.
If your work needs another track's output, use fixture/mock data only for local diagnostics or stop and wait.
```
