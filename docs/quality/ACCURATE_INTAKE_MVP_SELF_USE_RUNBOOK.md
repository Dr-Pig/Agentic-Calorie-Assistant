# Accurate Intake MVP Self-Use Runbook

This runbook is the human-readable operating record for the Accurate Intake MVP v1.8 local deterministic closure.
It is operator-shell supporting evidence, not the primary CurrentShell product-pages founder gate.

The claim scope: `local_deterministic_mvp_gate`.

## Scope

This runbook verifies the local product loop:

```text
input -> Manager structured decision -> evidence/packet support -> synthesis/final mapping -> commit/correction/removal -> budget/read model/debug surface
```

This is not product readiness, rollout readiness, live LLM readiness, web readiness, or production DB readiness.
Chat / Today / Body product-pages founder gating belongs to `docs/quality/ACCURATE_INTAKE_MVP_LIVE_DIAGNOSTIC_RUNBOOK.md` plus `product_pages_self_use_flow_gate`, `ui_context_alignment_pack`, and `browser_activation_evidence_gate`.

## Ownership Rules

- Manager structured decision fixtures own intent/workflow/target proposal.
- Deterministic runtime validates, rejects, downgrades unsafe mutations, and computes canonical state truth.
- Food evidence seeds are support-only: candidate evidence, semantic hints, portion/source provenance.
- Food evidence seeds cannot decide logged/draft/no_mutation, mutation legality, or ledger truth.
- Debug surface is read-only and mirrors canonical read models; it must not recompute consumed, remaining, overshoot, or correction targets.
- Explicit item removal is scoped to a unique target item via existing versioning; it is not hard delete, whole-meal undo, or a delete/void lifecycle.

## Fresh Checkout Commands

Run these from the repo root on Windows, macOS, Linux, Docker, or devcontainer environments with Python 3.12 configured:

```powershell
python -m pytest tests/test_accurate_intake_mvp_gate_runner.py tests/test_accurate_intake_mvp_ux_semantic_wall.py -q
python -m pytest tests/test_correction_commit_uow_adapter.py tests/test_accurate_intake_debug_surface.py -q
python -m pytest tests/test_product_loop_mvp_read_model.py tests/test_local_persistence_self_use.py tests/test_accurate_intake_mvp_self_use_smoke.py -q
python -m pytest tests/test_accurate_intake_mvp_self_use_scenario_wall.py -q
python -m pytest tests/test_food_knowledge_mvp_coverage.py tests/test_wave1_phase_b2_small_anchor_store.py tests/test_wave1_phase_b2_exact_item_card_lookup.py -q
python scripts/verify_accurate_intake_mvp.py --output artifacts/accurate_intake_mvp_gate.json
python scripts/run_accurate_intake_mvp_self_use_smoke.py
python scripts/run_accurate_intake_mvp_self_use_smoke.py --scenario-wall-v2
python scripts/run_accurate_intake_mvp_self_use_smoke.py --reopen-continuity
```

Run pytest groups sequentially on Windows. If a temporary SQLite file is locked, rerun the affected group after the prior process exits; do not classify that as product behavior evidence until the rerun result is known.

## Governance Wall

Before a PR or local closure claim, run:

```powershell
python scripts/check_layer_integrity.py
python scripts/check_runtime_boundaries.py
python scripts/audit_readiness_claim_integrity.py
python scripts/audit_deterministic_semantic_ownership.py --stage zero-high-risk
python scripts/audit_architecture_dependency_debt.py
lint-imports --config .importlinter
python scripts/check_markdown_encoding.py --policy-docs --require-bom
git diff --check
```

## Artifact Policy

Generated artifacts are local evidence, not repo truth.

Do not stage:

- `artifacts/accurate_intake_mvp_gate.json`
- `artifacts/accurate_intake_mvp_self_use_smoke.json`
- local SQLite files
- provider/live diagnostic outputs

Repo truth for this gate is the manifest, tests, runbook, canonical specs, and source code.

## Accurate Intake MVP v2.0 Scenario Wall

The Accurate Intake MVP v2.0 scenario wall expands the single local smoke into five deterministic Chinese self-use flows:

