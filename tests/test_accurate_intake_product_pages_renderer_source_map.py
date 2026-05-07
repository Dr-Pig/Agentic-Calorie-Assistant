from __future__ import annotations

import json
from pathlib import Path

from app.composition.accurate_intake_product_pages_renderer_source_map import (
    REQUIRED_PAGES,
    build_product_pages_renderer_source_map_artifact,
)


def test_product_pages_renderer_source_map_covers_chat_today_body_sources() -> None:
    artifact = build_product_pages_renderer_source_map_artifact()

    assert artifact["artifact_type"] == "accurate_intake_product_pages_renderer_source_map"
    assert artifact["status"] == "product_pages_renderer_source_map_ready_for_human_review"
    assert artifact["blockers"] == []
    assert artifact["pages"] == list(REQUIRED_PAGES)
    assert artifact["summary"]["page_count"] == 3
    assert artifact["summary"]["selector_count"] >= 30
    assert artifact["summary"]["endpoint_count"] >= 7
    assert artifact["summary"]["backend_field_count"] >= 25
    assert artifact["same_truth_renderer_contract_status"] == "ready_for_human_review"
    assert artifact["summary"]["same_truth_field_contract_count"] >= 8
    assert artifact["render_only_boundary_ok"] is True
    assert artifact["ui_truth_owner"] is False
    assert artifact["frontend_semantic_owner"] is False
    assert artifact["frontend_calculates_kcal"] is False
    assert artifact["frontend_calculates_remaining"] is False
    assert artifact["frontend_calculates_tdee"] is False
    assert artifact["frontend_selects_target"] is False
    assert artifact["ready_for_live_diagnostic_decision"] is False
    assert artifact["ready_for_fdb_integration"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["web_tavily_used"] is False
    assert artifact["fooddb_evidence_used"] is False
    assert artifact["product_readiness_claimed"] is False
    assert artifact["private_self_use_approved"] is False

    chat = artifact["source_map"]["chat"]
    assert chat["page_id"] == "accurate-intake-chat-page-v1"
    assert chat["surface_role"] == "chat"
    assert "/estimate" in chat["endpoints"]
    assert "/accurate-intake/chat-history" in chat["endpoints"]
    assert "#chat-scroll" in chat["selectors"]
    assert "#chat-context-strip" in chat["selectors"]
    assert "#chat-context-policy" in chat["selectors"]
    assert "#chat-context-loaded" in chat["selectors"]
    assert "#chat-context-omitted" in chat["selectors"]
    assert "#chat-context-pins" in chat["selectors"]
    assert "#chat-context-targets" in chat["selectors"]
    assert "#chat-target-candidate-list" in chat["selectors"]
    assert "payload.messages" in chat["backend_fields"]
    assert "payload.coach_message" in chat["backend_fields"]
    assert "message.context_policy_version" in chat["backend_fields"]
    assert "message.loaded_context_summary" in chat["backend_fields"]
    assert "message.omitted_context_summary" in chat["backend_fields"]
    assert "message.pending_pins_present" in chat["backend_fields"]
    assert "message.target_candidate_count" in chat["backend_fields"]
    assert "message.target_candidate_names" in chat["backend_fields"]

    today = artifact["source_map"]["today"]
    assert today["page_id"] == "accurate-intake-today-page-v1"
    assert today["surface_role"] == "today-diary"
    assert "/today/current-budget" in today["endpoints"]
    assert "#budget-kcal" in today["selectors"]
    assert "#meal-list" in today["selectors"]
    assert "#macro-panel" in today["selectors"]
    assert "#protein-g" in today["selectors"]
    assert "#carbs-g" in today["selectors"]
    assert "#fat-g" in today["selectors"]
    assert "#macro-guard-reason" in today["selectors"]
    assert "renderMacroPanel" in today["render_functions"]
    assert "payload.remaining_kcal" in today["backend_fields"]
    assert "payload.consumed_protein" in today["backend_fields"]
    assert "payload.consumed_carbs" in today["backend_fields"]
    assert "payload.consumed_fat" in today["backend_fields"]
    assert "payload.show_macro" in today["backend_fields"]
    assert "payload.macro_guard_reason" in today["backend_fields"]
    assert "meal.total_kcal" in today["backend_fields"]

    body = artifact["source_map"]["body"]
    assert body["page_id"] == "accurate-intake-body-page-v1"
    assert body["surface_role"] == "body-plan"
    assert "/body-plan/active" in body["endpoints"]
    assert "/weight/observations" in body["endpoints"]
    assert "/weight/observation" in body["endpoints"]
    assert "/onboarding/bootstrap" in body["endpoints"]
    assert "/body-plan/manual-daily-target" in body["endpoints"]
    assert "/today/deficit-summary" in body["endpoints"]
    assert "/today/effective-budget" in body["endpoints"]
    assert "/today/weekly-progress" in body["endpoints"]
    assert "#plan-tdee" in body["selectors"]
    assert "#body-budget-loop" in body["selectors"]
    assert "#weight-history" in body["selectors"]
    assert "plan.estimated_tdee" in body["backend_fields"]
    assert "payload.observations" in body["backend_fields"]
    assert "deficit.active_daily_target_kcal" in body["backend_fields"]
    assert "effective.runtime_effective_budget_kcal" in body["backend_fields"]
    assert "weekly.estimated_weekly_deficit_kcal" in body["backend_fields"]


def test_product_pages_renderer_source_map_declares_three_page_same_truth_contract() -> None:
    artifact = build_product_pages_renderer_source_map_artifact()
    contract = artifact["same_truth_renderer_contract"]

    chat = contract["chat"]
    assert chat["conversation_history"]["truth_owner"] == "composition_chat_history_read_model"
    assert chat["conversation_history"]["read_model_or_api"] == "/accurate-intake/chat-history"
    assert chat["conversation_history"]["ui_selector"] == "#chat-scroll"
    assert chat["current_turn_response"]["truth_owner"] == "manager_runtime_response"
    assert chat["current_turn_response"]["read_model_or_api"] == "/estimate"
    assert chat["current_turn_response"]["frontend_role"] == "render_backend_structured_fields_only"
    assert chat["context_status_strip"]["truth_owner"] == "manager_context_runtime_trace_sidecar"
    assert chat["context_status_strip"]["read_model_or_api"] == "/accurate-intake/chat-history"
    assert chat["context_status_strip"]["ui_selector"] == "#chat-context-strip"
    assert chat["context_status_strip"]["required_backend_fields"] == [
        "message.context_policy_version",
        "message.loaded_context_summary",
        "message.omitted_context_summary",
        "message.pending_pins_present",
        "message.target_candidate_count",
    ]
    assert chat["context_status_strip"]["must_not"] == [
        "frontend_infer_context_snapshot",
        "frontend_infer_manager_context_gap",
        "frontend_infer_intent",
    ]
    assert chat["read_only_target_candidates"]["truth_owner"] == "manager_context_target_candidate_sidecar"
    assert chat["read_only_target_candidates"]["read_model_or_api"] == "/accurate-intake/chat-history"
    assert chat["read_only_target_candidates"]["ui_selector"] == "#chat-target-candidate-list"
    assert chat["read_only_target_candidates"]["frontend_role"] == "render_backend_structured_fields_only"
    assert chat["read_only_target_candidates"]["must_not"] == [
        "frontend_select_target",
        "frontend_infer_correction_intent",
        "frontend_infer_mutation_legality",
    ]

    today = contract["today"]
    assert today["budget_summary"]["truth_owner"] == "budget_domain"
    assert today["budget_summary"]["read_model_or_api"] == "/today/current-budget"
    assert today["budget_summary"]["must_not"] == [
        "frontend_recompute_consumed",
        "frontend_recompute_remaining",
        "frontend_infer_overshoot",
    ]
    assert today["macro_surface"]["truth_owner"] == "budget_domain_macro_visibility_policy"
    assert today["macro_surface"]["read_model_or_api"] == "/today/current-budget"
    assert today["macro_surface"]["ui_selector"] == "#macro-panel"
    assert today["macro_surface"]["required_backend_fields"] == [
        "payload.consumed_protein",
        "payload.consumed_carbs",
        "payload.consumed_fat",
        "payload.show_macro",
        "payload.macro_guard_reason",
    ]
    assert today["macro_surface"]["must_not"] == [
        "frontend_infer_macro_visibility",
        "frontend_compute_macro_values",
        "frontend_parse_assistant_text_for_macro_truth",
    ]
    assert today["meal_summaries"]["truth_owner"] == "intake_and_budget_projection"
    assert today["meal_summaries"]["ui_selector"] == "#meal-list"

    body = contract["body"]
    assert body["active_body_plan"]["truth_owner"] == "body_domain"
    assert body["active_body_plan"]["read_model_or_api"] == "/body-plan/active"
    assert body["active_body_plan"]["must_not"] == [
        "frontend_calculate_tdee",
        "frontend_calculate_target",
        "frontend_infer_manual_override_legality",
    ]
    assert body["weight_observations"]["truth_owner"] == "body_domain"
    assert body["weight_observations"]["read_model_or_api"] == "/weight/observations"
    assert body["budget_deficit_summary"]["truth_owner"] == "composition_body_budget_read_model"
    assert body["budget_deficit_summary"]["read_model_or_api"] == "/today/deficit-summary"
    assert "frontend_calculate_estimated_deficit" in body["budget_deficit_summary"]["must_not"]
    assert body["effective_budget"]["truth_owner"] == "budget_composition_effective_budget_read_model"
    assert body["effective_budget"]["read_model_or_api"] == "/today/effective-budget"
    assert "frontend_calculate_effective_budget" in body["effective_budget"]["must_not"]
    assert body["weekly_progress"]["truth_owner"] == "composition_body_budget_weekly_read_model"
    assert body["weekly_progress"]["read_model_or_api"] == "/today/weekly-progress"
    assert "frontend_compute_weekly_deficit" in body["weekly_progress"]["must_not"]


def test_product_pages_renderer_source_map_blocks_contract_drift_when_backend_field_missing() -> None:
    html_overrides = {
        "body": Path("static/accurate-intake-body.html").read_text(encoding="utf-8").replace(
            "plan.recommended_target_kcal",
            "plan.recommended_target_missing",
        )
    }

    artifact = build_product_pages_renderer_source_map_artifact(html_overrides=html_overrides)

    assert artifact["status"] == "blocked"
    assert artifact["same_truth_renderer_contract_status"] == "blocked"
    assert (
        "body.same_truth_contract.active_body_plan.missing_backend_field:plan.recommended_target_kcal"
        in artifact["blockers"]
    )


def test_product_pages_renderer_source_map_blocks_chat_context_contract_drift() -> None:
    html_overrides = {
        "chat": Path("static/accurate-intake-chat.html").read_text(encoding="utf-8").replace(
            "message.context_policy_version",
            "message.context_policy_missing",
        )
    }

    artifact = build_product_pages_renderer_source_map_artifact(html_overrides=html_overrides)

    assert artifact["status"] == "blocked"
    assert "chat.missing_backend_field:message.context_policy_version" in artifact["blockers"]
    assert (
        "chat.same_truth_contract.context_status_strip.missing_backend_field:message.context_policy_version"
        in artifact["blockers"]
    )


def test_product_pages_renderer_source_map_rejects_missing_selector() -> None:
    html_overrides = {
        "chat": Path("static/accurate-intake-chat.html").read_text(encoding="utf-8").replace(
            'id="chat-scroll"',
            'id="chat-scroll-missing"',
        )
    }

    artifact = build_product_pages_renderer_source_map_artifact(html_overrides=html_overrides)

    assert artifact["status"] == "blocked"
    assert "chat.missing_selector:#chat-scroll" in artifact["blockers"]


def test_product_pages_renderer_source_map_rejects_missing_endpoint_or_backend_field() -> None:
    html_overrides = {
        "today": Path("static/accurate-intake-today.html").read_text(encoding="utf-8")
        .replace('currentBudget: "/today/current-budget"', 'currentBudget: "/wrong"')
        .replace("payload.remaining_kcal", "payload.remaining_missing")
    }

    artifact = build_product_pages_renderer_source_map_artifact(html_overrides=html_overrides)

    assert artifact["status"] == "blocked"
    assert "today.missing_endpoint:/today/current-budget" in artifact["blockers"]
    assert "today.missing_backend_field:payload.remaining_kcal" in artifact["blockers"]


def test_product_pages_renderer_source_map_requires_function_declarations_not_call_sites() -> None:
    html_overrides = {
        "chat": Path("static/accurate-intake-chat.html").read_text(encoding="utf-8").replace(
            "function renderHistory(payload)",
            "function renderHistoryMissing(payload)",
        )
    }

    artifact = build_product_pages_renderer_source_map_artifact(html_overrides=html_overrides)

    assert artifact["status"] == "blocked"
    assert "chat.missing_render_function:renderHistory" in artifact["blockers"]


def test_product_pages_renderer_source_map_rejects_fake_function_declaration_in_string_or_comment() -> None:
    original = Path("static/accurate-intake-chat.html").read_text(encoding="utf-8")
    html_without_declaration = original.replace(
        "function renderHistory(payload)",
        "function renderHistoryMissing(payload)",
    )
    html_overrides = {
        "chat": html_without_declaration
        + '\n<script>console.log("function renderHistory(payload)")</script>'
        + "\n<!-- function renderHistory(payload) -->"
    }

    artifact = build_product_pages_renderer_source_map_artifact(html_overrides=html_overrides)

    assert artifact["status"] == "blocked"
    assert "chat.missing_render_function:renderHistory" in artifact["blockers"]


def test_product_pages_renderer_source_map_rejects_fake_function_declaration_in_block_comment_or_template() -> None:
    original = Path("static/accurate-intake-chat.html").read_text(encoding="utf-8")
    html_without_declaration = original.replace(
        "function renderHistory(payload)",
        "function renderHistoryMissing(payload)",
    )
    html_overrides = {
        "chat": html_without_declaration
        + "\n<script>/*\nfunction renderHistory(payload)\n*/</script>"
        + "\n<script>const fake = `\nfunction renderHistory(payload)\n`;</script>"
    }

    artifact = build_product_pages_renderer_source_map_artifact(html_overrides=html_overrides)

    assert artifact["status"] == "blocked"
    assert "chat.missing_render_function:renderHistory" in artifact["blockers"]


def test_product_pages_renderer_source_map_rejects_frontend_semantic_or_math_fragments() -> None:
    html_overrides = {
        "body": Path("static/accurate-intake-body.html").read_text(encoding="utf-8")
        + "\n<script>const remaining = budget - consumed; if (text.includes('拿掉')) selectTarget();</script>"
    }

    artifact = build_product_pages_renderer_source_map_artifact(html_overrides=html_overrides)

    assert artifact["status"] == "blocked"
    assert "body.forbidden_semantic_fragment:budget - consumed" in artifact["blockers"]
    assert "body.forbidden_semantic_fragment:text.includes" in artifact["blockers"]
    assert "body.forbidden_semantic_fragment:selectTarget" in artifact["blockers"]


def test_product_pages_renderer_source_map_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts.build_accurate_intake_product_pages_renderer_source_map import main

    output_path = tmp_path / "source-map.json"
    exit_code = main(["--output", str(output_path)])
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert artifact["status"] == "product_pages_renderer_source_map_ready_for_human_review"
    assert artifact["source_map"]["chat"]["source_artifact_path"].endswith("accurate-intake-chat.html")


def test_product_pages_renderer_source_map_source_stays_out_of_fooddb_websearch_live_boundaries() -> None:
    source_paths = [
        Path("app/composition/accurate_intake_product_pages_renderer_source_map.py"),
        Path("scripts/build_accurate_intake_product_pages_renderer_source_map.py"),
    ]
    forbidden = [
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "from tavily",
        "import tavily",
        "BuilderSpaceAdapter",
        "builderspace_adapter",
        "kimi",
        "grok",
        "live_llm_invoked = True",
        "web_tavily_used = True",
        "ready_for_live_diagnostic_decision = True",
        "ready_for_fdb_integration = True",
    ]
    combined_source = "\n".join(path.read_text(encoding="utf-8").lower() for path in source_paths)

    for fragment in forbidden:
        assert fragment.lower() not in combined_source


def test_ci_builds_product_pages_renderer_source_map() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "test_accurate_intake_product_pages_renderer_source_map.py" in workflow
    assert "build_accurate_intake_product_pages_renderer_source_map.py" in workflow
    assert "accurate_intake_product_pages_renderer_source_map_ci.json" in workflow
