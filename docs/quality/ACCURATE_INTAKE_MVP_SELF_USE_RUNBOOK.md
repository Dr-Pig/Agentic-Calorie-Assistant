# Accurate Intake MVP Self-Use Runbook

This runbook is the human-readable operating record for the Accurate Intake MVP v1.8 local deterministic closure.

The claim scope: `local_deterministic_mvp_gate`.

## Scope

This runbook verifies the local product loop:

```text
input -> Manager structured decision -> evidence/packet support -> synthesis/final mapping -> commit/correction/removal -> budget/read model/debug surface
```

This is not product readiness, rollout readiness, live LLM readiness, web readiness, or production DB readiness.

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

Run a fresh local shell pass with:

```powershell
python scripts/run_accurate_intake_local_self_use_shell.py --scenario one_day_v1 --db-path .pytest_tmp_local/accurate_intake_self_use.sqlite --reset-db --output artifacts/accurate_intake_local_self_use_shell.json --print-debug-surface
```

Run reopen continuity against the same local SQLite DB with:

```powershell
python scripts/run_accurate_intake_local_self_use_shell.py --scenario one_day_v1 --db-path .pytest_tmp_local/accurate_intake_self_use.sqlite --keep-db --output artifacts/accurate_intake_local_self_use_shell_keep.json --print-debug-surface
```

Build the human-reviewable candidate packet with:

```powershell
python scripts/build_accurate_intake_local_self_use_candidate.py --shell-artifact artifacts/accurate_intake_local_self_use_shell.json --output artifacts/accurate_intake_local_self_use_candidate.json
```

The candidate packet may set `local_self_use_candidate_prepared=true` when the deterministic shell evidence is clean. It must keep `private_self_use_approved=false`, `product_readiness_claimed=false`, `production_selected=false`, and `live_manager_required=false`.

Build a local-only review artifact from runtime-turn traces with:

```powershell
python scripts/build_accurate_intake_dogfood_review_queue.py --trace-json path/to/runtime_turn_trace.json --output artifacts/accurate_intake_dogfood_review_queue.json
```

This local-only review artifact is dogfood triage material. It may mark `review_candidate` records from deterministic flags or reviewer-agent suggestions, but raw traces remain observation only and cannot become Food KB truth, golden truth, or canonical eval cases without human approval, product semantic source, stable expected behavior, and eval registration. The artifact can contain personal diet logs; keep it local and do not commit generated review artifacts.

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
