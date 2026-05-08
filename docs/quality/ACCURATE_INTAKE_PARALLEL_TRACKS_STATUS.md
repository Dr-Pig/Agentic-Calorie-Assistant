# CurrentShell Parallel Tracks Status

This file is the shared context pack for Current Shell v1 coordination work.
It is project coordination truth, not product runtime truth.
The canonical machine track is `CurrentShell`.
`ManagerRuntime`, `AppShell`, and `SharedCurrentShell` are `CurrentShell` owner lanes, not top-level tracks.
`FoodDB` remains an independent truth-owner track.
Legacy `PLCE` / `PL+CE` / `PL_CE` wording remains compatibility vocabulary only for older artifacts and file paths; it is not the active ownership model.
Draft PR bodies plus CI are the live sync truth; this file is the rule map and handoff template.

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

### Track FoodDB: FoodDB / Evidence Pipeline

Owns:
- raw source inventory
- FoodEvidenceCandidate schema
- adapters
- validators
- source quality and provenance
- auto-eligible and packet-ready candidate batches
- approved packet-ready evidence artifact

Must not touch:
- AppShell UI
- Manager context runtime
- runtime mutation legality
- frontend behavior

Outputs consumed by:
- ManagerRuntime via approved packet-ready evidence artifact
- runtime via stable NutritionEvidenceStorePort

### CurrentShell Owner Lane ManagerRuntime: Upstream Runtime Contract Owner

Owns:
- intent, tool, and target posture decisions
- bounded context packet acceptance
- guard and mutation boundary decisions
- chat-first Manager-managed app-state tools outside FoodDB/Search Evidence
- renderer input basis
- runtime-backed journey gates and gate ledger
- downstream dependency contracts consumed by AppShell/browser gates

Must not touch:
- FoodEvidenceRecord schema
- PacketReadyAnchor schema
- NutritionEvidenceStorePort contract
- FoodDB truth
- FoodDB/WebSearch ranking or packet promotion
- frontend truth math
- AppShell-only rendering behavior

Outputs consumed by:
- AppShell browser/runtime-backed gates
- human/operator review
- later live-diagnostic gate review

### CurrentShell Owner Lane AppShell: Downstream Renderer / Browser Verifier

Owns:
- browser-executed local shell smoke
- Chat, Today, and Body render-only product pages
- TodaySummary, meal list, and pending draft display
- chat history reload UX
- fixture-evidence browser dogfood
- local dogfood export and backup UX
- render-only display of ManagerRuntime-supplied context status, pending state, and target-candidate strips
- AppShell/browser consumption of machine-readable Current Shell contracts and ManagerRuntime gates
- browser same-truth verification against backend/read-model/renderer structured fields

Must not touch:
- FoodEvidenceRecord schema
- PacketReadyAnchor schema
- NutritionEvidenceStorePort contract
- FoodDB truth
- FoodDB/WebSearch ranking or packet promotion
- mutation legality
- shared ManagerContextPacket contract shape without a human gate
- ManagerRuntime semantic ownership or runtime truth

Outputs consumed by:
- integration dogfood later
- human/operator review
- later live-diagnostic gate review

### CurrentShell Owner Lane SharedCurrentShell: Shared Coordination Artifacts

Owns:
- machine-readable coordination artifacts that AppShell and merge governance consume
- the shared CurrentShell sync contract and gate-ledger wiring
- PR metadata examples and active coordination guidance
- active coordination markdown that explains owner-lane boundaries without redefining runtime semantics

Must not touch:
- FoodDB truth
- ManagerRuntime semantic ownership or runtime truth
- AppShell-only rendering behavior
- candidate-bundle readiness claims

Outputs consumed by:
- ManagerRuntime and AppShell PR templates
- merge-governance normalization and queue-readiness checks
- human/operator review

## Shared Interface Contracts

### Food Evidence Contract

ManagerRuntime may consume only:
- approved packet-ready generic anchors/cards
- fixture packet-ready evidence for local diagnostic only

ManagerRuntime must not consume:
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

### AppShell Contract

Frontend may render:
- chat bubbles
- TodaySummary
- Body plan / weight read-model fields
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