- `雞肉飯和湯 -> 雞肉飯少一點 -> 把湯拿掉 -> debug read`
- `珍珠奶茶 -> 半糖大杯`
- `滷味 -> 有豆干、海帶、貢丸`
- `今天吃了多少？`
- no-plan consumed query without target or remaining claims

The scenario wall remains local deterministic evidence. It uses Manager structured fixtures for intent, workflow, target proposal, and read-only query posture. The deterministic runner validates, rejects unsafe mutation, and computes canonical state/read-model truth; it must not route from raw text keywords or fabricate missing Manager semantic fields.

The scenario-wall JSON also includes an `operator_transcript` compact review view. This operator transcript is read-only and derived from existing scenario evidence: Manager decisions, runtime validation, state-before/state-after summaries, and canonical debug same-truth output. It is for human/operator review only and does not create a new truth surface.

After running the scenario wall against a local SQLite DB, run `python scripts/run_accurate_intake_mvp_self_use_smoke.py --reopen-continuity` against the same DB path to verify reopen continuity. The continuity report is read-only: it checks reloaded canonical meal versions, ledger audit event counts, no-plan posture, and same-truth summaries without adding another meal, correction, or draft.

Run it with:

```powershell
python scripts/run_accurate_intake_mvp_self_use_smoke.py --scenario-wall-v2
python scripts/run_accurate_intake_mvp_self_use_smoke.py --reopen-continuity
```

## Local Self-Use Shell And Candidate Packet

The local self-use operator shell is the deterministic dogfood surface for the one-day scenario. It defaults to fixture Manager mode and blocks unknown scenarios instead of parsing arbitrary raw text into intent, workflow, target attachment, or mutation disposition.

The local browser shell is available at:

```text
/static/accurate-intake-local-shell.html
```

This browser shell is an operator mirror for local dogfood only. It is backend-current-day only until `/estimate` has an explicit local-date contract. It first asks `/today/current-budget` for the backend `local_date`, then uses that date for debug, chat-history, and manual target follow-up calls. It posts raw chat text to `/estimate`, renders `/today/current-budget`, `/body-plan/active`, `/accurate-intake/debug`, and `/accurate-intake/chat-history`, and calls `/body-plan/manual-daily-target` for manual target updates. The browser shell must not infer intent, workflow, target attachment, disposition, kcal, consumed, remaining, follow-up semantics, or overshoot from raw text; those remain backend/runtime/read-model truth.

Conversation context for this shell is current-session/current-day only. Backend `/estimate` writes user and assistant messages to local SQLite `message_buffer` with a runtime-turn trace that links chat message, Manager decision, evidence packet, final mapping, state-before, state-after, and context snapshot. `/accurate-intake/chat-history` reads that SQLite surface back for rendering. This is not long-term memory, proactive behavior, rescue, or recommendation.

Manager Context Policy v1 is the MVP manager-input policy for this current-session/current-day shell. It keeps context structured-state-first: current turn, bounded recent chat, pending follow-up/draft pins, active day state, budget summary, and structured correction/removal target candidates may enter the Manager packet as read-only support evidence. Debug artifacts, dogfood review artifacts, raw trace dumps, FoodDB gap candidates, full-day transcript by default, long-term memory, proactive context, rescue context, and recommendation context are omitted from Manager input. The helper is `build_manager_context_packet_v1`; it does not authorize mutation, promote FoodDB truth, or create a parallel persistence truth surface.

Free-text daily target updates may enter through `/estimate` only when the Manager structured decision returns `intent_type=set_manual_daily_target` with an explicit `daily_target_kcal`. The browser shell must not keyword-route target text. The backend validates the target through the existing manual target service, blocks unsafe or ambiguous targets without food mutation, and keeps target calculation / TDEE automation out of this MVP.

Run the local browser-shell route-bridge smoke with:

```powershell
python scripts/run_accurate_intake_local_web_shell_smoke.py --db-path .pytest_tmp_local/accurate_intake_local_web_shell_bridge.sqlite3 --output artifacts/accurate_intake_local_web_shell_bridge.json
```

