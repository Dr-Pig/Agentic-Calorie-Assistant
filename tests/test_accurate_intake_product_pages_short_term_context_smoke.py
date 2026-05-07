from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from scripts import run_accurate_intake_product_pages_short_term_context_smoke as module


def _passing_report() -> dict[str, object]:
    return {
        "local_date": "2026-05-05",
        "browser_executed": True,
        "browser_reload_checked": True,
        "fixture_manager_used": True,
        "pending_followup_created": True,
        "pending_followup_reloaded": True,
        "context_policy_version_present": True,
        "loaded_context_summary_present": True,
        "omitted_context_summary_present": True,
        "pending_pins_present_after_followup": True,
        "target_candidates_present_or_not_checked": "not_checked",
        "chat_history_context_fields_reloaded": True,
        "chat_context_status_ui_rendered": True,
        "chat_cjk_roundtrip_rendered": True,
        "assistant_followup_bubble_rendered": True,
        "assistant_commit_bubble_rendered": True,
        "today_same_day_meal_rendered": True,
        "today_summary_rendered": True,
        "product_pages_no_debug_trace": True,
        "frontend_semantic_owner": False,
        "deterministic_semantic_inference_used": False,
        "raw_text_intent_router_used": False,
        "mutation_authority": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "fooddb_evidence_used": False,
        "real_fooddb_pass_claimed": False,
        "dogfood_pass": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "browser": {
            "fetch_sequence": [
                {"url": "/accurate-intake/chat-history?user_id=short-term-context", "method": "GET"},
                {
                    "url": "/estimate",
                    "method": "POST",
                    "body": (
                        '{"text":"晚餐吃滷味","user_id":"short-term-context",'
                        '"local_date":"2026-05-05","allow_search":false}'
                    ),
                },
                {
                    "url": "/estimate",
                    "method": "POST",
                    "body": (
                        '{"text":"有豆干、海帶、貢丸","user_id":"short-term-context",'
                        '"local_date":"2026-05-05","allow_search":false}'
                    ),
                },
                {"url": "/accurate-intake/debug?user_id=short-term-context", "method": "GET"},
                {"url": "/today/current-budget?user_id=short-term-context", "method": "GET"},
            ],
        },
        "fake_provider_calls": [
            {
                "stage": "entry",
                "context_policy_version_present": True,
                "loaded_context_summary_present": True,
                "omitted_context_summary_present": True,
                "pending_followup_pin_present": False,
                "raw_user_input_used_for_fixture_selection": False,
            },
            {
                "stage": "execution_after_followup",
                "context_policy_version_present": True,
                "loaded_context_summary_present": True,
                "omitted_context_summary_present": True,
                "pending_followup_pin_present": True,
                "raw_user_input_used_for_fixture_selection": False,
            },
        ],
    }


def test_product_pages_short_term_context_smoke_missing_playwright_is_blocked_not_readiness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_short_term_context_smoke_report(
        db_path=tmp_path / "short-term-context.sqlite3",
    )

    assert report["smoke_id"] == "accurate_intake_product_pages_short_term_context_smoke_v1"
    assert report["status"] == "blocked"
    assert report["browser_executed"] is False
    assert report["browser_execution_required"] is False
    assert report["blockers"] == ["playwright_not_installed"]
    assert report["live_llm_invoked"] is False
    assert report["web_tavily_used"] is False
    assert report["product_readiness_claimed"] is False
    assert report["private_self_use_approved"] is False


def test_product_pages_short_term_context_smoke_can_require_browser_execution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_short_term_context_smoke_report(
        db_path=tmp_path / "short-term-context.sqlite3",
        require_browser_execution=True,
    )

    assert report["status"] == "fail"
    assert report["browser_execution_required"] is True
    assert report["browser_executed"] is False
    assert report["blockers"] == ["playwright_not_installed"]


def test_product_pages_short_term_context_validator_requires_context_and_reload_evidence() -> None:
    status, blockers = module._validate(_passing_report())

    assert status == "pass"
    assert blockers == []


def test_product_pages_short_term_context_validator_rejects_missing_context_support() -> None:
    report = _passing_report()
    report["pending_followup_created"] = False
    report["pending_followup_reloaded"] = False
    report["context_policy_version_present"] = False
    report["loaded_context_summary_present"] = False
    report["omitted_context_summary_present"] = False
    report["pending_pins_present_after_followup"] = False
    report["chat_history_context_fields_reloaded"] = False
    report["chat_context_status_ui_rendered"] = False
    report["fake_provider_calls"] = []

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "pending_followup_not_created" in blockers
    assert "pending_followup_not_reloaded" in blockers
    assert "context_policy_version_missing" in blockers
    assert "loaded_context_summary_missing" in blockers
    assert "omitted_context_summary_missing" in blockers
    assert "pending_pins_not_present_after_followup" in blockers
    assert "chat_history_context_fields_not_reloaded" in blockers
    assert "chat_context_status_ui_not_rendered" in blockers
    assert "fake_provider_context_input_not_proven" in blockers


