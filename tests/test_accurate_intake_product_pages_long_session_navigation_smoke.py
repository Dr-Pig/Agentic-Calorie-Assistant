from __future__ import annotations

from pathlib import Path

from scripts import run_accurate_intake_product_pages_long_session_navigation_smoke as module


def _passing_report() -> dict[str, object]:
    message_count = 32
    return {
        "browser_executed": True,
        "message_count_requested": message_count,
        "long_session_message_count": message_count,
        "first_cjk_message_rendered": True,
        "middle_cjk_message_rendered": True,
        "last_cjk_message_rendered": True,
        "chat_scroll_overflow_checked": True,
        "chat_scroll_bottom_checked": True,
        "reload_preserved_long_history": True,
        "click_chat_to_today_preserved_session": True,
        "click_today_to_body_preserved_session": True,
        "click_body_to_chat_preserved_session": True,
        "chat_return_preserved_latest_message": True,
        "navigation_fetch_sequence_checked": True,
        "forbidden_storage_used": False,
        "visible_debug_trace_leaked": False,
        "frontend_semantic_owner": False,
        "live_llm_invoked": False,
        "web_tavily_used": False,
        "production_db_used": False,
        "web_readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "fetch_sequence": [
            {"url": "/accurate-intake/chat-history?user_id=u", "method": "GET"},
            *[
                {"url": "/estimate", "method": "POST", "body": '{"allow_search": false}'}
                for _ in range(message_count)
            ],
            {"url": "/today/current-budget?user_id=u", "method": "GET"},
            {"url": "/body-plan/active?user_id=u", "method": "GET"},
        ],
    }


def test_long_session_navigation_validator_accepts_full_browser_evidence() -> None:
    status, blockers = module._validate(_passing_report())

    assert status == "pass"
    assert blockers == []


def test_long_session_navigation_missing_playwright_is_blocked_not_readiness(
    monkeypatch,
    tmp_path: Path,
) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_long_session_navigation_smoke_report(
        db_path=tmp_path / "long-session.sqlite3",
    )

    assert report["status"] == "blocked"
    assert report["browser_executed"] is False
    assert report["browser_execution_required"] is False
    assert report["web_readiness_claimed"] is False
    assert report["product_readiness_claimed"] is False
    assert report["private_self_use_approved"] is False
    assert report["live_llm_invoked"] is False
    assert report["web_tavily_used"] is False


def test_long_session_navigation_can_require_browser_execution(monkeypatch, tmp_path: Path) -> None:
    def missing_playwright() -> object:
        raise module.BrowserSmokeDependencyMissing("playwright_not_installed")

    monkeypatch.setattr(module, "_load_sync_playwright", missing_playwright)

    report = module.build_product_pages_long_session_navigation_smoke_report(
        db_path=tmp_path / "long-session.sqlite3",
        require_browser_execution=True,
    )

    assert report["status"] == "fail"
    assert report["browser_execution_required"] is True
    assert report["blockers"] == ["playwright_not_installed"]


def test_long_session_navigation_validator_rejects_shallow_or_broken_navigation() -> None:
    report = _passing_report()
    report["long_session_message_count"] = 4
    report["first_cjk_message_rendered"] = False
    report["chat_scroll_bottom_checked"] = False
    report["reload_preserved_long_history"] = False
    report["click_chat_to_today_preserved_session"] = False
    report["click_today_to_body_preserved_session"] = False
    report["click_body_to_chat_preserved_session"] = False
    report["chat_return_preserved_latest_message"] = False
    report["navigation_fetch_sequence_checked"] = False

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "long_session_message_count_too_low" in blockers
    assert "first_cjk_message_not_rendered" in blockers
    assert "chat_scroll_bottom_not_checked" in blockers
    assert "reload_did_not_preserve_long_history" in blockers
    assert "chat_to_today_session_not_preserved" in blockers
    assert "today_to_body_session_not_preserved" in blockers
    assert "body_to_chat_session_not_preserved" in blockers
    assert "chat_return_latest_message_missing" in blockers
    assert "navigation_fetch_sequence_not_checked" in blockers


def test_long_session_navigation_validator_rejects_semantic_or_readiness_overclaims() -> None:
    report = _passing_report()
    report["frontend_semantic_owner"] = True
    report["live_llm_invoked"] = True
    report["web_tavily_used"] = True
    report["product_readiness_claimed"] = True
    report["private_self_use_approved"] = True
    report["fetch_sequence"] = [{"url": "/estimate", "method": "POST", "body": '{"allow_search": true}'}]

    status, blockers = module._validate(report)

    assert status == "fail"
    assert "frontend_semantic_owner" in blockers
    assert "live_llm_invoked" in blockers
    assert "web_tavily_used" in blockers
    assert "product_readiness_claimed" in blockers
    assert "private_self_use_approved" in blockers
    assert "estimate_post_count_too_low" in blockers
    assert "estimate_allow_search_not_false" in blockers


def test_long_session_navigation_source_stays_out_of_truth_and_provider_boundaries() -> None:
    source = Path(
        "scripts/run_accurate_intake_product_pages_long_session_navigation_smoke.py"
    ).read_text(encoding="utf-8")

    for fragment in (
        "NutritionEvidenceStorePort",
        "FoodEvidenceRecord",
        "PacketReadyAnchor",
        "TavilyClient",
        "BuilderSpaceAdapter",
        "requests",
        "httpx",
        "ready_for_live_diagnostic_decision = True",
        "fooddb_evidence_used = True",
    ):
        assert fragment not in source


def test_ci_keeps_long_session_navigation_smoke_out_of_required_merge_path() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "product-pages-browser-e2e" in workflow
    assert "run_accurate_intake_product_pages_long_session_navigation_smoke.py" not in workflow
    assert "accurate_intake_product_pages_long_session_navigation_smoke_ci.json" not in workflow