This route-bridge smoke proves static shell availability and backend route compatibility under deterministic Manager fixtures. It does not execute browser JavaScript; browser-executed fetch sequencing remains a separate UI QA/browser-automation slice before any web-readiness claim.

Run the chat-history reload gate with:

```powershell
python scripts/run_accurate_intake_chat_history_reload_gate.py --db-path .pytest_tmp_local/accurate_intake_chat_history_reload_gate.sqlite3 --output artifacts/accurate_intake_chat_history_reload_gate.json
```

This reload gate writes a CJK chat turn through `/estimate`, closes the first local app/session, reopens the same SQLite DB, and verifies `/accurate-intake/chat-history`, `/today/current-budget`, and `/accurate-intake/debug` from the reopened backend surfaces. It proves current-session/current-day transcript and runtime-turn trace linkage survive local reload; it is not browser execution, long-term memory, live LLM, Web/Tavily, production DB, or web-readiness evidence.

Run the optional browser-executed shell smoke with:

```powershell
python scripts/run_accurate_intake_browser_shell_smoke.py --db-path .pytest_tmp_local/accurate_intake_browser_shell_smoke.sqlite3 --output artifacts/accurate_intake_browser_shell_smoke.json
```

This smoke executes the local shell in a real Chromium browser only when Playwright is available in the operator environment. If Playwright is not installed, the artifact is `blocked` with `browser_executed=false`; that blocked artifact is allowed for local deterministic PR evidence and still must not claim `web_ready`. To require browser execution explicitly, add `--require-browser-execution`. A passing browser artifact only proves local browser fetch/render/CJK behavior for this shell; it is not a product, rollout, live LLM, Web/Tavily, or production DB readiness claim.

Run the browser realistic local dogfood diagnostic v2 with:

```powershell
python scripts/run_accurate_intake_browser_realistic_web_dogfood_v2.py --require-browser-execution --db-path .pytest_tmp_local/accurate_intake_browser_realistic_web_dogfood_v2.sqlite3 --output artifacts/accurate_intake_browser_realistic_web_dogfood_v2.json
```

This browser diagnostic drives the local shell through a target update and CJK food/query turns with deterministic fixture Manager decisions and fixture evidence only. Its success status is `browser_diagnostic_pass_with_fixture_evidence_gap` or `browser_diagnostic_pass_with_evidence_gap`; it must not emit `pass`, `dogfood_pass`, `realistic_pass`, or `fooddb_pass`. The fixture Manager can provide structured Manager decisions, and fixture evidence can simulate packet-ready evidence for local diagnostics only; those fixtures must not become FoodDB truth or update app knowledge.

Run a fresh local shell pass with:

```powershell
python scripts/run_accurate_intake_local_self_use_shell.py --scenario one_day_v1 --db-path .pytest_tmp_local/accurate_intake_self_use.sqlite --reset-db --output artifacts/accurate_intake_local_self_use_shell.json --print-debug-surface
```

Run reopen continuity against the same local SQLite DB with:

```powershell
python scripts/run_accurate_intake_local_self_use_shell.py --scenario one_day_v1 --db-path .pytest_tmp_local/accurate_intake_self_use.sqlite --keep-db --output artifacts/accurate_intake_local_self_use_shell_keep.json --print-debug-surface
```

Inspect local dogfood DB hygiene before reset or export with:

```powershell
python scripts/manage_accurate_intake_local_dogfood_data.py --operation inspect --db-path workspace_data/local_dogfood/accurate_intake.sqlite3 --output artifacts/accurate_intake_local_dogfood_data_hygiene.json
```

The inspect, backup, and export manifests must include source DB file metadata: `db_exists`, `db_size_bytes`, and `db_modified_at_utc`. Use those fields to confirm which local SQLite file was protected before reset or review export.

Back up real dogfood SQLite data before any reset with:

```powershell
python scripts/manage_accurate_intake_local_dogfood_data.py --operation backup --db-path workspace_data/local_dogfood/accurate_intake.sqlite3 --backup-dir workspace_data/local_dogfood_backups --label before-reset --output artifacts/accurate_intake_local_dogfood_backup.json
```