def test_product_pages_short_term_context_validator_rejects_frontend_or_deterministic_semantics() -> None:
    report = _passing_report()
    report["frontend_semantic_owner"] = True
    report["deterministic_semantic_inference_used"] = True
    report["raw_text_intent_router_used"] = True
    report["mutation_authority"] = True
    report["fake_provider_calls"][0]["raw_user_input_used_for_fixture_selection"] = True

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "frontend_semantic_owner_claimed" in blockers
    assert "deterministic_semantic_inference_used" in blockers
    assert "raw_text_intent_router_used" in blockers
    assert "mutation_authority_claimed" in blockers
    assert "fake_provider_used_raw_user_input_for_fixture_selection" in blockers


def test_product_pages_short_term_context_validator_rejects_readiness_or_evidence_truth_claims() -> None:
    report = _passing_report()
    report["live_llm_invoked"] = True
    report["web_tavily_used"] = True
    report["fooddb_evidence_used"] = True
    report["real_fooddb_pass_claimed"] = True
    report["dogfood_pass"] = True
    report["web_readiness_claimed"] = True
    report["product_readiness_claimed"] = True
    report["private_self_use_approved"] = True

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "live_llm_invoked" in blockers
    assert "web_tavily_used" in blockers
    assert "fooddb_evidence_used" in blockers
    assert "real_fooddb_pass_claimed" in blockers
    assert "dogfood_pass_claimed" in blockers
    assert "web_readiness_claimed" in blockers
    assert "product_readiness_claimed" in blockers
    assert "private_self_use_approved" in blockers


def test_product_pages_short_term_context_validator_requires_fetches_and_product_rendering() -> None:
    report = _passing_report()
    report["chat_cjk_roundtrip_rendered"] = False
    report["assistant_followup_bubble_rendered"] = False
    report["assistant_commit_bubble_rendered"] = False
    report["today_same_day_meal_rendered"] = False
    report["today_summary_rendered"] = False
    report["product_pages_no_debug_trace"] = False
    report["browser"]["fetch_sequence"] = []

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "chat_cjk_roundtrip_not_rendered" in blockers
    assert "assistant_followup_bubble_not_rendered" in blockers
    assert "assistant_commit_bubble_not_rendered" in blockers
    assert "today_same_day_meal_not_rendered" in blockers
    assert "today_summary_not_rendered" in blockers
    assert "product_pages_debug_trace_leaked" in blockers
    assert "required_fetch_missing:/accurate-intake/chat-history" in blockers
    assert "required_fetch_missing:/estimate" in blockers
    assert "required_fetch_missing:/accurate-intake/debug" in blockers
    assert "required_fetch_missing:/today/current-budget" in blockers


def test_product_pages_short_term_context_validator_requires_two_browser_posts_with_selected_date() -> None:
    report = _passing_report()
    report["browser"]["fetch_sequence"] = [
        {"url": "/accurate-intake/chat-history?user_id=short-term-context", "method": "GET"},
        {
            "url": "/estimate",
            "method": "POST",
            "body": '{"text":"晚餐吃滷味","user_id":"short-term-context","allow_search":false}',
        },
        {"url": "/accurate-intake/debug?user_id=short-term-context", "method": "GET"},
        {"url": "/today/current-budget?user_id=short-term-context&local_date=2026-05-05", "method": "GET"},
    ]

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "estimate_post_missing:followup_answer" in blockers
    assert "estimate_post_missing_selected_local_date" in blockers


def test_product_pages_short_term_context_validator_rejects_stale_report_date() -> None:
    report = _passing_report()
    report["local_date"] = "2026-05-06"

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "estimate_post_missing_selected_local_date" in blockers


def test_short_term_context_fake_manager_treats_public_non_fooddb_tools_as_entry() -> None:
    provider = module._ShortTermContextManagerProvider()
    public_read_only_tools = [
        "app.answer_usage_question",
        "body.get_active_plan",
        "body.get_latest_observation",
        "budget.get_day_meal_log",
        "budget.get_remaining_calories",
        "budget.get_today_summary",
        "calibration.get_pending_proposal",
    ]

    decision, trace = asyncio.run(
        provider.complete_with_trace(
            user_payload={
                "available_tools": public_read_only_tools,
                "round_index": 0,
                "raw_user_input": "晚餐吃滷味",
                "manager_context_packet_v1": {
                    "metadata": {"context_policy_version": "accurate_intake_mvp_context_policy_v1"},
                    "context_loading_artifact": {
                        "loaded_context_summary": {"recent_chat_messages": 0},
                        "omitted_context_summary": {
                            "policy_excluded_context_ids": [
                                "debug_artifacts",
                                "dogfood_review_artifacts",
                                "food_gap_candidates",
                            ]
                        },
                    },
                    "hard_pins": {},
                    "target_candidates": {},
                },
            }
        )
    )

    assert provider.calls[0]["stage"] == "entry"
    assert decision["semantic_decision"]["final_action_candidate"] == "route_to_intake"
    assert trace["stage"] == "entry"
