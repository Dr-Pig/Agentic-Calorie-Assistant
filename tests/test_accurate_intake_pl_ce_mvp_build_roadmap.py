from __future__ import annotations

from pathlib import Path


ROADMAP_PATH = Path("docs/quality/ACCURATE_INTAKE_PL_CE_MVP_BUILD_ROADMAP.md")
LIVE_RUNBOOK_PATH = Path("docs/quality/ACCURATE_INTAKE_MVP_LIVE_DIAGNOSTIC_RUNBOOK.md")


def test_pl_ce_roadmap_doc_exists_with_utf8_bom_and_track_split() -> None:
    raw = ROADMAP_PATH.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig")

    assert "CurrentShell Coordination Roadmap" in text
    assert "legacy-path document records the CurrentShell coordination map" in text
    assert "canonical track is `CurrentShell`" in text
    assert "CurrentShell owner lanes are `ManagerRuntime`, `AppShell`, and `SharedCurrentShell`" in text
    assert "merged legacy PL+CE checkpoint train" in text
    assert "PR508: pre-live artifact refresh chain" in text
    assert "FoodDB/Search Evidence owns retrieval, ranking" in text
    assert "ManagerRuntime owns upstream runtime contracts" in text
    assert "AppShell owns downstream browser verification" in text
    assert "FoodDB remains an independent truth-owner track." in text
    assert "blocked_waiting_for_fdb_artifact" in text
    assert "no Kimi full E2E" in text
    assert "no Tavily/WebSearch runtime calling" in text
    assert "human-approved live-diagnostic only" in text
    assert "provider health smoke" in text
    assert "schema contract probe" in text
    assert "context-only single-case live probe" in text
    assert "Merge Queue Delivery Policy" in text
    assert "mode: merge_queue_serial" in text
    assert "Add to Merge Queue" in text
    assert "wait for PR state MERGED" in text
    assert "do not use main-merge-lock" in text
    assert "cleanup only after merged and clean" in text
    assert "dependent_child_pr" in text
    assert "mode: stop_for_human_gate" in text


def test_pl_ce_roadmap_doc_records_best_practice_sources_and_non_claims() -> None:
    text = ROADMAP_PATH.read_text(encoding="utf-8-sig")

    for fragment in (
        "https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/",
        "https://developers.openai.com/api/docs/guides/function-calling",
        "https://developers.openai.com/api/docs/guides/structured-outputs",
        "https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents",
        "https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview",
        "must stay non-promotional",
        "must not claim product readiness, private self-use approval, real FoodDB pass, dogfood pass, live LLM truth ownership, web/Tavily truth use, production DB truth, FoodDB truth updates, or manager-context schema advancement",
    ):
        assert fragment in text


def test_pl_ce_roadmap_doc_records_non_fooddb_manager_tool_convergence() -> None:
    text = ROADMAP_PATH.read_text(encoding="utf-8-sig")

    for fragment in (
        "Non-FoodDB Manager Tool Convergence",
        "ManagerRuntime owns the chat-first Manager-managed tool surface for app-state capabilities outside FoodDB/Search Evidence.",
        "`budget.get_today_summary`",
        "`budget.get_remaining_calories`",
        "`budget.get_day_meal_log`",
        "`body.get_active_plan`",
        "`body.get_latest_observation`",
        "`body.record_observation`",
        "`calibration.preview_proposal`",
        "`calibration.get_pending_proposal`",
        "`calibration.apply_stored_proposal_action`",
        "`app.answer_usage_question`",
        "read_only",
        "proposal_persisting",
        "mutation_bearing",
        "Manager Tool Surface Inventory / Direct Lane Audit",
        "Non-FoodDB Manager Tool Contract",
        "Manager Tool-Choice Regression Wall",
        "Context-Conditioned Intent + Target Wall",
        "Read-Only Tool Loop Fake Smoke",
        "Proposal / Mutation Tool Guard Smoke",
        "Legacy `PLCE` Pre-FoodDB Candidate Bundle",
    ):
        assert fragment in text


def test_pl_ce_roadmap_doc_records_semantic_owner_boundary_for_tool_choice() -> None:
    text = ROADMAP_PATH.read_text(encoding="utf-8-sig")

    for fragment in (
        "Manager owns natural-language intent, tool choice, target posture, and final response planning.",
        "Deterministic code may provide context, candidates, schemas, allowed tool lists, validation, guard results, and canonical tool results.",
        "Deterministic code must not infer final intent, choose the final tool, select the final target, or authorize mutation from raw text.",
        "UI may render backend/read-model/trace structured fields only.",
        "FoodDB/Search Evidence still owns nutrition retrieval, ranking, packet-ready evidence, WebSearch candidate evidence, and runtime-visible nutrition truth.",
    ):
        assert fragment in text


def test_pl_ce_roadmap_doc_records_machine_readable_current_shell_coordination_artifacts() -> None:
    text = ROADMAP_PATH.read_text(encoding="utf-8-sig")

    for fragment in (
        "Current-Shell Coordination Artifacts",
        "SharedCurrentShell owns the machine-readable coordination artifacts",
        "CURRENT_SHELL_SYNC_CONTRACT.yaml",
        "MANAGER_RUNTIME_GATE_LEDGER.yaml",
        "downstream AppShell/browser gates and merge-governance checks should read instead of inferring runtime readiness from markdown prose alone",
    ):
        assert fragment in text


def test_pl_ce_roadmap_doc_marks_plce_as_legacy_umbrella_vocabulary() -> None:
    text = ROADMAP_PATH.read_text(encoding="utf-8-sig")

    for fragment in (
        "The file path retains `PL_CE` for compatibility",
        "Legacy `PLCE` / `PL+CE` / `PL_CE` wording remains compatibility vocabulary only for old paths and artifacts; it is not the canonical track model.",
        "AppShell must not invent runtime semantics, frontend truth math, or mutation legality.",
        "Every legacy `PL+CE` / `CurrentShell` compatibility artifact must stay non-promotional.",
        "the compatibility artifact `current_shell_compatibility_local_review_decision_pack` is green (legacy input alias: `pl_ce_local_review_decision_pack`).",
        "The later live diagnostic gate starts only after deterministic CurrentShell closure.",
    ):
        assert fragment in text

def test_live_diagnostic_runbook_requires_product_pages_and_non_fooddb_tool_evidence() -> None:
    text = LIVE_RUNBOOK_PATH.read_text(encoding="utf-8-sig")

    for fragment in (
        "This runbook belongs to the canonical `CurrentShell` track.",
        "`ManagerRuntime`, `AppShell`, and `SharedCurrentShell` are CurrentShell owner lanes.",
        "`product_pages_self_use_flow_gate`",
        "`ui_context_alignment_pack`",
        "`browser_activation_evidence_gate`",
        "`manager_tool_surface_inventory`",
        "`non_fooddb_manager_tool_contract`",
        "`manager_tool_choice_regression_wall`",
        "`context_conditioned_intent_wall`",
        "`non_fooddb_read_only_tool_loop_fake_smoke`",
        "`non_fooddb_mutation_tool_guard_smoke`",
        "The product-page evidence is required in addition to the older `browser_shell_smoke`.",
        "Non-FoodDB Manager tool diagnostics remain app-state only and must not use FoodDB/WebSearch evidence.",
        "The pre-live pack does not require `context_live_diagnostic_stage_gate`.",
    ):
        assert fragment in text