Export a local-only SQLite copy plus manifest for operator review or handoff inspection with:

```powershell
python scripts/manage_accurate_intake_local_dogfood_data.py --operation export --db-path workspace_data/local_dogfood/accurate_intake.sqlite3 --export-dir workspace_data/local_dogfood_exports --label review --output artifacts/accurate_intake_local_dogfood_export.json
```

Preview an export before any manual restore/import workflow with:

```powershell
python scripts/manage_accurate_intake_local_dogfood_data.py --operation import-preview --db-path workspace_data/local_dogfood/accurate_intake.sqlite3 --import-manifest workspace_data/local_dogfood_exports/accurate_intake.review.YYYYMMDDTHHMMSSZ.manifest.json --output artifacts/accurate_intake_local_dogfood_import_preview.json
```

Fixture and smoke DB paths under `.pytest_tmp_local` are disposable. Real dogfood DB paths under `workspace_data/local_dogfood` or explicitly named `real_dogfood` require backup before reset. Dogfood SQLite files, backups, JSONL exports, and generated hygiene manifests can contain personal diet logs; they are local-only and must not be committed.

Build the human-reviewable candidate packet with:

```powershell
python scripts/build_accurate_intake_local_self_use_candidate.py --shell-artifact artifacts/accurate_intake_local_self_use_shell.json --output artifacts/accurate_intake_local_self_use_candidate.json
```

The candidate packet may set `local_self_use_candidate_prepared=true` when the deterministic shell evidence is clean. It remains a local review packet only and must not claim private self-use approval, product readiness, production selection, or live-manager escalation.

Build the v2 aggregated web candidate packet with:

```powershell
python scripts/build_accurate_intake_local_web_self_use_candidate_v2.py --evidence-json path/to/all_evidence.json --output artifacts/accurate_intake_local_web_self_use_candidate_v2.json
```

The v2 packet aggregates evidence from PR103-PR108 and checks for clean status across all required gates. It must not unlock private self-use approval or product readiness claims.


Build a local-only review artifact from runtime-turn traces with:

```powershell
python scripts/build_accurate_intake_dogfood_review_queue.py --trace-json path/to/runtime_turn_trace.json --output artifacts/accurate_intake_dogfood_review_queue.json
```

This local-only review artifact is dogfood triage material. It may mark `review_candidate` records from deterministic flags or reviewer-agent suggestions, but raw traces remain observation only and cannot become Food KB truth, golden truth, or canonical eval cases without human approval, product semantic source, stable expected behavior, and eval registration. The artifact can contain personal diet logs; keep it local and do not commit generated review artifacts.

Build the operator review surface from the one-day realistic dogfood diagnostic with:

```powershell
python scripts/build_accurate_intake_dogfood_operator_review.py --dogfood-json artifacts/accurate_intake_one_day_realistic_web_dogfood.json --output artifacts/accurate_intake_dogfood_operator_review.json
```

For the browser realistic v2 diagnostic, use the same builder against the browser artifact:

```powershell
python scripts/build_accurate_intake_dogfood_operator_review.py --dogfood-json artifacts/accurate_intake_browser_realistic_web_dogfood_v2.json --output artifacts/accurate_intake_dogfood_operator_review_v2.json
```

This surface is a local-only triage view. It may classify turns as target update success, food evidence gap, blocked mutation, query/no-mutation, unsupported intent, manager/context gap, or not checked using structured artifact fields only. Runtime error / missing-payload status may classify a turn as `manager_context_gap`; raw user text and assistant text are display-only. Browser v2 manager context status is limited to `not_available`, `not_checked`, or `missing_context_snapshot`; this is diagnostic-only and must not claim a Context Engineering fault. The surface must not recompute kcal, update Food KB truth, promote canonical eval cases, or convert `diagnostic_pass_with_evidence_gap` or `browser_diagnostic_pass_with_fixture_evidence_gap` into `pass`.

Build the minimal approved packet-ready FoodDB artifact from the existing exact item seed lane with:

