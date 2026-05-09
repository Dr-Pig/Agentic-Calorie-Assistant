from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_accurate_intake_product_pages_browser_smoke as module


def _passing_report(*, local_date: str = "2026-05-05") -> dict[str, object]:
    previous_local_date = module._previous_local_date(local_date)
    return {
        "browser_executed": True,
        "local_date": local_date,
        "previous_local_date": previous_local_date,
        "launchpad_page_loaded": True,
        "launchpad_navigation_checked": True,
        "launchpad_navigation_values": {
            "chat": True,
            "today": True,
            "body": True,
            "feedback": True,
            "data": True,
        },
        "launchpad_non_claims": {
            "frontend_semantic_owner": False,
            "product_readiness_claimed": False,
            "local_debug_token_in_url": False,
        },
        "chat_page_loaded": True,
        "chat_sent_cjk_message": True,
        "chat_assistant_bubble_rendered": True,
        "chat_history_reloaded": True,
        "chat_url_state_preserved_after_date_change": True,
        "chat_reload_preserved_selected_date": True,
        "chat_user_url_state_preserved_after_user_change": True,
        "chat_reload_preserved_user_id": True,
        "chat_enter_key_send_checked": True,
        "chat_shift_enter_multiline_checked": True,
        "chat_scrollable": True,
        "chat_scroll_behavior_checked": True,
        "chat_reload_scroll_behavior_checked": True,
        "chat_session_status_rendered": True,
        "chat_context_status_rendered": True,
        "chat_no_debug_trace": True,
        "chat_body_observation_same_truth_checked": True,
        "chat_body_observation_written": True,
        "chat_body_observation_body_page_readback": True,
        "chat_body_observation_values": {
            "assistant_text": "Recorded weight 70.0 kg. Body plan was not changed.",
            "weight_history": f"{local_date} | 70 kg",
            "manager_call_count": 2,
        },
        "chat_body_observation_non_claims": {
            "body_plan_mutated": False,
            "ledger_updated": False,
            "frontend_weight_parser_used": False,
            "product_readiness_claimed": False,
        },
        "body_ui_weight_chat_readback_checked": True,
        "body_ui_weight_chat_readback_values": {
            "assistant_text": "Latest weight is 70.4 kg from your body log.",
            "latest_weight": "70.4 kg",
            "latest_weight_local_date": local_date,
            "selected_tool": "body.get_latest_observation",
            "manager_call_count": 2,
        },
        "body_ui_weight_chat_readback_non_claims": {
            "state_mutated": False,
            "body_plan_mutated": False,
            "ledger_updated": False,
            "frontend_weight_parser_used": False,
            "product_readiness_claimed": False,
        },
        "today_page_loaded": True,
        "today_date_switch_checked": True,
        "today_previous_day_empty_checked": True,
        "today_current_day_restored_checked": True,
        "today_url_state_preserved_after_date_change": True,
        "today_reload_preserved_selected_date": True,
        "today_user_url_state_preserved_after_user_change": True,
        "today_reload_preserved_user_id": True,
        "today_summary_rendered": True,
        "today_meal_list_rendered": True,
        "macro_present_exact_item_browser_checked": True,
        "macro_present_exact_item_values": {
            "macro_state": "visible",
            "protein_text": "12",
            "carbs_text": "48",
            "fat_text": "6",
        },
        "macro_missing_exact_item_browser_checked": True,
        "macro_missing_exact_item_values": {
            "macro_state": "guarded",
            "macro_grid_hidden": True,
            "macro_guard_reason_hidden": False,
            "macro_guard_reason_text": "no_macro_data",
            "protein_text": "--",
            "carbs_text": "--",
            "fat_text": "--",
        },
        "route_backed_macro_browser_checked": True,
        "route_backed_macro_present_current_budget": {
            "consumed_kcal": 300,
            "consumed_protein": 12,
            "consumed_carbs": 48,
            "consumed_fat": 6,
            "show_macro": True,
            "macro_guard_reason": "committed_and_aligned",
        },
        "route_backed_macro_missing_current_budget": {
            "consumed_kcal": 130,
            "consumed_protein": 0,
            "consumed_carbs": 0,
            "consumed_fat": 0,
            "show_macro": False,
            "macro_guard_reason": "no_macro_data",
        },
        "route_backed_macro_non_claims": {
            "live_llm_invoked": False,
            "web_tavily_used": False,
            "fooddb_truth_updated": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "fooddb_triad_same_truth_browser_checked": True,
        "fooddb_triad_same_truth_cases": module.EXPECTED_FOODDB_TRIAD_SAME_TRUTH_CASES,
        "fooddb_triad_same_truth_non_claims": module.FOODDB_TRIAD_SAME_TRUTH_NON_CLAIMS,
        "today_session_status_rendered": True,
        "today_no_debug_trace": True,
        "body_page_loaded": True,
        "body_query_user_id_honored": True,
        "body_url_state_preserved_after_date_change": True,
        "body_reload_preserved_selected_date": True,
        "body_user_url_state_preserved_after_user_change": True,
        "body_reload_preserved_user_id": True,
        "body_active_plan_rendered": True,
        "body_plan_read_model_fields_rendered": True,
        "body_weight_checkin_saved": True,
        "body_latest_weight_rendered_from_backend": True,
        "body_weight_history_date_scoped_readback": True,
        "body_budget_read_models_rendered": True,
        "body_plan_form_saved": True,
        "body_manual_target_saved": True,
        "body_plan_readback_checked": True,
        "body_manual_target_read_model_rendered": True,
        "today_manual_target_readback_checked": True,
        "body_session_status_rendered": True,
        "body_no_debug_trace": True,
        "feedback_page_loaded": True,
        "feedback_submitted": True,
        "feedback_jsonl_written": True,
        "feedback_review_queue_ingested": True,
        "feedback_record_values": {
            "category": "latency",
            "feedback_text": "Synthetic browser feedback",
            "trace_id": "trace-browser-feedback",
            "do_not_commit": True,
            "manager_context_injection_allowed": False,
            "food_kb_truth_update_allowed": False,
            "canonical_eval_promotion_allowed": False,
        },
        "feedback_review_queue_values": {
            "feedback_triage_record_count": 1,
            "feedback_can_create_product_truth": False,
            "feedback_can_create_fooddb_truth": False,
            "feedback_can_create_eval_truth": False,
        },
        "feedback_non_claims": {
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "fooddb_truth_updated": False,
            "canonical_eval_promoted": False,
            "manager_context_injected": False,
        },
        "data_page_loaded": True,
        "data_inspected": True,
        "data_backup_created": True,
        "data_export_created": True,
        "data_inspect_values": {
            "artifact_type": "accurate_intake_local_operator_data_hygiene_bundle",
            "status": "local_operator_data_hygiene_ready",
            "local_only": True,
            "do_not_commit": True,
            "writes_performed": False,
            "import_allowed": False,
            "fooddb_truth_updated": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
        },
        "data_backup_values": {
            "status": "pass",
            "local_only": True,
            "do_not_commit": True,
            "production_db_used": False,
            "fooddb_truth_updated": False,
            "backup_path_exists": True,
        },
        "data_export_values": {
            "status": "pass",
            "local_only": True,
            "do_not_commit": True,
            "production_db_used": False,
            "fooddb_truth_updated": False,
            "export_path_exists": True,
            "manifest_path_exists": True,
        },
        "data_non_claims": {
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "fooddb_truth_updated": False,
            "canonical_eval_promoted": False,
            "import_or_reset_written": False,
        },
        "desktop_no_overflow": True,
        "mobile_no_overflow": True,
        "mobile_populated_state_checked": True,
        "mobile_no_debug_trace": True,
        "product_cjk_copy_rendered": True,
        "nav_session_query_preserved": True,
        "forbidden_storage_used": False,
        "body_plan_read_model_values": {
            "daily_target": "1550 kcal",
            "tdee": "1819 kcal",
            "current_weight": "70 kg",
            "target_weight": "65 kg",
            "activity": "light",
            "goal": "Lose weight",
            "weight_history": f"{local_date} | 70.4 kg",
        },
        "body_budget_read_model_values": {
            "active_target": "1550 kcal",
            "consumed": "400 kcal",
            "remaining": "1150 kcal",
            "estimated_deficit": "269 kcal",
            "effective_budget": "1550 kcal",
            "weekly_progress": "400 kcal consumed",
        },
        "browser": {
            "fetch_sequence": [
                {"url": "/accurate-intake/chat-history?user_id=product-pages", "method": "GET"},
                {"url": "/estimate", "method": "POST", "body": '{"allow_search":false}'},
                {"url": "/today/current-budget?user_id=product-pages", "method": "GET"},
                {
                    "url": f"/today/current-budget?user_id=product-pages&local_date={previous_local_date}",
                    "method": "GET",
                },
                {"url": f"/today/current-budget?user_id=product-pages&local_date={local_date}", "method": "GET"},
                {"url": "/body-plan/active?user_id=product-pages", "method": "GET"},
                {
                    "url": f"/weight/observations?user_id=product-pages&local_date={local_date}",
                    "method": "GET",
                },
                {"url": f"/today/deficit-summary?user_id=product-pages&local_date={local_date}", "method": "GET"},
                {"url": f"/today/effective-budget?user_id=product-pages&local_date={local_date}", "method": "GET"},
                {"url": f"/today/weekly-progress?user_id=product-pages&local_date={local_date}", "method": "GET"},
                {
                    "url": "/accurate-intake/feedback",
                    "method": "POST",
                    "body": (
                        '{"category":"latency","feedback_text":"Synthetic browser feedback",'
                        '"trace_id":"trace-browser-feedback"}'
                    ),
                },
                {"url": "/accurate-intake/local-data-hygiene", "method": "GET"},
                {"url": "/accurate-intake/local-data-hygiene/backup", "method": "POST"},
                {"url": "/accurate-intake/local-data-hygiene/export", "method": "POST"},
                {
                    "url": "/weight/observation",
                    "method": "POST",
                    "body": f'{{"user_id":"product-pages","local_date":"{local_date}"}}',
                },
                {
                    "url": "/onboarding/bootstrap",
                    "method": "POST",
                    "body": f'{{"user_id":"product-pages","local_date":"{local_date}"}}',
                },
                {
                    "url": "/body-plan/manual-daily-target",
                    "method": "POST",
                    "body": f'{{"user_id":"product-pages","local_date":"{local_date}","source":"user_ui"}}',
                },
            ],
            "storage": {"localStorageKeys": [], "sessionStorageKeys": []},
            "product_page_text": "Chat Today Body",
        },
    }


def test_product_pages_browser_smoke_missing_playwright_is_blocked_not_readiness(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_browser_smoke_report(db_path=tmp_path / "product-pages.sqlite3")

    assert report["smoke_id"] == "accurate_intake_product_pages_browser_smoke_v1"
    assert report["status"] == "blocked"
    assert report["browser_executed"] is False
    assert report["browser_execution_required"] is False
    assert report["blockers"] == ["playwright_not_installed"]


def test_product_pages_browser_smoke_can_require_browser_execution(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_browser_smoke_report(
        db_path=tmp_path / "product-pages.sqlite3",
        require_browser_execution=True,
    )

    assert report["status"] == "fail"
    assert report["browser_execution_required"] is True
    assert report["browser_executed"] is False
    assert report["blockers"] == ["playwright_not_installed"]


def test_product_pages_browser_smoke_validator_requires_cross_page_evidence() -> None:
    status, blockers = module._validate(_passing_report(local_date="2026-05-05"))

    assert status == "pass"
    assert blockers == []


def test_product_pages_browser_smoke_validator_requires_feedback_capture_loop() -> None:
    report = _passing_report()
    report["feedback_page_loaded"] = False
    report["feedback_submitted"] = False
    report["feedback_jsonl_written"] = False
    report["feedback_review_queue_ingested"] = False

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "feedback_page_not_loaded" in blockers
    assert "feedback_not_submitted" in blockers
    assert "feedback_jsonl_not_written" in blockers
    assert "feedback_review_queue_not_ingested" in blockers


def test_product_pages_browser_smoke_validator_rejects_feedback_truth_promotion() -> None:
    report = _passing_report()
    record_values = dict(report["feedback_record_values"])
    record_values["food_kb_truth_update_allowed"] = True
    report["feedback_record_values"] = record_values
    queue_values = dict(report["feedback_review_queue_values"])
    queue_values["feedback_can_create_eval_truth"] = True
    report["feedback_review_queue_values"] = queue_values
    non_claims = dict(report["feedback_non_claims"])
    non_claims["manager_context_injected"] = True
    report["feedback_non_claims"] = non_claims

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "feedback_record_truth_promotion:food_kb_truth_update_allowed" in blockers
    assert "feedback_review_queue_truth_promotion:feedback_can_create_eval_truth" in blockers
    assert "feedback_non_claim_overclaim:manager_context_injected" in blockers


def test_product_pages_browser_smoke_validator_requires_data_hygiene_loop() -> None:
    report = _passing_report()
    report["data_page_loaded"] = False
    report["data_inspected"] = False
    report["data_backup_created"] = False
    report["data_export_created"] = False

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "data_page_not_loaded" in blockers
    assert "data_hygiene_not_inspected" in blockers
    assert "data_backup_not_created" in blockers
    assert "data_export_not_created" in blockers


def test_product_pages_browser_smoke_validator_rejects_data_truth_or_import_claims() -> None:
    report = _passing_report()
    inspect_values = dict(report["data_inspect_values"])
    inspect_values["product_readiness_claimed"] = True
    report["data_inspect_values"] = inspect_values
    backup_values = dict(report["data_backup_values"])
    backup_values["production_db_used"] = True
    report["data_backup_values"] = backup_values
    non_claims = dict(report["data_non_claims"])
    non_claims["import_or_reset_written"] = True
    report["data_non_claims"] = non_claims

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "data_inspect_value_mismatch:product_readiness_claimed" in blockers
    assert "data_backup_value_mismatch:production_db_used" in blockers
    assert "data_non_claim_overclaim:import_or_reset_written" in blockers


def test_product_pages_browser_smoke_validator_requires_launchpad_navigation() -> None:
    report = _passing_report()
    report["launchpad_page_loaded"] = False
    report["launchpad_navigation_checked"] = False
    values = dict(report["launchpad_navigation_values"])
    values["feedback"] = False
    report["launchpad_navigation_values"] = values

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "launchpad_page_not_loaded" in blockers
    assert "launchpad_navigation_not_checked" in blockers
    assert "launchpad_navigation_not_preserved:feedback" in blockers


def test_product_pages_browser_smoke_validator_rejects_launchpad_truth_or_token_claims() -> None:
    report = _passing_report()
    non_claims = dict(report["launchpad_non_claims"])
    non_claims["frontend_semantic_owner"] = True
    non_claims["local_debug_token_in_url"] = True
    report["launchpad_non_claims"] = non_claims

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "launchpad_non_claim_overclaim:frontend_semantic_owner" in blockers
    assert "launchpad_non_claim_overclaim:local_debug_token_in_url" in blockers


def test_product_pages_browser_smoke_validator_requires_chat_body_observation_same_truth() -> None:
    report = _passing_report(local_date="2026-05-05")
    report["chat_body_observation_same_truth_checked"] = False
    report["chat_body_observation_written"] = False
    report["chat_body_observation_body_page_readback"] = False
    report["chat_body_observation_values"] = {
        "assistant_text": "",
        "weight_history": "",
        "manager_call_count": 1,
    }
    report["chat_body_observation_non_claims"] = {
        "body_plan_mutated": True,
        "ledger_updated": True,
        "frontend_weight_parser_used": True,
        "product_readiness_claimed": True,
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "chat_body_observation_same_truth_not_checked" in blockers
    assert "chat_body_observation_not_written" in blockers
    assert "chat_body_observation_body_page_readback_missing" in blockers
    assert "chat_body_observation_value_mismatch:assistant_text" in blockers
    assert "chat_body_observation_value_mismatch:weight_history" in blockers
    assert "chat_body_observation_value_mismatch:manager_call_count" in blockers
    assert "chat_body_observation_non_claim_overclaim:body_plan_mutated" in blockers
    assert "chat_body_observation_non_claim_overclaim:ledger_updated" in blockers
    assert "chat_body_observation_non_claim_overclaim:frontend_weight_parser_used" in blockers
    assert "chat_body_observation_non_claim_overclaim:product_readiness_claimed" in blockers


def test_product_pages_browser_smoke_validator_requires_body_ui_weight_chat_readback() -> None:
    report = _passing_report(local_date="2026-05-05")
    report["body_ui_weight_chat_readback_checked"] = False
    report["body_ui_weight_chat_readback_values"] = {
        "assistant_text": "",
        "latest_weight": "70 kg",
        "latest_weight_local_date": "2026-05-04",
        "selected_tool": "body.get_active_plan",
        "manager_call_count": 1,
    }
    report["body_ui_weight_chat_readback_non_claims"] = {
        "state_mutated": True,
        "body_plan_mutated": True,
        "ledger_updated": True,
        "frontend_weight_parser_used": True,
        "product_readiness_claimed": True,
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "body_ui_weight_chat_readback_not_checked" in blockers
    assert "body_ui_weight_chat_readback_value_mismatch:assistant_text" in blockers
    assert "body_ui_weight_chat_readback_value_mismatch:latest_weight" in blockers
    assert "body_ui_weight_chat_readback_value_mismatch:latest_weight_local_date" in blockers
    assert "body_ui_weight_chat_readback_value_mismatch:selected_tool" in blockers
    assert "body_ui_weight_chat_readback_value_mismatch:manager_call_count" in blockers
    assert "body_ui_weight_chat_readback_non_claim_overclaim:state_mutated" in blockers
    assert "body_ui_weight_chat_readback_non_claim_overclaim:body_plan_mutated" in blockers
    assert "body_ui_weight_chat_readback_non_claim_overclaim:ledger_updated" in blockers
    assert "body_ui_weight_chat_readback_non_claim_overclaim:frontend_weight_parser_used" in blockers
    assert "body_ui_weight_chat_readback_non_claim_overclaim:product_readiness_claimed" in blockers


def test_product_pages_browser_smoke_validator_rejects_missing_reload_body_user_and_overflow() -> None:
    report = _passing_report()
    report["chat_history_reloaded"] = False
    report["chat_url_state_preserved_after_date_change"] = False
    report["chat_reload_preserved_selected_date"] = False
    report["chat_user_url_state_preserved_after_user_change"] = False
    report["chat_reload_preserved_user_id"] = False
    report["chat_enter_key_send_checked"] = False
    report["chat_shift_enter_multiline_checked"] = False
    report["chat_scroll_behavior_checked"] = False
    report["chat_session_status_rendered"] = False
    report["chat_context_status_rendered"] = False
    report["body_query_user_id_honored"] = False
    report["body_url_state_preserved_after_date_change"] = False
    report["body_reload_preserved_selected_date"] = False
    report["body_user_url_state_preserved_after_user_change"] = False
    report["body_reload_preserved_user_id"] = False
    report["mobile_no_overflow"] = False
    report["mobile_populated_state_checked"] = False
    report["nav_session_query_preserved"] = False

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "chat_history_not_reloaded" in blockers
    assert "chat_url_state_not_preserved_after_date_change" in blockers
    assert "chat_reload_did_not_preserve_selected_date" in blockers
    assert "chat_user_url_state_not_preserved_after_user_change" in blockers
    assert "chat_reload_did_not_preserve_user_id" in blockers
    assert "chat_enter_key_send_not_checked" in blockers
    assert "chat_shift_enter_multiline_not_checked" in blockers
    assert "chat_scroll_behavior_not_checked" in blockers
    assert "chat_session_status_not_rendered" in blockers
    assert "chat_context_status_not_rendered" in blockers
    assert "body_query_user_id_not_honored" in blockers
    assert "body_url_state_not_preserved_after_date_change" in blockers
    assert "body_reload_did_not_preserve_selected_date" in blockers
    assert "body_user_url_state_not_preserved_after_user_change" in blockers
    assert "body_reload_did_not_preserve_user_id" in blockers
    assert "mobile_overflow_detected" in blockers
    assert "mobile_populated_state_not_checked" in blockers
    assert "nav_session_query_not_preserved" in blockers


def test_product_pages_browser_smoke_validator_rejects_shallow_today_and_body_sync() -> None:
    report = _passing_report()
    report["today_previous_day_empty_checked"] = False
    report["today_current_day_restored_checked"] = False
    report["today_url_state_preserved_after_date_change"] = False
    report["today_reload_preserved_selected_date"] = False
    report["today_user_url_state_preserved_after_user_change"] = False
    report["today_reload_preserved_user_id"] = False
    report["body_plan_readback_checked"] = False
    report["body_plan_read_model_fields_rendered"] = False
    report["body_latest_weight_rendered_from_backend"] = False
    report["body_weight_history_date_scoped_readback"] = False
    report["body_budget_read_models_rendered"] = False
    report["body_manual_target_read_model_rendered"] = False
    report["today_manual_target_readback_checked"] = False
    report["today_session_status_rendered"] = False
    report["body_session_status_rendered"] = False

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "today_previous_day_empty_not_checked" in blockers
    assert "today_current_day_restored_not_checked" in blockers
    assert "today_url_state_not_preserved_after_date_change" in blockers
    assert "today_reload_did_not_preserve_selected_date" in blockers
    assert "today_user_url_state_not_preserved_after_user_change" in blockers
    assert "today_reload_did_not_preserve_user_id" in blockers
    assert "body_plan_readback_not_checked" in blockers
    assert "body_plan_read_model_fields_not_rendered" in blockers
    assert "body_latest_weight_not_rendered_from_backend" in blockers
    assert "body_weight_history_date_scoped_readback_missing" in blockers
    assert "body_budget_read_models_not_rendered" in blockers
    assert "body_manual_target_read_model_not_rendered" in blockers
    assert "today_manual_target_readback_not_checked" in blockers
    assert "today_session_status_not_rendered" in blockers
    assert "body_session_status_not_rendered" in blockers


def test_product_pages_browser_smoke_validator_rejects_stale_body_read_model_values() -> None:
    report = _passing_report()
    values = dict(report["body_plan_read_model_values"])
    values.update(
        {
            "daily_target": "1312 kcal",
            "tdee": "9999 kcal",
            "current_weight": "69 kg",
            "target_weight": "64 kg",
            "activity": "sedentary",
            "goal": "Maintain weight",
            "weight_history": "",
        }
    )
    report["body_plan_read_model_values"] = values

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "body_read_model_value_mismatch:daily_target" in blockers
    assert "body_read_model_value_mismatch:tdee" in blockers
    assert "body_read_model_value_mismatch:current_weight" in blockers
    assert "body_read_model_value_mismatch:target_weight" in blockers
    assert "body_read_model_value_mismatch:activity" in blockers
    assert "body_read_model_value_mismatch:goal" in blockers
    assert "body_read_model_value_mismatch:weight_history" in blockers


def test_product_pages_browser_smoke_validator_requires_date_scoped_body_weight_history_fetch() -> None:
    report = _passing_report(local_date="2026-05-05")
    browser = dict(report["browser"])
    browser["fetch_sequence"] = [
        item
        for item in browser["fetch_sequence"]  # type: ignore[index]
        if "/weight/observations" not in str(item.get("url") or "")
    ]
    browser["fetch_sequence"].append(
        {"url": "/weight/observations?user_id=product-pages", "method": "GET"}
    )
    report["browser"] = browser

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "body_weight_history_date_fetch_missing" in blockers


def test_product_pages_browser_smoke_validator_rejects_any_unscoped_body_weight_history_fetch() -> None:
    report = _passing_report(local_date="2026-05-05")
    browser = dict(report["browser"])
    browser["fetch_sequence"] = [
        *browser["fetch_sequence"],  # type: ignore[index]
        {"url": "/weight/observations?user_id=product-pages", "method": "GET"},
    ]
    report["browser"] = browser

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "body_weight_history_unscoped_fetch_detected" in blockers


def test_product_pages_browser_smoke_validator_requires_body_budget_read_model_fetches() -> None:
    report = _passing_report(local_date="2026-05-05")
    browser = dict(report["browser"])
    browser["fetch_sequence"] = [
        item
        for item in browser["fetch_sequence"]  # type: ignore[index]
        if not any(
            endpoint in str(item.get("url") or "")
            for endpoint in ("/today/deficit-summary", "/today/effective-budget", "/today/weekly-progress")
        )
    ]
    report["browser"] = browser

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "body_budget_read_model_fetch_missing:/today/deficit-summary" in blockers
    assert "body_budget_read_model_fetch_missing:/today/effective-budget" in blockers
    assert "body_budget_read_model_fetch_missing:/today/weekly-progress" in blockers


def test_product_pages_browser_smoke_validator_requires_macro_present_exact_item_e2e() -> None:
    report = _passing_report()
    report["macro_present_exact_item_browser_checked"] = False
    report["macro_present_exact_item_values"] = {
        "macro_state": "visible",
        "protein_text": "12",
        "carbs_text": "48",
        "fat_text": "6",
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "macro_present_exact_item_browser_not_checked" in blockers


def test_product_pages_browser_smoke_validator_rejects_macro_present_value_drift() -> None:
    report = _passing_report()
    report["macro_present_exact_item_values"] = {
        "macro_state": "visible",
        "protein_text": "11",
        "carbs_text": "48",
        "fat_text": "6",
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "macro_present_exact_item_value_mismatch:protein_text" in blockers


def test_product_pages_browser_smoke_validator_requires_macro_missing_exact_item_e2e() -> None:
    report = _passing_report()
    report["macro_missing_exact_item_browser_checked"] = False
    report["macro_missing_exact_item_values"] = {
        "macro_state": "guarded",
        "macro_grid_hidden": True,
        "macro_guard_reason_hidden": False,
        "macro_guard_reason_text": "no_macro_data",
        "protein_text": "--",
        "carbs_text": "--",
        "fat_text": "--",
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "macro_missing_exact_item_browser_not_checked" in blockers


def test_product_pages_browser_smoke_validator_rejects_macro_missing_value_leak() -> None:
    report = _passing_report()
    report["macro_missing_exact_item_values"] = {
        "macro_state": "visible",
        "macro_grid_hidden": False,
        "macro_guard_reason_hidden": True,
        "macro_guard_reason_text": "",
        "protein_text": "12",
        "carbs_text": "--",
        "fat_text": "--",
    }

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "macro_missing_exact_item_value_mismatch:macro_state" in blockers
    assert "macro_missing_exact_item_value_mismatch:protein_text" in blockers


def test_product_pages_browser_smoke_validator_requires_route_backed_macro_budget_truth() -> None:
    report = _passing_report()
    report["route_backed_macro_browser_checked"] = False

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "route_backed_macro_browser_not_checked" in blockers


def test_product_pages_browser_smoke_validator_requires_fooddb_triad_same_truth() -> None:
    report = _passing_report()
    report["fooddb_triad_same_truth_browser_checked"] = False

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "fooddb_triad_same_truth_browser_not_checked" in blockers


def test_product_pages_browser_smoke_validator_rejects_fooddb_triad_macro_leak() -> None:
    report = _passing_report()
    cases = {
        lane: dict(case)
        for lane, case in module.EXPECTED_FOODDB_TRIAD_SAME_TRUTH_CASES.items()
    }
    cases["generic_common_serving"]["macro_state"] = "visible"
    cases["generic_common_serving"]["protein_text"] = "22"
    report["fooddb_triad_same_truth_cases"] = cases

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "fooddb_triad_same_truth_case_mismatch:generic_common_serving:macro_state" in blockers
    assert "fooddb_triad_same_truth_case_mismatch:generic_common_serving:protein_text" in blockers


def test_product_pages_browser_smoke_validator_rejects_fooddb_triad_overclaim() -> None:
    report = _passing_report()
    non_claims = dict(module.FOODDB_TRIAD_SAME_TRUTH_NON_CLAIMS)
    non_claims["assistant_text_macro_parsed"] = True
    report["fooddb_triad_same_truth_non_claims"] = non_claims

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "fooddb_triad_same_truth_non_claim_overclaim:assistant_text_macro_parsed" in blockers


def test_product_pages_browser_smoke_validator_rejects_route_backed_macro_budget_drift() -> None:
    report = _passing_report()
    values = dict(report["route_backed_macro_present_current_budget"])
    values["consumed_protein"] = 11
    report["route_backed_macro_present_current_budget"] = values

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "route_backed_macro_present_current_budget_mismatch:consumed_protein" in blockers


def test_product_pages_browser_smoke_validator_rejects_route_backed_macro_overclaims() -> None:
    report = _passing_report()
    non_claims = dict(report["route_backed_macro_non_claims"])
    non_claims["product_readiness_claimed"] = True
    report["route_backed_macro_non_claims"] = non_claims

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "route_backed_macro_non_claim_overclaim:product_readiness_claimed" in blockers


def test_product_pages_browser_smoke_validator_rejects_stale_body_budget_read_model_values() -> None:
    report = _passing_report()
    values = dict(report["body_budget_read_model_values"])
    values.update(
        {
            "active_target": "1312 kcal",
            "consumed": "0 kcal",
            "remaining": "0 kcal",
            "effective_budget": "0 kcal",
            "weekly_progress": "",
        }
    )
    report["body_budget_read_model_values"] = values

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "body_budget_read_model_value_mismatch:active_target" in blockers
    assert "body_budget_read_model_value_mismatch:consumed" in blockers
    assert "body_budget_read_model_value_mismatch:remaining" in blockers
    assert "body_budget_read_model_value_mismatch:effective_budget" in blockers
    assert "body_budget_read_model_value_mismatch:weekly_progress" in blockers


def test_product_pages_browser_smoke_validator_rejects_debug_trace_or_stale_fetch_contract() -> None:
    report = _passing_report()
    report["today_no_debug_trace"] = False
    report["body_no_debug_trace"] = False
    report["product_cjk_copy_rendered"] = False
    report["browser"]["fetch_sequence"][1]["body"] = '{"allow_search":true}'
    previous_local_date = str(report["previous_local_date"])
    report["browser"]["fetch_sequence"] = [
        item for item in report["browser"]["fetch_sequence"] if previous_local_date not in str(item.get("url"))
    ]

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "today_debug_trace_leaked" in blockers
    assert "body_debug_trace_leaked" in blockers
    assert "product_cjk_copy_not_rendered" in blockers
    assert "estimate_allow_search_not_false" in blockers
    assert "today_previous_day_fetch_missing" in blockers


def test_body_page_honors_query_user_id_for_session_context() -> None:
    html = Path("static/accurate-intake-body.html").read_text(encoding="utf-8")

    assert 'params.get("user_id") || el("user-id").value' in html


def test_product_pages_browser_smoke_runs_real_browser_when_playwright_available(tmp_path: Path) -> None:
    try:
        module._load_sync_playwright()
    except module.BrowserSmokeDependencyMissing:
        pytest.skip("Playwright is not installed in this environment.")

    db_path = tmp_path / "product-pages-browser.sqlite3"
    report = module.build_product_pages_browser_smoke_report(
        db_path=db_path,
        require_browser_execution=True,
        timeout_ms=20000,
    )

    assert report["status"] == "pass"
    assert report["browser_executed"] is True
    assert report["chat_enter_key_send_checked"] is True
    assert report["chat_shift_enter_multiline_checked"] is True
    assert report["chat_session_status_rendered"] is True
    assert report["chat_context_status_rendered"] is True
    assert report["chat_url_state_preserved_after_date_change"] is True
    assert report["chat_reload_preserved_selected_date"] is True
    assert report["chat_user_url_state_preserved_after_user_change"] is True
    assert report["chat_reload_preserved_user_id"] is True
    assert report["chat_scroll_behavior_checked"] is True
    assert report["chat_reload_scroll_behavior_checked"] is True
    assert report["chat_body_observation_same_truth_checked"] is True
    assert report["chat_body_observation_written"] is True
    assert report["chat_body_observation_body_page_readback"] is True
    assert report["chat_body_observation_values"]["assistant_text"] == (
        "Recorded weight 70.0 kg. Body plan was not changed."
    )
    assert f'{report["local_date"]} | 70 kg' in report["chat_body_observation_values"]["weight_history"]
    assert report["chat_body_observation_values"]["manager_call_count"] == 2
    assert report["chat_body_observation_non_claims"]["body_plan_mutated"] is False
    assert report["chat_body_observation_non_claims"]["ledger_updated"] is False
    assert report["chat_body_observation_non_claims"]["frontend_weight_parser_used"] is False
    assert report["today_previous_day_empty_checked"] is True
    assert report["today_current_day_restored_checked"] is True
    assert report["today_session_status_rendered"] is True
    assert report["today_url_state_preserved_after_date_change"] is True
    assert report["today_reload_preserved_selected_date"] is True
    assert report["today_user_url_state_preserved_after_user_change"] is True
    assert report["today_reload_preserved_user_id"] is True
    assert report["body_plan_readback_checked"] is True
    assert report["body_session_status_rendered"] is True
    assert report["body_plan_read_model_fields_rendered"] is True
    assert report["body_latest_weight_rendered_from_backend"] is True
    assert report["body_manual_target_read_model_rendered"] is True
    assert report["body_plan_read_model_values"]["daily_target"] == "1550 kcal"
    assert report["body_plan_read_model_values"]["tdee"] == "1819 kcal"
    assert report["body_plan_read_model_values"]["current_weight"] == "70 kg"
    assert report["body_plan_read_model_values"]["target_weight"] == "65 kg"
    assert report["body_plan_read_model_values"]["activity"] == "light"
    assert report["body_plan_read_model_values"]["goal"] == "Lose weight"
    assert f'{report["local_date"]} | 70.4 kg' in report["body_plan_read_model_values"]["weight_history"]
    assert report["body_budget_read_models_rendered"] is True
    assert report["body_budget_read_model_values"]["active_target"] == "1550 kcal"
    assert report["body_budget_read_model_values"]["consumed"] == "400 kcal"
    assert report["body_budget_read_model_values"]["remaining"] == "1150 kcal"
    assert report["body_budget_read_model_values"]["estimated_deficit"] == "269 kcal"
    assert report["body_budget_read_model_values"]["effective_budget"] == "1550 kcal"
    assert "400 kcal consumed" in report["body_budget_read_model_values"]["weekly_progress"]
    assert report["body_url_state_preserved_after_date_change"] is True
    assert report["body_reload_preserved_selected_date"] is True
    assert report["body_user_url_state_preserved_after_user_change"] is True
    assert report["body_reload_preserved_user_id"] is True
    assert report["today_manual_target_readback_checked"] is True
    assert report["nav_session_query_preserved"] is True
    db_path.unlink()


def test_ci_requires_product_pages_browser_execution() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "product-pages-browser-e2e" in workflow
    assert "python -m playwright install --with-deps chromium" in workflow
    assert "run_accurate_intake_product_pages_browser_smoke.py --require-browser-execution" in workflow
    assert "accurate_intake_product_pages_browser_smoke_ci.json" in workflow


def test_product_pages_browser_smoke_stays_out_of_fooddb_websearch_and_live_boundaries() -> None:
    source = Path("scripts/run_accurate_intake_product_pages_browser_smoke.py").read_text(encoding="utf-8")

    forbidden = [
        "app.providers",
        "tavily_adapter",
        "Tavily",
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "fooddb_evidence_used = True",
        "live_llm_invoked = True",
        "web_tavily_used = True",
    ]
    for fragment in forbidden:
        assert fragment not in source