ManagerRuntime may also own chat-first Manager-managed app-state tools outside FoodDB/Search Evidence:
- budget/day-status read-only tools
- body read-only tools and guarded observation recording surfaces
- calibration preview / pending proposal / stored proposal action surfaces, but only as the CurrentShell calibration proposal seam; full calibration activation remains deferred
- app usage/help answers

AppShell must not infer tool choice, target selection, mutation legality, or nutrition truth in the frontend.

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

If ManagerRuntime or AppShell uses fixture evidence, it must report:
- fixture_evidence_used: true
- it must not claim a real FoodDB pass

If FoodDB produces packet-ready evidence, it must report:
- approved_packet_ready_evidence_artifact.path
- approved_packet_ready_evidence_artifact.schema_version
- approved_packet_ready_evidence_artifact.fixture_or_real
- approved_packet_ready_evidence_artifact.source_quality
- approved_packet_ready_evidence_artifact.ready_for_product_loop (legacy compatibility field name; current consumers are ManagerRuntime and AppShell)

If ManagerRuntime produces trace fields, it must report:
- context_trace_fields
- context_policy_version
- ready_for_review_panel

## Current Active Branches

This section is a status-block template, not the live status board.
Live sync truth is Draft PR body plus CI state.

### FoodDB Status

track: FoodDB
owner_lane: not_applicable
branch: not_reported_in_this_status_pack_yet
current_slice: not_reported_in_this_status_pack_yet
status: not_reported_in_this_status_pack_yet
expected_output: approved packet-ready evidence artifact
shared_contract_changed: false
blocked_by: not_reported_in_this_status_pack_yet

### CurrentShell / ManagerRuntime Status

track: CurrentShell
owner_lane: ManagerRuntime
branch: update_only_when_reporting_your_current_pr_or_main_based_slice
current_slice: update_only_when_reporting_your_current_pr_or_main_based_slice
status: update_only_when_reporting_your_current_pr_or_main_based_slice
expected_output: runtime contracts, gate ledger entries, manager/tool diagnostics, renderer input basis, downstream dependency contracts
shared_contract_changed: false
blocked_by: update_only_when_reporting_your_current_pr_or_main_based_slice

### CurrentShell / AppShell Status

track: CurrentShell
owner_lane: AppShell
branch: update_only_when_reporting_your_current_pr_or_main_based_slice
current_slice: update_only_when_reporting_your_current_pr_or_main_based_slice
status: update_only_when_reporting_your_current_pr_or_main_based_slice
expected_output: browser/product-page artifacts, render-only shell gates, same-truth verification packs, local review packs
shared_contract_changed: false
blocked_by: update_only_when_reporting_your_current_pr_or_main_based_slice

### CurrentShell / SharedCurrentShell Status

track: CurrentShell
owner_lane: SharedCurrentShell
branch: update_only_when_reporting_your_current_pr_or_main_based_slice
current_slice: update_only_when_reporting_your_current_pr_or_main_based_slice
status: update_only_when_reporting_your_current_pr_or_main_based_slice
expected_output: sync contract updates, gate-ledger wiring, queue/governance metadata examples, active coordination guidance
shared_contract_changed: false
blocked_by: update_only_when_reporting_your_current_pr_or_main_based_slice

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
3. Open or update the PR, wait for checks, and use GitHub Merge Queue as the serial delivery path.

Agents may update only their own track status block:
- FoodDB agents may update only FoodDB Status.
- ManagerRuntime agents may update only CurrentShell / ManagerRuntime Status.
- AppShell agents may update only CurrentShell / AppShell Status.
- SharedCurrentShell agents may update only CurrentShell / SharedCurrentShell Status.

Agents must not change Track Ownership, Shared Interface Contracts, Shared Contract Change Gate, Artifact Compatibility Gate, or Cross-Track Blockers without human approval.

## Standard Slice Report

Use this shape when reporting a completed slice:

```yaml
track:
owner_lane:
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

Use this prompt when starting any FoodDB, ManagerRuntime, or AppShell window:

```text
You are working in one track of the Current Shell v1 split delivery plan.

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