```powershell
python scripts/build_accurate_intake_approved_packet_ready_fooddb_artifact.py --output artifacts/accurate_intake_approved_packet_ready_fooddb_artifact.json
```

This artifact is the first real FoodDB handoff input for Current Shell validation. It selects a minimal three-lane packet set: one tracked exact item card with kcal plus complete label macros, one approved generic common-serving anchor with kcal/range and macro values preserved as null/unknown, and one approved listed-component anchor with kcal/range and macro values preserved as null/unknown. It reports `fixture_or_real=real`, includes the `macro_contract` required by the Current Shell handoff, and exposes lane counts for exact / generic / listed-component coverage. It does not broaden FoodDB coverage, ingest WebSearch, promote raw source rows, update runtime truth, or claim dogfood pass.

Build the legacy-named CurrentShell/FoodDB handoff v3 metadata gate without the FoodDB artifact to keep the previous blocked posture, or with the minimal approved artifact to validate the handoff:

```powershell
python scripts/build_accurate_intake_product_loop_handoff_v3.py --browser-shell-smoke artifacts/accurate_intake_browser_shell_smoke.json --local-web-candidate artifacts/accurate_intake_local_web_self_use_candidate_v2.json --browser-fixture-dogfood artifacts/accurate_intake_browser_one_day_fixture_dogfood.json --local-dogfood-hygiene artifacts/accurate_intake_local_dogfood_export.json --browser-realistic-dogfood artifacts/accurate_intake_browser_realistic_web_dogfood_v2.json --operator-review artifacts/accurate_intake_dogfood_operator_review_v2.json --mvp-gate artifacts/accurate_intake_mvp_gate.json --output artifacts/accurate_intake_product_loop_handoff_v3.json
python scripts/build_accurate_intake_product_loop_handoff_v3.py --browser-shell-smoke artifacts/accurate_intake_browser_shell_smoke.json --local-web-candidate artifacts/accurate_intake_local_web_self_use_candidate_v2.json --browser-fixture-dogfood artifacts/accurate_intake_browser_one_day_fixture_dogfood.json --local-dogfood-hygiene artifacts/accurate_intake_local_dogfood_export.json --browser-realistic-dogfood artifacts/accurate_intake_browser_realistic_web_dogfood_v2.json --operator-review artifacts/accurate_intake_dogfood_operator_review_v2.json --mvp-gate artifacts/accurate_intake_mvp_gate.json --fooddb-artifact artifacts/accurate_intake_approved_packet_ready_fooddb_artifact.json --output artifacts/accurate_intake_product_loop_handoff_v3.json
```

The handoff gate is validation-only. It requires the local web self-use candidate so the FoodDB handoff sees the same AppShell browser evidence chain used by Chat / Today / Body gates. Without a FoodDB artifact it stays blocked with `fooddb_artifact_status=blocked_waiting_for_fdb_artifact` and `ready_for_fdb_integration=false`. Fixture FoodDB evidence remains fixture-only and cannot be presented as a real FoodDB pass. Invalid FoodDB metadata blocks the gate and must not trigger auto-fix or FoodDB truth updates. Approved real FoodDB metadata must include `macro_contract` packet fields for `protein_g`, `carbs_g`, `fat_g`, `macro_visibility_status`, `macro_source_basis`, and `macro_confidence`, with missing macro values preserved as null/unknown rather than invented.

The same `macro_contract` must also include a shadow-only `shadow_schema` for FoodDB expansion. It reserves generic common serving point/range fields, listed component per-unit fields, exact label fields, empty basket/alias/modifier macro truth, and source-evidence candidate fields such as per-100g source values. This schema is not runtime promotion; it only lets FoodDB expand data without forcing ManagerRuntime or AppShell to accept unapproved macro truth.

Build the Food KB gap register from the operator review surface with:

```powershell
python scripts/build_accurate_intake_food_gap_register.py --operator-review-json artifacts/accurate_intake_dogfood_operator_review.json --output artifacts/accurate_intake_food_kb_gap_register.json
```

This register turns `food_evidence_gap` review turns into `review_candidate` records only. It may carry display-only user text for human review, but it must not update Food KB truth, create nutrition seeds, create exact cards, create packet truth, or promote canonical eval oracles. Manager context/runtime gaps and query/no-mutation turns remain non-candidates until the upstream blocker is reviewed.

Refresh the Food KB source-quality inventory with:

```powershell
python scripts/build_accurate_intake_food_kb_inventory.py --food-gap-register artifacts/accurate_intake_food_kb_gap_register.json --output docs/quality/accurate_intake_food_kb_v1_inventory.json
```

This inventory is the pre-expansion source-quality gate. It records source classes, required provenance, confidence posture, current seed/card counts, basket component count, missing source metadata, and optional PR112 gap candidate counts. It does not promote a gap candidate into Food KB truth; any future promotion needs human review and a source class that satisfies the policy.

Build the FoodDB quality improvement plan with:

```powershell
python scripts/build_accurate_intake_fooddb_quality_plan.py --inventory-json docs/quality/accurate_intake_food_kb_v1_inventory.json --food-gap-register artifacts/accurate_intake_food_kb_gap_register.json --output artifacts/accurate_intake_fooddb_quality_plan.json
```

This plan is review packets only. It may identify the first review batch families such as breakfast combo, chicken bento rice modifier, bubble tea sugar/size modifier, and luwei listed components, but it must not update FoodDB truth, create nutrition seeds, create exact cards, or claim one-day dogfood pass. LLM extraction may normalize candidate labels, source hints, or portion candidates for review, but deterministic promotion policy and human approval are required before any seed, exact card, or packet truth promotion.

PR117 adds a raw source inventory/registry foundation for the FoodDB ingestion pipeline stage boundary:

```text
raw source -> candidate -> validator_passed -> auto_eligible_packet_candidate -> packet_ready
```

Build the local raw source inventory with:

```powershell
python scripts/build_accurate_intake_food_raw_source_inventory.py --scan-root path\to\local\data --scan-root path\to\local\staging --output artifacts/accurate_intake_food_raw_source_inventory.json
```

The generated inventory is local-only and ignored. The tracked registry is `docs/quality/accurate_intake_food_raw_source_registry.json`; it records known source filenames, source classes, and intended candidate roles only. This PR117 boundary does not create candidates, packet-ready anchors/cards, nutrition seeds, exact cards, packet truth, runtime truth, or canonical eval oracles.

PR118 advances one stage to `FoodEvidenceCandidate` normalization only:

```powershell
python scripts/build_accurate_intake_food_evidence_candidates.py --scan-root path\to\local\data --scan-root path\to\local\staging --output artifacts/accurate_intake_food_evidence_candidates.json
```

The generated candidate artifact is local-only and ignored. `FoodEvidenceCandidate` rows may normalize labels, aliases, source class, serving basis, kcal point, and provenance from known raw/staging sources, but every row remains candidate-only and outside runtime truth. This PR118 boundary does not create validator-passed rows, auto-eligible packet candidates, packet-ready anchors/cards, nutrition seeds, exact cards, packet truth, runtime truth, or canonical eval oracles.

PR119 validates candidates and reports PR110 coverage diagnostics only:

```powershell
python scripts/build_accurate_intake_food_evidence_validation.py --candidate-json artifacts/accurate_intake_food_evidence_candidates.json --food-gap-register artifacts/accurate_intake_food_kb_gap_register.json --output artifacts/accurate_intake_food_evidence_validation.json
```

The generated validation artifact is local-only and ignored. It may mark candidate rows as `validator_passed`, `rejected`, or `needs_source_repair` using provenance, serving basis, kcal sanity, source class compatibility, parse-error repair, and duplicate/alias collision checks. `validator_passed` is still not packet-ready truth: validated rows remain outside runtime truth, do not update FoodDB truth, and cannot create nutrition seeds, exact cards, packet truth, runtime truth, or canonical eval oracles.

PR120 builds the stop-gate batch report before any FoodDB truth promotion:

```powershell
python scripts/build_accurate_intake_food_auto_eligible_batch.py --validation-json artifacts/accurate_intake_food_evidence_validation.json --output artifacts/accurate_intake_food_auto_eligible_batch.json --sample-size-per-group 10
```

The generated auto-eligible artifact is local-only and ignored. It may classify a subset of `validator_passed` rows as `auto_eligible_packet_candidate` and attach approval metadata for batch review, exception reporting, and sample audit. `auto_eligible_packet_candidate` is still not packet-ready truth: it remains outside runtime truth, and PR121 must not begin until the batch policy, exception report, and sample audit are reviewed. PR120 must not update FoodDB truth, create nutrition seeds, exact cards, packet truth, runtime truth, or canonical eval oracles.

PR121 promotes selected TFDA-backed MVP evidence in two separate runtime roles:

```powershell
python scripts/build_accurate_intake_tfda_batch_promotion.py --candidate-json artifacts/accurate_intake_food_evidence_candidates.json --auto-eligible-json artifacts/accurate_intake_food_auto_eligible_batch.json --source-evidence-output app/knowledge/tfda_per100g_source_evidence_tw.json --anchor-output artifacts/accurate_intake_tfda_selected_common_serving_anchors.json --report-output artifacts/accurate_intake_tfda_batch_promotion.json --update-small-anchor-store
```

The tracked TFDA per-100g file is `source_evidence_only`: it may preserve TFDA provenance and kcal-per-100g evidence, but it remains evidence-only rather than a runtime estimate or packetizer-serving source. It is not a user-facing serving estimate, packet truth, exact card, nutrition seed, or canonical eval oracle.

Only selected MVP portion-default anchors may become `common_serving_anchor` records in the small-anchor store. Each selected runtime anchor must carry `serving_basis`, `portion_basis`, `kcal_point`, `kcal_range`, source provenance/source refs back to `source_evidence_only`, range policy, approval metadata, and `runtime_truth_allowed=true`. PR121 must not promote all TFDA rows to runtime truth, must not consume official brand/Open Food Facts/USDA/old base candidates, and must not change basket semantics: bare baskets still ask follow-up, while listed baskets can only estimate components that already have approved runtime anchors.

Build the First Food Evidence human review pack with:

```powershell
python scripts/build_accurate_intake_food_evidence_human_review_pack.py --food-gap-register artifacts/accurate_intake_food_kb_gap_register.json --inventory-json docs/quality/accurate_intake_food_kb_v1_inventory.json --quality-plan-json artifacts/accurate_intake_fooddb_quality_plan.json --output artifacts/accurate_intake_food_evidence_human_review_pack.json
```

This review pack is the human decision surface before any first-batch FoodDB truth promotion. It groups PR110/PR112 gap candidates into the first review families and keeps every candidate in review-candidate-only status. Raw user text remains display-only; candidate grouping comes from structured gap-register fields. The pack must not update FoodDB truth, create nutrition seeds, create exact cards, create packet truth, promote canonical eval truth, or claim one-day dogfood pass.

SQLite-backed route/integration tests should use the shared `LocalSQLiteRouteHarness` when adding new route-level tests. JSON artifact producers should use `write_json_artifact` / `read_json_artifact` to avoid producer-consumer drift such as literal `"\\n"` suffixes. Unit tests should consume fixed artifact dictionaries where possible; DB-heavy scenario runners should be integration-scoped and run sequentially on Windows.

Windows operators should run SQLite-backed commands sequentially. If `.pytest_tmp_local` reports a temporary SQLite lock, wait for the previous process to exit and rerun the affected command before classifying the result. Do not run the reset and keep-db shell commands concurrently against the same DB path.

macOS, Linux, Docker, and devcontainer operators should use the same commands after the Python 3.12 environment is active. Docker/devcontainer usage is for environment parity only; it does not change the local deterministic claim scope.

For local backup, copy the SQLite DB file before running `--reset-db`. Local DB files and generated artifacts remain local-only evidence; repo truth is scripts, tests, docs, manifests, and canonical specs.

## Explicit Non-Goals

- No live LLM.
- No Tavily/web product truth.
- No Supabase/Postgres production schema.
- No polished UI.
- No user-facing rollout.
- No shadow/canary approval.
- No production model selection.
